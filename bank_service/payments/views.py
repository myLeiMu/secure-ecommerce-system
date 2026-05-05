import secrets
import time
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import BankAccount, PaymentTransaction
from .security import create_result_envelope, get_merchant_public_key, is_timestamp_fresh, verify_params


REQUIRED_PAY_FIELDS = ("order_no", "amount", "merchant_id", "timestamp", "signature")

PAY_QUERY_PARAMETERS = [
    openapi.Parameter("order_no", openapi.IN_QUERY, description="订单号", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("amount", openapi.IN_QUERY, description="支付金额", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("merchant_id", openapi.IN_QUERY, description="商户 ID", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("timestamp", openapi.IN_QUERY, description="Unix 秒级时间戳，5 分钟内有效", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("signature", openapi.IN_QUERY, description="商户 SM2 签名", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("return_url", openapi.IN_QUERY, description="可选：同步跳转地址", type=openapi.TYPE_STRING),
    openapi.Parameter("callback_url", openapi.IN_QUERY, description="可选：异步回调地址", type=openapi.TYPE_STRING),
    openapi.Parameter("account_number", openapi.IN_QUERY, description="已绑定银行卡号", type=openapi.TYPE_STRING),
]

PAY_PROCESS_FORM_PARAMETERS = [
    openapi.Parameter("order_no", openapi.IN_FORM, description="订单号", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("amount", openapi.IN_FORM, description="支付金额", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("merchant_id", openapi.IN_FORM, description="商户 ID", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("timestamp", openapi.IN_FORM, description="Unix 秒级时间戳，5 分钟内有效", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("signature", openapi.IN_FORM, description="商户 SM2 签名", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("account_number", openapi.IN_FORM, description="付款银行卡号", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("pay_password", openapi.IN_FORM, description="支付密码", type=openapi.TYPE_STRING, required=True),
    openapi.Parameter("return_url", openapi.IN_FORM, description="可选：同步跳转地址", type=openapi.TYPE_STRING),
    openapi.Parameter("callback_url", openapi.IN_FORM, description="可选：异步回调地址", type=openapi.TYPE_STRING),
]


def _merchant_callback_url(merchant_id: str, override_url: str = "") -> str:
    return override_url or settings.BANK_MERCHANT_CALLBACK_URLS.get(merchant_id, "")


def _result_params(payment: PaymentTransaction) -> dict:
    return {
        "transaction_id": payment.transaction_id,
        "encrypted_key": payment.result_payload.get("encrypted_key", ""),
        "iv": payment.result_payload.get("iv", ""),
        "data": payment.result_payload.get("data", ""),
    }


def _build_result_url(request, payment: PaymentTransaction) -> str:
    base_url = payment.return_url or request.build_absolute_uri(reverse("pay-result"))
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{urlencode(_result_params(payment))}"


def _send_callback(payment: PaymentTransaction) -> None:
    if not payment.callback_url:
        payment.callback_status = "skipped"
        payment.callback_response = "callback_url not configured"
        return

    try:
        response = requests.post(payment.callback_url, json=_result_params(payment), timeout=5)
        payment.callback_status = "success" if 200 <= response.status_code < 300 else "failed"
        payment.callback_response = f"{response.status_code} {response.text[:500]}"
    except requests.RequestException as exc:
        payment.callback_status = "failed"
        payment.callback_response = str(exc)


def _validate_pay_request(params):
    missing = [field for field in REQUIRED_PAY_FIELDS if not params.get(field)]
    if missing:
        return False, f"缺少参数: {', '.join(missing)}"

    try:
        amount = Decimal(params["amount"]).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return False, "金额格式不正确"
    if amount <= 0:
        return False, "金额必须大于 0"

    public_key = get_merchant_public_key(params["merchant_id"])
    if not public_key:
        return False, "未知商户或商户公钥未配置"

    if not verify_params(params, public_key, params.get("signature")):
        return False, "支付请求 SM2 签名校验失败"

    if not is_timestamp_fresh(params.get("timestamp")):
        return False, "支付请求已过期，请重新发起支付"

    return True, ""


@swagger_auto_schema(
    method="get",
    operation_summary="展示银行支付页面",
    operation_description="接收电商订单支付参数，用商户公钥验 SM2 签名，并检查时间戳是否在 5 分钟有效期内。",
    manual_parameters=PAY_QUERY_PARAMETERS,
    responses={200: "HTML 支付页面"},
    tags=["支付"],
)
@api_view(["GET"])
def pay_page(request):
    params = request.GET.dict()
    is_valid, error = _validate_pay_request(params)
    bound_account_number = params.get("account_number", "").strip()
    accounts = BankAccount.objects.filter(is_active=True)
    if bound_account_number:
        accounts = accounts.filter(account_number=bound_account_number)
        if is_valid and not accounts.exists():
            is_valid = False
            error = "绑定银行卡在银行侧不存在或已停用"
    accounts = accounts.order_by("account_number")
    return render(request, "payments/pay.html", {"params": params, "is_valid": is_valid, "error": error, "accounts": accounts})


@swagger_auto_schema(
    method="post",
    operation_summary="处理银行支付请求",
    operation_description="验签、检查时间戳、扣款，生成 SM4+SM2 数字信封，同步跳转并异步 POST 回调电商后端。",
    manual_parameters=PAY_PROCESS_FORM_PARAMETERS,
    responses={302: "重定向到支付结果地址"},
    tags=["支付"],
)
@api_view(["POST"])
@parser_classes([FormParser, MultiPartParser])
def process_payment(request):
    params = {field: request.POST.get(field, "") for field in REQUIRED_PAY_FIELDS}
    params["return_url"] = request.POST.get("return_url", "")
    params["callback_url"] = request.POST.get("callback_url", "")
    params["bound_account_number"] = request.POST.get("bound_account_number", "")
    is_valid, error = _validate_pay_request(params)
    account_number = request.POST.get("account_number", "").strip()
    pay_password = request.POST.get("pay_password", "")
    amount = Decimal(params["amount"]).quantize(Decimal("0.01")) if params.get("amount") else Decimal("0.00")

    payment = PaymentTransaction.objects.create(
        transaction_id=f"BNK{timezone.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(4).upper()}",
        order_no=params.get("order_no", ""),
        merchant_id=params.get("merchant_id", ""),
        amount=amount,
        account_number=account_number,
        return_url=params.get("return_url", ""),
        callback_url=_merchant_callback_url(params.get("merchant_id", ""), params.get("callback_url", "")),
        request_payload=params,
    )

    status = PaymentTransaction.STATUS_FAILED
    message = error

    if is_valid:
        if not account_number or not pay_password:
            message = "请输入银行卡号和支付密码"
        elif params.get("bound_account_number") and account_number != params["bound_account_number"]:
            message = "付款账户必须使用电商已绑定银行卡"
        else:
            with transaction.atomic():
                account = BankAccount.objects.select_for_update().filter(account_number=account_number).first()
                if not account or not account.is_active:
                    message = "银行卡不存在或已停用"
                elif account.pay_password != pay_password:
                    message = "支付密码错误"
                elif account.balance < amount:
                    message = "账户余额不足"
                else:
                    account.balance -= amount
                    account.save(update_fields=["balance", "updated_at"])
                    status = PaymentTransaction.STATUS_SUCCESS
                    message = "支付成功"
                    payment.paid_at = timezone.now()

    result_plaintext = {
        "order_no": payment.order_no,
        "status": status,
        "reason": message if status == PaymentTransaction.STATUS_FAILED else "",
        "bank_transaction_id": payment.transaction_id,
        "timestamp": str(int(time.time())),
    }
    merchant_public_key = get_merchant_public_key(payment.merchant_id)
    envelope = (
        create_result_envelope(result_plaintext, merchant_public_key)
        if merchant_public_key
        else {"encrypted_key": "", "iv": "", "data": ""}
    )

    payment.status = status
    payment.message = message
    payment.result_payload = envelope
    payment.encrypted_result = envelope["data"]
    if merchant_public_key:
        _send_callback(payment)
    else:
        payment.callback_status = "skipped"
        payment.callback_response = "merchant public key not configured"
    payment.save(
        update_fields=[
            "status",
            "message",
            "result_payload",
            "encrypted_result",
            "callback_status",
            "callback_response",
            "paid_at",
        ]
    )
    return redirect(_build_result_url(request, payment))


@swagger_auto_schema(
    method="post",
    operation_summary="银行退款",
    operation_description="按原银行交易流水号退款到原付款账户，供电商取消已支付订单时调用。",
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["transaction_id"],
        properties={
            "transaction_id": openapi.Schema(type=openapi.TYPE_STRING, description="原银行交易流水号"),
            "order_no": openapi.Schema(type=openapi.TYPE_STRING, description="订单号"),
            "amount": openapi.Schema(type=openapi.TYPE_STRING, description="退款金额"),
        },
    ),
    responses={200: "JSON"},
    tags=["退款"],
)
@api_view(["POST"])
def refund_payment(request):
    transaction_id = request.data.get("transaction_id", "")
    order_no = request.data.get("order_no", "")
    amount_value = request.data.get("amount", "")
    if not transaction_id:
        return Response({"code": 400, "message": "缺少 transaction_id", "data": None}, status=400)

    with transaction.atomic():
        payment = PaymentTransaction.objects.select_for_update().filter(transaction_id=transaction_id).first()
        if not payment:
            return Response({"code": 404, "message": "原支付交易不存在", "data": None}, status=404)
        if order_no and payment.order_no != order_no:
            return Response({"code": 400, "message": "订单号与原交易不一致", "data": None}, status=400)
        if payment.status == PaymentTransaction.STATUS_REFUNDED:
            return Response({
                "code": 0,
                "message": "该交易已退款",
                "data": {"transaction_id": payment.transaction_id, "refunded": True},
            })
        if payment.status != PaymentTransaction.STATUS_SUCCESS:
            return Response({"code": 400, "message": "只有支付成功交易可以退款", "data": None}, status=400)

        refund_amount = payment.amount
        if amount_value:
            try:
                refund_amount = Decimal(str(amount_value)).quantize(Decimal("0.01"))
            except (InvalidOperation, TypeError):
                return Response({"code": 400, "message": "退款金额格式不正确", "data": None}, status=400)
        if refund_amount != payment.amount:
            return Response({"code": 400, "message": "模拟银行仅支持全额退款", "data": None}, status=400)

        account = BankAccount.objects.select_for_update().filter(account_number=payment.account_number).first()
        if not account:
            return Response({"code": 404, "message": "原付款账户不存在", "data": None}, status=404)
        account.balance += refund_amount
        account.save(update_fields=["balance", "updated_at"])
        payment.status = PaymentTransaction.STATUS_REFUNDED
        payment.message = "已退款"
        payment.save(update_fields=["status", "message", "updated_at"])

    return Response({
        "code": 0,
        "message": "退款成功",
        "data": {
            "transaction_id": payment.transaction_id,
            "order_no": payment.order_no,
            "account_number": payment.account_number,
            "amount": str(refund_amount),
            "balance": str(account.balance),
        },
    })


@swagger_auto_schema(
    method="get",
    operation_summary="展示银行侧支付结果",
    manual_parameters=[
        openapi.Parameter("transaction_id", openapi.IN_QUERY, description="银行交易号", type=openapi.TYPE_STRING, required=True),
        openapi.Parameter("encrypted_key", openapi.IN_QUERY, description="SM2 加密后的 SM4 密钥", type=openapi.TYPE_STRING),
        openapi.Parameter("iv", openapi.IN_QUERY, description="SM4-CBC IV", type=openapi.TYPE_STRING),
        openapi.Parameter("data", openapi.IN_QUERY, description="SM4 加密后的支付结果正文", type=openapi.TYPE_STRING),
    ],
    responses={200: "HTML 支付结果页", 404: "交易不存在"},
    tags=["支付"],
)
@api_view(["GET"])
def payment_result(request):
    transaction_id = request.GET.get("transaction_id", "")
    payment = get_object_or_404(PaymentTransaction, transaction_id=transaction_id)
    return render(request, "payments/result.html", {"payment": payment})

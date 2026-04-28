import json
import requests
import time


"""
python api_service/tests/week7_8_acceptance_demo.py
"""

BASE_URL = "http://127.0.0.1:8080/api"
TOKEN_A = "eyJhbGciOiJIU00zIiwidHlwIjoiSldUIn0.eyJ1c2VyX2lkIjo4OTAzLCJ1c2VybmFtZSI6InRlc3R1c2VyMyIsInJvbGUiOiJub3JtYWwiLCJpYXQiOjE3NzY5MTQwOTAsImV4cCI6MTc3NzAwMDQ5MCwiaXNzIjoiZWNvbW1lcmNlLXN5c3RlbSIsImp0aSI6InFyWEloMjllRGxCYVdKZ01kb2RWRmcifQ.6rhYrX2jSqmpTW2ThmpNv2gD7HtBvBzaclOVXjpxMVY"  # 用户A JWT
TOKEN_B = "eyJhbGciOiJIU00zIiwidHlwIjoiSldUIn0.eyJ1c2VyX2lkIjo4OTA4LCJ1c2VybmFtZSI6InRlc3R1c2VyNCIsInJvbGUiOiJub3JtYWwiLCJpYXQiOjE3NzY5MTQ4NjUsImV4cCI6MTc3NzAwMTI2NSwiaXNzIjoiZWNvbW1lcmNlLXN5c3RlbSIsImp0aSI6Ikx6UHJ5WE9tT3BteDVTeS11Y1RCY2cifQ.P7DKQuhqYyEBXwEl5Ovl_uG7Q8tC6VwjjtnWNqlJhPE"  # 用户B JWT


def _banner(title: str):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def _step(name: str):
    print(f"\n[STEP] {name}")


def _ok(name: str, detail: str = ""):
    print(f"  [PASS] {name}" + (f" | {detail}" if detail else ""))


def _headers(token: str):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, token: str = "", data=None):
    url = f"{BASE_URL}{path}"
    kwargs = {}
    if token:
        kwargs["headers"] = _headers(token)
    if data is not None:
        kwargs["data"] = json.dumps(data, ensure_ascii=False)
    resp = requests.request(method, url, timeout=15, **kwargs)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}
    return resp.status_code, body


def must(cond: bool, message: str):
    if not cond:
        raise AssertionError(message)


def _pick_category_id() -> int:
    status, body = _request("GET", "/categories")
    must(status == 200 and body.get("code") == 0, f"获取分类失败: {status} {body}")
    data = body.get("data") or []
    if not data:
        raise AssertionError("分类为空，请先初始化分类数据")
    return data[0]["category_id"]


def _extract_product_ids_from_cart(cart_data):
    if isinstance(cart_data, list):
        items = cart_data
    elif isinstance(cart_data, dict):
        items = cart_data.get("items") or cart_data.get("cart_items") or []
    else:
        items = []

    product_ids = []
    for item in items:
        pid = item.get("product_id")
        if pid is None and isinstance(item.get("product"), dict):
            pid = item["product"].get("product_id")
        if pid is not None:
            product_ids.append(int(pid))
    return sorted(set(product_ids))


def _clear_cart(token: str):
    status, body = _request("GET", "/cart", token)
    must(status == 200 and body.get("code") == 0, f"读取购物车失败: {status} {body}")

    product_ids = _extract_product_ids_from_cart(body.get("data"))
    if not product_ids:
        _ok("清空购物车", "购物车本来就是空")
        return

    deleted = 0
    for pid in product_ids:
        d_status, d_body = _request("DELETE", f"/cart/items/{pid}", token)
        must(d_status == 200 and d_body.get("code") == 0, f"清空购物车失败(product_id={pid}): {d_status} {d_body}")
        deleted += 1
    _ok("清空购物车", f"删除{deleted}个历史商品")


def run_idor_only():
    must(TOKEN_A and TOKEN_B, "请先填入 TOKEN_A 和 TOKEN_B")
    _banner("IDOR 专项验收")
    category_id = _pick_category_id()
    sku = f"W78-DEMO-{int(time.time() * 1000)}"
    _ok("环境检查", f"BASE_URL={BASE_URL}")
    _ok("分类获取", f"category_id={category_id}")
    _clear_cart(TOKEN_A)

    _step("准备数据：A发布演示商品")
    status, body = _request("POST", "/products", TOKEN_A, {
        "sku": sku,
        "product_name": "IDOR演示商品",
        "description": "仅用于IDOR验收",
        "sale_price": "99.00",
        "stock_quantity": 10,
        "category_id": category_id,
        "image_urls": [],
        "specifications": {"idor_demo": True}
    })
    must(status == 200 and body.get("code") == 0, f"商品发布失败: {status} {body}")
    product_id = body["data"]["product_id"]
    _ok("商品发布", f"product_id={product_id}")

    _step("准备数据：A加入购物车并下单")
    status, body = _request("POST", "/cart", TOKEN_A, {"product_id": product_id, "quantity": 1})
    must(status == 200 and body.get("code") == 0, f"添加购物车失败: {status} {body}")
    _ok("A加入购物车", f"status={status}")
    status, body = _request("POST", "/orders", TOKEN_A, {"shipping_amount": "0.00", "discount_amount": "0.00"})
    must(status == 200 and body.get("code") == 0, f"下单失败: {status} {body}")
    order_id = body["data"]["order_id"]
    _ok("A创建订单", f"order_id={order_id}")

    _step("准备数据：A再加一次购物车（供B越权修改测试）")
    status, body = _request("POST", "/cart", TOKEN_A, {"product_id": product_id, "quantity": 1})
    must(status == 200 and body.get("code") == 0, f"重新添加购物车失败: {status} {body}")
    _ok("A重新加入购物车", f"status={status}")

    _banner("IDOR 验证")
    _step("IDOR-1：B修改A购物车（预期 403）")
    status, body = _request("PUT", f"/cart/items/{product_id}", TOKEN_B, {"quantity": 1})
    must(status == 403, f"IDOR防护失败(购物车修改)，返回: {status} {body}")
    _ok("IDOR-1通过", "actual=403")

    _step("IDOR-2：B编辑A商品（预期 403）")
    status, body = _request("PUT", f"/products/{product_id}", TOKEN_B, {
        "product_name": "非法修改",
        "sale_price": "1.00",
        "stock_quantity": 1,
        "category_id": category_id
    })
    must(status == 403, f"IDOR防护失败(商品编辑)，返回: {status} {body}")
    _ok("IDOR-2通过", "actual=403")

    _step("IDOR-3：B查看A订单详情（预期 403/404）")
    status, body = _request("GET", f"/orders/{order_id}", TOKEN_B)
    must(status in (403, 404), f"IDOR防护失败(查看订单)，返回: {status} {body}")
    _ok("IDOR-3通过", f"actual={status}")

    _step("IDOR-4：B取消A订单（预期 403）")
    status, body = _request("POST", f"/orders/{order_id}/cancel", TOKEN_B)
    must(status == 403, f"IDOR防护失败(取消订单)，返回: {status} {body}")
    _ok("IDOR-4通过", "actual=403")

    _banner("验收结果汇总")
    print(f"[RESULT] product_id = {product_id}")
    print(f"[RESULT] order_id   = {order_id}")
    print("[RESULT] 用例通过   = 4/4")
    print("[RESULT] 结论       = IDOR专项验收通过")


if __name__ == "__main__":
    run_idor_only()

from django.urls import path

from . import views


urlpatterns = [
    path("pay", views.pay_page, name="pay-page"),
    path("pay/process", views.process_payment, name="pay-process"),
    path("pay/result", views.payment_result, name="pay-result"),
    path("api/refund", views.refund_payment, name="refund-payment"),
]

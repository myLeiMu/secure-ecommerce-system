import time
from urllib.parse import urlencode

from django.core.management.base import BaseCommand
from django.urls import reverse

from payments.security import canonical_string, get_merchant_private_key, sign_params, sm3_hash_text


class Command(BaseCommand):
    help = "Print a signed mock bank payment URL."

    def add_arguments(self, parser):
        parser.add_argument("--order-no", required=True)
        parser.add_argument("--amount", required=True)
        parser.add_argument("--merchant-id", default="ECOMMERCE_DEMO")
        parser.add_argument("--bank-base-url", default="http://127.0.0.1:8000")
        parser.add_argument("--return-url", default="")
        parser.add_argument("--callback-url", default="")

    def handle(self, *args, **options):
        private_key = get_merchant_private_key(options["merchant_id"])
        if not private_key:
            raise SystemExit(f"Unknown merchant_id or missing private key: {options['merchant_id']}")

        params = {
            "order_no": options["order_no"],
            "amount": options["amount"],
            "merchant_id": options["merchant_id"],
            "timestamp": str(int(time.time())),
        }
        if options["return_url"]:
            params["return_url"] = options["return_url"]
        if options["callback_url"]:
            params["callback_url"] = options["callback_url"]

        params["signature"] = sign_params(params, private_key)
        url = f"{options['bank_base_url']}{reverse('pay-page')}?{urlencode(params)}"
        self.stdout.write(f"signing_text: {canonical_string(params)}")
        self.stdout.write(f"sm3: {sm3_hash_text(canonical_string(params))}")
        self.stdout.write(url)

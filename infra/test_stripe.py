import stripe
import os
import sys

# Get key from ../backend/.env
with open("../backend/.env") as f:
    for line in f:
        if line.startswith("STRIPE_SECRET_KEY"):
            stripe.api_key = line.split("=")[1].strip()
            
intent = stripe.PaymentIntent.create(
    amount=1000,
    currency="usd",
    payment_method="pm_card_visa",
    confirm=True,
    automatic_payment_methods={"enabled": True, "allow_redirects": "never"}
)
print("Intent status:", intent.status)

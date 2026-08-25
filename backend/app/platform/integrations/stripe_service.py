import time
# pyrefly: ignore [missing-import]
import stripe
from typing import Dict, Any, Optional
from app.platform.core.config import settings
from app.platform.observability.logging import logger
from app.platform.observability.metrics import stripe_api_latency_seconds
from app.platform.observability.tracing import get_tracer

class StripeService:
    """
    Service wrapper for Stripe API interactions.
    Handles Test Mode API keys, creating PaymentIntents, and verifying webhooks.
    """
    
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
        
    def create_payment_intent(self, amount: float, currency: str, idempotency_key: str, metadata: Optional[Dict[str, str]] = None, payment_method: str = "pm_card_visa") -> stripe.PaymentIntent:
        """
        Creates a Stripe PaymentIntent.
        
        Args:
            amount: The float amount (e.g., 100.50). This will be converted to cents for Stripe.
            currency: e.g., 'usd'
            idempotency_key: Passed directly to Stripe to prevent double charges on retries.
            metadata: Custom key-value pairs (like our internal transaction_id) to attach.
        """
        # Stripe requires amounts in the smallest currency unit (e.g., cents)
        amount_in_cents = int(amount * 100)
        
        start_time = time.perf_counter()
        tracer = get_tracer()
        
        try:
            if tracer:
                with tracer.start_as_current_span("stripe.create_payment_intent") as span:
                    span.set_attribute("stripe.amount_cents", amount_in_cents)
                    span.set_attribute("stripe.currency", currency.lower())
                    intent = stripe.PaymentIntent.create(
                        amount=amount_in_cents,
                        currency=currency.lower(),
                        metadata=metadata or {},
                        idempotency_key=idempotency_key,
                        # Auto-confirm with test card so we don't need manual CLI confirmation
                        payment_method=payment_method,
                        confirm=True,
                        automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                        return_url=f"{settings.PUBLIC_BASE_URL}/success"
                    )
                    span.set_attribute("stripe.intent_id", intent.id)
            else:
                intent = stripe.PaymentIntent.create(
                    amount=amount_in_cents,
                    currency=currency.lower(),
                    metadata=metadata or {},
                    idempotency_key=idempotency_key,
                    payment_method=payment_method,
                    confirm=True,
                    automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
                    return_url=f"{settings.PUBLIC_BASE_URL}/success"
                )
            
            # Record Stripe API latency
            stripe_api_latency_seconds.labels(
                node_id=settings.NODE_ID, operation="create_payment_intent"
            ).observe(time.perf_counter() - start_time)
            
            logger.info(f"Created & Confirmed Stripe PaymentIntent: {intent.id} for amount {amount} {currency}")
            return intent
        except stripe.error.StripeError as e:
            # Still record latency on failures
            stripe_api_latency_seconds.labels(
                node_id=settings.NODE_ID, operation="create_payment_intent"
            ).observe(time.perf_counter() - start_time)
            logger.error(f"Stripe API error during PaymentIntent creation: {e}")
            raise

    def construct_webhook_event(self, payload: bytes, sig_header: str) -> stripe.Event:
        """
        Verifies the signature of the incoming webhook and parses it into a Stripe Event object.
        This is critical for security to ensure the webhook genuinely came from Stripe and 
        isn't a replay attack.
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError as e:
            logger.error("Invalid payload in Stripe webhook")
            raise e
        except stripe.error.SignatureVerificationError as e:
            logger.error("Invalid signature in Stripe webhook")
            raise e

    def create_payout(self, amount: float, currency: str, idempotency_key: str, metadata: Optional[Dict[str, str]] = None) -> stripe.Payout:
        """
        Creates a Stripe Payout to send funds to a user's bank account.
        """
        amount_in_cents = int(amount * 100)
        
        start_time = time.perf_counter()
        tracer = get_tracer()
        
        try:
            if tracer:
                with tracer.start_as_current_span("stripe.create_payout") as span:
                    span.set_attribute("stripe.amount_cents", amount_in_cents)
                    span.set_attribute("stripe.currency", currency.lower())
                    # Requires a connected account or external bank account setup.
                    # For test mode, we just create a standard payout.
                    payout = stripe.Payout.create(
                        amount=amount_in_cents,
                        currency=currency.lower(),
                        metadata=metadata or {},
                        idempotency_key=idempotency_key,
                    )
                    span.set_attribute("stripe.payout_id", payout.id)
            else:
                payout = stripe.Payout.create(
                    amount=amount_in_cents,
                    currency=currency.lower(),
                    metadata=metadata or {},
                    idempotency_key=idempotency_key,
                )
            
            stripe_api_latency_seconds.labels(
                node_id=settings.NODE_ID, operation="create_payout"
            ).observe(time.perf_counter() - start_time)
            
            logger.info(f"Created Stripe Payout: {payout.id} for amount {amount} {currency}")
            return payout
        except stripe.error.StripeError as e:
            stripe_api_latency_seconds.labels(
                node_id=settings.NODE_ID, operation="create_payout"
            ).observe(time.perf_counter() - start_time)
            logger.error(f"Stripe API error during Payout creation: {e}")
            raise

# Singleton instance
stripe_service = StripeService()

# app.py — DriftGuard test fixture (do not fix: intentional usages)
import stripe

stripe.api_key = "sk_test_demo"

# Legacy flow: Charges API
charge = stripe.charges.create(amount=1000, currency="eur", source="tok_visa")
existing = stripe.charges.retrieve("ch_123456")

# Model shut down by OpenAI
MODEL = "text-davinci-003"

# Usage inside a comment — detected but flagged in_comment
# stripe.sources.create(card="tok_visa")

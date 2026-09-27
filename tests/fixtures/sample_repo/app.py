# app.py — fixture de test DriftGuard (ne pas corriger : usages volontaires)
import stripe

stripe.api_key = "sk_test_demo"

# Ancien flux : API Charges (dépréciée par Stripe)
charge = stripe.charges.create(amount=1000, currency="eur", source="tok_visa")
existing = stripe.charges.retrieve("ch_123456")

# Modèle retiré du service par OpenAI
MODEL = "text-davinci-003"

# Usage dans un commentaire — détecté mais marqué in_comment
# stripe.sources.create(card="tok_visa")

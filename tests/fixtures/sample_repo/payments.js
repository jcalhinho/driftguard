// payments.js — fixture de test DriftGuard
const stripe = require('stripe')('sk_test_demo');

const charge = await stripe.charges.create({ amount: 1000, currency: 'eur' });

// L'API RTM est dépréciée par Slack (voir migration)
rtm.start({ token: 'xoxb-demo' });

// payments.js — DriftGuard test fixture
const stripe = require('stripe')('sk_test_demo');

const charge = await stripe.charges.create({ amount: 1000, currency: 'eur' });

// Slack RTM and legacy file upload
rtm.start({ token: 'xoxb-demo' });
await client.files.upload({ channels: '#general', file });

# -*- coding: utf-8 -*-

# N-Genius API base URLs
# Sandbox: used when provider state == 'test'
# Production: used when provider state == 'enabled'
API_BASE_URLS = {
    'test': 'https://api-gateway.sandbox.ngenius-payments.com',
    'enabled': 'https://api-gateway.ngenius-payments.com',
}

# Authentication endpoint (relative path)
AUTH_ENDPOINT = '/identity/auth/access-token'

# Order creation endpoint template (relative path); format with outlet_id
ORDERS_ENDPOINT = '/transactions/outlets/{outlet_id}/orders'

# Order retrieval endpoint template (relative path); format with outlet_id and order_ref
ORDER_STATUS_ENDPOINT = '/transactions/outlets/{outlet_id}/orders/{order_ref}'

# Currency codes supported by N-Genius (ISO 4217).
# N-Genius primarily serves the GCC/MENA region.
SUPPORTED_CURRENCIES = [
    'AED',  # UAE Dirham
    'SAR',  # Saudi Riyal
    'BHD',  # Bahraini Dinar
    'KWD',  # Kuwaiti Dinar
    'OMR',  # Omani Rial
    'QAR',  # Qatari Riyal
    'EGP',  # Egyptian Pound
    'JOD',  # Jordanian Dinar
    'USD',  # US Dollar
    'EUR',  # Euro
    'GBP',  # British Pound
]

# Currencies where the minor unit is NOT 2 decimal places (ISO 4217 non-standard decimals).
# These currencies require amount in their lowest unit without the standard *100 multiplication.
# BHD, KWD, OMR, JOD all have 3 decimal places → multiply by 1000.
CURRENCY_MINOR_UNIT = {
    'AED': 2,
    'SAR': 2,
    'BHD': 3,
    'KWD': 3,
    'OMR': 3,
    'QAR': 2,
    'EGP': 2,
    'JOD': 3,
    'USD': 2,
    'EUR': 2,
    'GBP': 2,
}

# Payment method codes to activate when the N-Genius provider is enabled.
DEFAULT_PAYMENT_METHOD_CODES = {
    'card',
    'visa',
    'mastercard',
    'amex',
}

# Mapping from Odoo payment method codes to N-Genius payment type strings.
PAYMENT_METHODS_MAPPING = {
    'card': 'CARD',
    'visa': 'VISA',
    'mastercard': 'MASTERCARD',
    'amex': 'AMEX',
}

# Mapping from Odoo transaction states to N-Genius order/payment statuses.
# N-Genius order statuses: INITIATED, AUTHORISED, CAPTURED, PARTIALLY_CAPTURED,
#                          FAILED, CANCELLED, REVERSED, PARTIALLY_REVERSED
TRANSACTION_STATUS_MAPPING = {
    'pending': ('INITIATED', 'AUTHORISED'),
    'done': ('CAPTURED', 'PARTIALLY_CAPTURED'),
    'canceled': ('CANCELLED', 'REVERSED', 'PARTIALLY_REVERSED'),
    'error': ('FAILED',),
}

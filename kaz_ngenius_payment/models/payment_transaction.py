# -*- coding: utf-8 -*-
import logging
import math
import pprint

from werkzeug import urls as werkzeug_urls

from odoo import _, models
from odoo.exceptions import ValidationError

from odoo.addons.kaz_ngenius_payment import const
from odoo.addons.kaz_ngenius_payment.controllers.main import NGeniusController

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    # === REDIRECT FLOW === #

    def _get_specific_rendering_values(self, processing_values):
        """Override of payment to return N-Genius-specific rendering values.

        Workflow:
            1. Call the N-Genius order creation API.
            2. Extract the payment redirect URL from the response (_links.payment.href).
            3. Return it so the redirect form template can forward the customer.

        Args:
            processing_values (dict): Generic and provider-specific processing values.

        Returns:
            dict: {'api_url': <N-Genius HPP URL>}
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'ngenius':
            return res

        payload = self._ngenius_prepare_order_payload()
        _logger.info(
            "Sending N-Genius order creation request for tx %s:\n%s",
            self.reference, pprint.pformat(payload),
        )

        outlet_id = self.provider_id.ngenius_outlet_id
        endpoint = const.ORDERS_ENDPOINT.format(outlet_id=outlet_id)
        response = self.provider_id._ngenius_make_request(endpoint, payload=payload)

        _logger.info(
            "N-Genius order creation response for tx %s:\n%s",
            self.reference, pprint.pformat(response),
        )

        # Store the N-Genius order reference for later status verification.
        order_ref = response.get('reference')
        if order_ref:
            self.provider_reference = order_ref

        # Extract the hosted payment page URL.
        payment_href = (
            response
            .get('_links', {})
            .get('payment', {})
            .get('href')
        )
        if not payment_href:
            raise ValidationError(
                'N-Genius: ' + _('No payment URL was returned by the gateway. Please try again.')
            )

        # Parse the URL and extract query params as separate dict so the redirect
        # form template can inject them as hidden inputs. A plain GET form submission
        # drops the query string from the action URL — hidden inputs preserve them.
        parsed = werkzeug_urls.url_parse(payment_href)
        url_params = werkzeug_urls.url_decode(parsed.query)
        base_url = werkzeug_urls.url_unparse((parsed.scheme, parsed.netloc, parsed.path, '', ''))

        return {
            'api_url': base_url,
            'url_params': url_params,
        }

    def _ngenius_prepare_order_payload(self):
        """Build the JSON payload for the N-Genius order creation API call.

        N-Genius expects the amount in the lowest currency denomination
        (e.g. fils for AED, cents for USD). For 3-decimal currencies (KWD, BHD,
        OMR, JOD) the multiplier is 1000; for 2-decimal currencies it is 100.

        Returns:
            dict: The order creation request body.
        """
        base_url = self.provider_id.get_base_url()
        return_url = werkzeug_urls.url_join(base_url, NGeniusController._return_url)

        currency_name = self.currency_id.name
        minor_unit_places = const.CURRENCY_MINOR_UNIT.get(currency_name, 2)
        multiplier = 10 ** minor_unit_places
        amount_in_minor = math.floor(self.amount * multiplier)

        payload = {
            'action': 'SALE',
            'amount': {
                'currencyCode': currency_name,
                'value': amount_in_minor,
            },
            'merchantOrderReference': self.reference,
            'merchantAttributes': {
                'redirectUrl': return_url,
                'cancelUrl': return_url,
                'skipConfirmationPage': True,
            },
        }

        # Add optional email only if present — empty string can cause validation errors.
        if self.partner_email:
            payload['emailAddress'] = self.partner_email

        return payload

    # === NOTIFICATION HANDLING === #

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """Override of payment to find the transaction based on N-Genius return data.

        Args:
            provider_code (str): The provider code ('ngenius').
            notification_data (dict): Data received from the return redirect or webhook.

        Returns:
            payment.transaction: The matching transaction record.

        Raises:
            ValidationError: If no matching transaction is found.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'ngenius' or len(tx) == 1:
            return tx

        reference = notification_data.get('ref')
        if not reference:
            raise ValidationError(
                'N-Genius: ' + _('Received notification data with missing order reference.')
            )

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'ngenius')])
        if not tx:
            raise ValidationError(
                'N-Genius: ' + _('No transaction found matching reference %s.', reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """Override of payment to process the transaction based on N-Genius return data.

        Workflow:
            1. Retrieve the current order state from N-Genius via the GET order API.
            2. Update provider_reference with the N-Genius order reference.
            3. Map the N-Genius order state to an Odoo transaction state.

        Args:
            notification_data (dict): Data received from the return redirect or webhook.

        Raises:
            ValidationError: If the order state cannot be determined.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'ngenius':
            return

        # Use the stored provider_reference (set during order creation) or the ref from params.
        order_ref = self.provider_reference or notification_data.get('ref')
        if not order_ref:
            raise ValidationError(
                'N-Genius: ' + _('Cannot verify payment — order reference is missing.')
            )

        # Server-side status verification: never trust redirect params alone.
        outlet_id = self.provider_id.ngenius_outlet_id
        endpoint = const.ORDER_STATUS_ENDPOINT.format(
            outlet_id=outlet_id, order_ref=order_ref
        )
        order_data = self.provider_id._ngenius_make_request(endpoint, method='GET')
        _logger.info(
            "N-Genius order status response for tx %s:\n%s",
            self.reference, pprint.pformat(order_data),
        )

        self.provider_reference = order_ref

        # N-Genius order state is at the top level; payment-level state is in _embedded.
        # We check the payment-level state first (most granular), fall back to order state.
        order_state = order_data.get('orderStatus') or order_data.get('status', '')
        embedded = order_data.get('_embedded', {})
        payments = embedded.get('payment', [])
        if payments:
            # Use the state of the most recent payment attempt.
            payment_state = payments[-1].get('state', order_state)
        else:
            payment_state = order_state

        payment_state = payment_state.upper()

        if payment_state in const.TRANSACTION_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_state in const.TRANSACTION_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_state in const.TRANSACTION_STATUS_MAPPING['canceled']:
            self._set_canceled()
        elif payment_state in const.TRANSACTION_STATUS_MAPPING['error']:
            _logger.warning(
                "N-Genius: Transaction %s has error state: %s", self.reference, payment_state
            )
            self._set_error(
                'N-Genius: ' + _('Payment was not successful (status: %s).', payment_state)
            )
        else:
            _logger.warning(
                "N-Genius: Unknown payment state '%s' for transaction %s",
                payment_state, self.reference,
            )
            self._set_error(
                'N-Genius: ' + _('Received an unrecognised payment status: %s.', payment_state)
            )

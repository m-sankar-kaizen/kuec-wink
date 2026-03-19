# -*- coding: utf-8 -*-
import logging
import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class NGeniusController(http.Controller):
    _return_url = '/payment/ngenius/return'
    _webhook_url = '/payment/ngenius/webhook'

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def ngenius_return_from_checkout(self, **data):
        """Handle the redirect back from the N-Genius hosted payment page.

        N-Genius appends the order reference as the 'ref' query parameter when
        redirecting the customer back to the merchant's redirectUrl after payment.

        Workflow:
            1. Log the received query parameters for debugging.
            2. Call _handle_notification_data to find and update the transaction.
            3. Redirect the customer to Odoo's /payment/status page.

        Args:
            **data (dict): Query parameters from N-Genius (includes 'ref' order reference).
        """
        _logger.info(
            "N-Genius: Handling return redirect from hosted payment page:\n%s",
            pprint.pformat(data),
        )
        try:
            request.env['payment.transaction'].sudo()._handle_notification_data('ngenius', data)
        except ValidationError:
            _logger.exception("N-Genius: Failed to process return notification data")
        return request.redirect('/payment/status')

    @http.route(
        f'{_webhook_url}/<string:reference>',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def ngenius_webhook(self, reference, **_kwargs):
        """Handle asynchronous webhook notifications from N-Genius.

        N-Genius can send asynchronous payment status notifications to a configured
        webhook URL. This endpoint processes those notifications and updates the
        corresponding transaction. The transaction reference is embedded in the URL.

        Workflow:
            1. Parse the JSON notification body.
            2. Extract the order reference from the URL path parameter.
            3. Call _handle_notification_data using the embedded reference.
            4. Return an empty 200 response to acknowledge receipt.

        Args:
            reference (str): The Odoo transaction reference embedded in the URL.
            **_kwargs: Unused extra query parameters.

        Returns:
            str: Empty string to acknowledge the notification.
        """
        data = request.get_json_data()
        _logger.info(
            "N-Genius: Received webhook notification for reference %s:\n%s",
            reference, pprint.pformat(data),
        )
        try:
            # Merge the reference into the data dict so _get_tx_from_notification_data
            # can locate the transaction by the Odoo transaction reference.
            notification_payload = dict(data or {})
            notification_payload.setdefault('ref', reference)
            request.env['payment.transaction'].sudo()._handle_notification_data(
                'ngenius', notification_payload
            )
        except ValidationError:
            _logger.exception(
                "N-Genius: Unable to process webhook for reference %s — skipping to acknowledge",
                reference,
            )
        return ''

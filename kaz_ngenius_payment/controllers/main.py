# -*- coding: utf-8 -*-
import hashlib
import hmac
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
            1. Validate the HMAC-SHA256 signature when a webhook secret is configured.
            2. Parse the JSON notification body.
            3. Extract the order reference from the URL path parameter.
            4. Call _handle_notification_data using the embedded reference.
            5. Return an empty 200 response to acknowledge receipt.

        Args:
            reference (str): The Odoo transaction reference embedded in the URL.
            **_kwargs: Unused extra query parameters.

        Returns:
            str: Empty string to acknowledge receipt (200 OK).
                 Returns 'Forbidden' (403) when signature validation fails.
        """
        # Signature validation: protect against forged payment status notifications.
        # N-Genius signs each webhook request with HMAC-SHA256 using the shared
        # secret configured in the merchant portal. If no secret is stored we skip
        # validation and log a warning — this mode should NOT be used in production.
        provider = request.env['payment.provider'].sudo().search(
            [('code', '=', 'ngenius'), ('state', '!=', 'disabled')], limit=1
        )
        webhook_secret = provider.ngenius_webhook_secret if provider else None

        if webhook_secret:
            raw_body = request.httprequest.get_data()
            received_sig = request.httprequest.headers.get('X-Ngenius-Hmac-Sha256', '')
            expected_sig = hmac.new(
                webhook_secret.encode('utf-8'),
                raw_body,
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_sig, received_sig):
                _logger.warning(
                    "N-Genius: Webhook signature mismatch for reference %s — request rejected.",
                    reference,
                )
                return request.make_response('Forbidden', status=403)
        else:
            _logger.warning(
                "N-Genius: No webhook secret configured — signature validation skipped. "
                "Set ngenius_webhook_secret on the payment provider for production use."
            )

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

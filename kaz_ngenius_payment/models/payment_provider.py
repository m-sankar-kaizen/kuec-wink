# -*- coding: utf-8 -*-
import logging
import pprint

import requests
from werkzeug import urls

from odoo import _, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.kaz_ngenius_payment import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('ngenius', 'N-Genius')],
        ondelete={'ngenius': 'set default'},
    )
    ngenius_api_key = fields.Char(
        string='N-Genius API Key',
        required_if_provider='ngenius',
        groups='base.group_system',
        help='The API key issued by Network International for authenticating against the N-Genius gateway.',
    )
    ngenius_outlet_id = fields.Char(
        string='Outlet Reference ID',
        required_if_provider='ngenius',
        groups='base.group_system',
        help='The unique outlet reference ID assigned to your merchant account in the N-Genius portal.',
    )

    # === HELPERS === #

    def _ngenius_get_base_url(self):
        """Return the N-Genius API base URL based on the provider state.

        Returns:
            str: Sandbox URL when state is 'test', production URL otherwise.
        """
        self.ensure_one()
        return const.API_BASE_URLS.get(self.state, const.API_BASE_URLS['test'])

    def _ngenius_get_access_token(self):
        """Authenticate against N-Genius and return a short-lived Bearer token.

        Workflow:
            1. Build the auth endpoint URL from the current provider state.
            2. POST with the API key in the Authorization header.
            3. Parse the JSON response and extract the access_token field.

        Returns:
            str: The Bearer access token.

        Raises:
            ValidationError: If the HTTP request fails or the response is malformed.
        """
        self.ensure_one()
        url = urls.url_join(self._ngenius_get_base_url(), const.AUTH_ENDPOINT)
        headers = {
            'Authorization': f'Basic {self.ngenius_api_key}',
            'Content-Type': 'application/vnd.ni-identity.v1+json',
        }
        try:
            response = requests.post(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            _logger.exception("N-Genius auth failed at %s", url)
            raise ValidationError(
                'N-Genius: ' + _('Authentication failed. Please verify your API Key.')
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("N-Genius: Unable to reach auth endpoint at %s", url)
            raise ValidationError(
                'N-Genius: ' + _('Could not connect to the N-Genius gateway. Please try again.')
            )

        try:
            token = response.json().get('access_token')
        except ValueError:
            raise ValidationError(
                'N-Genius: ' + _('Unexpected response from the authentication endpoint.')
            )

        if not token:
            raise ValidationError(
                'N-Genius: ' + _('No access token returned. Please verify your API Key.')
            )
        return token

    def _ngenius_make_request(self, endpoint, payload=None, method='POST'):
        """Make an authenticated request to the N-Genius API.

        Workflow:
            1. Fetch a fresh access token via _ngenius_get_access_token().
            2. Build the full URL from the provider's base URL and the given endpoint.
            3. Execute the HTTP request with the Bearer token header.
            4. Return the parsed JSON response.

        Args:
            endpoint (str): Relative API path (e.g. '/transactions/outlets/{id}/orders').
            payload (dict): JSON body for POST requests. Ignored for GET.
            method (str): HTTP method — 'POST' or 'GET'.

        Returns:
            dict: Parsed JSON response body.

        Raises:
            ValidationError: If an HTTP error or connection problem occurs.
        """
        self.ensure_one()
        access_token = self._ngenius_get_access_token()
        url = urls.url_join(self._ngenius_get_base_url(), endpoint)
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/vnd.ni-payment.v2+json',
            'Accept': 'application/vnd.ni-payment.v2+json',
        }
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=15)
            else:
                _logger.info(
                    "Sending N-Genius %s request to %s:\n%s",
                    method, url, pprint.pformat(payload),
                )
                response = requests.post(url, json=payload, headers=headers, timeout=15)

            response.raise_for_status()
        except requests.exceptions.HTTPError:
            try:
                error_body = response.json()
                error_msg = error_body.get('message') or error_body.get('error') or str(response.status_code)
            except ValueError:
                error_body = response.text
                error_msg = str(response.status_code)
            _logger.error(
                "N-Genius API error %s at %s\nPayload: %s\nResponse body: %s",
                response.status_code, url, pprint.pformat(payload), pprint.pformat(error_body)
            )
            raise ValidationError(
                'N-Genius: ' + _(
                    'The API request failed. N-Genius responded with: %(msg)s',
                    msg=error_msg,
                )
            )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("N-Genius: Unable to reach endpoint at %s", url)
            raise ValidationError(
                'N-Genius: ' + _('Could not establish a connection to the N-Genius gateway.')
            )

        return response.json()

    # === OVERRIDES === #

    def _get_supported_currencies(self):
        """Override of payment to return the currencies supported by N-Genius."""
        supported = super()._get_supported_currencies()
        if self.code == 'ngenius':
            supported = supported.filtered(lambda c: c.name in const.SUPPORTED_CURRENCIES)
        return supported

    def _get_default_payment_method_codes(self):
        """Override of payment to return the default payment method codes for N-Genius."""
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'ngenius':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

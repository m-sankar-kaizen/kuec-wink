# -*- coding: utf-8 -*-
import json
import werkzeug.urls
import werkzeug.utils

from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome as Home


class OAuthLogin(Home):
    """
    OAuthLogin extends the default Odoo authentication controller to dynamically list
    and build login URLs for all enabled OAuth providers (e.g., Microsoft, Google, etc.).

    This customization enables SSO integration with external identity providers.

    Inherits:
        - odoo.addons.auth_signup.controllers.main.AuthSignupHome

    Methods:
        - list_providers: Builds login URLs for each enabled OAuth provider using their config.
    """

    def list_providers(self):
        """
        Retrieve and prepare the list of OAuth providers configured in the system.

        This method fetches all `auth.oauth.provider` records where the `enabled` flag is True.
        For each provider, it constructs a full OAuth authorization URL with appropriate query
        parameters like `client_id`, `redirect_uri`, `scope`, and `state`.

        Returns:
            list of dict:
                A list of dictionaries, each representing an OAuth provider with an additional
                key `auth_link` containing the full login URL.

        Notes:
            - If a custom redirect URI (`redirect_uri_microsoft`) is configured, it is used;
              otherwise, the fallback is `http://<domain>/auth_oauth/signin`.
            - The state parameter includes serialized OAuth context for CSRF protection and session recovery.
        """
        super().list_providers()

        try:
            # Fetch all enabled OAuth providers from the database
            auth_providers = request.env['auth.oauth.provider'].sudo().search_read([('enabled', '=', True)])
        except Exception:
            # In case of any failure (e.g., database connection issue), fallback to empty list
            auth_providers = []

        for rec in auth_providers:
            # Choose the redirect URI:
            # If a custom Microsoft redirect URI is set, use it. Otherwise, fallback to the default Odoo endpoint
            return_url = rec['redirect_uri_microsoft'] if rec.get('redirect_uri_microsoft') else request.httprequest.url_root + 'auth_oauth/signin'

            # Build the state dictionary which may include useful session info or CSRF tokens
            state = self.get_state(rec)

            # Compose query parameters for the OAuth login request
            params = dict(
                response_type=rec['response_type'],  # Usually 'code'
                client_id=rec['client_id'],
                redirect_uri=return_url,
                scope=rec['scope'],
                state=json.dumps(state),  # Serialize state info as JSON string
            )

            # Construct the full login URL to redirect the user to the provider's auth page
            rec['auth_link'] = "%s?%s" % (rec['auth_endpoint'], werkzeug.urls.url_encode(params))

        return auth_providers

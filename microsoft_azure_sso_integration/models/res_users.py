# -*- coding: utf-8 -*-
import json
import logging
import requests

from odoo.http import request
from odoo import api, models, exceptions
from odoo.exceptions import ValidationError
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons import base

# Extend user private fields to include the access token
base.models.res_users.USER_PRIVATE_FIELDS.append('oauth_access_token')

_logger = logging.getLogger(__name__)

# Attempt to import PyJWT
try:
    import jwt
except ImportError:
    _logger.warning(
        "Login with Microsoft account won't be available. Please install the 'PyJWT' Python library."
    )
    jwt = None


class ResUsers(models.Model):
    """
    Extends the core `res.users` model to support Microsoft OAuth 2.0 login.

    This module overrides the default OAuth flow to handle:
    - Authorization Code validation
    - OAuth login using tokens from Microsoft
    - Decoding `id_token` using PyJWT
    - User matching and creation based on email/user_id
    """

    _inherit = 'res.users'

    @api.model
    def _auth_oauth_rpc(self, endpoint, access_token):
        """
        Fetch user information from an OAuth provider using the access token.

        Args:
            endpoint (str): API endpoint to fetch user data from.
            access_token (str): OAuth access token.

        Returns:
            dict: Decoded JSON response with user data.
        """
        res = super()._auth_oauth_rpc(endpoint, access_token)
        if endpoint:
            return requests.get(endpoint, params={'access_token': access_token}).json()
        return res

    @api.model
    def _auth_oauth_code_validate(self, provider, code):
        """
        Validates the OAuth authorization code received from the provider.

        Args:
            provider (int): OAuth provider ID.
            code (str): Authorization code returned by the provider.

        Returns:
            dict: A dictionary containing the validated user data and access token.

        Raises:
            Exception: If the token exchange fails or validation fails.
        """
        auth_oauth_provider = self.env['auth.oauth.provider'].browse(provider)
        redirect_uri = auth_oauth_provider.redirect_uri_microsoft or request.httprequest.url_root + 'auth_oauth/signin'

        req_params = {
            'client_id': auth_oauth_provider.client_id,
            'client_secret': auth_oauth_provider.client_secret_id,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
        }

        headers = {'Accept': 'application/json'}

        token_info = requests.post(
            auth_oauth_provider.validation_endpoint,
            headers=headers,
            data=req_params
        ).json()

        if token_info.get("error"):
            raise Exception(token_info['error'])

        access_token = token_info.get('access_token')
        validation = {'access_token': access_token}

        if token_info.get('id_token'):
            if not jwt:
                raise exceptions.AccessDenied("PyJWT is not installed.")
            data = jwt.decode(
                token_info['id_token'],
                options={"verify_signature": False},
                algorithms=["RS256"]
            )
        else:
            data = self._auth_oauth_rpc(auth_oauth_provider.data_endpoint, access_token)

        validation.update(data)
        return validation

    @api.model
    def _auth_oauth_signin(self, provider, validation, params):
        """
        Signs in the user using validated OAuth data. Optionally creates a new user if enabled.

        Args:
            provider (int): OAuth provider ID.
            validation (dict): Validated OAuth user information.
            params (dict): Original OAuth parameters.

        Returns:
            str: Login of the authenticated user.

        Raises:
            AccessDenied: If user lookup or creation fails.
        """
        user = self.search([('login', '=', str(validation.get('email')))])
        if not user:
            raise ValidationError("User not found in the system.")

        user.write({
            'oauth_provider_id': provider,
            'oauth_uid': validation['user_id'],
            'oauth_access_token': params['access_token'],
        })

        oauth_uid = validation['user_id']
        try:
            oauth_user = self.search([
                ('oauth_uid', '=', oauth_uid),
                ('oauth_provider_id', '=', provider)
            ])
            if not oauth_user:
                raise exceptions.AccessDenied()
            assert len(oauth_user) == 1
            oauth_user.write({'oauth_access_token': params['access_token']})
            return oauth_user.login
        except (exceptions.AccessDenied, exceptions.access_denied_exception):
            if self.env.context.get('no_user_creation'):
                return None
            state = json.loads(params.get('state', '{}'))
            token = state.get('t')
            values = self._generate_signup_values(provider, validation, params)
            try:
                _, login, _ = self.signup(values, token)
                return login
            except SignupError:
                raise exceptions.access_denied_exception

        return super()._auth_oauth_signin(provider, validation, params)

    @api.model
    def auth_oauth(self, provider, params):
        """
        Main OAuth entry point that processes access token or authorization code for login.

        Args:
            provider (int): OAuth provider ID.
            params (dict): Parameters returned from the OAuth provider.

        Returns:
            tuple: (dbname, login, access_token)

        Raises:
            AccessDenied: If authentication fails.
        """
        if params.get('code'):
            validation = self._auth_oauth_code_validate(provider, params['code'])
            access_token = validation.pop('access_token')
            params['access_token'] = access_token
        else:
            access_token = params.get('access_token')
            validation = self._auth_oauth_validate(provider, access_token)

        if not validation.get('user_id'):
            if validation.get('id'):
                validation['user_id'] = validation['id']
            elif validation.get('oid'):
                validation['user_id'] = validation['oid']
            else:
                raise exceptions.AccessDenied("OAuth response does not"
                                              " include a valid user identifier.")

        login = self._auth_oauth_signin(provider, validation, params)
        if not login:
            raise exceptions.AccessDenied("OAuth login failed.")

        if provider and params:
            return (self.env.cr.dbname, login, access_token)

        return super().auth_oauth(provider, params)

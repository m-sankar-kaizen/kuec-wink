# -*- coding: utf-8 -*-
from odoo import fields, models


class AuthOauthProvider(models.Model):
    """
    Extends the 'auth.oauth.provider' model to support Microsoft OAuth-specific configuration.

    This model customization adds Microsoft-specific fields such as `client_secret_id`,
    response type selection, an optional redirect URI override, and a logo for the login button.

    Intended for use with Microsoft Azure Active Directory integration via OAuth 2.0.
    """

    _inherit = 'auth.oauth.provider'

    client_secret_id = fields.Char(
        string='Client Secret',
        help="Client Secret issued by Microsoft Azure during app registration. "
             "Used for token validation during OAuth flow."
    )

    response_type = fields.Selection(
        [('token', 'Token'), ('code', 'Code')],
        default='token',
        required=True,
        string="Response Type",
        help="OAuth 2.0 response type. Use 'code' for Authorization Code Flow (recommended), "
             "or 'token' for Implicit Flow (legacy and less secure)."
    )

    logo = fields.Binary(
        string="Login Button Logo",
        help="Custom logo image to show on the Microsoft OAuth login button. Should be a base64-encoded image."
    )

    redirect_uri_microsoft = fields.Char(
        string="Redirect URI",
        help="Optional custom redirect URI used by Microsoft OAuth login. "
             "If not set, the default '/auth_oauth/signin' is used."
    )

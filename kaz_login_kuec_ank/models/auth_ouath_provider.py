# -*- coding: utf-8 -*-
from odoo import models, fields


class OauthProvider(models.Model):
    """
    Extends the OAuth authentication provider model to support a custom logo field.

    Purpose:
    --------
    Adds a `logo` field to the `auth.oauth.provider` model to allow each OAuth provider
    (e.g., Google, Microsoft) to have an associated image for login page display or UI branding.

    Field:
    ------
    - logo (Char): A string path or URL to the provider's logo image.
                   Used in custom login templates or provider listings.
    """
    _inherit = 'auth.oauth.provider'

    logo = fields.Char(
        string="Logo",
        help="Path or URL of the logo image for this OAuth provider."
    )
    #FixMe: The logo is already declared as binary in microsoft sso app but re-declared as char here

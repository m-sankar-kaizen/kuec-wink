# -*- coding: utf-8 -*-
from odoo import models, fields


class AuthSamlProvider(models.Model):
    """
    Extends the SAML authentication provider model to support a custom logo field.

    Purpose:
    --------
    Adds a `logo` field to the `auth.saml.provider` model so each SAML provider
    can optionally have a visual logo (e.g., for display on a login page or identity provider listing).

    Field:
    ------
    - logo (Char): A string path or URL to the provider's logo image.
                   This is meant to be used for branding or UI enhancement.
    """
    _inherit = 'auth.saml.provider'

    logo = fields.Char(
        string="Logo",
        help="Path or URL of the logo image for this SAML provider."
    )



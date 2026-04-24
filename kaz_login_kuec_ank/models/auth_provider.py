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

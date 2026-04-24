
from odoo import fields, models


class OAuthProviderLinkedin(models.Model):
    """ Adding client_secret field because some apps likes twitter,
       linkedIn are using this value for its API operations """
    _inherit = 'auth.oauth.provider'

    client_secret = fields.Char(string='Client Secret',
                                help="Only need LinkedIn, Twitter etc..")

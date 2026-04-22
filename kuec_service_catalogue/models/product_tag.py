# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductTag(models.Model):
    _inherit = 'product.tag'

    is_ribbon = fields.Boolean(
        string='Show as Ribbon on Website',
        default=False,
        help='If checked, this tag will act as a diagonal ribbon on service cards.',
    )
    color_html = fields.Char(
        string='Colour (Hex)',
        help='Hex colour code for this tag on the portal (e.g. #FF5733). '
             'Leave empty to use the default grey badge.',
    )

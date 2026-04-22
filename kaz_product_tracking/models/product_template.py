from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = "product.template"

    type = fields.Selection(tracking=True)
    name = fields.Char(tracking=True)

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    vendor_score = fields.Float(
        related="partner_id.vendor_score",
        store=True,
        readonly=True
    )

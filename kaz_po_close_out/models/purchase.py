from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    department_id = fields.Many2one(
        'hr.department',
        related='custom_requisition_id.department_id')

# -*- coding: utf-8 -*-
from odoo import models, fields, _


class PurchaseOrderApproval(models.Model):
    _name = 'purchase.order.approval'
    _description = 'Purchase Order Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'purchase_id'

    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', )

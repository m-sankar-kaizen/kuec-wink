# -*- coding: utf-8 -*-
from odoo import models, fields, _


class MaterialPurchaseRequisitionApproval(models.Model):
    _name = 'material.purchase.requisition.approval'
    _description = 'Material Purchase Requisition Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'requisition_id'

    requisition_id = fields.Many2one('material.purchase.requisition', string='Requisition')

# -*- coding: utf-8 -*-
from odoo import models, fields


class MaterialPurchaseRequisitionLine(models.Model):
    _inherit = "material.purchase.requisition.line"

    company_id = fields.Many2one(related="requisition_id.company_id", string="Company")
    company_code = fields.Selection(related="requisition_id.company_code", string="Company Code")

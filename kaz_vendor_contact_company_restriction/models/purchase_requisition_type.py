# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseRequisitionType(models.Model):
    _inherit = 'purchase.requisition.type'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
# -*- coding: utf-8 -*-
from odoo import models, fields, _


class ChooseVendor(models.TransientModel):
    _name = 'choose.vendor'
    _description = 'Choose Vendor'

    material_purchase_requisition_id = fields.Many2one('material.purchase.requisition',
                                                       'Purchase Requisition')
    partner_id = fields.Many2one('res.partner', 'Partner')


    def action_choose_vendor(self):
        self.ensure_one()
        return self.material_purchase_requisition_id.action_create_rfq(self.partner_id.id)

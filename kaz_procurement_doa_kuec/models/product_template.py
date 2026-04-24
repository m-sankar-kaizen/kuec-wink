# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def default_get(self, default_fields):
        rec = super().default_get(default_fields)
        rec.update({
            'company_id': self.env.company.id
        })
        return rec

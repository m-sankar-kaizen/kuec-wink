# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PartnerChecklistConf(models.Model):
    _name = 'partner.checklist.conf'
    _description = 'Partner Checklist Conf'
    _check_company_auto = True

    name = fields.Char('Question Name', required=True)
    for_customer = fields.Boolean('For Customer')
    for_vendor = fields.Boolean('For Vendor')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    @api.constrains('for_customer', 'for_vendor')
    def _check_customer_or_vendor(self):
        for record in self:
            if not record.for_customer and not record.for_vendor:
                raise ValidationError(
                    "At least one of 'For Customer' or 'For Vendor' must be enabled."
                )

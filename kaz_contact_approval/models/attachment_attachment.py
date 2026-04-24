# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Attachment(models.Model):
    _name = 'attachment.attachment'
    _description = 'Attachment'
    _check_company_auto = True

    name = fields.Char('Name', required=True)
    company_type = fields.Selection(string='Company Type',
                                    required=True,
                                    selection=[('person', 'Individual'), ('company', 'Company')],
                                    default='person')
    is_vendor = fields.Boolean("Is Vendor")
    is_customer = fields.Boolean("Is Customer")
    checklist_line_ids = fields.One2many('attachment.line', 'attachment_id')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    @api.constrains('is_vendor', 'is_customer')
    def _check_customer_or_vendor(self):
        for record in self:
            if not record.is_vendor and not record.is_customer:
                raise ValidationError(
                    "At least one of 'Is Customer' or 'Is Vendor' must be enabled."
                )


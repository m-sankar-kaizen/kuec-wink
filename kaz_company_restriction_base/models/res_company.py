# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_company_code_selection(self):
        return [
            ('ANK', 'ANKABUT (ANK)'),
            ('KUEC', 'KHALIFA UNIVERSITY (KUEC)'),
            ('BEY', 'BEYOND (BEY)'),
            ('INFO', 'INFRATOMICS (INFO)'),
            ('NEW', 'NEW'),
        ]

    company_code = fields.Selection(
        selection=_get_company_code_selection,
        required=True,
        string='Company Code',
    )
    company_warning_message = fields.Text("Company Warning Message",
                                          compute='_compute_company_warning_message')
    company_ceo_user_id = fields.Many2one(
        'res.users',
        string='CEO',
        help='This user will be used as the CEO and their signature will be applied where required.'
    )

    @api.depends('company_code')
    def _compute_company_warning_message(self):
        for rec in self:
            if rec.company_code == "NEW":
                rec.company_warning_message = (
                    "This is a new company. Many features may not work for this company. "
                    "Please contact the development team to assist you with the onboarding."
                )
            else:
                rec.company_warning_message = ""

    @api.constrains('company_code')
    def _check_unique_company_code(self):
        for rec in self:
            if rec.company_code:
                exists = self.search([
                    ('company_code', '=', rec.company_code),
                    ('id', '!=', rec.id)
                ], limit=1)
                if exists:
                    raise ValidationError(
                        f"The company code '{rec.company_code}' is already assigned "
                        f"to another company. Each code can only be used once."
                    )

# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'company_id' in fields_list and not res.get('company_id'):
            res['company_id'] = self.env.company.id
        return res

    def _get_vendor_evaluation_company_ids(self):
        return self.env['res.company'].sudo().search([('company_code', 'in', ['KUEC'])])

    @api.depends('state', 'company_id')
    def _compute_readonly_form(self):
        for record in self:
            record.is_readonly = record.state in ['approved', 'rejected'] and record.company_code in ['KUEC']

    def _compute_show_partner_category_required(self):
        """Compute partner category requirement only for partners in company KUEC."""
        for record in self:
            partner = record.sudo()

            if partner.company_code not in ['KUEC']:
                partner.show_partner_category_required = False
                continue

            partner.show_partner_category_required = (
                    not partner.employee_ids and
                    not partner.parent_id
            )

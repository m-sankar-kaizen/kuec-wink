# -*- coding: utf-8 -*-
from odoo import models, fields, api


class WorkedCompany(models.Model):
    _name = 'worked.company'
    _description = 'Worked Company'
    _check_company_auto = True

    name = fields.Char(string='Company Name', required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-increment sequence within the same company, safe for batch creation."""
        sequence_cache = {}

        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id

            # Skip if sequence is already provided manually
            if 'sequence' in vals:
                continue

            # Initialize cache entry if not present
            if company_id not in sequence_cache:
                # Fetch latest sequence for this company
                last_record = self.sudo().search(
                    [('company_id', '=', company_id), ('partner_id', '=', vals.get('partner_id'))],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

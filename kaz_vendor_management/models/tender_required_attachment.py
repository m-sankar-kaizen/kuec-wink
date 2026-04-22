# -*- coding: utf-8 -*-
from odoo import models, fields, api


class TenderRequiredAttachment(models.Model):
    _name = 'tender.required.attachment'
    _description = 'Tender Required Attachment'
    _check_company_auto = True

    sequence = fields.Integer(string='Sequence', required=True)
    name = fields.Char(string='Name', required=True)
    tender_rfq_id = fields.Many2one('tender.rfq', string='Tender RFQ', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-increment sequence within the same company, safe for batch creation."""
        sequence_cache = {}

        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id
            # Initialize cache entry if not present
            if company_id not in sequence_cache:
                # Fetch latest sequence for this company
                last_record = self.sudo().search(
                    [('company_id', '=', company_id), ('tender_rfq_id', '=', vals.get('tender_rfq_id'))],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

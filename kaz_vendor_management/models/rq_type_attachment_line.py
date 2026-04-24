# -*- coding: utf-8 -*-
from odoo import fields, models, api


class RequisitionTypeAttachmentLine(models.Model):
    _name = 'rq.type.attachment.line'
    _description = 'Requisition Type Attachment Line'
    _inherit = 'attachment.line.mixin'
    _check_company_auto = True

    requirement_type_id = fields.Many2one('purchase.requisition.type',
                                          string="Purchase Requisition Type")

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
                    [('company_id', '=', company_id),
                     ('requirement_type_id', '=', vals.get('requirement_type_id'))],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

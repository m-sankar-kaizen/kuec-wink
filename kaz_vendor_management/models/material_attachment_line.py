# -*- coding: utf-8 -*-
from odoo import fields, models, api


class MaterialAttachmentLine(models.Model):
    _name = 'material.attachment.line'
    _description = 'Material Attachment Line'
    _inherit = 'attachment.line.mixin'
    _check_company_auto = True

    purchase_requisition_id = fields.Many2one('material.purchase.requisition',
                                                       'Purchase Requisition')
    attachment_link = fields.Char('Attachment Link')
    ir_attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

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
                     ('purchase_requisition_id', '=', vals.get('purchase_requisition_id'))],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

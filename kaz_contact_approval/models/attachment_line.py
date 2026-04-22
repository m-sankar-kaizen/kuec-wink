# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ChecklistLine(models.Model):
    _name = 'attachment.line'
    _inherit = 'attachment.line.mixin'
    _description = 'Attachment Line'

    attachment_id = fields.Many2one('attachment.attachment')

    @api.model_create_multi
    def create(self, vals_list):
        sequence_cache = {}

        for vals in vals_list:
            attachment_id = vals.get('attachment_id')
            if not attachment_id or 'sequence' in vals:
                continue

            if attachment_id not in sequence_cache:
                last_record = self.sudo().search_fetch(
                    domain=[('attachment_id', '=', attachment_id)],
                    field_names=['sequence'],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 1
                sequence_cache[attachment_id] = last_sequence

            sequence_cache[attachment_id] += 1
            vals['sequence'] = sequence_cache[attachment_id]

        return super().create(vals_list)

    @api.constrains('attachment_is_required', 'expiry_date_required')
    def _check_expiry_date_required(self):
        for record in self:
            if not record.attachment_is_required and record.expiry_date_required:
                raise ValidationError(
                    "Expiry Date cannot be required if Attachment is not required."
                )

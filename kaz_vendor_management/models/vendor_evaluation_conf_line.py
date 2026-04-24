# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorEvaluationConfLine(models.Model):
    _name = 'vendor.evaluation.conf.line'
    _description = 'Vendor Evaluation Conf Line'
    _check_company_auto = True

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    evaluation_conf_id = fields.Many2one('vendor.evaluation.conf', string='Evaluation Conf', )
    weight = fields.Integer(string='Weight')

    @api.constrains('weight')
    def _check_weight_limit(self):
        for rec in self:
            if rec.weight > 100:
                raise ValidationError(_("Weight cannot exceed 100."))
            if rec.weight < 0:
                raise ValidationError(_("Weight cannot be negative."))

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
                     ('evaluation_conf_id', '=', vals.get('evaluation_conf_id'))],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

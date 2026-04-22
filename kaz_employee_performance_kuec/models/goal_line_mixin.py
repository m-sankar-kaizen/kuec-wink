# -*- coding: utf-8 -*-
from odoo import fields, models, api


class PerformanceGoalLine(models.AbstractModel):
    _name = 'goal.line.mixin'
    _description = 'Goal Line Mixin'
    _check_company_auto = True
    _sequence_parent = None

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    sequence = fields.Integer(string='Sequence')
    weight = fields.Float(string='Weight')
    description = fields.Char(string='Description')
    evaluation_category_id = fields.Many2one('evaluation.category', string='Evaluation Category')

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-increment sequence within the same company, safe for batch creation."""
        sequence_cache = {}

        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id
            # Initialize cache entry if not present
            if company_id not in sequence_cache:
                domain = [('company_id', '=', company_id)]
                if self._sequence_parent is not None:
                    parent_key = self._sequence_parent
                    domain.append((parent_key, '=', vals.get(parent_key)))
                # Fetch latest sequence for this company
                last_record = self.sudo().search(
                    domain,
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

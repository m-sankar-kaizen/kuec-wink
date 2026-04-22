# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api


class Year(models.Model):
    _name = 'year.year'
    _description = 'Year'
    _order = 'sequence'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _check_company_auto = True

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    date_from = fields.Date(string='Start Date', required=True)
    date_to = fields.Date(string='End Date', required=True)

    @api.onchange('date_from')
    def _onchange_date_from(self):
        """If date_from is set, auto-set date_to to +1 year"""
        if self.date_from:
            self.date_to = (self.date_from + relativedelta(years=1) - relativedelta(days=1))

    @api.onchange('date_to')
    def _onchange_date_to(self):
        """If date_to is set, auto-set date_from to -1 year"""
        if self.date_to:
            self.date_from = (self.date_to - relativedelta(years=1) + relativedelta(days=1))

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
                    [('company_id', '=', company_id)],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

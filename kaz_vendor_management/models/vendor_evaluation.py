# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command


class VendorEvaluation(models.Model):
    _name = 'vendor.evaluation'
    _description = 'Vendor Evaluation'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'vendor_evaluation_conf_id'
    _order = 'create_date desc'

    sequence = fields.Integer(string='Sequence', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    vendor_evaluation_conf_id = fields.Many2one(related='partner_id.vendor_evaluation_conf_id')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    total_score = fields.Float(string='Total Score', compute='_compute_rating_and_score',
                               store=True)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('evaluated', 'Evaluated')],
        default='draft',
        tracking=True,
        string='State',
    )
    vendor_evaluation_line_ids = fields.One2many('vendor.evaluation.line', 'evaluation_id',
                                                 string='Vendor Evaluation Lines')
    rating = fields.Selection(
        selection=[
            ('0', '0%'),
            ('1', '20%'),
            ('2', '40%'),
            ('3', '60%'),
            ('4', '80%'),
            ('5', '100%'),
        ],
        default='0',
        compute='_compute_rating_and_score',
        store=True,
        string='Rating',
    )

    def action_generate_line(self):
        self.ensure_one()
        if not self.vendor_evaluation_line_ids:
            self.write({
                'vendor_evaluation_line_ids': [
                    Command.create({
                        'sequence': idx + 1,
                        'name': rec.name,
                        'weight': rec.weight,
                    }) for idx, rec in
                    enumerate(self.vendor_evaluation_conf_id.evaluation_conf_line_ids)
                ]
            })

    @api.depends('vendor_evaluation_line_ids.score')
    def _compute_rating_and_score(self):
        for record in self:
            # Compute total score out of 100
            total = sum(record.vendor_evaluation_line_ids.mapped('score'))
            record.total_score = total

            # Determine rating based on score percentage
            if total >= 90:
                record.rating = '5'
            elif total >= 80:
                record.rating = '4'
            elif total >= 60:
                record.rating = '3'
            elif total >= 40:
                record.rating = '2'
            elif total >= 20:
                record.rating = '1'
            else:
                record.rating = '0'

    def action_evaluate(self):
        self.ensure_one()
        self.state = 'evaluated'

    def action_reset_to_draft(self):
        self.ensure_one()
        self.state = 'draft'

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-increment sequence within the same company, safe for batch creation."""
        sequence_cache = {}

        for vals in vals_list:
            if vals.get('sequence'):
                continue

            company_id = vals.get('company_id') or self.env.company.id
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

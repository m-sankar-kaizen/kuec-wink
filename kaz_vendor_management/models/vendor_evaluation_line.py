# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VendorEvaluationLine(models.Model):
    _name = 'vendor.evaluation.line'
    _description = 'Vendor Evaluation Line'
    _check_company_auto = True

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    evaluation_id = fields.Many2one('vendor.evaluation', string='Evaluation Conf')
    evaluation_state = fields.Selection(related='evaluation_id.state', string='Evaluation State')
    weight = fields.Integer(string='Weight')
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
        required=True,
        string='Rating',
    )
    score = fields.Float(
        string='Score',
        compute='_compute_score',
        store=True,
        help="Calculated as (rating percentage × weight) / 100."
    )
    comment = fields.Char(string='Comment')

    @api.depends('rating', 'weight')
    def _compute_score(self):
        """Compute weighted score based on rating and weight."""
        for rec in self:
            rating_map = {
                '0': 0,
                '1': 20,
                '2': 40,
                '3': 60,
                '4': 80,
                '5': 100,
            }
            percentage = rating_map.get(rec.rating, 0)
            rec.score = (rec.weight * percentage) / 100.0 if rec.weight else 0.0

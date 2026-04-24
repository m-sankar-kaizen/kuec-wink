# -*- coding: utf-8 -*-

from odoo import models, fields, api


class RatingRatingWink(models.Model):
    _inherit = 'rating.rating'

    wink_satisfaction_label = fields.Char(
        compute='_compute_wink_satisfaction_label',
        string='Satisfaction Rate',
        help='5-point satisfaction label derived from the numeric rating score.',
    )

    @api.depends('rating')
    def _compute_wink_satisfaction_label(self):
        """Map 1–5 rating score to WINK satisfaction labels."""
        label_map = {
            1: 'Extremely Unsatisfied',
            2: 'Unsatisfied',
            3: 'Neutral',
            4: 'Satisfied',
            5: 'Extremely Satisfied',
        }
        for rec in self:
            score = int(round(rec.rating)) if rec.rating else 0
            rec.wink_satisfaction_label = label_map.get(score, '')

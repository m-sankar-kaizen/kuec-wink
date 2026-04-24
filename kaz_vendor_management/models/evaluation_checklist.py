# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import AccessError


class EvaluationChecklist(models.Model):
    _name = 'evaluation.checklist'
    _description = 'Evaluation Checklist'
    _check_company_auto = True

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    evaluation_type = fields.Selection(
        selection=[
            ('commercial', 'Commercial'),
            ('technical', 'Technical'),
        ],
        string='Type',
        default='commercial',
        required=True,
    )
    weight = fields.Integer(string='Weight')
    rating_score = fields.Float(string='Rating', default=0)
    comment = fields.Char(string='Comment')
    tender_bid_technical_id = fields.Many2one('tender.bid', string='Tender Bid (Technical)')
    tender_bid_commercial_id = fields.Many2one('tender.bid', string='Tender Bid (Commercial)')
    score = fields.Float(
        string='Score',
        compute='_compute_score',
        store=True,
        help="Calculated as (rating percentage × weight) / 100."
    )
    technical_state = fields.Selection(related='tender_bid_technical_id.state', string='Technical State')
    commercial_state = fields.Selection(related='tender_bid_commercial_id.state', string='Commercial State')

    @api.depends('rating_score', 'weight')
    def _compute_score(self):
        """Compute weighted score based on rating and weight."""
        for rec in self:
            rec.score = (rec.weight * rec.rating_score) / 100.0 if rec.weight else 0.0

    def write(self, vals):
        """Restrict write access for rating/comment fields based on user group."""
        restricted_fields = {'rating_score', 'comment'}

        if restricted_fields.intersection(vals.keys()):
            for rec in self:
                # Case 1: Technical evaluation
                if rec.tender_bid_technical_id:
                    allowed_users = rec.tender_bid_technical_id.technical_user_ids
                    if self.env.user not in allowed_users:
                        raise AccessError(_(
                            "You are not authorized to update technical evaluation fields "
                            "for this record."
                        ))

                # Case 2: Commercial evaluation
                elif rec.tender_bid_commercial_id:
                    allowed_users = rec.tender_bid_commercial_id.commercial_user_ids
                    if self.env.user not in allowed_users:
                        raise AccessError(_(
                            "You are not authorized to update commercial evaluation fields "
                            "for this record."
                        ))

        return super().write(vals)

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

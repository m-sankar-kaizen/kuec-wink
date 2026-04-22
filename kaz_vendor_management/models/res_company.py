# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    technical_score_weight = fields.Float(
        string='Technical Score Weight',
        compute='_compute_scores',
        inverse='_inverse_technical_score',
        store=True,
    )
    commercial_score_weight = fields.Float(
        string='Commercial Score Weight',
        compute='_compute_scores',
        inverse='_inverse_commercial_score',
        store=True,
    )
    vendor_evaluation_reminder_days = fields.Integer(string='Vendor Evaluation Reminder Days',
                                                     help='Number of days before vendor evaluation is reminded',
                                                     default=150)
    support_email_address = fields.Char(string="Portal Support Email Address")
    vendor_procurement_policy_link = fields.Char(string='Vendor Procurement Policy')

    purchase_material = fields.Html(
        string='Purchase Material Terms',
        help='Default terms and conditions for Purchase Order - Material Request'
    )
    purchase_service = fields.Html(
        string='Purchase Service Terms',
        help='Default terms and conditions for Purchase Order - Service Order'
    )

    # New fields added
    contract_material = fields.Html(
        string='Contract Material Terms',
        help='Default terms and conditions for Contract Agreement - Material Request'
    )
    contract_service = fields.Html(
        string='Contract Service Terms',
        help='Default terms and conditions for Contract Agreement - Service Order'
    )

    blanket_material = fields.Html(
        string='Blanket Material Terms',
        help='Default terms and conditions for Blanket Order - Material Request'
    )
    blanket_service = fields.Html(
        string='Blanket Service Terms',
        help='Default terms and conditions for Blanket Order - Service Order'
    )

    @api.depends('technical_score_weight', 'commercial_score_weight')
    def _compute_scores(self):
        """Ensure both always add up to 100. If one is missing, assume default 50/50."""
        for rec in self:
            # Initialize defaults only if both are empty
            if not rec.technical_score_weight and not rec.commercial_score_weight:
                rec.technical_score_weight = 50.0
                rec.commercial_score_weight = 50.0
            else:
                # Normalize total to 100
                total = rec.technical_score_weight + rec.commercial_score_weight
                if total != 100:
                    # Keep technical as is, fix commercial
                    rec.commercial_score_weight = 100 - rec.technical_score_weight

    def _inverse_technical_score(self):
        """When user modifies technical score, automatically recalc commercial."""
        for rec in self:
            if rec.technical_score_weight < 0:
                rec.technical_score_weight = 0
            if rec.technical_score_weight > 100:
                rec.technical_score_weight = 100
            rec.commercial_score_weight = 100 - rec.technical_score_weight

    def _inverse_commercial_score(self):
        """When user modifies commercial score, automatically recalc technical."""
        for rec in self:
            if rec.commercial_score_weight < 0:
                rec.commercial_score_weight = 0
            if rec.commercial_score_weight > 100:
                rec.commercial_score_weight = 100
            rec.technical_score_weight = 100 - rec.commercial_score_weight

    @api.constrains('technical_score_weight', 'commercial_score_weight')
    def _check_score_weights(self):
        for rec in self:
            total = (rec.technical_score_weight or 0) + (rec.commercial_score_weight or 0)
            if total != 100:
                raise ValidationError(
                    _("The total of Technical Score Weight and Commercial Score Weight must always be 100.")
                )

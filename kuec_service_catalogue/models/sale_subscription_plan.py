# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import ValidationError


class SaleSubscriptionPlan(models.Model):
    _inherit = 'sale.subscription.plan'

    kuec_is_reference_plan = fields.Boolean(
        string='Reference Plan',
        default=False,
        help='Check this to use this plan as the baseline for savings calculation on the portal. '
             'Example: Mark Monthly as reference; Yearly 1000 AED vs 12×100 AED → customer saves 16.67%%. '
             'Only one recurring plan should be marked as reference.',
    )

    @api.constrains('kuec_is_reference_plan')
    def _check_only_one_reference_plan(self):
        """Ensure only one plan is marked as the reference plan.

        The reference plan is used as the monthly price baseline for savings
        calculations across the portal. Multiple reference plans would produce
        ambiguous results, so this constraint enforces uniqueness system-wide.

        Raises:
            ValidationError: If another plan already has kuec_is_reference_plan = True.
        """
        for rec in self:
            if not rec.kuec_is_reference_plan:
                continue
            others = self.search([
                ('kuec_is_reference_plan', '=', True),
                ('id', '!=', rec.id),
            ])
            if others:
                raise ValidationError(
                    'Only one Recurring Plan can be marked as Reference Plan. '
                    'Uncheck "%s" first.' % others[0].name
                )

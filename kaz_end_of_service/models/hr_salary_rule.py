# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrSalaryRule(models.Model):
    """
    Extension of the hr.salary.rule model to support
    categorization of salary rules specifically for End of Service (EOS) processing.

    This allows Odoo to distinguish between EOS components like:
    - Basic Settlement
    - Gratuity
    - Pension Deduction
    - Leave Balance Compensation

    It also adds a constraint to prevent duplicate rules for the same EOS category
    within a single payroll structure.
    """
    _inherit = 'hr.salary.rule'

    eos_categories = fields.Selection(
        selection=[
            ('basic', 'Basic Settlement'),
            ('gratuity', 'Gratuity Settlement'),
            ('pension', 'Pension'),
            ('leave_balance', 'Leave Balance')
        ],
        string="End of Service Category",
        help="Defines which part of the EOS settlement this rule represents."
    )

    is_end_of_service = fields.Boolean(
        related='struct_id.is_end_of_service',
        string="Is EOS Structure",
        help="Indicates if this rule belongs to a payroll structure "
             "that is marked as End of Service."
    )

    @api.constrains('eos_categories')
    def constraint_eos_categories(self):
        """
        Ensures that only one salary rule per EOS category exists
        within the same payroll structure.

        This avoids duplication of components like Basic or Gratuity
        in the EOS payslip computation.
        """
        for rule in self:
            if rule.eos_categories:
                # Count how many rules in the structure have the same EOS category
                same_category_count = rule.struct_id.rule_ids.filtered(
                    lambda r: r.eos_categories == rule.eos_categories
                              and r.id != rule.id
                )
                if same_category_count:
                    raise ValidationError(_(
                        "A rule for the '%s' category already exists "
                        "in the selected payroll structure.") % dict(self._fields['eos_categories'].selection).get(rule.eos_categories)
                    )

# -*- coding: utf-8 -*-
from odoo import models, fields, api

class HrGrade(models.Model):
    """
    Extension of the hr.grade model to support education fee reimbursement settings.

    This model adds configuration fields to determine whether a grade is eligible for education
    allowance and to define monetary limits for per-child and total reimbursement amounts.
    """
    _inherit = 'hr.grade'

    is_education_allowance = fields.Boolean(
        string="Education Allowance",
        help="Indicates whether employees in this grade are eligible for education fee reimbursement."
    )
    per_child_allowance = fields.Monetary(
        string="Per Child Allowance",
        currency_field='currency_id',
        help="Maximum allowance amount that can be reimbursed per child."
    )
    reimbursement_limit = fields.Monetary(
        string="Reimbursement Limit",
        currency_field='currency_id',
        help="Maximum total reimbursement amount allowed for the employee in one academic year."
    )

    @api.onchange('is_education_allowance')
    def onchange_education_allowance(self):
        """
        Clears the allowance fields if the education allowance is disabled.

        When the 'is_education_allowance' flag is unchecked, this method resets
        both 'per_child_allowance' and 'reimbursement_limit' to zero to prevent
        stale or irrelevant data from being retained.
        """
        if not self.is_education_allowance:
            self.per_child_allowance = 0
            self.reimbursement_limit = 0

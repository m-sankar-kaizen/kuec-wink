# -*- coding: utf-8 -*-
"""
Extension of the HR Contract model to include computed child allowance support.

This module calculates a monetary child allowance based on the number of eligible
children linked to an approved child allowance request for the employee.
"""

from odoo import models, fields


class HrContract(models.Model):
    """
    Inherits the HR Contract model to add child allowance computation.

    The child allowance is determined by:
    - Searching for an approved `child.allowance` record for the employee.
    - Counting the number of `kids.eligibility` entries marked as eligible.
    - Multiplying the count of eligible kids by a fixed amount (600).
    """

    _inherit = 'hr.contract'

    kaz_child_allowance = fields.Monetary(
        string='Child Allowance',
        compute='compute_kaz_child_allowance',
        help=(
            "This field calculates the total child allowance for the employee "
            "based on the number of eligible children in an approved request. "
            "Each eligible child contributes a fixed allowance amount (e.g., 600)."
        )
    )

    def compute_kaz_child_allowance(self):
        """
        Compute method for 'kaz_child_allowance'.

        This function performs the following steps:
        1. Identify the current employee associated with the contract.
        2. Search for an approved child allowance record (`state == 'approved'`).
        3. Count how many children in that request are marked as eligible.
        4. Multiply the eligible count by a fixed allowance value (600).
        5. Assign the result to the monetary field `kaz_child_allowance`.

        Notes:
        - Assumes one approved child allowance record per employee. If multiple
          are possible, logic must be adapted accordingly.
        - The fixed amount (600) can later be made configurable via settings or
          a system parameter.
        - This field auto-updates when needed, based on dependencies (implicitly).
        """

        for rec in self:
            # Default to zero if no allowance found or no eligible children
            applicable = 0

            # Step 1: Search for the first approved child allowance record
            # You may remove `limit=1` if multiple records should be summed
            allowance_id = self.env['child.allowance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('state', '=', 'approved')
            ], limit=1)

            # Step 2: If a record exists, count eligible kids
            if allowance_id:
                # 'kid_ids' is a One2many to 'kids.eligibility' model
                # We filter only those marked as 'is_eligible = True'
                eligible_kids = allowance_id.kid_ids.filtered(lambda kid: kid.is_eligible)
                applicable = len(eligible_kids)

            # Step 3: Compute total allowance (600 per eligible kid)
            # NOTE: 600 is hardcoded here but can be moved to a config parameter
            rec.kaz_child_allowance = applicable * 600

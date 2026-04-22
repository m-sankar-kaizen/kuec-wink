# -*- coding: utf-8 -*-


from odoo import models, fields, _
from odoo.exceptions import ValidationError


class HrLoan(models.Model):
    """
    Extension of the `hr.loan` model to introduce multi-level loan approval workflow
    and enforce installment computation before approval.

    States added:
        - `draft`: Initial state after creation.
        - `waiting_approval_1`: Submitted by the employee for approval.
        - `approve`: Approved by HR or designated manager.
        - `done`: Final approval and disbursement done.
        - `refuse`: Rejected.
        - `cancel`: Cancelled before processing.

    Methods:
        - `action_submit`: Moves loan to 'waiting_approval_1'.
        - `action_approve`: Validates loan lines before approval.
        - `action_double_approve`: Moves loan to final state 'done'.
    """
    _inherit = 'hr.loan'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval_1', 'Submitted'),
        ('approve', 'HR Approval'),
        ('done', 'Done'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', tracking=True, copy=False,
        help="Workflow state of the loan request.")

    def action_submit(self):
        """
        Transition the loan request from 'draft' to 'waiting_approval_1'.

        Used when the employee formally submits the loan request.
        """
        self.write({'state': 'waiting_approval_1'})

    def action_approve(self):
        """
        Approve the loan after verifying installment lines exist.

        Raises:
            ValidationError: If loan_lines are not computed yet.
        """
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please compute installment before approval."))
            data.write({'state': 'approve'})

    def action_double_approve(self):
        """
        Final approval step, typically by finance or a top-level manager.

        Transitions the loan to the 'done' state.
        """
        self.write({'state': 'done'})
        return True

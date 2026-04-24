# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import ValidationError


class HrLoan(models.Model):
    """
    Extension of the 'hr.loan' model to support custom approval states and notifications.

    This model adds a custom approval workflow with multiple states including HR Team and HR Manager
    levels. It also defines utility methods to notify users in a specific group (excluding higher
    authority groups), and to validate loan constraints such as existing loans or mismatched installments.

    Key Features:
    - Custom approval states: 'draft', 'hr_team', 'hr_manager', 'approve', 'refuse', 'cancel'
    - Tracks if loan has been granted
    - Sends activity notifications to appropriate users in the approval hierarchy
    - Validates loan amount limit and installment consistency before submission
    """
    _inherit = 'hr.loan'
    _order = "id desc"

    # Extended approval state with HR-level granularity
    state = fields.Selection([
        ('draft', 'Draft'),
        ('hr_team', 'HR Team'),
        ('hr_manager', 'HR Manager'),
        ('approve', 'Approved'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', tracking=True, copy=False)

    # Boolean to track whether loan is actually granted
    loan_granted = fields.Boolean(string="Granted", copy=False)

    def send_notify2_group(self, group_xml_id):
        """
        Schedule an activity for users in the given group (excluding users from higher groups).

        This method filters out users who belong to higher authority groups to avoid redundant
        or unauthorized approvals. Then, it schedules a mail activity for users in the exact
        group requested to approve the loan.

        :param group_xml_id: XML ID of the security group to notify
        """

        # Resolve the group record from its XML ID
        group = self.env.ref(group_xml_id)

        # Get all users in the given group
        all_users = self.env['res.users'].search([('groups_id', 'in', group.id)])

        # Define the approval hierarchy from low to high authority
        hierarchy = [
            'ent_ohrms_loan.hr_loan_user',
            'ent_ohrms_loan.group_loan_branch_manager',
            'ent_ohrms_loan.group_loan_super_admin',
        ]

        # Determine the index of the current group in the hierarchy
        current_index = hierarchy.index(group_xml_id)

        # Get all higher-level groups
        higher_groups = hierarchy[current_index + 1:]

        # Fetch all users from higher-level groups to exclude them
        higher_users = self.env['res.users']
        for high_group_id in higher_groups:
            high_group = self.env.ref(high_group_id)
            higher_users |= self.env['res.users'].search([('groups_id', 'in', high_group.id)])

        # Subtract higher-level users to get the exact users to notify
        target_users = all_users - higher_users

        # Schedule activity for each user in the correct group
        for user in target_users:
            self.activity_schedule(
                act_type_xmlid='kaz_ent_loan.mail_activity_loan_approve',
                note='Please Approve',
                user_id=user.id
            )

    def validate_loan(self):
        """
        Validate loan constraints before submission.

        - Ensure no other pending or active (unpaid) loans exist for the employee.
        - Ensure the loan amount does not exceed the annual limit (monthly limit * 12).
        - Ensure number of loan lines matches installment count.

        :raises ValidationError: On any rule violation
        """
        existing_loans = self.sudo().search([
            ('employee_id', '=', self.employee_id.id),
            ('fully_paid', '=', False),
        ])

        for loan in existing_loans:
            if loan.state in ['hr_team', 'hr_manager']:
                raise ValidationError(
                    "There are other requested loans that are pending approval. "
                    "Ask HR to cancel that loan request and request again."
                )
            elif loan.state == 'approve':
                raise ValidationError(
                    "You have an active loan that is not fully paid."
                )

        # Get max loan amount based on employee grade
        loan_amount = self.grade_id.per_month_housing_advance * 12
        if self.loan_amount > loan_amount:
            raise ValidationError(
                _(f"Loan amount exceeds the maximum loan amount of {loan_amount}")
            )

        # Check installment count matches number of lines
        if len(self.loan_lines) != int(self.installment):
            raise ValidationError(
                _(f"Number of Installments chosen doesn't match the actual number of lines. Please recompute.")
            )

    def action_submit(self):
        """
        Submit the loan for approval by HR Team.

        - Validates loan eligibility and consistency
        - Ensures installments are computed and match total loan amount
        - Changes state to 'hr_team' and notifies branch managers
        """
        for data in self:
            data.validate_loan()

            if not data.loan_lines:
                raise ValidationError(_("Please compute the installment."))

            total_installment = round(sum(data.loan_lines.mapped('amount')), 2)
            expected_amount = round(data.loan_amount, 2)

            if total_installment != expected_amount:
                raise ValidationError(_(
                    "Please recompute the installment. The loan amount (%.2f) doesn't match the total of the lines (%.2f)."
                ) % (expected_amount, total_installment))

            data.write({'state': 'hr_team'})
            data.send_notify2_group('ent_ohrms_loan.group_loan_branch_manager')

    def send2_hr_manager(self):
        """
        Escalate the loan to HR Manager level.

        - Changes state to 'hr_manager'
        - Notifies the HR Super Admin group
        """
        self.write({'state': 'hr_manager'})
        self.send_notify2_group('ent_ohrms_loan.group_loan_super_admin')

    def action_approve(self):
        """
        Approve the loan request.

        - Simply sets the state to 'approve'
        """
        self.write({'state': 'approve'})

    def reset_draft(self):
        """
        Reset the loan to 'draft' state.
        """
        self.write({'state': 'draft'})

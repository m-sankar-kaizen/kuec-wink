# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class BudgetTransferRequest(models.Model):
    """
    Model to handle internal budget transfer requests between two budget lines
    within the organization. Each request contains multiple lines defining the
    source (decrease) and target (increase) budget lines.

    States:
    - draft: Initial state, editable.
    - first_approve: Approved at first level.
    - second_approve: Fully approved, budget lines are modified.
    - rejected: Rejected state, no budget change happens.
    """

    _name = 'budget.transfer.request'
    _description = 'Budget Transfer Request'

    justification = fields.Text(
        string="Justification",
        readonly=True,
        help="Reason for initiating the budget transfer request."
    )

    requister_id = fields.Many2one(
        comodel_name='res.users',
        string='Requister',
        help="User who initiated the transfer request."
    )

    name = fields.Char(
        string="Name",
        required=True,
        copy=False,
        default='/',
        help="Unique identifier for this transfer request, auto-generated from sequence."
    )

    requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string="Requisition",
        readonly=True,
        help="Reference to the associated material purchase requisition, if applicable."
    )

    line_ids = fields.One2many(
        'budget.transfer.request.line',
        'budget_transfer_request_id',
        string="Lines",
        help="Lines describing how the budget is reallocated."
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('first_approve', 'First Approve'),
        ('second_approve', 'Approved'),
        ('rejected', 'Rejected')
    ], string="State", default='draft', help="Current approval state of this request.")

    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now(),
        readonly=True,
        help="Datetime when the request was created."
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Overrides create to automatically assign a sequence-based name.
        """
        for vals in vals_list:
            vals['name'] = self.env[
                'ir.sequence'].next_by_code('budget.transfer.request')
        return super().create(vals_list)

    def unlink(self):
        """
        Prevents deletion of approved or rejected records.
        Only draft state records can be deleted.
        """
        for record in self:
            if record.state != 'draft':
                raise UserError(_("You cannot delete a record that is not in draft state."))
        return super(BudgetTransferRequest, self).unlink()

    def button_first_approve(self):
        """
        Moves the request to the 'first_approve' state.
        """
        self.state = 'first_approve'

    def button_second_approve(self):
        """
        Final approval action:
        - Validates that all lines have source (decrease) budgets.
        - Validates that the requested amount does not exceed available.
        - Adjusts the `masked_planned_amount` of both decrease and increase lines.
        - Recomputes budget warning on associated requisition.
        """
        for line in self.line_ids:
            if not line.decrease_budget_id:
                raise ValidationError(_("You must select a budget to decrease from"))

        for line in self.line_ids:
            available_amount = abs(line.decrease_budget_id.budget_amount) - abs(
                line.decrease_budget_id.achieved_amount)
            if line.amount > available_amount:
                raise ValidationError(_(
                    f"The amount requested is greater than the remaining amount in budget {line.decrease_budget_id.display_name}.\n"
                    f"Please reduce the amount or select another cost center in 'Decrease Budget' field."
                ))

        # Perform budget reallocation
        for line in self.line_ids:
            # Increase the planned amount on the target budget line
            line.increase_budget_id.masked_planned_amount += line.amount
            line.increase_budget_id._onchange_masked_planned_amount()

            # Decrease the planned amount on the source budget line
            line.decrease_budget_id.masked_planned_amount -= line.amount
            line.decrease_budget_id._onchange_masked_planned_amount()

        # Recalculate warnings if any on the requisition
        self.requisition_id._compute_budget_warning_message()

        # Move to final approval
        self.state = 'second_approve'

    def reject(self):
        """
        Rejects the request, moves to 'rejected' state.
        """
        self.state = 'rejected'

    def reset_to_draft(self):
        """
        Resets the request to draft for editing or resubmission.
        """
        self.state = 'draft'

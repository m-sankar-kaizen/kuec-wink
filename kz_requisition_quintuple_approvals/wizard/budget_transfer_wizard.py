# -*- coding: utf-8 -*-
from odoo import models, fields, _, Command
from odoo.exceptions import ValidationError


class BudgetTransferWizard(models.TransientModel):
    """
    Transient model implementing the budget transfer wizard.

    This wizard manages multiple budget transfer lines related to a purchase requisition,
    allowing users to justify and request transfers between budget lines.

    Fields:
        line_ids (One2many): List of budget transfer lines linked to this wizard.
        requisition_id (Many2one): Reference to the related purchase requisition.
        date (Datetime): Date of the transfer request, defaults to current datetime, readonly.
        justification (Text): Justification text required to explain the transfer.

    Methods:
        transfer():
            Validates data and creates a budget.transfer.request record with the details.

        _prepare_lines():
            Prepares and formats budget transfer lines for the creation of the transfer request.
    """

    _name = 'budget.transfer.wizard'
    _description = 'Transfer Wizard'

    line_ids = fields.One2many(
        'budget.transfer.line', 'wizard_id', string="Lines",
        help="Budget transfer lines detailing amounts and budget sources/targets.")

    requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string='Requisition',
        readonly=True,
        help="Purchase requisition related to this budget transfer.")

    date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now,
        readonly=True,
        help="Date and time when the transfer is requested.")

    justification = fields.Text(
        string="Justification",
        help="Explanation for the budget transfer request, mandatory field.")

    def transfer(self):
        """
        Validates the budget transfer wizard data and creates a corresponding budget transfer request.

        Validation steps:
            - 'justification' must be filled.
            - Each transfer line must have a decrease budget selected.
            - Requested amount must not exceed the remaining amount in the decrease budget.

        Raises:
            ValidationError: If any validation fails.

        On successful validation:
            Creates a 'budget.transfer.request' record with the requisition, lines, date,
            user who requested, and justification.
        """
        if not self.justification:
            raise ValidationError(_("Justification field is mandatory"))

        for line in self.line_ids:
            if not line.decrease_budget_id:
                raise ValidationError(_("You must select a budget to decrease from"))

        for line in self.line_ids:
            max_amount = abs(line.decrease_budget_id.budget_amount) - abs(
                line.decrease_budget_id.achieved_amount)
            if line.amount > max_amount:
                raise ValidationError(_(
                    f"The amount requested is bigger than the remaining amount in budget "
                    f"{line.decrease_budget_id.display_name}.\n"
                    f"Please decrease the amount or select another cost center in the 'Decrease Budget' field."
                ))

        if self.requisition_id:
            vals_dict = {
                'requisition_id': self.requisition_id.id,
                'line_ids': self._prepare_lines(),
                'date': self.date,
                'requister_id': self.env.user.id,
                'justification': self.justification,
            }
            self.env['budget.transfer.request'].create(vals_dict)

    def _prepare_lines(self):
        """
        Prepare the data lines for creating a budget transfer request.

        Converts each line in the wizard into a dict suitable for One2many creation.

        Returns:
            List of command tuples for One2many 'line_ids' creation.
        """
        prepared_lines = []
        for line in self.line_ids:
            prepared_lines.append(Command.create({
                'increase_budget_id': line.increase_budget_id.id if line.increase_budget_id else False,
                'amount': line.amount,
                'decrease_budget_id': line.decrease_budget_id.id if line.decrease_budget_id else False,
            }))
        return prepared_lines

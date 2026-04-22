# -*- coding: utf-8 -*-
import ast
import re

from odoo import models, fields, Command


class RejectWarningWizard(models.TransientModel):
    """
    Transient wizard model to handle rejection warnings and approval workflows
    for purchase requisitions.

    This wizard supports two modes:
        - Reject: Allows the user to enter remarks and reject the requisition.
        - Approve: Opens a budget transfer wizard to handle over-budget approvals.

    Attributes:
        requisition_id (Many2one): Reference to the related purchase requisition.
        mode (Selection): Operation mode, either 'reject' or 'approve'.
        remarks (Text): User remarks entered when rejecting the requisition.
        message (Text, related): Read-only message showing budget warnings from the requisition.

    Methods:
        confirm():
            Executes the confirmation action based on the selected mode.
            For 'reject', it posts remarks as a chatter message and rejects the requisition.
            For 'approve', it opens a budget transfer wizard to continue the approval workflow.

        _get_transfer_wizard():
            Creates and returns an action dictionary to open the budget transfer wizard
            pre-filled with data from the current requisition.

        _prepare_lines():
            Prepares the budget transfer lines based on the over-budget data
            stored in the requisition's over_budget_text field.

        _get_list_ids(text):
            Parses a string representing budget increase requests into a
            list of lists with numeric IDs and amounts.
    """

    _name = 'reject.warning.wizard'
    _description = 'Reject warning wizard'

    requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string='Requisition',
        required=False,
        help="Reference to the purchase requisition being approved or rejected.")

    mode = fields.Selection(
        string='Mode',
        selection=[('reject', 'Reject'),
                   ('approve', 'Approve')],
        required=False,
        help="Select 'Reject' to reject the requisition with remarks, or 'Approve' to proceed with budget transfer.")

    remarks = fields.Text(
        string="Remarks",
        required=False,
        help="Remarks or comments provided when rejecting the requisition.")

    message = fields.Text(
        string="Message",
        required=False,
        related='requisition_id.budget_warning_message',
        help="Related budget warning message from the requisition, read-only.")

    def confirm(self):
        """
        Execute the confirmation action based on the mode.

        If mode is 'reject':
            - Create a mail.message record with the rejection remarks linked to the requisition.
            - Call 'reject_requisition' on the requisition with a context flag 'reject_anyway' to force rejection.

        If mode is 'approve':
            - Opens the budget transfer wizard by returning the action dictionary from _get_transfer_wizard().
            - (Note: The original approve button_approve() call is commented out, implying approval is handled post transfer.)

        Returns:
            - An action dictionary opening the budget transfer wizard (if approving).
            - None otherwise.
        """
        if self.mode == 'reject':
            if self.remarks and self.requisition_id:
                # Post remarks as a chatter message on the requisition
                vals_dict = {
                    'body': self.remarks,
                    'model': 'material.purchase.requisition',
                    'res_id': self.requisition_id.id,
                    'message_type': 'comment',
                    'create_uid': self.env.user.id,
                }
                self.env['mail.message'].sudo().create(vals_dict)
            # Reject the requisition forcibly with context
            self.requisition_id.with_context(reject_anyway=True).reject_requisition()

        if self.mode == 'approve':
            # Open budget transfer wizard to continue approval
            return self._get_transfer_wizard()
            # Uncomment if direct approval without transfer is needed
            # self.requisition_id.with_context(approve_anyway=True).button_approve()

    def _get_transfer_wizard(self):
        """
        Prepare and return the action to open the budget transfer wizard.

        The wizard is created with:
            - requisition_id set to the current requisition.
            - line_ids prepared from the over-budget text of the requisition.
            - justification initially empty.

        Returns:
            A dictionary representing an ir.actions.act_window to open the budget transfer wizard form.
            Returns None if requisition_id is not set.
        """
        if self.requisition_id:
            print('mleeekkkaaa')
            wizard = self.env['budget.transfer.wizard'].create({
                'requisition_id': self.requisition_id.id,
                'line_ids': self._prepare_lines(),
                'justification': "",
            })
            return {
                'name': 'Budget Transfer',
                'type': 'ir.actions.act_window',
                'res_model': 'budget.transfer.wizard',
                'view_mode': 'form',
                'view_id': self.env.ref(
                    'kz_requisition_quintuple_approvals.view_transfer_wizard_form').id,
                'target': 'new',
                'res_id': wizard.id,
            }
        else:
            return None

    def _prepare_lines(self):
        """
        Prepare budget transfer lines based on the requisition's over_budget_text.

        Parses the over_budget_text to extract budget increase requests
        and formats them as a list of command tuples suitable for one2many fields.

        Returns:
            A list of tuples [Command.create({...}), ...] representing new records for budget transfer lines.
            Returns None if no over_budget_text is present.
        """
        if self.requisition_id.over_budget_text:
            print('self.requisition_id.over_budget_text', self.requisition_id.over_budget_text)
            list_ids = self._get_list_ids(self.requisition_id.over_budget_text)
            print('list_ids', list_ids)

            prepared_lines = []
            for line in list_ids:
                increase_budget_id, amount = line
                prepared_lines.append({
                    'increase_budget_id': increase_budget_id,
                    'amount': amount,
                })
            return [Command.create(line) for line in prepared_lines]

    def _get_list_ids(self, text):
        """
        Parse a string representation of budget increase data into a structured list.

        The input text is expected to be a string resembling a list of lists, e.g.
        "[[123, 1000.0], [456, 2000]]" or using slashes and spaces like "123 / 1000.0, 456 / 2000".

        Steps:
            - Replace occurrences of '/' surrounded by spaces with ','.
            - Ensure the string starts and ends with square brackets.
            - Use ast.literal_eval for safe evaluation into a Python list.
            - Convert numeric values to int or float as appropriate.

        Args:
            text (str): The input string to parse.

        Returns:
            list of list: Parsed list with inner lists containing numeric budget IDs and amounts.

        Raises:
            ValueError: If the string cannot be parsed into a valid Python list.
        """
        # Replace ' / ' with ',' for easier parsing

        print('text', text)

        text = re.sub(r'\s*/\s*', ',', text)

        print('text', text)

        # Ensure the text looks like a Python list literal
        if not (text.startswith('[') and text.endswith(']')):
            text = '[' + text + ']'

        try:
            result = ast.literal_eval(text)
        except (SyntaxError, ValueError) as e:
            raise ValueError(f"Error parsing the text: {e}")

        # Convert each item in the nested lists to int or float as needed
        final_result = [
            [float(item) if '.' in str(item) else int(item) for item in sublist]
            for sublist in result
        ]

        return final_result

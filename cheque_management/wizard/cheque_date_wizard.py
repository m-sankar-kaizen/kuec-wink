""" Initialize Cheque Date """

from odoo import fields, models


class ChequeDateWizard(models.TransientModel):
    """
        Initialize Cheque Date:
         -
    """
    _name = 'cheque.date.wizard'
    _description = 'Cheque Date Wizard'

    cheque_received_date = fields.Date()
    cheque_send_date = fields.Date()
    deposit_date = fields.Date()
    bank_account_id = fields.Many2one(
        'account.journal', domain="[('type', '=', 'bank')]",
    )
    cheque_management_id = fields.Many2one(
        'cheque.management'
    )
    button_type = fields.Char()
    cash_type = fields.Char()
    cash_date = fields.Date()
    collected_by_another_bank_treasury = fields.Many2one(
        'account.journal', domain="[('type', '=', ['bank','cash'])]",
        string='Collected By Another Bank/Treasury'
    )
    deducted_by_another_bank_treasury = fields.Many2one(
        'account.journal', domain="[('type', '=', ['bank','cash'])]",
        string='Deducted By Another Bank/Treasury'
    )
    bounced_date = fields.Date()
    return_to_partner_date = fields.Date()
    return_from_partner_date = fields.Date()

    def confirm(self):
        """ Confirm """
        if self.button_type == 'confirm':
            self.cheque_management_id.confirm(self.cheque_received_date)
        if self.button_type == 'send_to_bank':
            self.cheque_management_id.send_to_bank(self.cheque_send_date,
                                                   self.bank_account_id)
        if self.button_type == 'in_deposit':
            self.cheque_management_id.in_deposit(self.deposit_date)
        if self.button_type == 'out_deposit':
            self.cheque_management_id.out_deposit(self.deposit_date)
        if self.button_type == 'cashed':
            self.cheque_management_id.cashed(
                self.cash_date,
                self.collected_by_another_bank_treasury,
                self.deducted_by_another_bank_treasury,
            )
        if self.button_type == 'in_bounced':
            self.cheque_management_id.in_bounced(self.bounced_date)
        if self.button_type == 'out_bounced':
            self.cheque_management_id.out_bounced(self.bounced_date)
        if self.button_type == 'return_to_partner':
            self.cheque_management_id.return_to_partner(
                self.return_to_partner_date)
        if self.button_type == 'return_from_partner':
            self.cheque_management_id.return_from_partner(
                self.return_from_partner_date)

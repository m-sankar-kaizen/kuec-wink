from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_intercompany_payment = fields.Boolean(
        related='journal_id.is_intercompany_payment', store=True)
    intercompany_id = fields.Many2one(
        related='journal_id.intercompany_id', store=True)
    intercompany_account_ids = fields.Many2many('account.account',
                                                string='Intercompany Accounts',
                                                compute="_get_intercompany_accounts")
    intercompany_account_id = fields.Many2one(comodel_name='account.account')
    intercompany_journal_id = fields.Many2one('account.journal', string='Intercompany Journal')
    cheque_number = fields.Char(string='Cheque Number', copy=False)
    
    # is_cheque = fields.Boolean(
    #     string='Is Cheque',
    #     compute='_compute_is_cheque',
    # )


    def _create_payments(self):
        payments = super(AccountPaymentRegister, self.with_context(
                intercompany_account_id=self.intercompany_account_id.id
            )
            )._create_payments()
        moves = self.line_ids.move_id
        if self.is_intercompany_payment and moves and len(moves) == 1:
            moves.update({'is_intercompany_payment': True, 'intercompany_paid_amount': self.amount})
        return payments

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        vals.update({
            'intercompany_account_id': self.intercompany_account_id.id,
            'intercompany_journal_id': self.intercompany_journal_id.id,
            'is_intercompany_payment': self.is_intercompany_payment,
        })
        return vals

    @api.depends('intercompany_journal_id', 'payment_type')
    def _get_intercompany_accounts(self):
        """
        Compute the intercompany accounts based on the selected journal.
        """
        for payment in self:
            if payment.intercompany_journal_id:
                if payment.payment_type == 'outbound':
                    payment.intercompany_account_ids = payment.intercompany_journal_id.outbound_payment_method_line_ids.mapped('payment_account_id')
                else:
                    payment.intercompany_account_ids = payment.intercompany_journal_id.inbound_payment_method_line_ids.mapped('payment_account_id')
            else:
                payment.intercompany_account_ids = False

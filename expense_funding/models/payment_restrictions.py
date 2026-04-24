from odoo import models
from odoo.exceptions import ValidationError


class AccountPaymentRestrictPost(models.Model):
    _inherit = 'account.payment'

    def _is_restricted_journal(self, journal):
        if self._context.get('expense_funding'):
            return False
        if not journal:
            return False
        if journal.is_petty_cash:
            return True
        if journal.type == 'credit':
            return True
        return False

    def post(self):
        for payment in self:
            if self._is_restricted_journal(payment.journal_id):
                raise ValidationError(
                    "Posting is not allowed: use the Expense Funding module to post payments using Petty Cash or Credit Card journals.")
        return super(AccountPaymentRestrictPost, self).post()

    def action_post(self):
        # compatibility: some versions use action_post
        for payment in self:
            if self._is_restricted_journal(payment.journal_id):
                raise ValidationError(
                    "Posting is not allowed: use the Expense Funding module to post payments using Petty Cash or Credit Card journals.")
        return super(AccountPaymentRestrictPost, self).action_post()


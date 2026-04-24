import logging
from odoo import models, fields, api, _, Command
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    is_intercompany_payment = fields.Boolean(
        string='IS Intercompany Payment',
        compute='_compute_is_intercompany_payment',
    )
    intercompany_move_id = fields.Many2one(string="Intercom Entry",
                                           comodel_name='account.move',
                                           copy=False)
    intercompany_id = fields.Many2one(related='journal_id.intercompany_id',
                                      store=True)
    intercompany_account_ids = fields.Many2many('account.account',
                                                string='Intercompany Accounts',
                                                compute="_get_intercompany_accounts")
    intercompany_account_id = fields.Many2one(comodel_name='account.account')
    intercompany_journal_id = fields.Many2one('account.journal',
                                              string='Intercompany Journal')
    # TODO: RMV
    cheque_number = fields.Char(string='Cheque Number', copy=False)

    @api.depends('intercompany_journal_id', 'payment_type')
    def _get_intercompany_accounts(self):
        """
        Compute the intercompany accounts based on the selected journal.
        """
        for payment in self:
            if payment.intercompany_journal_id:
                ic_journal = payment.intercompany_journal_id
                if payment.payment_type == 'outbound':
                    payment.intercompany_account_ids = ic_journal.outbound_payment_method_line_ids.mapped('payment_account_id')
                else:
                    payment.intercompany_account_ids = ic_journal.inbound_payment_method_line_ids.mapped('payment_account_id')
            else:
                payment.intercompany_account_ids = False

    def _num2words(self, number, lang):
        if num2words is None:
            _logger.warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        return num2words(number, lang=lang).title()

    @api.depends('journal_id')
    def _compute_is_intercompany_payment(self):
        for payment in self:
            payment.is_intercompany_payment = payment.journal_id.is_intercompany_payment

    def button_open_intercom_entry(self):
        self.ensure_one()
        return {
            'name': _("Intercom Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.intercompany_move_id.id,
        }

    def action_draft(self):
        result = super().action_draft()
        if self.intercompany_move_id.state in ['posted', 'cancel']:
            self.intercompany_move_id.button_draft()
            self.is_intercompany_payment = False
        return result

    def action_cancel(self):
        result = super().action_cancel()
        if self.intercompany_move_id.state in ['draft']:
            self.intercompany_move_id.button_cancel()
            self.is_intercompany_payment = False
        return result

    def action_post(self):
        result = super().action_post()
        ic_to_post = self.filtered(lambda p: p.intercompany_move_id and p.intercompany_move_id.state == 'draft')
        ic_to_create = self.filtered(lambda p: p.is_intercompany_payment and not p.intercompany_move_id)
        ic_to_post._ic_post()
        ic_to_create._ic_create()
        return result

    def _ic_post(self):
        for payment in self:
            inter_company_line = self.env.company.get_intercompany_line(self.intercompany_id.id)
            if not inter_company_line:
                raise ValidationError(
                    f"Unable to find a related line for the company '{self.intercompany_id.name}' in the current company '{self.env.company.name}'."
                )
            inter_company_account = inter_company_line.account_id

            move = payment.intercompany_move_id
            payment.date = self.date

            account_mapping = {
                'inbound': {'debit': self.intercompany_account_id.id, 'credit': inter_company_account.id},
                'outbound': {'debit': inter_company_account.id, 'credit': self.intercompany_account_id.id}
            }
            debit_account = account_mapping[payment.payment_type]['debit'] or self.env.context.get('intercompany_account_id')
            credit_account = account_mapping[payment.payment_type]['credit'] or self.env.context.get('intercompany_account_id')

            move_line_vals = [
                {'account_id': debit_account, 'debit': payment.amount, 'credit': 0, 'date': payment.date },
                {'account_id': credit_account, 'debit': 0, 'credit': payment.amount, 'date': payment.date },
            ]

            move.write(
                {
                    'cheque_due_date': self.cheque_due_date,
                    'cheque_number': self.custom_reference,
                    'other_intercompany_move': True,
                    'invoice_line_ids': [Command.clear()] +  [Command.create(line) for line in move_line_vals],
                }
            )
            move.sudo().action_post()

    def _ic_create(self):
        for payment in self:
            # Retrieve the inter_company line for the related company.
            inter_company_line = self.env.company.get_intercompany_line(self.intercompany_id.id)
            if not inter_company_line:
                raise ValidationError(
                    f"Unable to find a related line for the company '{self.intercompany_id.name}' in the current company '{self.env.company.name}'."
                )
            inter_company_account = inter_company_line.account_id
            inter_company_journal = inter_company_line.journal_id

            payment.date = self.date or fields.Date.context_today(self)

            # Create the intercompany move on the other company with selected account and journal
            move_vals = {
                'move_type': 'entry',
                'ref': self.memo,
                'company_id': self.intercompany_id.id,
                'journal_id': inter_company_journal.id,
                'invoice_date': payment.date,
                'date': payment.date,
                'other_intercompany_move': True,
            }

            account_mapping = {
                'inbound': {'debit': self.intercompany_account_id.id, 'credit': inter_company_account.id},
                'outbound': {'debit': inter_company_account.id, 'credit': self.intercompany_account_id.id}
            }
            debit_account = account_mapping[payment.payment_type]['debit'] or self.env.context.get('intercompany_account_id')
            credit_account = account_mapping[payment.payment_type]['credit'] or self.env.context.get('intercompany_account_id')
            move_line_vals = [
                {'account_id': debit_account, 'debit': payment.amount, 'credit': 0, 'date': payment.date, },
                {'account_id': credit_account, 'debit': 0, 'credit': payment.amount, 'date': payment.date, },
            ]

            move_vals['invoice_line_ids'] = [(0, 0, line) for line in move_line_vals]
            intercom_move = self.env['account.move'].sudo().create(move_vals)
            intercom_move.sudo().action_post()
            payment.write({'intercompany_move_id': intercom_move.id})

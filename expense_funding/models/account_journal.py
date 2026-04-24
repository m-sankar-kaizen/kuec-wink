from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    credit_card = fields.Char(string='Credit Card Number')
    maximum_credit_card = fields.Char(string='Maximum Spending limit')
    card_responsible_uid = fields.Many2one('hr.employee', string='Responsible')
    card_holder_uid = fields.Many2one('hr.employee', string='Holder')
    is_petty_cash = fields.Boolean(string='Is Petty Cash Journal')

    # New limits
    annual_limit = fields.Float(string='Annual Limit', help='Annual limit for this journal')
    single_transaction_limit = fields.Float(string='Single Transaction Limit', help='Maximum allowed per single transaction (for credit card journals)')

from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    default_petty_cash_journal_id = fields.Many2one('account.journal', string='Default Cash Journal')


class Configuration(models.TransientModel):
    _inherit = 'res.config.settings'

    company_default_petty_cash_journal_id = fields.Many2one(
        related='company_id.default_petty_cash_journal_id', readonly=False
    )

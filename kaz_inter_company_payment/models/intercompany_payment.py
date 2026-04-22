from odoo import models, fields, api


class InterCompanyPayment(models.Model):
    _name = 'inter.company_payment'

    parent_id = fields.Many2one('res.company')
    company_id = fields.Many2one('res.company')
    account_id = fields.Many2one('account.account')
    journal_id = fields.Many2one('account.journal')

    @api.onchange('company_id')
    def _onchange_company(self):
        self.account_id = False
        self.journal_id = False

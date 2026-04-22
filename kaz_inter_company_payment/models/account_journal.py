from odoo import models, fields, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    is_intercompany_payment = fields.Boolean(
        string='Is Intercompany Payment',
        copy=False,
        tracking=True)
    intercompany_id = fields.Many2one(
        comodel_name='res.company',
        string='Intercompany',
        copy=False)

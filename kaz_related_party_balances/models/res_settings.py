from odoo import models, fields


class ResSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    related_party_journal_id = fields.Many2one(
        'account.journal',
        related='company_id.related_party_journal_id',
        check_company=True,
        readonly=False)

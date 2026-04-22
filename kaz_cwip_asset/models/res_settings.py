from odoo import models, fields


class ResSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cwip_journal_id = fields.Many2one('account.journal',
                                      related="company_id.cwip_journal_id",
                                      domain="[('type', '=', 'general')]",
                                      check_company=True,
                                      readonly=False)


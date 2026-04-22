from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    cwip_journal_id = fields.Many2one('account.journal',
                                      domain="[('type', '=', 'general')]",
                                      check_company=True)

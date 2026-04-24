from odoo import models, fields


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    cwip_move_id = fields.Many2one('account.move')

    def show_cwip_journal_entry(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entry',
            'res_model': 'account.move',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.cwip_move_id.id,
        }

from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    cwip_asset_id = fields.Many2one('account.asset')

    def show_cwip_asset(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Asset',
            'res_model': 'account.asset',
            'view_mode': 'form',
            'target': 'current',
            'res_id': self.cwip_asset_id.id,
        }

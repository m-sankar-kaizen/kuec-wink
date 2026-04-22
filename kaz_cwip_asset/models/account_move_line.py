from odoo import models, fields, _


class AccountMove(models.Model):
    _inherit = 'account.move.line'

    def turn_as_asset_cwip(self):
        return {
            "name": _("CWIP Wizard"),
            "type": "ir.actions.act_window",
            "res_model": "cwip.wizard",
            "views": [[False, "form"]],
            "target": "new",
            "context": {
                'default_company_id': self.company_id.id},
        }

# -*- coding: utf-8 -*-
from odoo import fields, models, _


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    write_off_id = fields.Many2one('write.off.request', string='Write Off')

    def action_open_write_off(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Write Off'),
            'view_mode': 'form',
            'res_model': 'write.off.request',
            'views': [(False, 'form')],
            'res_id': self.write_off_id.id,
            'context': {'create': False},
        }

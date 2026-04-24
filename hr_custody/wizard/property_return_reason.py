from odoo import models, fields


class PropertyReturnReason(models.TransientModel):
    """
        Hr custody contract refuse wizard.
    """
    _name = 'property.return.reason'
    _description = 'Property Return Reason'

    def action_send_reason(self):
        """The function used to send
        rejection reason for the associated record."""
        reject_obj = self.env[self._context.get('model_id')].search(
            [('id', '=', self._context.get('reject_id'))])
        if 'renew' in self._context.keys():
            reject_obj.write({'state': 'approved',
                              'is_renew_reject': True,
                              'renew_rejected_reason': self.reason})
        else:
            if self._context.get('model_id') == 'hr.holidays':
                reject_obj.write({'rejected_reason': self.reason})
                reject_obj.action_refuse()
            else:
                reject_obj.write({'state': 'rejected',
                                  'rejected_reason': self.reason})

    reason = fields.Text(string="Reason", help="Add the reason")

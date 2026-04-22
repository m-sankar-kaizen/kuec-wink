# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class PurchaseOrderWink(models.Model):
    _inherit = 'purchase.order'

    wink_task_id = fields.Many2one(
        'project.task',
        string='WINK Task',
        readonly=True,
        ondelete='set null',
        help='The WINK delivery task this RFQ was generated from.',
    )

    def action_view_wink_task(self):
        """Open the linked WINK task from the smart button."""
        self.ensure_one()
        if not self.wink_task_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('WINK Task'),
            'res_model': 'project.task',
            'res_id': self.wink_task_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_create_vendor_subtask_from_rfq(self):
        """Create a vendor subtask on the linked WINK task.

        Sets the task vendor from the RFQ partner if not already assigned,
        then delegates to the task's subtask creation action.

        Returns:
            dict: Action to open the newly created vendor subtask form.
        """
        self.ensure_one()
        if not self.wink_task_id:
            raise UserError(_('No WINK task is linked to this RFQ.'))
        task = self.wink_task_id
        if not task.wink_vendor_id:
            task.sudo().write({'wink_vendor_id': self.partner_id.id})
        return task.action_create_vendor_subtask()

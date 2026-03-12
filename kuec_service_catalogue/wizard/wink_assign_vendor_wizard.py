# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WinkAssignVendorWizard(models.TransientModel):
    _name = 'wink.assign.vendor.wizard'
    _description = 'Assign Vendor & Create RFQ'

    task_id = fields.Many2one(
        'project.task',
        string='Task',
        required=True,
        help='The delivery task this vendor will be assigned to.',
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain=[('is_company', '=', True)],
        help='Select the vendor to deliver this task. A draft RFQ will be created automatically upon assignment.',
    )

    def action_assign(self):
        """Assign the selected vendor to the task and auto-create the RFQ."""
        self.ensure_one()
        task = self.task_id
        if not task.exists():
            raise UserError(_('The linked task no longer exists.'))
        # Set vendor — triggers rating sync via task.write()
        task.wink_vendor_id = self.vendor_id
        # Create the RFQ (discards the navigation action — user stays on task form)
        task.action_assign_vendor_rfq()
        return {'type': 'ir.actions.act_window_close'}

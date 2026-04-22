from odoo import models, fields


class OffCcleStaffingReason(models.Model):
    _name = 'off_cycle.staffing.reason'
    _description = 'Off-Cycle Staffing Reason'

    name = fields.Char(
        required=True)
    company_id = fields.Many2one('res.company',
                                 readonly=True,
                                 default=lambda self: self.env.company.id)

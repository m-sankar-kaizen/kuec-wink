from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employee_notice_period = fields.Integer(
        string='Employee Notice Period (Days)',
        related='company_id.employee_notice_period',
        readonly=False,
        help='Default notice period in days that employees must give before leaving the company.',
    )
    remind_for_x_days_before_notice_end = fields.Integer(
        string='Remind X Days Before Contract End',
        readonly=False,
        related='company_id.remind_for_x_days_before_notice_end',
        help='Number of days before the Contract end date to send a reminder.'
    )

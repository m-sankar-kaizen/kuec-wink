from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    employee_notice_period = fields.Integer(
        string='Employee Notice Period (Days)',
        default=14,
        help='Default notice period in days that employees must give before leaving the company.'
    )

    remind_for_x_days_before_notice_end = fields.Integer(
        string='Remind X Days Before Notice Period End',
        default=7,
        help='Number of days before the notice period end date to send a reminder.'
    )

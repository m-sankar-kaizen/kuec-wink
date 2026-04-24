
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Inherited the res_config_settings to add notice_period
    configurations."""
    _inherit = 'res.config.settings'

    notice_period = fields.Boolean(string='Notice Period',
                                   help='Enable to configure a notice period'
                                        ' for an employee.',
                                   config_parameter='hr_employee_updation.notice_period')
    no_of_days = fields.Integer(string='Notice Period Days',
                                help='Set the number of days for the notice'
                                     ' period.',
                                config_parameter='hr_employee_updation.no_of_days')

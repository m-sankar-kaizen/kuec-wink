from odoo import fields, models


class HrContract(models.Model):
    """This class extends the 'hr.contract' model to add a custom 'notice_days'
     field. The 'notice_days' field is used to store the notice period for HR
     contracts."""
    _inherit = 'hr.contract'

    def _default_notice_days(self):
        """Get the default notice period from the  configuration.
            :return: The default notice period in days.
            :rtype: int """
        return self.env['ir.config_parameter'].get_param(
            'hr_employee_updation.no_of_days') if self.env[
            'ir.config_parameter'].get_param(
            'hr_employee_updation.notice_period') else 0

    notice_days = fields.Integer(string="Notice Period",
                                 default=_default_notice_days,
                                 help="Number of days required for notice"
                                      " before termination.")

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'


    probation_period_days = fields.Integer(
        string='Probation Period (Days) (KUEC)',
        related='company_id.probation_period_days',
        readonly=False,
        default=90,
        help='X number of days to be probation period of any new comers.'
    )
    remind_for_x_days_before_probation_end = fields.Integer(
        string='Remind X Days Before Probation End (KUEC)',
        related='company_id.remind_for_x_days_before_probation_end',
        readonly=False,
        help='Number of days before the probation end date to send a reminder.'
    )

    maximum_probation_extension_period = fields.Integer(
        string='Maximum Probation Extension Period (Days) (KUEC)',
        related='company_id.maximum_probation_extension_period',
        readonly=False,
        default=30,
        help='Maximum number of days to which the probation period can be extended.'
    )

from odoo import models, fields


class HrContract(models.Model):
    _inherit = 'hr.contract'

    probation_end_date = fields.Date(string='Probation End Date',
                                     related='employee_id.probation_end_date',
                                     help='End date of the probation '
                                          'period for this contract.')
from odoo import models, fields, api


class HrInternshipFeedback(models.Model):
    _inherit = 'hr.internship.feedback'

    probation_employee_id = fields.Many2one('hr.employee',
                                            string='Employee on Probation')

    internship_id = fields.Many2one('hr.internship',
                                    required=False)

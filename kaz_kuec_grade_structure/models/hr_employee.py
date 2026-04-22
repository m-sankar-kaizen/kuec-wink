from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    kuec_grade_id = fields.Many2one('kuec.grade',
                                    related='job_id.kuec_grade_id')
    company_code = fields.Selection(related='company_id.company_code')


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    kuec_grade_id = fields.Many2one('kuec.grade',
                                    related='employee_id.kuec_grade_id')
    company_code = fields.Selection(related='employee_id.company_code')



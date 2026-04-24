from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    company_code = fields.Selection(
        related='company_id.company_code')

    kaz_employee_type = fields.Selection(
        string='Nationality Status',
    )


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    company_code = fields.Selection(
        related='employee_id.company_code')

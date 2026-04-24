from odoo import models, fields, api
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    age = fields.Float(string='Age', compute='_compute_age', store=True)

    @api.model
    def _cron_compute_employee_age(self):
        employees = self.search([('birthday', '!=', False)])
        employees._compute_age()

    @api.depends('birthday')
    def _compute_age(self):
        today = fields.Date.context_today(self)
        for employee in self:
            if employee.birthday:
                birth_date = employee.birthday
                employee.age = today.year - birth_date.year - (
                        (today.month, today.day) < (
                birth_date.month, birth_date.day)
                )
            else:
                employee.age = 0


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    age = fields.Float(string='Age', related='employee_id.age')

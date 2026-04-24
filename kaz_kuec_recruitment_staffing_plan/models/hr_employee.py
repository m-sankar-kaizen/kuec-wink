from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    approved_hiring_request_id = fields.Many2one(
        'hr.recruitment.requests',
        readonly=True)


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    approved_hiring_request_id = fields.Many2one(
        'hr.recruitment.requests',
        related='employee_id.approved_hiring_request_id')

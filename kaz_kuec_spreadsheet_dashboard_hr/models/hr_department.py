from odoo import models, fields, api


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    average_age = fields.Float(
        compute="_compute_avg_age",
        group_operator="avg",
        store=True)

    @api.depends('member_ids',
                 'member_ids.age',
                 'member_ids.department_id',
                 'member_ids.active')
    def _compute_avg_age(self):
        for department in self:
            employees = department.member_ids.filtered(
                lambda e: e.active and e.age and e.birthday
            )
            department.average_age = (
                sum(employees.mapped('age')) / len(employees)
                if employees else 0.0
            )


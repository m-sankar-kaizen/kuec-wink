from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    warning_count = fields.Integer(compute='_compute_warning_count', string="Notice")

    def _compute_warning_count(self):
        for employee in self:
            employee.warning_count = self.env['hr.disciplinary.action'].search_count([
                ('employee_id', '=', employee.id)
            ])

    def action_open_warning(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Disciplinary Action',
            'res_model': 'hr.disciplinary.action',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'target': 'current',
        }
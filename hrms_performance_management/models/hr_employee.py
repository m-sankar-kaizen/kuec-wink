from odoo import models, fields, api,_

class EmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    warning_count = fields.Integer(compute="_compute_warning_count")

    def _compute_warning_count(self):
        for rec in self:
            rec.warning_count = self.env['hrms.warning'].search_count([('employee_id','=',rec.id)])


    def action_goals_assignment(self):
        self.ensure_one()  # Ensure only one record is being processed
        return {
            'name': 'Goals Assignment',
            'type': 'ir.actions.act_window',
            'res_model': 'goals.assignment',
            'view_mode': 'form',
            'target': 'new', 
            'context': {
                'default_employee_id': self.id,  # Pre-fill employee field
                'from_employee_form': True,
            },
            'views': [(self.env.ref('hrms_performance_management.view_goals_assignment_form_main').id, 'form')],
        }
    
    def action_show_employee_warning(self):
        self.ensure_one()
        employee_warning = self.env['hrms.warning'].search([('employee_id','=',self.id)])
        if self.warning_count == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "hrms.warning",
                "views": [[False, "form"]],
                "res_id": employee_warning.id,
            }
        elif self.warning_count > 1:
            return {
                "name": _("Employee Warning"),
                "type": "ir.actions.act_window",
                "res_model": "hrms.warning",
                "view_mode": "list,form",
                "domain": [('employee_id', '=', self.id)],
            }
        
   


    

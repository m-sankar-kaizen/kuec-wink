from odoo import models, fields, api
from datetime import datetime, timedelta


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_employment_status = fields.Selection([
        ('probation', 'Under Probation'),
        ('employment', 'Under Employment'),
    ],
        store=True,
        compute='compute_employee_employment_status')

    is_extended = fields.Boolean()

    def action_extend_probation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Extend Probation',
            'res_model': 'extend.probation',
            'view_mode': 'form',
            'view_id': self.env.ref(
                'kaz_kuec_employee_probation.view_extend_probation_wizard_form'
            ).id,
            'target': 'new',
            'context': {
                'active_id': self.id,
                'active_model': self._name,
                'default_employee_id': self.id,
                'default_new_date': self.probation_end_date,
                'default_company_id': self.company_id.id,
                'default_existing_date': self.probation_end_date
            },
        }

    @api.depends('probation_end_date', 'hire_date')
    def compute_employee_employment_status(self):
        for employee in self:
            if employee.hire_date and employee.probation_end_date and employee.company_code == 'KUEC':
                today = fields.Date.context_today(employee)
                if today <= employee.probation_end_date:
                    employee.employee_employment_status = 'probation'
                else:
                    employee.employee_employment_status = 'employment'
            else:
                employee.employee_employment_status = False

    probation_end_date = fields.Date(compute='compute_probation_end_date',
                                     string='Probation End Date',
                                     readonly=False,
                                     store=True)

    @api.depends('hire_date', 'company_id.probation_period_days')
    def compute_probation_end_date(self):
        for employee in self:
            if employee.hire_date and employee.company_id.probation_period_days:
                probation_days = employee.company_id.probation_period_days
                employee.probation_end_date = employee.hire_date + \
                    timedelta(days=probation_days)
            else:
                employee.probation_end_date = False

    probation_feedback_ids = fields.One2many(
        'hr.internship.feedback',
        'probation_employee_id')

    resignation_id = fields.Many2one('register.form')

    def action_feedback_on_probation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Probation Feedback',
            'res_model': 'hr.internship.feedback',
            'view_mode': 'form',
            'view_id': self.env.ref('kaz_kuec_employee_probation.view_hr_internship_feedback_form_primary').id,
            'target': 'new',
            'context': {
                'default_probation_employee_id': self.id,
            },
        }

    def action_terminate_on_probation(self):
        self.ensure_one()
        resignation_form = self.env['register.form'].sudo().create({
            'name': self.id,
        })
        self.resignation_id = resignation_form
        action = self.env.ref('kaz_kuec_offboarding.action_ank_register_form').read()[0]
        action.update({
            "views": [[self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id, "form"]],
            "view_mode": "form",
            "target": "current",
            "context": {'create': False,
                        'edit': True,
                        'delete': True},
            "view_id": self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id,
            "res_id": resignation_form.id,
        })
        return action

    def open_related_resignation(self):
        self.ensure_one()
        action = self.env.ref('kaz_kuec_offboarding.action_ank_register_form').read()[0]
        action.update({
            "views": [[self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id, "form"]],
            "view_mode": "form",
            "target": "current",
            "context": {'create': False,
                        'edit': True,
                        'delete': False},
            "view_id": self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id,
            "res_id": self.resignation_id.id,
        })
        return action


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    probation_end_date = fields.Date(string='Probation End Date',
                                     related='employee_id.probation_end_date',
                                     help='End date of the probation period for this employee.')

    employee_employment_status = fields.Selection(
        related='employee_id.employee_employment_status')

    is_extended = fields.Boolean(related='employee_id.is_extended')

    resignation_id = fields.Many2one('register.form',
                                     related='employee_id.resignation_id')


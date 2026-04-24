from odoo import models, fields, _
from odoo.exceptions import ValidationError


class ResignationForm(models.Model):
    _inherit = 'register.form'

    employee_department_id = fields.Many2one('hr.department',
                                             string='Department',
                                             related='name.department_id')
    exit_interview_id = fields.Many2one('exit.interview') # done
    exit_clearance_id = fields.Many2one('exit.clearance') # done
    employee_settlement_id = fields.Many2one('hr.employee.settlements') #done

    def proceed_to_exit_interview(self):
        exit_interview = self.env['exit.interview'].create({
            'name': self.name.id,
            'resignation_form_id': self.id,
        })
        self.write({
            'exit_interview_id': exit_interview.id
        })
        employee_manager = self.name.parent_id or self.name.coach_id
        employee_manager_user = employee_manager.user_id or self.env.user
        self.env['mail.activity'].sudo().create({
            'summary': f'Please do the exit interview for {self.name.name}.',
            'activity_type_id': self.env.ref('kaz_kuec_offboarding.mail_activity_data_interview').id,
            'res_model_id': self.env['ir.model']._get_id(
                'exit.interview'),
            'res_id': exit_interview.id,
            'user_id': employee_manager_user.id
        })
        action = self.env.ref('kaz_kuec_offboarding.exit_interview_form').read()[0]
        action.update({
            "res_id": self.exit_interview_id.id,
            "context": {"create": False},
        })
        return action

    def action_view_exit_interview(self):
        action = self.env.ref('kaz_kuec_offboarding.exit_interview_form').read()[0]
        action.update({
            "res_id": self.exit_interview_id.id,
            "context": {"create": False},
        })
        return action

    def action_view_exit_clearance(self):
        action = self.env.ref('kaz_kuec_offboarding.exit_clearance_form').read()[0]
        action.update({
            "res_id": self.exit_clearance_id.id,
            "context": {"create": False},
        })
        return action

    def action_view_employee_settlement(self):
        action = self.env.ref('kaz_kuec_offboarding.hr_employee_settlements').read()[0]
        action.update({
            "res_id": self.employee_settlement_id.id,
            "context": {"create": False},
        })
        return action

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                raise ValidationError(
                    _("You can only delete resignation "
                      "forms in Draft or Cancel state.")
                )



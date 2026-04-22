from odoo import models, fields, _
from odoo.exceptions import ValidationError


class ExitInterview(models.Model):
    _inherit = 'exit.interview'

    resignation_form_id = fields.Many2one('register.form') # done
    exit_clearance_id = fields.Many2one('exit.clearance') # done
    employee_settlement_id = fields.Many2one('hr.employee.settlements') # done

    def has_pending_todo_activity(self):
        self.ensure_one()
        todo_type = self.env.ref('kaz_kuec_offboarding.mail_activity_data_interview')
        activity = self.env["mail.activity"].search([
            ("res_model_id", "=", self.env["ir.model"]._get(self._name).id),
            ("res_id", "=", self.id),
            ("activity_type_id", "=", todo_type.id),
            ("state", "=", "pending")
        ], limit=1)

        return bool(activity)

    def proceed_to_exit_clearance(self):

        activity_pending = self.has_pending_todo_activity()
        if activity_pending:
            raise ValidationError(
                _("You have pending Interview activities for this exit interview. "
                  "Please complete them before proceeding to exit clearance.")
            )
        exit_clearance = self.env['exit.clearance'].create({
            'name': self.name.id,
            'resignation_form_id': self.resignation_form_id.id,
            'exit_interview_id': self.id,
        })
        self.write({
            'exit_clearance_id': exit_clearance.id
        })
        self.resignation_form_id.exit_clearance_id = exit_clearance.id
        action = self.env.ref('kaz_kuec_offboarding.exit_clearance_form').read()[0]
        action.update({
            "res_id": exit_clearance.id,
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

    def action_view_resignation_form(self):
        action = self.env.ref('kaz_kuec_offboarding.action_ank_register_form').read()[0]
        action.update({
            "views": [[self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id, "form"]],
            "view_mode": "form",
            "view_id": self.env.ref(
                'kaz_kuec_offboarding.register_form_form_view').id,
            "res_id": self.resignation_form_id.id,
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


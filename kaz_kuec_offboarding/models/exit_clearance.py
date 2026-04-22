from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class ExitClearance(models.Model):
    _inherit = 'exit.clearance'

    exit_interview_id = fields.Many2one('exit.interview')# done
    resignation_form_id = fields.Many2one('register.form')# done
    employee_settlement_id = fields.Many2one('hr.employee.settlements')# done

    notifications = fields.Html(compute='_compute_notifications')

    def check_validations(self):
        employee_id = self.name.id
        errors = []

        def _check_block(model, domain, message):
            if self.env[model].search_count(domain):
                errors.append(message)

        _check_block(
            'hr.custody',
            [('employee_id', '=', employee_id), ('state', '=', 'approved')],
            _("• Employee has assigned assets. Please clear all assigned assets.")
        )
        _check_block(
            'credit.card.request',
            [('requester_emp_id', '=', employee_id),
             ('state', '=', 'complete'),
             ('settlement_state', '!=', 'full')
             ],
            _("• Employee has an active credit card. Please settle the credit card.")
        )
        _check_block(
            'petty.cash.request',
            [('requester_emp_id', '=', employee_id),
             ('state', '=', 'complete'),
             ('settlement_state', '!=', 'full')
             ],
            _("• Employee has an active petty cash. Please settle the petty cash.")
        )
        _check_block(
            'hr.loan',
            [('employee_id', '=', employee_id),
             ('state', '=', 'approve'),
             ('fully_paid', '=', False),
             ],
            _("• Employee has an active loan. Please settle the loan.")
        )

        return errors

    @api.depends('name')
    def _compute_notifications(self):
        for rec in self:
            errors = rec.check_validations()
            if errors:
                html_list = "".join(f"<br/>{msg}" for msg in errors)
                rec.notifications = f"""
                            <div class="alert alert-danger" style="font-size:14px;">
                                <strong>Employee Pending Items:</strong>
                                {html_list}
                            </div>
                        """
            else:
                rec.notifications = False

    def proceed_to_employee_settlement(self):
        self.ensure_one()
        errors = self.check_validations()
        if errors:
            error_message = _(
                "You cannot proceed to Employee Settlement due to the following issues:\n\n"
            ) + "\n".join(errors)
            raise ValidationError(error_message)

        employee_settlement = self.env['hr.employee.settlements'].create({
            'employee_id': self.name.id,
            'resignation_form_id': self.resignation_form_id.id,
            'exit_interview_id': self.exit_interview_id.id,
            'exit_clearance_id': self.id,
            'relieving_date': fields.Date.today(),
            'last_working_date': fields.Date.today(),
        })
        self.write({
            'employee_settlement_id': employee_settlement.id
        })
        self.exit_interview_id.employee_settlement_id = employee_settlement.id
        self.resignation_form_id.employee_settlement_id = employee_settlement.id

        action = self.env.ref('kaz_kuec_offboarding.hr_employee_settlements').read()[0]
        action.update({
            "res_id": employee_settlement.id,
            "context": {"create": False},
        })
        return action

    def action_view_employee_settlement_form(self):
        action = self.env.ref('kaz_kuec_offboarding.hr_employee_settlements').read()[0]
        action.update({
            "res_id": self.employee_settlement_id.id,
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

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                raise ValidationError(
                    _("You can only delete resignation "
                      "forms in Draft or Cancel state.")
                )

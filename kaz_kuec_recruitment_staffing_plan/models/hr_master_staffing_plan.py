from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HRMasterPlan(models.Model):
    _name = 'hr.master.plan'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Yearly Manpower Plan'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    deadline = fields.Date(default=fields.Date.today())
    fiscal_year_id = fields.Many2one('account.fiscal.year',
                                     domain="[('company_id', '=', company_id)]")
    date_start = fields.Date(tracking=True, related='fiscal_year_id.date_from')
    date = fields.Date(tracking=True, related='fiscal_year_id.date_to')
    department_ids = fields.Many2many(
        'hr.department',
        required=True,
        default=lambda self: self._default_departments())
    company_id = fields.Many2one(
        'res.company',
        readonly=True,
        default=lambda self: self.env.company)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Plan Open'),
        ('close', 'Plan Close'),
        ('active', 'Active'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('canceled', 'Canceled'),
    ],
        default='draft',
        tracking=True,
        copy=False)

    description = fields.Html()

    staffing_plan_details_ids = fields.One2many(
        'staffing.plan.details',
        'master_staffing_plan_id')

    staffing_plan_ids = fields.Many2many(
        'hr.staffing.plan',
        copy=False)

    @api.model
    def _default_departments(self):
        """Return all hr.department records as default."""
        return self.env[
            'hr.department'].search(['|',
                ('company_id', '=', False),
                ('company_id', '=', self.env.company.id),
                                         ]).ids

    def action_cancel(self):
        self.write({
            'status': 'canceled'
        })

    def action_close(self):
        self.write({
            'status': 'close'
        })

    def action_active(self):
        self.write({
            'status': 'active'
        })

    def rejected(self):
        self.write({
            'status': 'rejected'
        })

    def action_done(self):
        self.write({
            'status': 'done'
        })

    def reset_to_draft(self):
        self.write({
            'status': 'draft'
        })

    def action_request(self):
        self.ensure_one()
        for department in self.department_ids:
            if department.manager_id:
                department_staffing_plan = self.env['hr.staffing.plan'].sudo().create({
                    'name': 'Staffing Plan for ' + self.name,
                    'company_id': self.company_id.id,
                    'department_id': department.id,
                    'master_plan_id': self.id,
                    'fiscal_year_id': self.fiscal_year_id.id,
                    'date_start': self.date_start,
                    'date': self.date,
                })
                employee_user = department.manager_id.user_id or department.parent_id.manager_id.user_id
                if employee_user:
                    self.env['mail.activity'].sudo().create({
                        'summary': 'Please fill the Master Staffing Plan.',
                        'date_deadline': self.deadline,
                        'activity_type_id': self.env.ref(
                            'mail.mail_activity_data_todo').id,
                        'res_model_id': self.env['ir.model']._get_id(
                            'hr.staffing.plan'),
                        'res_id': department_staffing_plan.id,
                        'user_id': employee_user.id
                    })
                self.staffing_plan_ids = [(4, department_staffing_plan.id)]
        self.write({
            'status': 'open'
        })

    def view_master_staffing_plans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": 'hr.staffing.plan',
            "domain": [("id", "in", self.staffing_plan_ids.ids)],
            "name": _("Staffing Plans"),
        }

    def unlink(self):
        for rec in self:
            if rec.status not in ['draft', 'canceled']:
                raise ValidationError(
                    "Cannot delete staffing master plan which "
                    "are not in draft or canceled stage."
                )
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProcurementMasterPlan(models.Model):
    _name = 'procurement.master.plan'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Procurement Master Plan'
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    deadline = fields.Date(default=fields.Date.today)
    date_start = fields.Date(tracking=True)
    date = fields.Date(tracking=True)
    department_ids = fields.Many2many(
        'hr.department',
        required=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
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
        ('canceled', 'Canceled'),
    ],
        default='draft',
        tracking=True,
        copy=False)

    description = fields.Html()

    procurement_plan_item_ids = fields.One2many(
        'annual.department.procurement.plan.items',
        'master_plan_id', domain='[("status", "=", "submitted")]')

    department_procurement_plan_ids = fields.Many2many(
        'annual.department.procurement.plan',
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

    def action_done(self):
        self.write({
            'status': 'done'
        })

    def action_request(self):
        self.ensure_one()
        plan_ids = []
        for department in self.department_ids:
            department_procurement_plan = self.env[
                'annual.department.procurement.plan'].sudo().create({
                    'name': 'Annual Department Procurement Plan for ' + self.name,
                    'company_id': self.company_id.id,
                    'department_id': department.id,
                    'master_plan_id': self.id,
                    'employee_id': department.manager_id.id
                })
            plan_ids.append(department_procurement_plan.id)
            employee_user = department.manager_id.user_id
            if employee_user:
                self.env['mail.activity'].sudo().create({
                    'summary': 'Please fill the Annual Procurement Plan.',
                    'date_deadline': self.deadline or fields.Date.today(),
                    'activity_type_id': self.env.ref(
                        'mail.mail_activity_data_todo').id,
                    'res_model_id': self.env['ir.model']._get_id(
                        'annual.department.procurement.plan'),
                    'res_id': department_procurement_plan.id,
                    'user_id': employee_user.id
                })
        self.write({
            'department_procurement_plan_ids': [(6, 0, plan_ids)],
            'status': 'open'
        })

    def view_master_procurement_plans(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "list,form",
            "res_model": 'annual.department.procurement.plan',
            "context": {'create': False},
            "domain": [("id", "in", self.department_procurement_plan_ids.ids)],
            "name": _("Annual Department Procurement Plan"),
        }

    def unlink(self):
        for rec in self:
            if rec.status not in ['draft', 'canceled']:
                raise ValidationError(
                    "Cannot delete procurement master plan which "
                    "are not in draft or canceled stage."
                )


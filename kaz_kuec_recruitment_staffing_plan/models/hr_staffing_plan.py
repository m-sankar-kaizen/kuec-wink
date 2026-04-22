from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo import Command


class HrStaffingPlan(models.Model):
    _name = 'hr.staffing.plan'
    _description = 'Hr Staffing Plan'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    _check_company_auto = True
    _rec_name = 'number'

    _sql_constraints = [
        (
            'budget_line_unique',
            'unique(budget_line_id)',
            'Each Budget Line can be linked to only one Staffing Plan.'
        )
    ]

    def _get_default_department(self):
        department = self.env['hr.department'].sudo().search([
            ('manager_id.user_id', '=', self.env.user.id),
            ('company_id', 'in', [self.env.company.id, False])
        ], limit=1)
        return department.id

    name = fields.Char(required=True,
                       tracking=True,)
    number = fields.Char(readonly=True,
                         tracking=True,
                         copy=False)
    created_date = fields.Date(
        default=fields.Date.today(),
        readonly=True)
    fiscal_year_id = fields.Many2one('account.fiscal.year',
                                     domain="[('company_id', '=', company_id)]")

    date_start = fields.Date(
        tracking=True, related='fiscal_year_id.date_from')
    date = fields.Date(tracking=True, related='fiscal_year_id.date_to')
    department_id = fields.Many2one(
        'hr.department',
        domain="[('company_id', 'in', [company_id, False])]",
        default=_get_default_department,
        required=True,
        tracking=True)
    department_manager_id = fields.Many2one(
        'hr.employee',
        string="Department Manager",
        related='department_id.manager_id')
    assigned_to_id = fields.Many2one(
        'res.users',
        string="Manager User",
        related='department_manager_id.user_id')
    company_id = fields.Many2one('res.company',
                                 readonly=True,
                                 copy=False,
                                 default=lambda self: self.env.company.id)
    budget_line_id = fields.Many2one('budget.line')
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  string="Currency")
    status = fields.Selection([
        ('draft', "Draft"),
        ('confirmed', "Confirmed"),
        ('approved', "Approved"),
        ('done', "Done"),
        ('rejected', "Rejected"),
        ('canceled', "Canceled")
    ],
        tracking=True,
        default='draft',
        copy=False
    )

    existing_plan_ids = fields.Many2many('existing.staffing.plan',
                                         compute='_compute_existing_plan_ids')

    @api.depends('department_id')
    def _compute_existing_plan_ids(self):
        Job = self.env['hr.job']
        Employee = self.env['hr.employee']
        ExistingPlan = self.env['existing.staffing.plan']

        for rec in self:
            rec.existing_plan_ids = [Command.clear()]
            plans = ExistingPlan
            if not rec.department_id:
                rec.existing_plan_ids = plans
                continue
            jobs = Job.search([
                ('department_id', '=', rec.department_id.id)
            ])
            for job in jobs:
                employees = Employee.search([
                    ('job_id', '=', job.id),
                    ('active', '=', True)
                ])
                employee_count = len(employees)
                total_salary = sum(
                    emp.contract_id.wage
                    for emp in employees
                    if emp.contract_id
                )
                plan = ExistingPlan.create({
                    'department_id': rec.department_id.id,
                    'position_id': job.id,
                    'no_of_employees': employee_count,
                    'company_id': rec.company_id.id,
                    'salaries': total_salary,
                })

                plans |= plan
            rec.existing_plan_ids = plans

    staffing_plan_ids = fields.One2many('staffing.plan.details',
                                        'staffing_plan_id')

    recruitment_request_ids = fields.One2many('hr.recruitment.requests',
                                              'staffing_plan_id')
    job_position_request_ids = fields.One2many('hr.job.position.request',
                                               'staffing_plan_id')
    master_plan_id = fields.Many2one('hr.master.plan')
    master_plan_status = fields.Selection(related='master_plan_id.status')

    confirmed_id = fields.Many2one('res.users',
                                   string="Confirmed By",
                                   tracking=True)
    approved_id = fields.Many2one('res.users',
                                  string="Approved By",
                                  tracking=True)
    rejected_id = fields.Many2one('res.users',
                                  string="Rejected By",
                                  tracking=True)
    done_id = fields.Many2one('res.users',
                              string="Done By",
                              tracking=True)
    canceled_id = fields.Many2one('res.users',
                                  string="Canceled By",
                                  tracking=True)

    confirmed_date = fields.Date(tracking=True)
    approved_date = fields.Date(tracking=True)
    rejected_date = fields.Date(tracking=True)
    done_date = fields.Date(tracking=True)
    canceled_date = fields.Date(tracking=True)
    description = fields.Html(tracking=True)

    warning_info = fields.Html(string="Warning information",
                               compute='_compute_warning_info')

    @api.depends('budget_line_id',
                 'staffing_plan_ids',
                 'staffing_plan_ids.total_estimated_cost')
    def _compute_warning_info(self):
        for rec in self:
            rec.warning_info = ''
            if rec.budget_line_id and rec.staffing_plan_ids:
                if rec.budget_line_id.masked_planned_amount < sum(rec.staffing_plan_ids.mapped('total_estimated_cost')):
                    rec.warning_info = 'Total Estimate for staffing exceeded the planned amount for Budget.'

    @api.constrains('department_id')
    def constrains_department(self):
        for rec in self:
            if not rec.department_manager_id:
                raise ValidationError(_(f'Please choose the manager'
                                        f' of the department - {rec.department_id.name}.'))
            if not rec.assigned_to_id:
                raise ValidationError(_(f'Please choose a user for '
                                        f'the manager of the department - {rec.department_id.name}.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            number = self.env['ir.sequence'].next_by_code(
                'hr.staffing.plan')
            vals.update({
                'number': number
            })
            vals['number'] = number
        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.status not in ['canceled']:
                raise ValidationError(_('Cannot delete staffing plan'
                                        ' which is not canceled.'))

    def action_confirm(self):
        self.ensure_one()
        self.write({
            'confirmed_id': self.env.user.id,
            'confirmed_date': fields.Date.today(),
            'status': 'confirmed'
        })

    def action_cancel(self):
        self.ensure_one()
        self.write({
            'canceled_id': self.env.user.id,
            'canceled_date': fields.Date.today(),
            'status': 'canceled'
        })

    def action_approve(self):
        self.ensure_one()
        self.write({
            'approved_id': self.env.user.id,
            'approved_date': fields.Date.today(),
            'status': 'approved'
        })

    def action_reject(self):
        self.ensure_one()
        self.write({
            'rejected_id': self.env.user.id,
            'rejected_date': fields.Date.today(),
            'status': 'rejected'
        })

    def action_done(self):
        self.ensure_one()
        self.write({
            'done_id': self.env.user.id,
            'done_date': fields.Date.today(),
            'status': 'done'
        })

    def action_reset(self):
        self.ensure_one()
        self.write({
            'status': 'draft'
        })

    def action_create_recruitment_requests(self):
        self.ensure_one()
        staffing_plans = self.staffing_plan_ids
        if self.master_plan_status != 'active':
            raise ValidationError(_('Cannot create recruitment requests '
                                    'if the master plan is not active.'))

        for rec in staffing_plans:
            if not rec.request_new_position:
                self.env['hr.recruitment.requests'].create({
                    'department_id': self.department_id.id,
                    'job_position_id': rec.position_id.id,
                    'priority': rec.priority,
                    'expected_employees': rec.vacancies,
                    'staffing_plan_id': self.id,
                    'expected_start_date': self.date_start,
                })
            elif rec.request_new_position:
                self.env['hr.job.position.request'].create({
                    'position_name': rec.new_position_name,
                    'department_id': self.department_id.id,
                    'company_id': self.company_id.id,
                    'requester_id': self.create_uid.id,
                    'target': rec.vacancies,
                    'staffing_plan_id': self.id
                })

    def action_show_recruitment_requests(self):
        return {
            "name": _("Recruitment Requests"),
            "type": "ir.actions.act_window",
            "res_model": "hr.recruitment.requests",
            'domain': [
                ('id', 'in', self.recruitment_request_ids.ids)],
            'views': [(False, 'list'), (False, 'form')],
            "target": "current",
        }

    def action_show_job_position_requests(self):
        return {
            "name": _("Job Position Request"),
            "type": "ir.actions.act_window",
            "res_model": "hr.job.position.request",
            'domain': [
                ('id', 'in', self.job_position_request_ids.ids)],
            'views': [(False, 'list'), (False, 'form')],
            "target": "current",
        }

    total_cost_new_old = fields.Monetary(compute='_compute_total_cost_new_old',
                                         currency_field='currency_id')

    total_estimation_per_year = fields.Float(
                                                string='Total Cost (New + Existing) Per Year',
                                                compute='_compute_total_cost_new_old_per_year')

    @api.depends('total_cost_new_old')
    def _compute_total_cost_new_old_per_year(self):
        for rec in self:
            rec.total_estimation_per_year = rec.total_cost_new_old * 12

    @api.depends('staffing_plan_ids',
                 'staffing_plan_ids.new_total_cost_per_employee',
                 'existing_plan_ids',
                 'existing_plan_ids.salaries')
    def _compute_total_cost_new_old(self):
        for rec in self:
            total_new = sum(rec.staffing_plan_ids.mapped(
                'new_total_cost_per_employee'))
            total_old = sum(rec.existing_plan_ids.mapped('salaries'))
            rec.total_cost_new_old = total_new + total_old


class StaffingPlanDetails(models.Model):
    _name = 'staffing.plan.details'
    _description = 'Staffing Plan Details'

    master_staffing_plan_id = fields.Many2one('hr.master.plan',
                                              store=True,
                                              related='staffing_plan_id.master_plan_id')
    staffing_plan_id = fields.Many2one('hr.staffing.plan')
    department_id = fields.Many2one('hr.department',
                                    related="staffing_plan_id.department_id")
    request_new_position = fields.Boolean()
    new_position_name = fields.Char()
    company_id = fields.Many2one('res.company',
                                 related='staffing_plan_id.company_id')
    currency_id = fields.Many2one('res.currency',
                                  related='staffing_plan_id.currency_id')
    priority = fields.Selection([('0', 'Low'),
                                 ('1', 'Normal'),
                                 ('2', 'High'),
                                 ('3', 'Urgent')], default='0')
    position_id = fields.Many2one('hr.job',
                                  domain="['&', '|', ('department_id', '=', department_id), ('department_id', '=', False), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    number_of_position = fields.Integer(compute='compute_number_of_position', string="Total Employees")

    @api.depends('position_id', 'request_new_position')
    def compute_number_of_position(self):
        for rec in self:
            rec.number_of_position = 0
            if not rec.request_new_position and rec.position_id:
                rec.number_of_position = len(rec.position_id.employee_ids)

    vacancies = fields.Integer()
    estimated_cost = fields.Monetary(
        string="Average Salary Per Month",
        currency_field='currency_id',
        compute='compute_average_cost')

    @api.depends('position_id', 'request_new_position')
    def compute_average_cost(self):
        for rec in self:
            rec.estimated_cost = 0
            if not rec.request_new_position and rec.position_id:
                employees = rec.position_id.employee_ids.filtered(
                    lambda emp: emp.contract_id)
                total_wage = sum(emp.contract_id.wage for emp in employees)
                emp_count = len(employees)
                if emp_count > 0:
                    rec.estimated_cost = total_wage / emp_count

    total_estimated_cost = fields.Monetary(compute='compute_sub_total',
                                           string="Total Salary Per Month",
                                           currency_field='currency_id')

    @api.depends('position_id', 'request_new_position')
    def compute_sub_total(self):
        for rec in self:
            rec.total_estimated_cost = 0
            if not rec.request_new_position and rec.position_id:
                employees = rec.position_id.employee_ids.filtered(
                    lambda emp: emp.contract_id)
                total_wage = sum(emp.contract_id.wage for emp in employees)
                rec.total_estimated_cost = total_wage

    new_average_cost_per_employee = fields.Monetary(currency_field='currency_id')
    new_total_cost_per_employee = fields.Monetary(currency_field='currency_id',
                                                  compute='_compute_total_cost')

    @api.depends('new_average_cost_per_employee', 'vacancies')
    def _compute_total_cost(self):
        for rec in self:
            rec.new_total_cost_per_employee = rec.new_average_cost_per_employee * rec.vacancies


class ExistingStaffingPlan(models.Model):
    _name = 'existing.staffing.plan'
    _description = 'Existing Staffing Plan'
    _rec_name = 'position_id'

    department_id = fields.Many2one(
        'hr.department',
        required=True
    )
    position_id = fields.Many2one('hr.job')
    no_of_employees = fields.Integer('Total Employees')
    avg_salary = fields.Monetary(currency_field='currency_id',
                                 string='Average Salary Per Month',
                                 compute='_compute_avg_salary')
    salaries = fields.Monetary(currency_field='currency_id',
                               string='Total Salary Per Month')

    @api.depends('no_of_employees', 'salaries')
    def _compute_avg_salary(self):
        for rec in self:
            if rec.no_of_employees > 0:
                rec.avg_salary = rec.salaries / rec.no_of_employees
            else:
                rec.avg_salary = 0
    company_id = fields.Many2one('res.company', readonly=True)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id',
                                  string="Currency")








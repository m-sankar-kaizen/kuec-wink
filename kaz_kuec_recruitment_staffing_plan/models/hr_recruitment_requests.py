from odoo import models, fields, api, _


class HrRecruitmentRequests(models.Model):
    _name = 'hr.recruitment.requests'
    _description = "HR Recruitment Requests"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(readonly=True,
                       copy=False,
                       tracking=True)
    created_date = fields.Date(
        default=fields.Date.today()
    )
    department_id = fields.Many2one('hr.department',
                                    tracking=True)
    job_position_id = fields.Many2one('hr.job',
                                      tracking=True)
    priority = fields.Selection([('0', 'Low'),
                                 ('1', 'Normal'),
                                 ('2', 'High'),
                                 ('3', 'Urgent')],
                                tracking=True,
                                default='0')
    requested_by = fields.Many2one('res.users',
                                   default=lambda self: self.env.user.id)
    expected_employees = fields.Integer(default=1)
    is_off_cycle_staffing = fields.Boolean()
    reason_id = fields.Many2one(
        'off_cycle.staffing.reason')
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company.id)

    staffing_plan_id = fields.Many2one('hr.staffing.plan')

    is_off_cycle_staffing = fields.Boolean(
        default=False,
        string="Off-Cycle Staffing")
    reason_id = fields.Many2one(
        'off_cycle.staffing.reason')

    expected_start_date = fields.Date()

    application_ids = fields.One2many('hr.applicant',
                                      'job_position_id',
                                      compute="compute_application"
                                      )

    @api.depends('job_position_id')
    def compute_application(self):
        for rec in self:
            rec.application_ids = rec.job_position_id.application_ids

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

    description = fields.Html()
    is_recruitment_started = fields.Boolean()

    def action_confirm(self):
        self.ensure_one()
        self.write({
            'status': 'confirmed'
        })

    def action_cancel(self):
        self.ensure_one()
        self.write({
            'status': 'canceled'
        })

    def action_reset(self):
        self.ensure_one()
        self.write({
            'status': 'draft'
        })

    def action_approve(self):
        self.ensure_one()
        self.write({
            'status': 'approved'
        })

    def action_reject(self):
        self.ensure_one()
        self.write({
            'status': 'rejected'
        })

    def action_done(self):
        self.ensure_one()
        self.write({
            'status': 'done'
        })

    def action_start_recruitment(self):
        self.job_position_id.no_of_recruitment = self.expected_employees
        self.is_recruitment_started = True


    def action_go_to_job(self):
        self.ensure_one()
        return {
            'name': _("Job Position"),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.job',
            'res_id': self.job_position_id.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code(
                'hr.recruitment.requests')
            vals.update({
                'name': name
            })
            vals['name'] = name
        return super().create(vals_list)

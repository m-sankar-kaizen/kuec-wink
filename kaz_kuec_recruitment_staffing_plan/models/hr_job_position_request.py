from odoo import models, fields, api, _


class JobPositionRequest(models.Model):
    _name = 'hr.job.position.request'
    _description = 'Job Position Request'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(
        readonly=True)
    position_name = fields.Char(required=True)
    department_id = fields.Many2one('hr.department',
                                    tracking=True)
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company.id,
                                 tracking=True)
    requester_id = fields.Many2one('res.users',
                                   default=lambda self: self.env.user.id,
                                   tracking=True)
    target = fields.Integer(default=1,
                            required=True)
    created_date = fields.Date(default=fields.Date.today(),
                               readonly=True)

    staffing_plan_id = fields.Many2one('hr.staffing.plan')

    hr_job_id = fields.Many2one('hr.job')

    status = fields.Selection([
        ('draft', "Draft"),
        ('requested', "Requested"),
        ('approved', "Approved"),
        ('rejected', "Rejected"),
        ('confirmed', "Confirmed"),
        ('canceled', "Canceled"),
    ],
        default='draft',
        tracking=True,
        copy=False)
    description = fields.Html()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code(
                'hr.job.position.request')
            vals.update({
                'name': name
            })
            vals['name'] = name
        return super().create(vals_list)

    def action_requested(self):
        self.ensure_one()
        self.write({'status': 'requested'})

    def action_cancel(self):
        self.ensure_one()
        self.write({'status': 'canceled'})

    def action_approve(self):
        self.ensure_one()
        self.write({'status': 'approved'})

    def action_reject(self):
        self.ensure_one()
        self.write({'status': 'rejected'})

    def action_confirm(self):
        self.ensure_one()
        job = self.env['hr.job'].sudo().create({
            'name': self.position_name,
            'department_id': self.department_id.id,
            'no_of_recruitment': self.target,
            'request_id': self.id,
            'company_id': self.company_id.id
        })
        self.write({
            'hr_job_id': job.id,
            'status': 'confirmed'})

    def action_show_job(self):
        self.ensure_one()
        return {
            'name': _("Job Position"),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.job',
            'res_id': self.hr_job_id.id,
            'views': [(False, 'form')],
            'target': 'current',
        }


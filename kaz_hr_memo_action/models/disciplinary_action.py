from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrDisciplinaryAction(models.Model):
    _name = 'hr.disciplinary.action'
    _description = 'Employee Disciplinary Action'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Action Reference',
                       copy=False,
                       index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee',
                                  string='Employee',
                                  required=True)
    action_date = fields.Date(string='Action Date',
                              default=fields.Date.today,
                              required=True)
    action_category_type_id = fields.Many2one('hr.disciplinary.action.category',
                                              string='Category Type',
                                              required=True)
    action_type_id = fields.Many2one('hr.disciplinary.action.type',
                                     string='Action Type',
                                     required=True)
    reason = fields.Text(string='Decision of infraction',
                         required=True)
    notes = fields.Text(string='Notes')
    improvement_plan = fields.Text(string='Action Improvement Plan')
    consequence = fields.Text(string='Consequence of infraction')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    disciplinary_action_type = fields.Selection([
        ('warning', 'Warning'),
        ('complaint', 'Complaint'),
    ], required=True)
    company_id = fields.Many2one('res.company',
                                 required=True,
                                 readonly=True,
                                 default=lambda self: self.env.company)
    issued_by = fields.Many2one('res.users',
                                string='Issued By',
                                default=lambda self: self.env.user)
    manager_id = fields.Many2one('hr.employee',
                                 compute='_compute_from_employee_id',
                                 store=True, readonly=False)
    job_id = fields.Many2one('hr.job', 'Job Position',
                             domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                             compute='_compute_from_employee_id',
                             store=True, readonly=False)
    contract_id = fields.Many2one(
        'hr.contract', string='Current Contract',
        groups="hr.group_hr_user",
        compute='_compute_from_employee_id',
        store=True, readonly=False,
        help='Current contract of the employee',
        domain="[('company_id', '=', company_id), ('employee_id', '=', id)]")
    attachment_ids = fields.Many2many('ir.attachment',
                                      'disciplinary_attach_rel',
                                      'action_id', 'attachment_id',
                                      string="Attachments",
                                      help='You can attach the copy of your document',
                                      copy=False)
    deduction_required = fields.Boolean()
    based_on_days = fields.Boolean()
    no_of_days = fields.Integer()

    @api.onchange('no_of_days',
                  'employee_id',
                  'contract_id',
                  'based_on_days')
    def onchange_based_on_days(self):
        if self.based_on_days:
            active_contract = self.contract_id
            if not active_contract:
                self.based_on_days = False
                raise ValidationError(_("Employee doesn't have an active contract."))
            else:
                daily_wage = active_contract.wage / 30
                self.write({'deduction_amount': daily_wage * self.no_of_days})

    deduction_amount = fields.Monetary(
        store=True,
        currency_field='currency_id')
    is_deducted = fields.Boolean(default=False,
                                 tracking=True)
    currency_id = fields.Many2one('res.currency',
                                  related='company_id.currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            action_type = vals.get('disciplinary_action_type')
            existing_domain = [('employee_id', '=', vals.get('employee_id')),
                               ('disciplinary_action_type', '=', action_type)]

            existing_records = self.search(existing_domain, order="create_date desc")

            if action_type in ['warning', 'complaint']:
                if vals.get('name', 'New') == 'New':
                    if existing_records:
                        parent_name = existing_records[0].name.split('/')[0]
                        child_records = self.search([('name', 'like', parent_name + '/%')])
                        child_numbers = [
                            int(rec.name.split('/')[-1]) for rec in child_records
                            if '/' in rec.name and rec.name.split('/')[-1].isdigit()
                        ]
                        next_number = max(child_numbers) + 1 if child_numbers else 1
                        vals['name'] = f"{parent_name}/{next_number}"
                    else:
                        seq_code = 'disciplinary.action.warning.seq' if action_type == 'warning' else 'disciplinary.action.complaint.seq'
                        seq = self.env['ir.sequence'].next_by_code(seq_code)
                        vals['name'] = seq
        return super().create(vals_list)

    @api.onchange('action_category_type_id')
    def _onchange_action_category(self):
        if self.action_category_type_id:
            return {
                'domain': {
                    'action_type_id': [('action_category_id', '=', self.action_category_type_id.id)]
                }
            }
        return {'domain': {'action_type_id': []}}

    @api.depends('employee_id')
    def _compute_from_employee_id(self):
        for rec in self:
            rec.manager_id = rec.employee_id.parent_id.id or False
            rec.job_id = rec.employee_id.job_id.id or False
            rec.contract_id = rec.employee_id.contract_id.id or False

    def action_send_disciplinary_email(self):
        self.ensure_one()
        template = self.env.ref('kaz_hr_memo_action.email_template_hr_disciplinary_action',
                                raise_if_not_found=False)
        if not template:
            return

        compose_form = self.env.ref('mail.email_compose_message_wizard_form')
        ctx = {
            'default_model': self._name,
            'default_res_ids': [self.id],
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'default_email_to': self.employee_id.work_email,
        }
        return {
            'name': 'Notice Email',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_done(self):
        for record in self:
            record.state = 'done'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

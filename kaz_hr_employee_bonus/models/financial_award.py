# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class FinancialAward(models.Model):
    _name = 'financial.award'
    _description = 'Financial Award'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department',
                                    related='employee_id.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Title', related='employee_id.job_id',
                             readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    basic_salary = fields.Monetary(string='Basic Salary', compute='_compute_basic_salary',
                                   store=True, currency_field='currency_id', )
    max_award_amount = fields.Monetary(string='Max Award Amount (5x Salary)',
                                       compute='_compute_max_award', store=True,
                                       currency_field='currency_id')
    award_amount = fields.Monetary(string='Award Amount', required=True, tracking=True,
                                   currency_field='currency_id')
    award_type = fields.Selection([
        ('performance', 'Performance Award'),
        ('loyalty', 'Loyalty Award'),
        ('special', 'Special Recognition'),
        ('milestone', 'Milestone Achievement'),
    ], string='Award Type', required=True, tracking=True)
    reason = fields.Text(string='Reason for Award', required=True, tracking=True,
                         help='Detailed justification for the financial award')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Waiting for Approval'),
        ('hr_approved', 'HR Manager Approved'),
        ('ccoe_approved', 'CCOE Approved'),
        ('ceo_approved', 'CEO Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, required=True)
    award_year = fields.Integer(string='Award Year', required=True,
                                default=lambda self: datetime.now().year)
    award_approval_ids = fields.One2many(
        'financial.award.approval', 'award_id',
        string="Approval/Rejection/Return History")

    def _get_group_users(self, group_xml_id):
        group = self.env.ref(group_xml_id, raise_if_not_found=False)
        if not group:
            raise ValidationError(f"The group '{group_xml_id}' does not exist.")
        if not group.users:
            raise ValidationError(f"No users are assigned to the group '{group.name}'.")
        return group.users

    def assign_activity(self, user_ids, summary, note, activity_type_xml_id=False):
        activity_type_xml_id = activity_type_xml_id or 'mail.mail_activity_data_todo'
        for user in user_ids:
            self.activity_schedule(
                activity_type_id=self.env.ref(activity_type_xml_id).id,
                user_id=user.id,
                summary=summary,
                note=note,
                date_deadline=fields.Date.today() + timedelta(days=3)
            )

    def _mark_activity_done(self, activity_type_xml_id=False):
        """Mark pending activities of a specific type as done."""
        self.ensure_one()
        activity_type_xml_id = activity_type_xml_id or 'mail.mail_activity_data_todo'
        activity_type = self.env.ref(activity_type_xml_id, raise_if_not_found=False)
        if activity_type:
            activities = self.env['mail.activity'].search([
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('state', '!=', 'done')
            ])
            activities.action_feedback()

    def _open_approve_reject_wizard(self, name, request_type, next_action):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'financial.award.approval',
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(self.award_approval_ids) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': self.state.title(),
                'default_next_action': next_action,
                'default_award_id': self.id
            }
        }

    @api.depends('employee_id')
    def _compute_basic_salary(self):
        """Get employee's basic salary from current contract"""
        for record in self:
            if record.employee_id:
                contract = record.employee_id.contract_ids.filtered(
                    lambda c: c.state == 'open' and c.company_id == record.company_id
                )
                if contract:
                    record.basic_salary = contract[0].wage
                else:
                    record.basic_salary = 0.0
            else:
                record.basic_salary = 0.0

    @api.depends('basic_salary')
    def _compute_max_award(self):
        """Calculate max award amount (5x basic salary)"""
        for record in self:
            record.max_award_amount = record.basic_salary * 5

    @api.constrains('award_amount', 'max_award_amount')
    def _check_award_limit(self):
        """Ensure award does not exceed stored max_award_amount and salary exists"""
        for record in self:
            cap = record.max_award_amount or 0.0
            if cap <= 0.0:
                raise ValidationError(
                    _('No active contract wage found for the employee in this company. Please set an open contract with a positive wage before submitting an award.')
                )
            if record.award_amount > cap:
                raise ValidationError(
                    _('Award amount AED %.2f exceeds maximum limit of 5x salary (AED %.2f).')
                    % (record.award_amount, cap)
                )

    @api.constrains('award_year', 'employee_id', 'company_id')
    def _check_annual_limit(self):
        """Ensure no more than 20% of company employees receive awards per year"""
        for record in self:
            if record.state in ['ceo_approved', 'paid']:
                # Count approved/paid awards for this year
                approved_awards = self.env['financial.award'].search_count([
                    ('award_year', '=', record.award_year),
                    ('company_id', '=', record.company_id.id),
                    ('state', 'in', ['ceo_approved', 'paid']),
                    ('id', '!=', record.id),
                ])

                # Count total active employees in company
                total_employees = self.env['hr.employee'].search_count([
                    ('company_id', '=', record.company_id.id),
                    ('active', '=', True),
                ])

                # 20% threshold check
                max_award_count = int(total_employees * 0.20)
                if approved_awards >= max_award_count and record.id not in [
                    a.id for a in self.env['financial.award'].search([
                        ('award_year', '=', record.award_year),
                        ('company_id', '=', record.company_id.id),
                        ('state', 'in', ['ceo_approved', 'paid']),
                    ])
                ]:
                    raise ValidationError(
                        _('Cannot award more than 20% of company employees (%d) in a fiscal year. '
                          'Current approved/paid: %d of %d employees.')
                        % (max_award_count, approved_awards, total_employees)
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('financial.award')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

    def _perform_action(self, state, user_ids=None, summary=None, note=None):
        self.ensure_one()
        self._mark_activity_done()
        self.state = state
        if user_ids:
            self.assign_activity(user_ids, summary, note)

    def _perform_common_action(self, group_xml_id, state):
        self.ensure_one()
        users = self._get_group_users(group_xml_id)
        summary = _("Please Review The Financial Award Form")
        note = _("Please review and confirm the submitted Financial Award Form.")
        self._perform_action(state, users, summary, note)

    def action_submit_for_hr_approval(self):
        """Submit award for HR approval"""
        self.ensure_one()
        self._perform_common_action('kaz_kuec_overall_doa_approval.group_kuec_employee_hohr', 'pending')

    def action_hr_manager_approve(self):
        """HR approves the award"""
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('kaz_procurement_doa_kuec.group_kuec_ccoe', 'hr_approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_hr_manager_approve')

    def action_ccoe_approve(self):
        """CCOE approves the award"""
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('kaz_procurement_doa_kuec.group_kuec_ceo', 'ccoe_approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_ccoe_approve')

    def action_ceo_approve(self):
        """CEO approves the award"""
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('ceo_approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_ceo_approve')

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self.action_reset_to_draft()
            summary = _("Financial Award Form Returned for Correction")
            note = _(
                f"The Financial Award has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Financial Award"
            )
            self.assign_activity(self.create_uid, summary, note)
            self._mark_activity_done()
            return True
        else:
            return self._open_approve_reject_wizard('Return for Correction', 'rfc',
                                                    'action_rfc_request')

    def action_reject_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self.action_reject()
            summary = _("Financial Award Form Rejected")
            note = _(
                f"The Financial Award has been Rejected by {self.env.user.display_name}. "
                "Please review the submitted Financial Award"
            )
            self.assign_activity(self.create_uid, summary, note)
            self._mark_activity_done()
            return True
        else:
            return self._open_approve_reject_wizard('Reject Financial Award', 'reject',
                                                    'action_reject_request')

    def action_reject(self):
        """Reject the award"""
        self.ensure_one()
        if self.state in ['ceo_approved', 'paid']:
            raise UserError(_('Cannot reject an already approved or paid award.'))
        self._perform_action('rejected')

    def action_mark_as_paid(self):
        """Mark award as paid"""
        self.ensure_one()
        if self.state != 'ceo_approved':
            raise UserError(_('Only CEO-approved awards can be marked as paid.'))
        self.state = 'paid'
        self.message_post(body=_('Award marked as paid'))

    def action_reset_to_draft(self):
        """Reset award to draft (admin use)"""
        self.ensure_one()
        if self.state not in ['rejected', 'draft']:
            self.state = 'draft'
            self.message_post(body=_('Award reset to Draft.'))

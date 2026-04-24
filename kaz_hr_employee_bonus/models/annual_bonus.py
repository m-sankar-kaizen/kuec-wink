# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class AnnualBonus(models.Model):
    _name = 'annual.bonus'
    _description = 'Annual Bonus'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department',
                                    related='employee_id.department_id', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Title', related='employee_id.job_id',
                             readonly=True)
    hire_date = fields.Date(string='Hire Date', compute='_compute_hire_date', store=True,
                            readonly=True)
    months_of_service = fields.Integer(string='Months of Service',
                                       compute='_compute_months_of_service', store=True)
    bonus_type = fields.Selection([
        ('performance', 'Performance Bonus'),
        ('corporate', 'Corporate Performance Bonus'),
        ('core_business', 'Core Business Performance Bonus'),
    ], string='Bonus Type', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    base_amount = fields.Monetary(string='Base Amount', required=True, tracking=True,
                                  help='Base amount for bonus calculation',
                                  currency_field='currency_id')
    multiplier = fields.Float(string='Multiplier / Percentage', default=1.0, tracking=True,
                              help='Multiplier or percentage to apply to base amount')
    total_bonus = fields.Monetary(string='Total Bonus', compute='_compute_total_bonus', store=True,
                                  currency_field='currency_id')
    min_attendance = fields.Float(string='Min Attendance %', default=75.0,
                                  help='Minimum attendance percentage required')
    actual_attendance = fields.Float(string='Actual Attendance %', tracking=True,
                                     help='Employee\'s actual attendance percentage')
    is_eligible = fields.Boolean(string='Eligible', compute='_compute_eligibility', store=True,
                                 help='Auto-calculated: True if 6+ months in service AND attendance >= min')
    performance_score = fields.Float(string='Performance Score (%)', tracking=True,
                                     help='Employee performance rating (0-100)')
    scorecard_reference = fields.Char(string='Scorecard Reference',
                                      help='Reference to performance scorecard or appraisal')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Waiting for Approval'),
        ('department_approved', 'Department Approved'),
        ('hr_approved', 'HR Manager Approved'),
        ('ccoe_approved', 'CCOE Approved'),
        ('ceo_approved', 'CEO Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ], string='Status', default='draft', tracking=True)
    # Payment Details
    payment_date = fields.Date(string='Payment Date', readonly=True)
    payment_status = fields.Selection([
        ('pending', 'Pending'),
        ('processed', 'Processed'),
    ], string='Payment Status', default='pending')
    payment_reference = fields.Char(string='Payment Reference', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, required=True)
    bonus_year = fields.Integer(string='Bonus Year', required=True,
                                default=lambda self: datetime.now().year)
    bonus_period = fields.Selection([
        ('annual', 'Annual'),
        ('half_yearly', 'Half-Yearly'),
    ], string='Bonus Period', default='annual', required=True)
    bonus_approval_ids = fields.One2many(
        'annual.bonus.approval', 'bonus_id',
        string="Approval/Rejection/Return History")

    @api.depends('employee_id')
    def _compute_hire_date(self):
        """Get hire date from employee contract start date (preferred open contract, else earliest)"""
        for record in self:
            hire_dt = False
            if record.employee_id:
                contracts = record.employee_id.contract_ids
                # Prefer current open contract
                open_contracts = contracts.filtered(lambda c: c.state == 'open')
                target = open_contracts[:1] or contracts.sorted(
                    key=lambda c: c.date_start or fields.Date.today())[:1]
                if target:
                    hire_dt = target[0].date_start
            record.hire_date = hire_dt or False

    @api.depends('employee_id', 'hire_date')
    def _compute_months_of_service(self):
        """Calculate months of service for the employee"""
        for record in self:
            if record.employee_id and record.hire_date:
                from_date = record.hire_date
                to_date = fields.Datetime.now().date()
                delta = (to_date.year - from_date.year) * 12 + (to_date.month - from_date.month)
                record.months_of_service = max(0, delta)
            else:
                record.months_of_service = 0

    @api.constrains('employee_id', 'company_id')
    def _check_contract_for_hire_date(self):
        """Warn/block when no contract start date is available for hire_date"""
        for record in self:
            if not record.hire_date:
                raise ValidationError(
                    _('No contract start date found for this employee. Please set an employee contract with a valid start date (preferably an open contract) before creating an Annual Bonus.')
                )

    @api.depends('base_amount', 'multiplier')
    def _compute_total_bonus(self):
        """Calculate total bonus (base * multiplier)"""
        for record in self:
            record.total_bonus = record.base_amount * record.multiplier

    @api.depends('months_of_service', 'actual_attendance', 'min_attendance', 'bonus_type')
    def _compute_eligibility(self):
        """Check eligibility: 6+ months service AND attendance >= minimum"""
        for record in self:
            # All bonus types require 6 months service
            min_months_met = record.months_of_service >= 6

            # Check attendance (if provided)
            attendance_met = True
            if record.actual_attendance:
                attendance_met = record.actual_attendance >= record.min_attendance

            record.is_eligible = min_months_met and attendance_met

    @api.constrains('bonus_type', 'employee_id')
    def _check_eligibility_type(self):
        """Ensure eligibility bonus type only for eligible employees"""
        for record in self:
            if record.bonus_type == 'eligibility' and not record.is_eligible:
                raise ValidationError(
                    _('Employee is not eligible for Eligibility Bonus. '
                      'Required: 6+ months service and attendance >= %.0f%%.')
                    % record.min_attendance
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('annual.bonus')
                vals['name'] = seq or _('New')
        return super().create(vals_list)

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
            'res_model': 'annual.bonus.approval',
            'views': [(False, 'form')],
            'context': {
                'default_sequence': len(self.bonus_approval_ids) + 1,
                'default_request_type': request_type,
                'default_parent_state_at_request': self.state.title(),
                'default_next_action': next_action,
                'default_bonus_id': self.id
            }
        }

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

    def _get_department_head(self):
        return self.department_id.manager_id

    def _validate_hod(self):
        """Validate that the current user is the assigned Department Head.

            Ensures that only the Department Head linked to the employee can
            perform approval actions on the evaluation form.

            Raises:
                UserError: If the current user is not the assigned Department Head.
        """
        self.ensure_one()
        manager = self._get_department_head()
        if manager:
            if manager.user_id:
                if self.env.user != manager.user_id:
                    raise UserError(
                        _("Only the Head of Department assigned to this employee can confirm this request."))
            else:
                raise UserError(_("The Department Head does not have an assigned user."))
        else:
            raise UserError(_("A Department Head is not assigned for this employee."))

    def action_submit_for_approval(self):
        """Submit bonus for department head approval"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft bonuses can be submitted for approval.'))
        if not self.is_eligible:
            raise UserError(
                _('Employee is not eligible for bonus. Check service duration and attendance.'))
        manager = self._get_department_head()
        if not manager:
            raise UserError(_("A Department Head is not assigned for this employee."))
        if not manager.user_id:
            raise UserError(_("The Department Head does not have an assigned user."))
        summary = _("Please Review The Financial Award Form")
        note = _("Please review and confirm the submitted Financial Award Form.")

        self._perform_action('pending', manager.user_id, summary, note)

    def action_department_approve(self):
        """Department head approves the bonus"""
        self.ensure_one()
        self._validate_hod()
        if self._context.get('signed', False):
            self._perform_common_action('kaz_kuec_overall_doa_approval.group_kuec_employee_hohr',
                                        'department_approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_department_approve')

    def action_hr_manager_approve(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('kaz_procurement_doa_kuec.group_kuec_ccoe',
                                        'hr_approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_hr_manager_approve')

    def action_ccoe_approve(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_common_action('kaz_procurement_doa_kuec.group_kuec_ceo',
                                        'ccoe_approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_ccoe_approve')

    def action_ceo_approve(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self._perform_action('ceo_approved')
            return True
        else:
            return self._open_approve_reject_wizard('Approve', 'approve',
                                                    'action_ceo_approve')

    def action_department_reject(self):
        """Department head approves the bonus"""
        self.ensure_one()
        self._validate_hod()
        return self.action_reject_request()

    def action_department_rfc(self):
        """Department head approves the bonus"""
        self.ensure_one()
        self._validate_hod()
        return self.action_rfc_request()

    def action_rfc_request(self):
        self.ensure_one()
        if self._context.get('signed', False):
            self.action_reset_to_draft()
            summary = _("Annual Bonus Form Returned for Correction")
            note = _(
                f"The Annual Bonus has been Returned for Correction by {self.env.user.display_name}. "
                "Please review the submitted Annual Bonus"
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
            summary = _("Annual Bonus Form Rejected")
            note = _(
                f"The Annual Bonus has been Rejected by {self.env.user.display_name}. "
                "Please review the submitted Annual Bonus"
            )
            self.assign_activity(self.create_uid, summary, note)
            self._mark_activity_done()
            return True
        else:
            return self._open_approve_reject_wizard('Reject Annual Bonus', 'reject',
                                                    'action_reject_request')

    def action_reject(self):
        """Reject the bonus"""
        self.ensure_one()
        if self.state in ['ceo_approved', 'paid']:
            raise UserError(_('Cannot reject an already approved or paid bonus.'))
        self.state = 'rejected'

    def action_mark_as_paid(self):
        """Mark bonus as paid"""
        self.ensure_one()
        if self.state != 'ceo_approved':
            raise UserError(_('Only manager-approved bonuses can be marked as paid.'))
        self.state = 'paid'
        self.payment_date = fields.Date.today()
        self.payment_status = 'processed'
        self.payment_reference = self.env['ir.sequence'].next_by_code(
            'annual.bonus.payment') or 'BONUS-PAY-' + str(fields.Date.today())
        self.message_post(
            body=_('Bonus marked as paid on %s. Payment Ref: %s') % (self.payment_date,
                                                                     self.payment_reference))

    def action_reset_to_draft(self):
        """Reset bonus to draft (admin use)"""
        self.ensure_one()
        self.state = 'draft'

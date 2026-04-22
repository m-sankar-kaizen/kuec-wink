# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class HrEmployeeSecondment(models.Model):
    _name = 'hr.employee.secondment'
    _description = 'Employee Secondment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'
    _rec_name = 'name'

    # Basic Information
    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        help='Unique reference number for this secondment request'
    )
    
    # Employee Information Section
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True,
        help='Employee being seconded to a new position'
    )
    
    department_id = fields.Many2one(
        'hr.department',
        string='Current Department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
        help='Employee\'s current department'
    )
    
    job_id = fields.Many2one(
        'hr.job',
        string='Current Position',
        related='employee_id.job_id',
        store=True,
        readonly=True,
        help='Employee\'s current job position'
    )
    
    current_grade_id = fields.Many2one(
        'kuec.grade',
        string='Current Grade (KUEC)',
        related='employee_id.kuec_grade_id',
        store=True,
        readonly=True,
        help='Employee\'s current job grade level'
    )

    is_paid = fields.Boolean(copy=False)
    payslip_id = fields.Many2one('hr.payslip',
                                 copy=False)

    def action_view_payslip(self):
        """View payslip associated with secondment allowance payment"""
        self.ensure_one()
        if not self.payslip_id:
            raise UserError(_('No payslip is linked to this secondment allowance payment.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Payslip'),
            'res_model': 'hr.payslip',
            'res_id': self.payslip_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # Secondment Details Section
    secondment_job_id = fields.Many2one(
        'hr.job',
        string='Secondment Position',
        required=True,
        tracking=True,
        domain="[('company_id', '=', company_id)]",
        help='Target position for the secondment'
    )
    
    secondment_department_id = fields.Many2one(
        'hr.department',
        string='Secondment Department',
        related='secondment_job_id.department_id',
        store=True,
        readonly=True,
        help='Department of the secondment position'
    )

    secondment_kuec_grade_id = fields.Many2one(
        'kuec.grade',
        string='Secondment Grade (KUEC)',
        related='secondment_job_id.kuec_grade_id',
        store=True,
        readonly=True,
        help='Secondment position\'s job grade level'
    )

    @api.constrains('secondment_kuec_grade_id', 'current_grade_id')
    def check_secondment_constrains(self):
        """Ensure secondment grade is not lower than two current grade"""
        for record in self:
            if record.secondment_kuec_grade_id and record.current_grade_id:
                current_seq = record.current_grade_id.sequence
                target_seq = record.secondment_kuec_grade_id.sequence
                difference = int(
                    self.env['ir.config_parameter'].sudo().get_param(
                        'hr_employee_secondment.max_grade_difference',
                        default=2
                    ))
                if current_seq > target_seq + difference:
                    raise ValidationError(_(
                        'The employee is not eligible for this secondment.\n\n'
                        'Current Grade: %s\n'
                        'Secondment Grade: %s\n\n'
                        'An employee’s current grade cannot be more than two levels below '
                        'the grade of the secondment position.'
                    ) % (record.current_grade_id.name,
                         record.secondment_kuec_grade_id.name))

    date_start = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
        help='Date when the secondment begins'
    )
    
    date_end = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
        help='Original planned end date for the secondment'
    )
    
    duration_months = fields.Integer(
        string='Duration (Months)',
        compute='_compute_duration_months',
        store=True,
        help='Total duration of the secondment in months'
    )
    
    duties = fields.Html(
        string='Secondment Duties',
        help='Description of duties and responsibilities during secondment'
    )
    
    # Extension Management
    is_extended = fields.Boolean(
        string='Extended',
        default=False,
        copy=False,
        tracking=True,
        help='Indicates if this secondment has been extended'
    )
    
    extension_date_end = fields.Date(
        string='Extension End Date',
        copy=False,
        tracking=True,
        help='New end date after extension approval'
    )
    
    extension_duration_months = fields.Integer(
        string='Extension Duration (Months)',
        compute='_compute_extension_duration',
        store=True,
        help='Duration of the extension period in months'
    )
    
    total_duration_months = fields.Integer(
        string='Total Duration (Months)',
        compute='_compute_total_duration',
        store=True,
        help='Total duration including extension'
    )
    
    effective_end_date = fields.Date(
        string='Effective End Date',
        compute='_compute_effective_end_date',
        store=True,
        help='Actual end date (extended date if applicable, otherwise original end date)'
    )
    
    # Allowance Management
    maintains_original_duties = fields.Boolean(
        string='Maintains Original Duties',
        default=False,
        tracking=True,
        help='Check if employee continues to perform their original position duties'
    )
    
    allowance_eligible = fields.Boolean(
        string='Allowance Eligible',
        compute='_compute_allowance_eligible',
        store=True,
        help='Indicates if employee qualifies for secondment allowance'
    )
    
    base_salary = fields.Monetary(
        string='Current Basic Salary',
        compute='_compute_base_salary',
        store=True,
        currency_field='currency_id',
        readonly=True,
        help='Employee\'s current basic salary from contract'
    )
    
    secondment_base_salary = fields.Monetary(
        string='Secondment Position Salary',
        currency_field='currency_id',
        help='Basic salary of the secondment position (used for allowance calculation)'
    )
    
    allowance_amount = fields.Monetary(
        string='Monthly Allowance',
        compute='_compute_allowance_amount',
        store=True,
        currency_field='currency_id',
        help='Monthly allowance amount based on configured percentage'
    )
    
    total_allowance = fields.Monetary(
        string='Total Allowance',
        compute='_compute_total_allowance',
        store=True,
        currency_field='currency_id',
        help='Total allowance for the entire secondment period'
    )
    
    # Applied Configuration (Snapshot)
    applied_max_duration = fields.Integer(
        string='Applied Max Duration',
        help='Maximum duration setting at time of creation'
    )
    
    applied_allowance_percentage = fields.Float(
        string='Applied Allowance %',
        digits=(5, 2),
        help='Allowance percentage setting at time of creation'
    )
    
    applied_allowance_threshold = fields.Integer(
        string='Applied Threshold',
        help='Allowance threshold setting at time of creation'
    )
    
    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False,
        help='Current state of the secondment request')
    
    # Smart Button Counts
    history_count = fields.Integer(
        string='History Count',
        compute='_compute_history_count',
        help='Number of previous secondments for this employee'
    )
    
    # Other Fields
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        store=True,
        readonly=True
    )
    
    notes = fields.Text(
        string='Notes',
        help='Additional notes or comments about the secondment'
    )
    
    rejection_reason = fields.Text(
        string='Rejection Reason',
        tracking=True,
        help='Reason for rejecting the secondment request'
    )

    # ========================================
    # Computed Fields
    # ========================================
    
    @api.depends('employee_id',
                 'employee_id.contract_id',
                 'employee_id.contract_id.wage')
    def _compute_base_salary(self):
        """Get current basic salary from employee's active contract"""
        for record in self:
            if record.employee_id and record.employee_id.contract_id:
                record.base_salary = record.employee_id.contract_id.wage
            else:
                record.base_salary = 0.0
    
    @api.depends('date_start', 'date_end')
    def _compute_duration_months(self):
        """Calculate duration in months"""
        for record in self:
            if record.date_start and record.date_end:
                delta = relativedelta(record.date_end, record.date_start)
                record.duration_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
            else:
                record.duration_months = 0
    
    @api.depends('date_end', 'extension_date_end')
    def _compute_extension_duration(self):
        """Calculate extension duration in months"""
        for record in self:
            if record.is_extended and record.date_end and record.extension_date_end:
                delta = relativedelta(record.extension_date_end, record.date_end)
                record.extension_duration_months = delta.years * 12 + delta.months + (1 if delta.days > 0 else 0)
            else:
                record.extension_duration_months = 0
    
    @api.depends('duration_months', 'extension_duration_months')
    def _compute_total_duration(self):
        """Calculate total duration including extension"""
        for record in self:
            record.total_duration_months = record.duration_months + record.extension_duration_months
    
    @api.depends('date_end', 'extension_date_end', 'is_extended')
    def _compute_effective_end_date(self):
        """Calculate the actual end date considering extensions"""
        for record in self:
            if record.is_extended and record.extension_date_end:
                record.effective_end_date = record.extension_date_end
            else:
                record.effective_end_date = record.date_end
    
    @api.depends('total_duration_months', 'maintains_original_duties')
    def _compute_allowance_eligible(self):
        """Determine if employee is eligible for allowance based on configuration"""
        for record in self:
            threshold = int(self.env['ir.config_parameter'].sudo().get_param(
                'hr_employee_secondment.allowance_threshold_months', default=2
            ))
            requires_original_duties = self.env['ir.config_parameter'].sudo().get_param(
                'hr_employee_secondment.requires_original_duties', default='True'
            ) == 'True'
            
            if requires_original_duties:
                record.allowance_eligible = (
                    record.total_duration_months >= threshold and 
                    record.maintains_original_duties
                )
            else:
                record.allowance_eligible = record.total_duration_months >= threshold
    
    @api.depends('allowance_eligible', 'secondment_base_salary')
    def _compute_allowance_amount(self):
        """Calculate monthly allowance as 25% of secondment position salary"""
        for record in self:
            if record.allowance_eligible and record.secondment_base_salary:
                percentage = float(self.env['ir.config_parameter'].sudo().get_param(
                    'hr_employee_secondment.allowance_percentage', default=25.0
                ))
                record.allowance_amount = record.secondment_base_salary * (percentage / 100.0)
            else:
                record.allowance_amount = 0.0
    
    @api.depends('allowance_amount', 'total_duration_months', 'allowance_eligible')
    def _compute_total_allowance(self):
        """Calculate total allowance for entire secondment period (all months if eligible)"""
        for record in self:
            if record.allowance_eligible and record.allowance_amount:
                # Pay allowance for ALL months worked (not just months after threshold)
                record.total_allowance = record.allowance_amount * record.total_duration_months
            else:
                record.total_allowance = 0.0
    
    @api.depends('employee_id')
    def _compute_history_count(self):
        """Count previous secondments for this employee"""
        for record in self:
            if record.employee_id:
                record.history_count = self.search_count([
                    ('employee_id', '=', record.employee_id.id),
                    ('id', '!=', record.id),
                ])
            else:
                record.history_count = 0

    # ========================================
    # Constraints
    # ========================================
    
    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        """Validate that end date is after start date"""
        for record in self:
            if record.date_start and record.date_end:
                if record.date_start >= record.date_end:
                    raise ValidationError(_('End date must be after start date.'))
    
    @api.constrains('date_start', 'date_end')
    def _check_max_duration(self):
        """Validate secondment duration doesn't exceed configured maximum"""
        for record in self:
            if record.date_start and record.date_end and record.state in ['draft', 'submitted']:
                max_duration = int(self.env['ir.config_parameter'].sudo().get_param(
                    'hr_employee_secondment.max_duration_months', default=6
                ))
                
                if record.duration_months > max_duration:
                    raise ValidationError(_(
                        'Secondment duration (%s months) exceeds the maximum allowed duration of %s months.\n'
                        'Please adjust the end date or contact HR to modify settings.'
                    ) % (record.duration_months, max_duration))
    
    @api.constrains('employee_id', 'state', 'date_start', 'date_end')
    def _check_overlapping_secondments(self):
        """Prevent overlapping active secondments for the same employee"""
        for record in self:
            if record.state in ['approved', 'active'] and record.employee_id:
                overlapping = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('id', '!=', record.id),
                    ('state', 'in', ['approved', 'active']),
                    '|',
                    '&', ('date_start', '<=', record.effective_end_date or record.date_end),
                         ('effective_end_date', '>=', record.date_start),
                    '&', ('date_start', '<=', record.date_start),
                         ('effective_end_date', '>=', record.date_start),
                ], limit=1)
                
                if overlapping:
                    raise ValidationError(_(
                        'Employee %s already has an active secondment (%s) during this period.\n'
                        'Period: %s to %s'
                    ) % (
                        record.employee_id.name,
                        overlapping.name,
                        overlapping.date_start,
                        overlapping.effective_end_date
                    ))
    
    @api.constrains('extension_date_end', 'date_end')
    def _check_extension_duration(self):
        """Validate extension doesn't exceed configured maximum"""
        for record in self:
            if record.is_extended and record.extension_date_end and record.date_end:
                max_extension = int(self.env['ir.config_parameter'].sudo().get_param(
                    'hr_employee_secondment.max_extension_months', default=6
                ))
                
                if record.extension_duration_months > max_extension:
                    raise ValidationError(_(
                        'Extension duration (%s months) exceeds the maximum allowed extension of %s months.\n'
                        'Please adjust the extension end date or contact HR to modify settings.'
                    ) % (record.extension_duration_months, max_extension))

    # ========================================
    # CRUD Methods
    # ========================================
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate sequence and store configuration snapshot"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.employee.secondment') or _('New')
            
            # Store configuration snapshot
            if 'applied_max_duration' not in vals:
                vals['applied_max_duration'] = int(self.env['ir.config_parameter'].sudo().get_param(
                    'hr_employee_secondment.max_duration_months', default=6
                ))
            if 'applied_allowance_percentage' not in vals:
                vals['applied_allowance_percentage'] = float(self.env['ir.config_parameter'].sudo().get_param(
                    'hr_employee_secondment.allowance_percentage', default=25.0
                ))
            if 'applied_allowance_threshold' not in vals:
                vals['applied_allowance_threshold'] = int(self.env['ir.config_parameter'].sudo().get_param(
                    'hr_employee_secondment.allowance_threshold_months', default=2
                ))
        
        return super().create(vals_list)

    # ========================================
    # Action Methods
    # ========================================
    
    def action_submit(self):
        """Submit secondment request for approval"""
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_('Please select an employee before submitting.'))
        if not self.secondment_job_id:
            raise UserError(_('Please select a secondment position before submitting.'))
        
        self.state = 'submitted'
        
        # Create activity for HR Manager
        hr_managers = self.env.ref('hr.group_hr_manager').users
        if hr_managers:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                date_deadline=fields.Date.today() + timedelta(days=3),
                summary=_('Approve Secondment Request'),
                note=_('Please review and approve secondment request for %s.<br/>'
                       'Position: %s<br/>'
                       'Period: %s to %s (%s months)') % (
                    self.employee_id.name,
                    self.secondment_job_id.name,
                    self.date_start,
                    self.date_end,
                    self.duration_months
                ),
                user_id=hr_managers[0].id
            )
        
        self.message_post(
            body=_('Secondment request submitted for approval.'),
            subject=_('Secondment Submitted')
        )
        
        return True
    
    def action_approve(self):
        """Approve secondment request"""
        self.ensure_one()
        self.state = 'approved'
        
        # Notify employee and departments
        partners_to_notify = []
        if self.employee_id.user_id:
            partners_to_notify.append(self.employee_id.user_id.partner_id.id)
        if self.department_id.manager_id.user_id:
            partners_to_notify.append(self.department_id.manager_id.user_id.partner_id.id)
        if self.secondment_department_id and self.secondment_department_id.manager_id.user_id:
            partners_to_notify.append(self.secondment_department_id.manager_id.user_id.partner_id.id)
        
        self.message_post(
            body=_('Secondment request has been approved.<br/>'
                   'Employee: %s<br/>'
                   'Position: %s<br/>'
                   'Period: %s to %s') % (
                self.employee_id.name,
                self.secondment_job_id.name,
                self.date_start,
                self.date_end
            ),
            subject=_('Secondment Approved'),
            partner_ids=partners_to_notify
        )
        
        return True
    
    def action_reject(self):
        """Reject secondment request"""
        self.ensure_one()
        if not self.rejection_reason:
            raise UserError(_('Please provide a rejection reason.'))
        self.state = 'rejected'
        
        # Notify employee
        if self.employee_id.user_id:
            self.message_post(
                body=_('Secondment request has been rejected.<br/>Reason: %s') % self.rejection_reason,
                subject=_('Secondment Rejected'),
                partner_ids=[self.employee_id.user_id.partner_id.id]
            )
        
        return True
    
    def action_activate(self):
        """Activate secondment (set to active state)"""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Only approved secondments can be activated.'))
        
        self.state = 'active'
        
        self.message_post(
            body=_('Secondment is now active.'),
            subject=_('Secondment Activated')
        )
        
        return True
    
    def action_complete(self):
        """Mark secondment as completed"""
        self.ensure_one()
        if self.state != 'active':
            raise UserError(_('Only active secondments can be completed.'))
        
        self.state = 'completed'
        
        self.message_post(
            body=_('Secondment has been completed.'),
            subject=_('Secondment Completed')
        )
        
        return True
    
    def action_cancel(self):
        """Cancel secondment request"""
        self.ensure_one()
        if self.state in ['completed', 'rejected']:
            raise UserError(_('Cannot cancel a %s secondment.') % self.state)
        
        self.state = 'cancelled'
        
        self.message_post(
            body=_('Secondment has been cancelled.'),
            subject=_('Secondment Cancelled')
        )
        
        return True
    
    def action_extend(self):
        """Extend secondment period"""
        self.ensure_one()
        
        # Check if extensions are allowed
        allow_extensions = self.env['ir.config_parameter'].sudo().get_param(
            'hr_employee_secondment.allow_extensions', default='True'
        ) == 'True'
        
        if not allow_extensions:
            raise UserError(_('Secondment extensions are not allowed according to current settings.'))
        
        if self.is_extended:
            raise UserError(_('This secondment has already been extended. Only one extension is allowed.'))
        
        if self.state not in ['approved', 'active']:
            raise UserError(_('Only approved or active secondments can be extended.'))
        
        if not self.extension_date_end:
            raise UserError(_('Please set the Extension End Date before extending.'))
        
        if self.extension_date_end <= self.date_end:
            raise UserError(_('Extension End Date must be after the original End Date.'))
        
        # Mark as extended
        self.is_extended = True
        
        self.message_post(
            body=_('Secondment extended until %s') % self.extension_date_end,
            subject=_('Secondment Extended')
        )
        
        return True
    
    def action_set_to_draft(self):
        """Reset to draft state"""
        self.ensure_one()
        if self.state not in ['rejected', 'cancelled']:
            raise UserError(_('Only rejected or cancelled secondments can be reset to draft.'))
        
        self.state = 'draft'
        self.rejection_reason = False
        
        return True
    
    def action_view_history(self):
        """View secondment history for this employee"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Secondment History - %s') % self.employee_id.name,
            'res_model': 'hr.employee.secondment',
            'domain': [('employee_id', '=', self.employee_id.id), ('id', '!=', self.id)],
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {'default_employee_id': self.employee_id.id}
        }
    
    def action_view_employee(self):
        """View employee record"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Employee'),
            'res_model': 'hr.employee',
            'res_id': self.employee_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ========================================
    # Cron Methods
    # ========================================
    
    @api.model
    def _cron_check_ending_secondments(self):
        """
        Scheduled action to check secondments nearing end date and create activities.
        Runs daily.
        """
        notification_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'hr_employee_secondment.notification_days_before_end', default=30
        ))
        
        notification_date = fields.Date.today() + timedelta(days=notification_days)
        
        # Find active secondments approaching end date
        secondments = self.search([
            ('state', '=', 'active'),
            ('effective_end_date', '=', notification_date),
        ])
        
        hr_managers = self.env.ref('hr.group_hr_manager').users
        
        for secondment in secondments:
            if hr_managers:
                # Check if activity already exists
                existing_activity = self.env['mail.activity'].search([
                    ('res_id', '=', secondment.id),
                    ('res_model', '=', 'hr.employee.secondment'),
                    ('summary', 'ilike', 'Secondment Ending Soon'),
                ], limit=1)
                
                if not existing_activity:
                    secondment.activity_schedule(
                        'mail.mail_activity_data_todo',
                        date_deadline=fields.Date.today() + timedelta(days=7),
                        summary=_('Secondment Ending Soon'),
                        note=_('Secondment for %s will end on %s.<br/>'
                               'Position: %s<br/>'
                               'Please review and decide on:<br/>'
                               '- Extension (if applicable)<br/>'
                               '- Transfer/Promotion<br/>'
                               '- Return to original position') % (
                            secondment.employee_id.name,
                            secondment.effective_end_date,
                            secondment.secondment_job_id.name
                        ),
                        user_id=hr_managers[0].id
                    )
        
        return True
    
    @api.model
    def _cron_auto_complete_secondments(self):
        """
        Scheduled action to automatically complete secondments on end date.
        Only runs if configured to auto-complete.
        """
        auto_complete = self.env['ir.config_parameter'].sudo().get_param(
            'hr_employee_secondment.auto_complete_on_end', default='False'
        ) == 'True'
        
        if not auto_complete:
            return True
        
        today = fields.Date.today()
        
        # Find active secondments that have reached end date
        secondments = self.search([
            ('state', '=', 'active'),
            ('effective_end_date', '<=', today),
        ])
        
        for secondment in secondments:
            secondment.action_complete()
        
        return True

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrInternship(models.Model):
    _name = 'hr.internship'
    _description = 'Internship'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, index=True,
                                 help='Company to which this internship record belongs')

    # Basic Information
    name = fields.Char(string='Reference',
                       required=True,
                       readonly=True,
                       default='/',
                       copy=False,
                      help='Auto-generated unique reference number for the internship')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, help='Current state of the internship workflow')

    # Intern & Assignment
    intern_id = fields.Many2one('res.partner', string='Intern', required=True, tracking=True,
                               help='The intern/contact assigned to this internship')
    department_id = fields.Many2one('hr.department', string='Department', required=True,
                                   help='Department where intern will work')
    mentor_id = fields.Many2one('hr.employee', string='Mentor', required=True,
                               help='HR employee assigned as mentor for this intern')
    
    # Duration & Type
    date_start = fields.Date(required=True, tracking=True,
                            help='Internship start date')
    date_end = fields.Date(required=True, tracking=True,
                          help='Internship end date')
    
    internship_type = fields.Selection([
        ('part_time', 'Part-Time'),
        ('temporary', 'Temporary'),
        ('freelance', 'Freelance'),
    ], default='temporary', required=True, tracking=True,
       help='Type of internship: Part-Time (flexible hours), Temporary (fixed duration), or Freelance (project-based)')

    # Internship Details - Payment Status
    payment_status = fields.Selection([
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
    ], required=True, tracking=True,
       help='Whether the internship is paid or unpaid')
    
    # For backward compatibility / legacy reference
    is_paid = fields.Boolean(compute='_compute_is_paid', store=True, 
                            help='Computed flag: True if payment_status is paid')
    
    stipend_amount = fields.Float(default=0, string='Monthly Stipend/Hourly Rate',
                                 help='Monthly stipend (in AED) or hourly rate for paid internships')
    part_time_hours_per_week = fields.Float(string='Hours per Week',
                                           help='Expected weekly hours for part-time internships')
    freelance_compensation_type = fields.Selection([
        ('fixed', 'Fixed Fee'),
        ('hourly', 'Hourly Rate'),
    ], string='Freelance Compensation Type',
       help='Compensation structure for freelance contracts')
    freelance_fixed_fee = fields.Float(string='Fixed Fee Amount (AED)',
                                       help='Total fixed fee for freelance contract')
    freelance_hourly_rate = fields.Float(string='Hourly Rate (AED)',
                                        help='Hourly rate for freelance contract')
    freelance_contract_reference = fields.Char(string='Freelance Contract Reference',
                                              help='Reference or link to the freelance contract')
    freelance_contract_confirmed = fields.Boolean(string='Freelance Contract Confirmed', default=False,
                                                 help='Indicates the freelance contract has been created/validated')

    # UI helper flags for Odoo 18 (attrs deprecated)
    show_part_time_fields = fields.Boolean(compute='_compute_visibility_flags')
    show_freelance_fields = fields.Boolean(compute='_compute_visibility_flags')
    show_stipend_fields = fields.Boolean(compute='_compute_visibility_flags')
    show_academic_credit_field = fields.Boolean(compute='_compute_visibility_flags')
    
    # Academic Credit
    is_academic_credit = fields.Boolean(default=False, string='Part of Academic Credit Program', tracking=True,
                                       help='Check if this internship is part of an academic credit program')
    notes = fields.Text(help='Additional information or notes about the internship')
    # One2many relationships
    reward_ids = fields.One2many('hr.internship.reward', 'internship_id', string='Rewards')
    feedback_ids = fields.One2many('hr.internship.feedback', 'internship_id', string='Feedback')
    orientation_ids = fields.One2many('hr.internship.orientation', 'internship_id', string='Orientation')
    freelance_deliverable_ids = fields.One2many('hr.internship.freelance.deliverable', 'internship_id',
                                               string='Deliverables')
    # Computed fields for monitoring
    total_feedback_count = fields.Integer(string='Total Feedback Records', compute='_compute_total_feedback_count')
    total_reward_count = fields.Integer(string='Total Reward Requests', compute='_compute_total_reward_count')
    approved_reward_amount = fields.Float(string='Total Approved Rewards', compute='_compute_approved_reward_amount')
    total_deliverable_count = fields.Integer(string='Total Deliverables', compute='_compute_total_deliverable_count')
    
    @api.depends('feedback_ids')
    def _compute_total_feedback_count(self):
        for record in self:
            record.total_feedback_count = len(record.feedback_ids)
    
    @api.depends('reward_ids')
    def _compute_total_reward_count(self):
        for record in self:
            record.total_reward_count = len(record.reward_ids)
    
    @api.depends('reward_ids.state', 'reward_ids.amount')
    def _compute_approved_reward_amount(self):
        for record in self:
            record.approved_reward_amount = sum(
                r.amount for r in record.reward_ids if r.state == 'approved'
            )

    @api.depends('freelance_deliverable_ids')
    def _compute_total_deliverable_count(self):
        for record in self:
            record.total_deliverable_count = len(record.freelance_deliverable_ids)

    @api.depends('internship_type', 'payment_status')
    def _compute_visibility_flags(self):
        """Helper flags for view visibility (attrs deprecated in Odoo 18)."""
        for record in self:
            record.show_part_time_fields = record.internship_type == 'part_time'
            record.show_freelance_fields = record.internship_type == 'freelance'
            record.show_stipend_fields = record.payment_status == 'paid' and record.internship_type != 'freelance'
            record.show_academic_credit_field = record.payment_status == 'unpaid'

    @api.depends('payment_status')
    def _compute_is_paid(self):
        """Compute is_paid from payment_status for backward compatibility."""
        for record in self:
            record.is_paid = record.payment_status == 'paid'

    @api.constrains('part_time_hours_per_week', 'freelance_compensation_type', 'freelance_fixed_fee', 'freelance_hourly_rate', 'payment_status', 'internship_type')
    def _check_policy_requirements(self):
        for record in self:
            # Part-time must have hours defined
            if record.internship_type == 'part_time' and (record.part_time_hours_per_week is None or record.part_time_hours_per_week <= 0):
                raise ValidationError(_('Please specify weekly hours for part-time internships.'))

            # Freelance paid engagements must have compensation details
            if record.internship_type == 'freelance' and record.payment_status == 'paid':
                if not record.freelance_compensation_type:
                    raise ValidationError(_('Select freelance compensation type (fixed or hourly).'))
                if record.freelance_compensation_type == 'fixed':
                    if record.freelance_fixed_fee is None or record.freelance_fixed_fee <= 0:
                        raise ValidationError(_('Enter a positive fixed fee amount.'))
                else:  # hourly
                    if record.freelance_hourly_rate is None or record.freelance_hourly_rate <= 0:
                        raise ValidationError(_('Enter a positive hourly rate.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.internship') or 'INT000'
        return super().create(vals_list)

    # State Transition Actions
    def action_start(self):
        """Activate internship"""
        self.state = 'active'
        self.message_post(body=_("Internship activated and moved to Active state."))
        return True

    def action_add_feedback(self):
        """Add feedback for internship"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.internship.feedback',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_internship_id': self.id, 'default_mentor_id': self.mentor_id.id},
        }

    def action_add_reward(self):
        """Add reward request for internship"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.internship.reward',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_internship_id': self.id},
        }

    def action_add_orientation(self):
        """Add orientation record"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.internship.orientation',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_internship_id': self.id},
        }

    def action_complete(self):
        """Complete internship"""
        self.state = 'completed'
        self.message_post(body=_("Internship completed."))

    def action_cancel(self):
        """Cancel internship"""
        self.state = 'cancelled'
        self.message_post(body=_("Internship cancelled."))

    def action_view_feedback(self):
        """Open feedback records for this internship"""
        return {
            'name': _('Feedback Records'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.internship.feedback',
            'view_mode': 'list,form',
            'domain': [('internship_id', '=', self.id)],
            'context': {'default_internship_id': self.id},
        }

    def action_view_rewards(self):
        """Open reward requests for this internship"""
        return {
            'name': _('Reward Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.internship.reward',
            'view_mode': 'list,form',
            'domain': [('internship_id', '=', self.id)],
            'context': {'default_internship_id': self.id},
        }

    def action_view_deliverables(self):
        """Open deliverables for this internship"""
        return {
            'name': _('Deliverables'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.internship.freelance.deliverable',
            'view_mode': 'list,form',
            'domain': [('internship_id', '=', self.id)],
            'context': {'default_internship_id': self.id},
        }





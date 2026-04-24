from odoo import models, fields, _, api
from datetime import date
from odoo.exceptions import ValidationError



class MyGoals(models.Model):
    _name = 'my.goals'
    _description = 'My Goals'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Char(string='Sequence', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    name = fields.Char(string='Goal Name', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)
    kra_id = fields.Many2one('kra.kra', string='KRA', readonly=True)
    kpi_id = fields.Many2many(
        'kra.kpi',
        string='KPIs',
        compute='_compute_kpis',
        store=True,
        readonly=True
    )
    kpi_score = fields.Float(
        string='KPI Score',
        compute='_compute_kpi_score',
        store=True,
        readonly=True
    )
    kpi_rating = fields.Selection([
        ('not_done', 'Not Done'),
        ('poor', 'Poor'),
        ('needs_improvement', 'Needs Improvement'),
        ('good', 'Good'),
        ('very_good', 'Very Good'),
        ('outstanding', 'Outstanding'),   
    ], string="KPI Rating", compute="_compute_kpi_score", store=True, readonly=True)

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True
    )
    job_id = fields.Many2one(
        'hr.job',
        string='Job Position',
        related='employee_id.job_id',
        store=True,
        readonly=True
    )
    target = fields.Char(string='Target', readonly=True)
    weightage = fields.Float(string='Weightage (%)', readonly=True)
    timeline_start = fields.Date(string='Start Date', readonly=True)
    timeline_end = fields.Date(string='End Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('not_finished', 'Not Finished'),
        ('expired', 'Expired')
    ], default='draft', string='Status')

    user_id = fields.Many2one('res.users',default=lambda self: self.env.uid)

    @api.depends('state', 'weightage')
    def _compute_kpi_score(self):
        state_score_map = {
            'in_progress': 0.25,
            'completed': 1.00,
            'not_finished': 0.50,
            'expired': 0.00,
            'draft': 0.00,
            'active': 0.00,
        }

        for record in self:
            score_factor = state_score_map.get(record.state, 0.00)
            kpi_score = (record.weightage * score_factor) / 100.0
            record.kpi_score = kpi_score

            # Compute KPI Rating
            if kpi_score >= 0.90:
                record.kpi_rating = 'outstanding'
            elif kpi_score >= 0.75:
                record.kpi_rating = 'very_good'
            elif kpi_score >= 0.50:
                record.kpi_rating = 'good'
            elif kpi_score >= 0.25:
                record.kpi_rating = 'needs_improvement'
            elif kpi_score > 0.00:
                record.kpi_rating = 'poor'
            else:
                record.kpi_rating = 'not_done'

    @api.constrains('employee_id', 'department_id', 'job_id')
    def _check_mandatory_employee_fields(self):
        for record in self:
            missing_fields = []
            if not record.employee_id:
                missing_fields.append('Employee')
            if not record.department_id:
                missing_fields.append('Department')
            if not record.job_id:
                missing_fields.append('Job Position')

            if missing_fields:
                raise ValidationError(
                    _('You cannot create a record here. Its only for Employees. Instead, create a record in the "Goals Assignment".'))

    @api.depends('kra_id')
    def _compute_kpis(self):
        for record in self:
            record.kpi_id = record.kra_id.kpi_id


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sequence', _('New')) == _('New'):
                vals['sequence'] = self.env['ir.sequence'].next_by_code('my.goals') or _('New')

            # Set user_id from employee's user if not already set
            if not vals.get('user_id') and vals.get('employee_id'):
                employee = self.env['hr.employee'].browse(vals['employee_id'])
                if employee.user_id:
                    vals['user_id'] = employee.user_id.id
        return super(MyGoals, self).create(vals_list)
    
    def write(self, vals):
        # If employee_id is being updated, set corresponding user_id
        if 'employee_id' in vals:
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if employee and employee.user_id:
                vals['user_id'] = employee.user_id.id
            else:
                vals['user_id'] = False  # Clear if no related user
        return super(MyGoals, self).write(vals)

    
    def action_set_to_completed(self):
        for record in self:
            record.state = 'completed'
            # Find corresponding my.goals record and update its state
            goals_assignment = self.env['goals.assignment'].search([
                ('employee_id', '=', record.employee_id.id),
                ('name', '=', record.name),
                ('target', '=', record.target)
            ], limit=1)
            if goals_assignment:
                goals_assignment.state = 'completed'

            # Post message in chatter
            record.message_post(
                body=f'✅ Goal "{record.name} Completed by "{self.env.user.name}".',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )

            # Create To-Do activity for admin
            # Get performance manager group users
            group = self.env.ref('hrms_performance_management.group_performance_manager')
            group_users = group.users if group else self.env['res.users']
            
            for user in group_users:
                self.env['mail.activity'].create({
                    'res_model_id': self.env['ir.model']._get_id('my.goals'),
                    'res_id': record.id,
                    'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                    'summary': f"Review Completed Goal: {record.name}",
                    'note': f"The goal '{record.name}' for {record.employee_id.name} has been marked as completed. Please review it.",
                    'user_id': user.id,
                })

    def action_set_to_in_progress(self):
        for record in self:
            record.state = 'in_progress'
            # Find corresponding my.goals record and update its state
            goals_assignment = self.env['goals.assignment'].search([
                ('employee_id', '=', record.employee_id.id),
                ('name', '=', record.name),
                ('target', '=', record.target)
            ], limit=1)
            if goals_assignment:
                goals_assignment.state = 'in_progress'

            record.message_post(
                body=f'✅ Goal "{record.name} In Progress by "{self.env.user.name}".',
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
    
    # def print_department(self):
    #     for record in self:
    #         print(f"[INFO] Department for Goal '{record.name}': {record.department_id.name}")


    def check_and_update_deadline(self):
        today = date.today()
        deadline_goals = self.search([
            ('state', 'in', ['active', 'in_progress']),
            ('timeline_end', '<', today)
        ])
        for goal in deadline_goals:
            goal.write({'state': 'not_finished'})
            goal.state = 'not_finished'

            # Optionally update goals.assignment too
            goals_assignment = self.env['goals.assignment'].search([
                ('employee_id', '=', goal.employee_id.id),
                ('name', '=', goal.name),
                ('target', '=', goal.target)
            ], limit=1)
            if goals_assignment and goals_assignment.state != 'completed':
                goals_assignment.write({'state': 'not_finished'})
                goals_assignment.state = 'not_finished'

    def check_and_update_expiry(self):
        today = date.today()
        expired_goals = self.search([
            ('state', 'in', ['active']),
            ('timeline_start', '<', today)
        ])
        for goal in expired_goals:
            goal.write({'state': 'expired'})
            goal.state = 'expired'

            # Optionally update goals.assignment too
            goals_assignment = self.env['goals.assignment'].search([
                ('employee_id', '=', goal.employee_id.id),
                ('name', '=', goal.name),
                ('target', '=', goal.target)
            ], limit=1)
            if goals_assignment and goals_assignment.state != 'completed':
                goals_assignment.write({'state': 'expired'})
                goals_assignment.state = 'expired'

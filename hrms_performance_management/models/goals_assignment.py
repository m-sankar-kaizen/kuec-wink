from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class GoalAssignment(models.Model):
    _name = 'goals.assignment'
    _description = 'Goal Assignment'

    name = fields.Char(string='Goal', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')

    kra_department_id = fields.Many2one('kra.kra', string='KRA', domain="[('is_department_wise','=',True),('department_id','=',department_id)]")
    kra_job_id = fields.Many2one('kra.kra', string='KRA', domain="[('is_jobposition_wise','=',True),('job_id','=',job_id)]")
    kra_normal_id = fields.Many2one('kra.kra', string='KRA')

    kpi_id = fields.Many2many(
        'kra.kpi',
        string='KPIs',
        compute='_compute_kpis',
        store=True,
        readonly=True
    )
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
    weightage = fields.Float(string='Weightage (%)', required=True)
    target = fields.Char(string='Target')
    timeline_start = fields.Date(string='Start Date', required=True)
    timeline_end = fields.Date(string='End Date', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('not_finished', 'Not Finished'),
        ('expired', 'Expired')
    ], default='draft', string='Status')
    is_department_wise = fields.Boolean(string='(KRA)Department Wise', default=True)
    is_jobposition_wise = fields.Boolean(string='(KRA)Job Position Wise', default=False)

    from_employee_form = fields.Boolean(string='From Employee Form', compute='_compute_from_employee_form', store=False)

    @api.onchange('is_department_wise')
    def _onchange_is_department_wise(self):
        if self.is_department_wise:
            self.is_jobposition_wise = False

    @api.onchange('is_jobposition_wise')
    def _onchange_is_jobposition_wise(self):
        if self.is_jobposition_wise:
            self.is_department_wise = False

    @api.depends_context('from_employee_form')
    def _compute_from_employee_form(self):
        for record in self:
            record.from_employee_form = self.env.context.get('from_employee_form', False)

    @api.depends('kra_department_id', 'kra_job_id', 'kra_normal_id', 'is_department_wise', 'is_jobposition_wise')
    def _compute_kpis(self):
        for record in self:
            if record.is_department_wise:
                kra = record.kra_department_id
            elif record.is_jobposition_wise:
                kra = record.kra_job_id
            else:
                kra = record.kra_normal_id

            record.kpi_id = kra.kpi_id if kra else [(5, 0, 0)]  # Clear if no KRA selected



    @api.constrains('kra_department_id', 'kra_job_id', 'kpi_id')
    def _check_kpi_presence_with_kra(self):
        for record in self:
            kra = record.kra_department_id if record.is_department_wise else record.kra_job_id
            if kra and not kra.kpi_id:
                raise ValidationError(
                    f"The selected KRA '{kra.name}' has no related KPIs. Please add KPIs to the KRA before assigning it."
                )
            
    @api.constrains('weightage')
    def _check_kra_type_selected(self):
        for record in self:
            if record.weightage == 0.00:
                raise ValidationError("Weightage cannot be zero. Please provide a weightage.")



    def action_active_goal(self):
        for record in self:
            record.state = 'active'
            # Find corresponding my.goals record and update its state
            my_goal = self.env['my.goals'].search([
                ('employee_id', '=', record.employee_id.id),
                ('name', '=', record.name),
                ('target', '=', record.target)
            ], limit=1)
            if my_goal:
                my_goal.state = 'active'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'
            # Find corresponding my.goals record and update its state
            my_goal = self.env['my.goals'].search([
                ('employee_id', '=', record.employee_id.id),
                ('name', '=', record.name),
                ('target', '=', record.target)
            ], limit=1)
            if my_goal:
                my_goal.state = 'draft'



    @api.model_create_multi
    def create(self, vals_list):
        # First create the goals.assignment record
        res = super(GoalAssignment, self).create(vals_list)
        for record in res:
            _logger.info("GoalAssignment created: %s", record.name)
            # Determine which KRA to use
            kra_id = record.kra_department_id.id if record.is_department_wise else record.kra_job_id.id
            # Then create the corresponding my.goals record
            self.env['my.goals'].create({
                'name': record.name,
                'employee_id': record.employee_id.id,
                'department_id': record.department_id.id,
                'job_id': record.job_id.id,
                'kra_id': kra_id,
                'kpi_id': record.kpi_id.ids,
                'target': record.target,
                'weightage': record.weightage,
                'timeline_start': record.timeline_start,
                'timeline_end': record.timeline_end,
                'state': record.state,
            })
            _logger.info("my.goals record created for: %s", record.name)
        return res
    
    def write(self, vals):
        res = super(GoalAssignment, self).write(vals)
        
        for record in self:
            # Find the corresponding my.goals record
            my_goal = self.env['my.goals'].search([
                ('employee_id', '=', record.employee_id.id),
                ('name', '=', record.name if 'name' not in vals else vals['name']),
                ('target', '=', record.target if 'target' not in vals else vals['target'])
            ], limit=1)

            if my_goal:
                update_vals = {}

                if 'name' in vals:
                    update_vals['name'] = vals['name']
                if 'employee_id' in vals:
                    update_vals['employee_id'] = vals['employee_id']
                if 'department_id' in vals:
                    update_vals['department_id'] = vals['department_id']
                if 'job_id' in vals:
                    update_vals['job_id'] = vals['job_id']
                if 'target' in vals:
                    update_vals['target'] = vals['target']
                if 'timeline_start' in vals:
                    update_vals['timeline_start'] = vals['timeline_start']
                if 'timeline_end' in vals:
                    update_vals['timeline_end'] = vals['timeline_end']
                if 'state' in vals:
                    update_vals['state'] = vals['state']
                if 'weightage' in vals:
                    update_vals['weightage'] = vals['weightage']
                if 'kra_id' in vals:
                    update_vals['kra_id'] = vals['kra_id']
                if 'kpi_id' in vals:
                    update_vals['kpi_id'] = vals['kpi_id']

                if update_vals:
                    my_goal.write(update_vals)

        return res


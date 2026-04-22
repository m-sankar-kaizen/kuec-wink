# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError, UserError


class PerformanceEvaluation(models.Model):
    _name = 'performance.improvement.plan'
    _description = 'Performance Improvement Plan'
    _order = 'id desc'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position')
    employee_hod_id = fields.Many2one(related='employee_id.parent_id', string='Department Head')
    performance_id = fields.Many2one('performance.evaluation',
                                     string='Parent Revised Performance Evaluation')
    hr_user_id = fields.Many2one('res.users', string='HR Representative')
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    performance_concern = fields.Html(string='Performance Concern')
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')], default='draft',
                             string='Status', tracking=True)
    performance_improvement_line_ids = fields.One2many('performance.improvement.line',
                                                       'improvement_plan_id',
                                                       string='Performance Improvement Lines')

    def copy(self, default=None):
        """Block duplication of Performance Improvement Plans."""
        raise ValidationError(_(
            "Duplicating a Performance Improvement Plan is not allowed."
        ))

    def action_open_performance_goal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Goal Evaluation"),
            'view_mode': 'form',
            'res_model': 'performance.evaluation',
            'views': [(False, 'form')],
            'res_id': self.performance_id.id,
        }

    def _validate_hod(self):
        """Validate that the current user is the assigned Department Head.

            Ensures that only the Department Head linked to the employee can
            perform approval actions on the evaluation form.

            Raises:
                UserError: If the current user is not the assigned Department Head.
        """
        self.ensure_one()
        if self.env.user != self.employee_hod_id.user_id:
            raise UserError(
                _("Only the Head of Department assigned to this employee can confirm this request."))

    def action_done(self):
        """Completion of Performance Improvement Plans."""
        self.ensure_one()
        self._validate_hod()
        self.state = 'done'

    def action_draft(self):
        """Draft Performance Improvement Plans."""
        self.ensure_one()
        self._validate_hod()
        self.state = 'draft'

# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class EmployeeGoalLine(models.Model):
    _name = 'employee.goal.line'
    _description = 'Employee Goal Line'
    _inherit = 'goal.line.mixin'
    _sequence_parent = 'goal_line_id'

    name = fields.Char(string='Goal Name')
    deadline = fields.Date(string='Deadline')
    goal_line_id = fields.Many2one('performance.goal.line', string='Goal Category', copy=False)
    performance_id = fields.Many2one(related='goal_line_id.performance_id',
                                     string='Performance Evaluation')
    mid_term_evaluated = fields.Boolean(string='Mid Term Evaluated',
                                        related='goal_line_id.mid_term_evaluated')
    final_eval_done = fields.Boolean(string='Final Evaluation Done',
                                        related='goal_line_id.final_eval_done')
    expected_kpi = fields.Text(string='Expected KPI')
    performance_state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('pending', 'Pending Confirmation'),
        ('confirmed', 'Confirmed'),
        ('mid_term', 'Mid Term Evaluation'),
        ('final_eval', 'Final Evaluation'),
        ('revised', 'Revised'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], compute='_compute_performance_state', string='Performance State')
    mid_term_rating = fields.Selection(
        selection=[
            ('on_track', 'On Track'),  # --> 1
            ('off_track', 'Off Track'),  # --> 0
        ],
        string='Mid Term Evaluation',
        copy=False,
    )
    final_rating = fields.Selection(
        selection=[
            ('0', '0%'),
            ('1', '25% - (Unacceptable)'),
            ('2', '50% - (Below Expectations)'),
            ('3', '75% - (Meets Expectations)'),
            ('4', '100% - (Exceeds Expectations)'),
        ],
        default='0',
        string='Final Rating',
        copy=False,
    )
    mid_term_score = fields.Float(
        string='Mid Term Score',
        compute='_compute_scores',
        store=True
    )
    final_score = fields.Float(
        string='Final Score',
        compute='_compute_scores',
        store=True
    )
    evaluation_category_id = fields.Many2one('evaluation.category', string='Evaluation Category',
                                             compute='_compute_evaluation_category')
    evaluation_method_id = fields.Many2one('evaluation.method', string='Evaluation Method')

    @api.depends('performance_id.state')
    def _compute_performance_state(self):
        for rec in self:
            rec.performance_state = rec.performance_id.state

    @api.depends('goal_line_id')
    def _compute_evaluation_category(self):
        for rec in self:
            rec.evaluation_category_id = rec.goal_line_id.evaluation_category_id.id if rec.goal_line_id else False

    @api.depends('weight', 'mid_term_rating', 'final_rating')
    def _compute_scores(self):
        for line in self:
            # Mid-term score: weight if 'on_track', else 0
            line.mid_term_score = line.weight if line.mid_term_rating == 'on_track' else 0.0

            # Final score: weight * rating percentage
            rating_map = {
                '0': 0.0,
                '1': 25.0,
                '2': 50.0,
                '3': 75.0,
                '4': 100.0,
            }
            line.final_score = line.weight * (rating_map.get(line.final_rating, 0) / 100.0)

    @api.constrains('deadline', 'goal_line_id')
    def _check_deadline(self):
        for rec in self:
            if rec.goal_line_id and rec.deadline > rec.performance_id.date_to:
                raise ValidationError(_(
                    "The deadline for the goal line '%s' cannot be later than the end of the performance evaluation (%s)."
                ) % (rec.name or 'Unnamed', rec.performance_id.date_to))

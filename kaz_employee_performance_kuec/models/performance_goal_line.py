# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class PerformanceGoalLine(models.Model):
    _name = 'performance.goal.line'
    _description = 'Performance Goal Line'
    _inherit = 'goal.line.mixin'
    _sequence_parent = 'performance_id'
    _rec_name = 'description'

    performance_id = fields.Many2one('performance.evaluation', string='Performance Evaluation',
                                     copy=False)
    performance_state = fields.Selection(related='performance_id.state', string='Performance State')
    mid_term_evaluated = fields.Boolean(string='Mid Term Evaluated', copy=False)
    final_eval_done = fields.Boolean(string='Final Evaluation Done', copy=False)
    date_from = fields.Date(string='Date From', compute='_compute_performance_dates', store=True)
    date_to = fields.Date(string='Date To', compute='_compute_performance_dates', store=True)
    mid_term_score = fields.Float(
        string='Total Mid Term Score',
        compute='_compute_scores',
        store=True
    )
    final_score = fields.Float(
        string='Total Final Score',
        compute='_compute_scores',
        store=True
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
        string='Avg. Final Rating',
        compute='_compute_scores',
        store=True,
    )
    rating_text = fields.Selection(
        selection=[
            ('0', ''),
            ('1', 'Unacceptable #1'),
            ('2', 'Below Expectations #2'),
            ('3', 'Meets Expectations #3'),
            ('4', 'Exceeds Expectations #4'),
        ],
        default='0',
        string='Rating',
        compute='_compute_scores',
    )
    employee_goal_line_ids = fields.One2many('employee.goal.line', 'goal_line_id',
                                             string='Employee Goal Lines')
    goal_weight = fields.Float(compute='_compute_weight', string='Total Weight', store=True)

    def action_mid_term_done(self):
        self.ensure_one()
        self.performance_id._validate_hod()
        for rec in self.employee_goal_line_ids:
            if not rec.mid_term_rating:
                raise ValidationError(_(
                    "Please select the Mid Term Evaluation for the goal '%s' before proceeding."
                ) % (rec.name or 'Unnamed Goal'))
        self.mid_term_evaluated = True
        # self.performance_id._action_mid_term_done()

    def action_final_eval_done(self):
        self.ensure_one()
        self.performance_id._validate_hod()
        for rec in self.employee_goal_line_ids:
            if rec.final_rating == '0':
                raise ValidationError(_(
                    "Please select the Final Rating for the goal '%s' before proceeding."
                ) % (rec.name or 'Unnamed Goal'))
        self.final_eval_done = True
        self.performance_id.action_final_term_done()

    @api.depends('performance_id', 'performance_id.date_from', 'performance_id.date_to')
    def _compute_performance_dates(self):
        for rec in self:
            rec.date_from = rec.performance_id.date_from if rec.performance_id else False
            rec.date_to = rec.performance_id.date_to if rec.performance_id else False

    @api.constrains('goal_weight')
    def _check_total_weight(self):
        """Ensure that the total weight of employee goal lines under the same parent does not exceed 100."""
        for line in self:
            if line.goal_weight > 100:
                raise ValidationError(_(
                    "The total weight of all goal lines under '%s' exceeds 100%%. "
                    "Current total: %.2f%%") % (line.description, line.goal_weight))

    @api.depends('employee_goal_line_ids.weight')
    def _compute_weight(self):
        for rec in self:
            rec.goal_weight = sum(rec.employee_goal_line_ids.mapped('weight'))

    @api.depends('employee_goal_line_ids.mid_term_score',
                 'employee_goal_line_ids.mid_term_rating',
                 'employee_goal_line_ids.final_rating',
                 'employee_goal_line_ids.final_score')
    def _compute_scores(self):
        rating_map = {'0': 0, '1': 25, '2': 50, '3': 75, '4': 100}
        reverse_map = {v: k for k, v in rating_map.items()}
        for line in self:
            if not line.employee_goal_line_ids:
                line.mid_term_score = 0
                line.final_score = 0
                line.final_rating = '0'
                line.rating_text = '0'
                continue

            # Aggregate numeric scores
            mid_term_score = line.employee_goal_line_ids.mapped('mid_term_score')
            line.mid_term_score = sum(mid_term_score) / len(mid_term_score)
            line.final_score = line.weight * sum(
                line.employee_goal_line_ids.mapped('final_score')) / 100

            final_values = [rating_map.get(x.final_rating, 0) for x in line.employee_goal_line_ids]
            avg_final = 0
            if final_values:
                avg_final = sum(final_values) / len(final_values)
            # Find nearest rating
            closest = min(rating_map.values(), key=lambda x: abs(x - avg_final))
            final_rating  = reverse_map[closest]
            line.final_rating = final_rating
            line.rating_text = final_rating

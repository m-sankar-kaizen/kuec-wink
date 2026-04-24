# -*- coding: utf-8 -*-
from odoo import fields, models


class GoalTemplateLine(models.Model):
    _name = 'goal.template.line'
    _description = 'Goal Template Line'
    _inherit = 'goal.line.mixin'
    _sequence_parent = 'goal_template_id'

    goal_template_id = fields.Many2one('goal.template', string='Performance Evaluation')

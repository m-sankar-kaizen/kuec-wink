# -*- coding: utf-8 -*-
from odoo import fields, models, _


class Survey(models.Model):
    _inherit = 'survey.survey'

    performance_id = fields.Many2one('performance.evaluation', string='Performance Evaluation')

    def action_open_goal(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Goal Evaluation"),
            'view_mode': 'form',
            'res_model': 'performance.evaluation',
            'views': [(False, 'form')],
            'res_id': self.performance_id.id,
        }

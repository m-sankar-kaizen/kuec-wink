# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    goal_template_id = fields.Many2one('goal.template', string='Default Goal Template',
                                       domain="[('state', '=', 'active')]")
    final_eval_trigger_days_before = fields.Integer(
        string='Days Before Final Evaluation',
        help="Number of days before the final evaluation date when the system should automatically trigger "
             "the final evaluation state and notify the HOD. Used by the performance evaluation cron job."
    )

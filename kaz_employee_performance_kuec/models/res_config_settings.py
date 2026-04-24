# -*- coding: utf-8 -*-
from odoo import fields, api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    goal_template_id = fields.Many2one(related='company_id.goal_template_id',
                                       string='Default Goal Template', readonly=False)
    final_eval_trigger_days_before = fields.Integer(
        string='Days Before Final Evaluation',
        readonly=False,
        related='company_id.final_eval_trigger_days_before',
        help="Number of days before the final evaluation date when the system should automatically trigger "
             "the final evaluation state and notify the HOD. Used by the performance evaluation cron job."
    )

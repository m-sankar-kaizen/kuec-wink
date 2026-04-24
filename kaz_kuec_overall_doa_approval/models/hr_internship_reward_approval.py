# -*- coding: utf-8 -*-
from odoo import models, fields, _


class InternshipRewardApproval(models.Model):
    _name = 'hr.internship.reward.approval'
    _description = 'Internship Reward Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'reward_id'

    reward_id = fields.Many2one('hr.internship.reward', string='Internship Reward')

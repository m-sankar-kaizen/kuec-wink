# -*- coding: utf-8 -*-
from odoo import models, fields


class GoalModifiedReason(models.Model):
    _name = 'goal.modified.reason'
    _description = 'Goal Modified Reason'
    _check_company_auto = True

    name = fields.Text(string='Reason', required=True)
    performance_id = fields.Many2one('performance.evaluation', string='Performance Evaluation')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    action_type = fields.Selection(
        selection=[
            ('cancel', 'Cancel'),
            ('draft', 'Return for Correction')
        ],
        string='Action Type',
        default='cancel'
    )
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)

    def action_confirm(self):
        """Confirm the performance evaluation."""
        self.ensure_one()
        self.performance_id._perform_action(self.action_type)

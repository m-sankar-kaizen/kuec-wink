# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class GoalTemplate(models.Model):
    _name = 'goal.template'
    _description = 'Goal Template'
    _order = 'id desc'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    goal_template_line_ids = fields.One2many('goal.template.line', 'goal_template_id',
                                             string='Goal Templates')
    total_weight = fields.Float(string='Total Weight', compute='_compute_total_weight', store=True)
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active')], string='State',
                             default='draft')

    def action_activate(self):
        self.ensure_one()
        if self.total_weight != 100:
            raise UserError(
                _("Cannot activate this Goal Template. "
                  "The total weight of all goal lines must be exactly 100. "
                  "Current total weight: %s") % self.total_weight
            )
        self.state = 'active'

    def action_reset(self):
        self.ensure_one()
        self.state = 'draft'

    @api.depends('goal_template_line_ids')
    def _compute_total_weight(self):
        for record in self:
            record.total_weight = sum(record.goal_template_line_ids.mapped('weight'))

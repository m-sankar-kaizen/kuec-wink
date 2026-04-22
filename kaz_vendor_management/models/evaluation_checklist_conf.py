# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EvaluationChecklistConf(models.Model):
    _name = 'evaluation.checklist.conf'
    _description = 'Evaluation Checklist Configuration'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    evaluation_type = fields.Selection(
        selection=[
            ('commercial', 'Commercial'),
            ('technical', 'Technical'),
        ],
        string='Type',
        default='commercial',
        required=True,
    )
    total_weight = fields.Integer(string='Total Weight', compute='_compute_total_weight')
    checklist_conf_line_ids = fields.One2many('evaluation.checklist.conf.line', 'checklist_conf_id',
                                              string='Checklist Conf Lines')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
        ],
        default='draft',
        string='State',
        required=True,
        tracking=True,
    )

    def action_activate(self):
        if self.total_weight != 100:
            raise ValidationError(
                _("The total weight must be exactly 100. Please re-distribute the checklist line weights.")
            )
        self.state = 'active'

    def action_reset_to_draft(self):
        self.state = 'draft'

    @api.depends('checklist_conf_line_ids', 'checklist_conf_line_ids.weight')
    def _compute_total_weight(self):
        for checklist_conf in self:
            checklist_conf.total_weight = sum(
                checklist_conf.checklist_conf_line_ids.mapped('weight'))

    @api.constrains('checklist_conf_line_ids', 'checklist_conf_line_ids.weight')
    def _check_total_weight(self):
        for rec in self:
            if rec.total_weight > 100:
                raise ValidationError(
                    _("The total weight of all checklist lines cannot exceed 100%.")
                )

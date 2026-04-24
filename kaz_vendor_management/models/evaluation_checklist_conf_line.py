# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EvaluationChecklist(models.Model):
    _name = 'evaluation.checklist.conf.line'
    _description = 'Evaluation Checklist Configuration Line'
    _check_company_auto = True

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    weight = fields.Integer(string='Weight')
    checklist_conf_id = fields.Many2one('evaluation.checklist.conf', string='Checklist')

    @api.constrains('weight')
    def _check_weight_limit(self):
        for rec in self:
            if rec.weight > 100:
                raise ValidationError(_("Weight cannot exceed 100."))
            if rec.weight < 0:
                raise ValidationError(_("Weight cannot be negative."))

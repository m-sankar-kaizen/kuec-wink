# -*- coding: utf-8 -*-
from odoo import models, fields, _


class RegisterFormApproval(models.Model):
    _name = 'register.form.approval'
    _description = 'Register Form Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'register_id'

    register_id = fields.Many2one('register.form', string='Resignation')

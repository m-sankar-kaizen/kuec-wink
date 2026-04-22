# -*- coding: utf-8 -*-
from odoo import models, fields, _


class WriteOffRequest(models.Model):
    _name = 'write.off.request.approval'
    _description = 'Write Off Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'write_off_id'

    write_off_id = fields.Many2one('write.off.request', string='Write Off')

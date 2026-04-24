#*- coding: utf-8 -*-

from odoo import models, fields, api,_

class HrmsWarning(models.Model):
    _name = 'hrms.warning'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Warning'


    name = fields.Char(string='Sequence',copy=False, readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee')
    warning = fields.Text()
    document = fields.Binary(string="Attachment")


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hrms.warning') or _('New')
        return super().create(vals_list)
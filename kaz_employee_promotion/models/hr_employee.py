# -*- coding: utf-8 -*-
from odoo import fields, models, _


class HrEmployee(models.Model):
    """Inheriting employee to add employee promotion form as many 2many field"""
    _inherit = 'hr.employee'

    promotion_ids = fields.One2many('employee.promotion', 'employee_id', string='Promotions',
                                    help='The promotions that an employee has received')

    def action_open_employee_promotions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Promotions'),
            'view_mode': 'list,form',
            'res_model': 'employee.promotion',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.promotion_ids.ids)],
        }

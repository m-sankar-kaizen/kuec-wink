# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    religion_id = fields.Many2one('hr.religion', string='Religion')
    sub_religion_id = fields.Many2one('hr.sub.religion', string='Sect',
                                      domain="[('religion_id', '=', religion_id)]")


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    religion_id = fields.Many2one('hr.religion', string='Religion')
    sub_religion_id = fields.Many2one('hr.sub.religion', string='Sect',
                                      domain="[('religion_id', '=', religion_id)]")

# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    hr_email_address = fields.Char(string='Hr Email Address')
    public_relation_manager_id = fields.Many2one('hr.employee',
                                                 string='Public Relation Manager')
    public_relation_manager_arabic_name = fields.Char(
        related='public_relation_manager_id.employee_arabic_name',
        string='Public Relation Manager (Arabic)',
        help="Arabic name of the selected Public Relation Manager, "
             "used in bilingual reports and contracts."
    )
    public_relation_manager_arabic_job_position = fields.Char(
        related='public_relation_manager_id.employee_arabic_job_position',
        string="Public Relation Manager's Position (Arabic)",
        help="Arabic version of the Public Relation Manager's job "
             "position for use in Arabic documents."
    )

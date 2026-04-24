# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompanyExtend(models.Model):
    _inherit = 'res.company'

    menu_ids = fields.Many2many('ir.ui.menu', string='Hide Menu')

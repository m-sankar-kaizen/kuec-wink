# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    portal_bank_name = fields.Char(string="Portal Bank Name")

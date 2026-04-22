# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_company_code_selection(self):
        selection = super()._get_company_code_selection()
        selection.append(('WINK', 'WINK'))
        return selection

    company_code = fields.Selection(
        selection=_get_company_code_selection,
        )

# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_directory_enabled = fields.Boolean(
        string='Enable Employee Directory Portal',
        default=False,
        help='If checked, this partner will have access to the Employee Directory /my/employees app in the portal.'
    )

    wink_company_type = fields.Selection(
        [
            ('ku', 'KU'),
            ('kuec', 'KUEC'),
            ('uae', 'UAE Team Emirates'),
            ('outside', 'Outside UAE'),
        ],
        string='Company Type (WINK)',
    )

    trade_license_number = fields.Char(
        string="Trade License No.",
        copy=False
    )

    tax_license_number = fields.Char(
        string="Tax Registration No.",
        copy=False
    )

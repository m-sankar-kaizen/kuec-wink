# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_directory_enabled = fields.Boolean(
        string='Enable Employee Directory Portal',
        default=False,
        help='If checked, this partner will have access to the Employee Directory /my/employees app in the portal.'
    )

    legal_entity_type = fields.Selection(
        [
            ('llc', 'Limited Liability Company (LLC / Ltd.)'),
            ('corp', 'Corporation (Inc. / Corp.)'),
            ('plc', 'Public Listed Company'),
            ('partnership', 'Partnership'),
            ('lp', 'Limited Partnership (LP / LLP)'),
            ('gov', 'Government Entity'),
            ('soe', 'State-Owned Enterprise'),
            ('non_profit', 'Non-Profit Organization'),
            ('other', 'Other (Specify)'),
        ],
        string='Legal Entity Type',
    )

    trade_license_number = fields.Char(
        string="Trade License No.",
        copy=False
    )

    tax_license_number = fields.Char(
        string="Tax Registration No.",
        copy=False
    )

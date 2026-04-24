# -*- coding: utf-8 -*-

from odoo import models, fields


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    is_rou_asset = fields.Boolean(
        string='ROU Asset',
        default=False,
        help='Right-of-Use Asset created from IFRS 16 Lease Contract'
    )
    
    lease_contract_id = fields.Many2one(
        'lease.lessee.contract',
        string='Lease Contract',
        help='Related lease contract for this ROU asset'
    )

    is_leased = fields.Boolean(string="Leased")

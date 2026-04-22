# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountAsset(models.Model):
    """
    Inherits the standard account.asset model to add additional
    informational fields for tracking and identification purposes.
    These fields are useful for asset audits, location tracking,
    and inventory management.
    """
    _inherit = 'account.asset'

    asset_number = fields.Char(string="Asset Number")
    tag_number = fields.Char(string="Tag Number")
    serial_number = fields.Char(string="Serial Number")
    site = fields.Char(string="Site")
    room = fields.Char(string="Room")

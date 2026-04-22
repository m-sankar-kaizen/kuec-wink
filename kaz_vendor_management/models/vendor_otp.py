# -*- coding: utf-8 -*-
import random

from odoo import models, fields
from datetime import timedelta


class VendorOTP(models.TransientModel):
    _name = 'vendor.otp'
    _description = 'Vendor OTP'
    _transient_max_hours = 2
    _rec_name = 'email'

    def _generate_otp(self):
        """Generate a 6-digit random OTP"""
        return ''.join(random.choices('0123456789', k=6))

    name = fields.Char(string='Vendor Name')
    email = fields.Char('Email', required=True, index=True)
    otp = fields.Char('OTP', required=True, default=_generate_otp, index=True)
    expiry = fields.Datetime('Expiry Time',
                             default=lambda self: fields.Datetime.now() + timedelta(minutes=5))

    def is_valid(self):
        """
        Check if OTP matches and not expired.
        Returns True if valid, False otherwise.
        """
        if fields.Datetime.now() > self.expiry:
            return False
        return True

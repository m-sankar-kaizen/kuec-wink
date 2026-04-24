# -*- coding: utf-8 -*-
from odoo import models, fields


class ResBank(models.Model):
    """
    Extend res.bank to store additional bank information:
    - bank_name: Full name of the bank
    - bank_number: Internal bank code or identifier
    - iban_no: International Bank Account Number
    - swift_code: Bank Identifier Code used for international transfers
    """
    _inherit = 'res.bank'

    bank_name = fields.Char(string='Bank Name')  # Custom display name (if needed in reports/UI)
    bank_number = fields.Char(string='Bank Number')  # Custom bank code or reference number
    iban_no = fields.Char(string='IBAN NO')  # IBAN number (used in bank transfers)
    swift_code = fields.Char(string='Swift Code')  # SWIFT/BIC code for international banking

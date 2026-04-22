# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResBank(models.Model):
    """
    Inherits the `res.bank` model to include additional banking details
    required for employee salary transfers and international remittance.

    These fields are primarily used in integration with payroll systems,
    especially where routing or intermediary banking information is needed.
    """
    _inherit = 'res.bank'

    emp_routing_no = fields.Char(
        string='Agent ID/Routing No',
        required=False,
        help="Optional routing number or agent ID used for interbank transactions. "
             "Can be useful for specific banks that use routing codes or intermediary bank identifiers.")

    iban_num = fields.Char(string='IBAN NO')

    swift_address_bic = fields.Char(
        string='Swift Address/BIC',
        required=False,
        help="SWIFT/BIC code for the bank. Used in international transfers to identify the bank's branch uniquely.")

    # @api.onchange('iban_num')
    # def _onchange_iban(self):
    #     """Prepend 'AE' to IBAN if not already present."""
    #     for rec in self:
    #         if rec.iban_num and not rec.iban_num.startswith('AE'):
    #             rec.iban_num = f"AE{rec.iban_num}"

    # @api.constrains('iban_num')
    # def _check_iban_format(self):
    #     """Ensure IBAN format: starts with 'AE' and followed by 21 digits."""
    #     for rec in self:
    #         if (
    #                 not rec.iban_num or
    #                 not rec.iban_num.startswith('AE') or
    #                 len(rec.iban_num) != 23 or
    #                 not rec.iban_num[2:].isdigit()
    #         ):
    #             raise ValidationError(
    #                 "IBAN must start with 'AE' followed by exactly 21 digits.")

# -*- coding: utf-8 -*-
from odoo import models, fields


class ResBank(models.Model):
    """
    Inherits the standard Odoo res.bank model to extend its functionality
    by introducing an Arabic name field for banks.

    This enhancement is particularly useful for bilingual implementations
    (e.g., English-Arabic environments) where displaying or printing bank
    names in Arabic is necessary for legal, financial, or user accessibility purposes.
    """

    _inherit = 'res.bank'

    bank_arabic_name = fields.Char(
        string="Arabic Name",
        help="The name of the bank in Arabic. Used in Arabic-language reports or documents."
    )

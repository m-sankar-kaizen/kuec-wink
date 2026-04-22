# -*- coding: utf-8 -*-
from odoo import models, fields


class AddressTo(models.Model):
    """
    A simple master data model to store "addressed to" recipients for official documents
    like letters or certificates. Useful for populating dropdown fields when generating
    formal letters to external entities, including banks, ministries, etc.
    """

    _name = 'address.to'
    _description = 'Address To'

    name = fields.Char(
        string="Name",
        help="The recipient's name in English."
    )

    arabic_name = fields.Char(
        string="Arabic Name",
        help="The recipient's name in Arabic, used in bilingual documents."
    )

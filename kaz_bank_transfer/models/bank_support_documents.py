# -*- coding: utf-8 -*-
from odoo import fields, models


class BankSupportingDocuments(models.Model):
    """
    Stores documents uploaded in support of a bank transfer request.
    """
    _name = 'bank.support.documents'
    _description = "Bank Support Documents"

    name = fields.Char(
        required=True,
        help="Name or title of the supporting document."
    )
    attachment = fields.Binary(
        required=True,
        help="The uploaded file (PDF, image, etc)."
    )
    attachment_name = fields.Char(
        help="Original filename of the uploaded document."
    )
    description = fields.Text(
        help="Optional remarks or explanation for the document."
    )
    transfer_id = fields.Many2one(
        'bank.transfer',
        help="Link to the bank transfer request this document supports."
    )

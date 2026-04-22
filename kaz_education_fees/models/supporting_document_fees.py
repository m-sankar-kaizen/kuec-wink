# -*- coding: utf-8 -*-
from odoo import models, fields


class SupportingDocuments(models.Model):
    """
    Supporting Documents for Education Fee Requests.

    This model stores binary attachments and metadata related to documents
    supporting an education reimbursement claim, such as fee receipts,
    school certificates, or invoices.
    """
    _name = 'supporting.documents.fees'
    _description = 'Education Fee Supporting Documents'

    name = fields.Char(
        string='Document Name',
        required=True,
        help="A descriptive name for the uploaded document (e.g., 'Tuition Receipt')."
    )

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        default=lambda self: self.env.company,
        help="Company associated with this document. Defaults to the current user's company."
    )

    attachment = fields.Binary(
        string='Attachment',
        required=True,
        attachment=True,
        help="Upload the actual supporting document file here."
    )

    education_fees_id = fields.Many2one(
        'education.fees',
        string="Education Fee Request",
        help="Link to the related education fee reimbursement request."
    )

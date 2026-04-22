# -*- coding: utf-8 -*-
from odoo import models, fields


class SupportingDocuments(models.Model):
    """
    Stores uploaded documents that support the child allowance request.

    Each record is linked to one request and may optionally reference a child.
    """
    _name = 'supporting.documents'
    _description = 'Supporting Documents'

    name = fields.Char('Document Name', required=True)
    attachment = fields.Binary('Attachment', attachment=True)
    attachment_name = fields.Char('Filename')
    description = fields.Text('Description (optional)')
    kid_id = fields.Many2one(
        'kids.details',
        domain="[('parent_id', '=', employee_id)]",
        string="Related Child"
    )
    child_allowance_id = fields.Many2one(
        'child.allowance',
        string="Child Allowance Request"
    )
    employee_id = fields.Many2one(
        related='child_allowance_id.employee_id',
        string="Employee"
    )

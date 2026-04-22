# -*- coding: utf-8 -*-
from odoo import fields, models


class AttachmentLineMixin(models.AbstractModel):
    _name = 'attachment.line.mixin'
    _description = 'Attachment Line Mixin'

    name = fields.Char('Name', required=True)
    attachment_is_required = fields.Boolean('Attachment Required')
    expiry_date_required = fields.Boolean('Expiry Date Required')
    sequence = fields.Integer('Sequence')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    attachment_type = fields.Selection(
        # [('link', 'Link'), ('attachment', 'Attachment')],
        [('attachment', 'Attachment')],
        default='attachment',
        required=True,
        string='Attachment Type',
    )

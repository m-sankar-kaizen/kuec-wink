# -*- coding: utf-8 -*-

from odoo import models, fields

class KuecServiceDocument(models.Model):
    _name = 'kuec.service.document'
    _description = 'KUEC Service Required Document'
    _order = 'sequence, id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Service Product',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(
        string='Document Name',
        required=True
    )
    requirement = fields.Selection(
        selection=[
            ('required', 'Required'),
            ('optional', 'Optional')
        ],
        string='Requirement',
        required=True,
        default='required'
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10
    )

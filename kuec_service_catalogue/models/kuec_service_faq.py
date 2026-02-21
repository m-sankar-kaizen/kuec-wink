# -*- coding: utf-8 -*-

from odoo import models, fields

class KuecServiceFaq(models.Model):
    _name = 'kuec.service.faq'
    _description = 'KUEC Service FAQ'
    _order = 'sequence, id'

    product_tmpl_id = fields.Many2one('product.template', string='Service Product', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    question = fields.Char(string='Question', required=True, translate=True)
    answer = fields.Html(string='Answer', required=True, translate=True)

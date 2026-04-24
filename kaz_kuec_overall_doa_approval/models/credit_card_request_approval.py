# -*- coding: utf-8 -*-
from odoo import models, fields, _


class CreditCardRequestApproval(models.Model):
    _name = 'credit.card.request.approval'
    _description = 'Credit Card Request Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'card_request_id'

    card_request_id = fields.Many2one('credit.card.request', string='Credit Card Request')

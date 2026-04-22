# -*- coding: utf-8 -*-
from odoo import models, fields, _


class RelatedPartyEntriesApproval(models.Model):
    _name = 'related.party.entries.approval'
    _description = 'Related Party Entries Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'related_party_id'

    related_party_id = fields.Many2one('related.party.entries', string='Related Party Entry')

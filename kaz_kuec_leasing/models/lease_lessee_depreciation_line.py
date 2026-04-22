# -*- coding: utf-8 -*-

from odoo import models, fields, api


class LeaseLesseeDepreciationLine(models.Model):
    _name = 'lease.lessee.depreciation.line'
    _description = 'Lease Lessee Depreciation Line'
    _order = 'date asc'

    contract_id = fields.Many2one(
        'lease.lessee.contract',
        string='Lease Contract',
        required=True,
        ondelete='cascade',
        index=True
    )
    
    date = fields.Date(
        string='Date',
        required=True,
        help='Date of the depreciation entry'
    )
    
    amount = fields.Monetary(
        string='Depreciation Amount',
        required=True,
        currency_field='currency_id',
        help='Depreciation amount for this period'
    )
    
    accumulated_amount = fields.Monetary(
        string='Accumulated Depreciation',
        readonly=True,
        currency_field='currency_id',
        help='Total accumulated depreciation up to this date'
    )
    
    remaining_value = fields.Monetary(
        string='Remaining Value',
        readonly=True,
        currency_field='currency_id',
        help='Remaining book value of the ROU asset'
    )
    
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        help='Related depreciation journal entry'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='contract_id.currency_id',
        store=True
    )
    
    state = fields.Selection(
        related='move_id.state',
        string='Status',
        store=True
    )

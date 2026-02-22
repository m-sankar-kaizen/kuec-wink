# -*- coding: utf-8 -*-

from odoo import models, fields

class KuecBundleGroup(models.Model):
    _name = 'kuec.bundle.group'
    _description = 'Bundle Group / Tier'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    
    line_ids = fields.One2many(
        'kuec.bundle.group.line', 
        'bundle_group_id', 
        string='Tiers',
        copy=True
    )
    
    allow_upgrade = fields.Boolean(string='Allow Upgrade', default=True)
    allow_downgrade = fields.Boolean(string='Allow Downgrade', default=True)
    allow_cancellation = fields.Boolean(string='Allow Cancellation', default=False)
    
    credit_routing = fields.Selection([
        ('wallet', 'Wallet'),
        ('credit_note', 'Credit Note')
    ], string='Credit Routing', default='wallet')

    loyalty_program_id = fields.Many2one(
        'loyalty.program',
        string="Wallet / Gift Card Program",
        domain=[('program_type', '=', 'gift_card')],
        help="Odoo loyalty program used to issue wallet credit on plan changes. Required when credit_routing = gift_card."
    )

    def compute_remaining_value(self, product_tmpl, subscription_end_date):
        from odoo.exceptions import UserError
        today = fields.Date.today()
        remaining_days = (subscription_end_date - today).days
        if remaining_days <= 0:
            raise UserError(
                "Subscription end date is in the past. "
                "Cannot compute remaining value."
            )
        if not product_tmpl.standard_monthly_price:
            raise UserError(
                "Standard Monthly Price is not set on "
                "'%s'. Please set it before processing "
                "a plan change." % product_tmpl.name
            )
        return (product_tmpl.standard_monthly_price / 30.0) * remaining_days

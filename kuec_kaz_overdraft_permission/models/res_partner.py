from odoo import models, fields


class Partner(models.Model):
    _inherit = 'res.partner'

    use_partner_debit_limit = fields.Boolean()
    use_partner_block_limits = fields.Boolean(string='Use Block Limits')
    receivable_block_limit = fields.Monetary(string='Receivable Block Limit')
    payable_block_limit = fields.Monetary(string='Payable Block Limit')

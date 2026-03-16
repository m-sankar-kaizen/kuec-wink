# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_directory_enabled = fields.Boolean(
        string='Enable Employee Directory Portal',
        default=False,
        help='If checked, this partner will have access to the Employee Directory /my/employees app in the portal.'
    )

    legal_entity_type = fields.Selection(
        [
            ('llc', 'Limited Liability Company (LLC / Ltd.)'),
            ('corp', 'Corporation (Inc. / Corp.)'),
            ('plc', 'Public Listed Company'),
            ('partnership', 'Partnership'),
            ('lp', 'Limited Partnership (LP / LLP)'),
            ('gov', 'Government Entity'),
            ('soe', 'State-Owned Enterprise'),
            ('non_profit', 'Non-Profit Organization'),
            ('other', 'Other (Specify)'),
        ],
        string='Legal Entity Type',
    )

    trade_license_number = fields.Char(
        string="Trade License No.",
        copy=False
    )

    tax_license_number = fields.Char(
        string="Tax Registration No.",
        copy=False
    )

    wink_company_type = fields.Selection([
        ('ku', 'KU'),
        ('kuec', 'KUEC'),
        ('uae', 'UAE Company'),
        ('outside', 'Outside UAE'),
    ], string='Company Classification',
       help="This helps us serve you better.")

    # EPIC-11: Vendor performance rating aggregated from customer evaluations on WINK tasks
    wink_avg_rating = fields.Float(
        compute='_compute_wink_avg_rating',
        string='Avg. Service Rating',
        digits=(4, 2),
        help='Average customer rating (1–5) across all WINK service tasks where this partner is the assigned vendor.',
    )
    wink_rating_count = fields.Integer(
        compute='_compute_wink_avg_rating',
        string='Rating Count',
        help='Total number of consumed customer ratings linked to this vendor.',
    )

    def action_view_wink_ratings(self):
        """Open the CX ratings list filtered to this vendor."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'kuec_service_catalogue.action_wink_cx_report'
        )
        action['domain'] = [
            ('rated_partner_id', 'child_of', self.id),
            ('consumed', '=', True),
            ('res_model', '=', 'project.task'),
        ]
        action['display_name'] = 'Ratings — %s' % self.name
        return action

    def _compute_wink_avg_rating(self):
        """Aggregate rating.rating records where rated_partner_id = this vendor."""
        ratings = self.env['rating.rating'].search([
            ('rated_partner_id', 'in', self.ids),
            ('consumed', '=', True),
            ('res_model', '=', 'project.task'),
        ])
        from collections import defaultdict
        score_map = defaultdict(list)
        for r in ratings:
            score_map[r.rated_partner_id.id].append(r.rating)
        for partner in self:
            scores = score_map.get(partner.id, [])
            partner.wink_rating_count = len(scores)
            partner.wink_avg_rating = sum(scores) / len(scores) if scores else 0.0

    wallet_transaction_ids = fields.One2many(
        'kuec.wallet.transaction',
        'partner_id',
        string='Wallet Transactions',
        help='All eWallet transactions for this customer.',
    )

    wink_wallet_balance = fields.Float(
        string='Wallet Balance',
        compute='_compute_wink_wallet_balance',
        digits=(10, 2),
        help='Current eWallet balance: sum of all done transactions (positive = credit, negative = debit).',
    )

    def _compute_wink_wallet_balance(self):
        """Sum all done kuec.wallet.transaction amounts for each partner."""
        txn_model = self.env['kuec.wallet.transaction']
        for partner in self:
            txns = txn_model.search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'done'),
            ])
            partner.wink_wallet_balance = sum(txns.mapped('amount'))

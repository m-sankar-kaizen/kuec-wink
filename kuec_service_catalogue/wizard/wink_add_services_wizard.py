# -*- coding: utf-8 -*-
# Issue 3: Multi-select services wizard for bundle tier configuration

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WinkAddServicesWizard(models.TransientModel):
    _name = 'wink.add.services.wizard'
    _description = 'Add Multiple Services to Bundle Tier'

    tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Bundle Tier',
        required=True,
        ondelete='cascade',
        readonly=True,
        help='The bundle tier to add services to.',
    )
    bundle_name = fields.Char(
        related='tier_id.bundle_id.name',
        string='Bundle',
        readonly=True,
    )
    service_product_ids = fields.Many2many(
        'product.template',
        'wink_add_svc_wizard_product_rel',
        'wizard_id',
        'product_tmpl_id',
        string='Services to Add',
        domain=[
            ('type', '=', 'service'),
            ('sale_ok', '=', True),
            ('wink_is_bundle', '=', False),
        ],
        help='Select one or more services to add to this tier. Services already in the tier will be skipped.',
    )

    def action_confirm(self):
        """Create wink.bundle.tier.item records for each selected service (skip duplicates)."""
        self.ensure_one()
        if not self.service_product_ids:
            raise UserError(_('Please select at least one service to add.'))

        existing_product_ids = set(self.tier_id.item_ids.mapped('service_product_id.id'))
        next_seq = max((self.tier_id.item_ids.mapped('sequence') or [0])) + 10

        added = 0
        skipped = 0
        for product in self.service_product_ids:
            if product.id in existing_product_ids:
                skipped += 1
                continue
            self.env['wink.bundle.tier.item'].create({
                'tier_id': self.tier_id.id,
                'service_product_id': product.id,
                'qty': 1,
                'sequence': next_seq,
            })
            next_seq += 10
            added += 1

        msg = _('%d service(s) added to tier "%s".') % (added, self.tier_id.name)
        if skipped:
            msg += _(' %d already present — skipped.') % skipped

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Services Added'),
                'message': msg,
                'type': 'success',
                'sticky': False,
            },
        }

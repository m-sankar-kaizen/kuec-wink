# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class SaleOrderLineBundle(models.Model):
    _inherit = 'sale.order.line'

    wink_is_bundle_child = fields.Boolean(
        string='Bundle Child Service',
        default=False,
    )
    wink_bundle_activation_state = fields.Selection(
        [
            ('pending', 'Pending'),
            ('requested', 'Activation Requested'),
            ('active', 'Active'),
            ('completed', 'Completed'),
        ],
        string='Activation Status',
        default='pending',
    )
    wink_bundle_parent_line_id = fields.Many2one(
        'sale.order.line',
        string='Parent Bundle Line',
        ondelete='set null',
    )

    def action_bundle_activate(self):
        """Coordinator activates a requested bundle child service."""
        self.ensure_one()
        self.write({
            'wink_bundle_activation_state': 'active',
        })
        self.order_id.message_post(
            body=(
                f"Bundle service <strong>"
                f"{self.name}</strong>"
                f" activated."
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

    def action_bundle_complete(self):
        """Coordinator marks a bundle child service as completed."""
        self.ensure_one()
        self.write({
            'wink_bundle_activation_state': 'completed',
        })
        self.order_id.message_post(
            body=(
                f"Bundle service <strong>"
                f"{self.name}</strong>"
                f" completed."
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )


class SaleOrderConfirm(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Overrides action_confirm to validate commercial structures.
        Bundle products submitted via WINK portal (with child lines)
        skip the old bundled validation since the tier system handled it.
        """
        for order in self:
            for line in order.order_line:
                if (line.product_id
                        and line.product_id.commercial_structure == 'bundled'
                        and not line.wink_is_bundle_child
                        and not order.wink_bundle_tier_id):
                    is_bundled = (
                        self.env.context.get('is_bundle_line', False)
                        or (hasattr(line, 'linked_line_id') and line.linked_line_id)
                    )
                    if not is_bundled:
                        raise ValidationError(_(
                            "'%(name)s' can only be purchased as part of a bundle. "
                            "It cannot be added as a standalone order line."
                        ) % {'name': line.product_id.name})

        return super().action_confirm()

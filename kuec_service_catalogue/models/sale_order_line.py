# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class SaleOrderLineBundle(models.Model):
    _inherit = 'sale.order.line'

    wink_entitlement_id = fields.Many2one(
        'wink.bundle.entitlement',
        string='Bundle Entitlement',
        ondelete='set null',
        help='Links this activated line back to its bundle '
             'entitlement record.',
    )


class SaleOrderConfirm(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Validate that bundled products are only purchased through
        the WINK bundle flow (with a tier selected), not added
        as standalone order lines.
        """
        for order in self:
            for line in order.order_line:
                if (line.product_id
                        and line.product_id.product_tmpl_id
                            .commercial_structure == 'bundled'
                        and not line.wink_entitlement_id
                        and not order.wink_bundle_tier_id):
                    is_bundled = (
                        self.env.context.get('is_bundle_line', False)
                        or (hasattr(line, 'linked_line_id')
                            and line.linked_line_id)
                    )
                    if not is_bundled:
                        raise ValidationError(_(
                            "'%(name)s' can only be purchased "
                            "as part of a bundle. It cannot be "
                            "added as a standalone order line."
                        ) % {'name': line.product_id.name})

        return super().action_confirm()

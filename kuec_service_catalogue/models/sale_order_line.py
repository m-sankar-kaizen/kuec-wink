# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Overrides action_confirm to validate commercial structures.
        Only fires on manual confirmation, avoiding conflicts with
        automated subscription renewals and cron jobs.
        """
        for order in self:
            for line in order.order_line:
                if line.product_id and line.product_id.commercial_structure == 'bundled':
                    # Check if standard Odoo 18 combo fields are present. Natively, they use linked_line_id
                    is_bundled = self.env.context.get('is_bundle_line', False) or hasattr(line, 'linked_line_id') and line.linked_line_id
                    
                    if not is_bundled:
                        raise ValidationError(_(
                            "'%(name)s' can only be purchased as part of a bundle. "
                            "It cannot be added as a standalone order line."
                        ) % {'name': line.product_id.name})
                        
        return super().action_confirm()

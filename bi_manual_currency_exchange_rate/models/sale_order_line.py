# -*- coding: utf-8 -*-
from odoo import models


class SaleOrderLine(models.Model):
    """
    Extension of the `sale.order.line` model to propagate manual currency rate to price computation context.

    Methods:
        - _get_product_price_context: Supplies the pricing engine with FX override flags.
    """
    _inherit = 'sale.order.line'

    def _conditional_add_to_compute(self, fname, condition):
        field = self._fields[fname]
        to_reset = self.filtered(lambda move:
                                 condition(move)
                                 and not self.env.is_protected(field, move._origin)
                                 and (move._origin or not move[fname])
                                 )
        to_reset.invalidate_recordset([fname])
        self.env.add_to_compute(field, to_reset)

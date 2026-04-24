# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _create_or_update_service_picking(self):
        no_srn = self._context.get('no_srn', False)
        if no_srn:
            return
        else:
            super()._create_or_update_service_picking()

# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrderLine(models.Model):
    """
    Inherits the `purchase.order.line` model to add a
    reference to the specific requisition line item.

    Purpose:
    --------
    - Maintains a linkage between individual PO lines and the
     corresponding lines in a Material Purchase Requisition.
    - Facilitates line-level traceability, allocation analysis,
     and budget tracking when needed.

    Use Case:
    ---------
    - Allows users to trace each item in a PO line back to the
     specific requisitioned item for control and reconciliation.

    Field:
    ------
    - `custom_requisition_line_id`: A Many2one relation pointing
     to `material.purchase.requisition.line`.
    """
    _inherit = 'purchase.order.line'

    custom_requisition_line_id = fields.Many2one(
        'material.purchase.requisition.line',
        string='Requisitions Line',
        copy=False,
        help="Reference to the corresponding material"
             " purchase requisition line item."
    )

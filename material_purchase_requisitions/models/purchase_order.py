# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrder(models.Model):
    """
    Inherits the `purchase.order` model to add a link
    to the originating material purchase requisition.

    Purpose:
    --------
    - Establishes a reference between a Purchase Order and the originating
     custom Material Purchase Requisition (`material.purchase.requisition`).
    - Enables traceability from the PO to the requisition document, which is
    useful for audit, reporting, and approval tracking.

    Use Case:
    ---------
    - When a Purchase Order is generated from a Material Purchase Requisition,
     this field links the PO to its source requisition.

    Field:
    ------
    - `custom_requisition_id`: A Many2one relation pointing to the originating
    `material.purchase.requisition` record.
    """
    _inherit = 'purchase.order'

    custom_requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisitions',
        copy=False,
        help="Reference to the originating material purchase requisition"
             " from which this purchase order was generated."
    )

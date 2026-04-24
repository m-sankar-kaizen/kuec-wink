# -*- coding: utf-8 -*-
from odoo import models, fields


class StockPicking(models.Model):
    """
    Inherits: stock.picking

    Adds linkage between a stock picking and a custom material purchase requisition.

    This is useful to trace internal transfers or receipts that originated from a requisition request.
    Enables full traceability and audit trail across the procurement workflow.

    Fields:
        - custom_requisition_id: A link to the related `material.purchase.requisition` record that initiated this picking.
    """
    _inherit = 'stock.picking'

    custom_requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Purchase Requisition',
        readonly=True,
        copy=True,
        help="Reference to the originating material purchase requisition (if this picking was generated from one)."
    )

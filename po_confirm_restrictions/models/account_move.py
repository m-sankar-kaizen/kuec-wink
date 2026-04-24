# -*- coding: utf-8 -*-
"""
This module extends the standard `account.move` model in Odoo
to add functionality specific to Purchase Order (PO) tracking,
particularly for handling partial approvals, financial amounts,
and relevant document attachments.

Key Enhancements:
-----------------
1. `partial_po`: A boolean flag to indicate if the purchase order was partially approved or processed.
2. `total_amount`: A float to store the total expected amount of the related purchase order.
3. `remaining_amount`: A float to store the unprocessed or unpaid balance amount.
4. `purchase_order_attach`: A binary field to store the scanned or uploaded version of the purchase order.
5. `goods_received_note`: A binary field to store the GRN (Goods Received Note) for verification purposes.

Typical Use Case:
-----------------
This customization is useful in financial and procurement audits where partial payment tracking,
invoice reconciliation, and proof of delivery/receipts are essential for compliance or approval workflows.

Model Inheritance:
------------------
Inherits from `account.move` (the base model for accounting journal entries and invoices in Odoo).
"""

from odoo import models, fields, api


class AccountMove(models.Model):
    """
        Extension of the Account Move model to capture additional purchase order-related data
        for improved tracking, financial reconciliation, and documentation workflows.

        Fields:
        --------
        - partial_po (Boolean): Indicates if the related Purchase Order is only partially invoiced.
        - total_amount (Float): Represents the total value of the linked Purchase Order.
        - remaining_amount (Float): Reflects the unbilled value remaining from the PO.
        - purchase_order_attach (Binary): A binary field to attach a copy of the Purchase Order document.
        - goods_received_note (Binary): A binary field to attach the corresponding Goods Received Note (GRN).

        Purpose:
        --------
        Enables downstream visibility into Purchase Order data within the invoice for organizations
        with advanced procurement and finance approval workflows.

        This extension is especially useful when POs are partially fulfilled or partially invoiced
        and where the original documents (PO, GRN) must be attached for auditing, review, or approval.
        """
    _inherit = 'account.move'

    # Indicates whether the purchase order linked to this invoice is partially processed.
    partial_po = fields.Boolean(
        string='Partial Purchase Order',
        default=False,
        help="Check this if the purchase order is only partially fulfilled or processed."
    )

    # Total amount expected from the purchase order related to this invoice.
    total_amount = fields.Float(
        string='Total PO Amount',
        help="Represents the total value of the related purchase order, used for reconciliation and validation."
    )

    # Remaining amount yet to be processed or paid.
    remaining_amount = fields.Float(
        string='Remaining Amount',
        help="Amount pending from the total PO, helpful in tracking partial payments or receipts."
    )

    # Attachment for the original purchase order document.
    purchase_order_attach = fields.Binary(
        string='Purchase Order Attachment',
        help="Upload the scanned purchase order document for reference or audit trail."
    )

    # Attachment for the Goods Received Note (GRN).
    goods_received_note = fields.Binary(
        string='Goods Received Note',
        help="Upload the Goods Received Note (GRN) to confirm delivery and receipt of goods/services."
    )

# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PurchaseOrder(models.Model):
    """
    Model Inheritance: Extends `purchase.order`

    This model extension adds custom fields to capture contract-related metadata
    and tracks the user who confirms the purchase order. It also overrides the
    `button_confirm` method to store the confirming user's identity.

    Added Fields:
        - so_title (Char): Title or subject for the sales order or purchase order.
        - contract_ref (Char): Reference number or code for the related contract.
        - effective_date (Date): The date when the contract or PO becomes effective.
        - end_date (Date): The date when the contract or PO expires or ends.
        - confirm_uid (Many2one to res.users): The user who confirmed the purchase order.
        - employee_id (Many2one to hr.employee): The employee associated with the PO (e.g., requester or owner).
    """

    _inherit = 'purchase.order'

    # Optional subject/title of the order, often used in contract contexts
    so_title = fields.Char(
        string="SO Title",
        help="Descriptive title or subject for the purchase order."
    )

    # Contract reference number (internal or external)
    contract_ref = fields.Char(
        string="Contract Reference",
        help="Reference identifier for the associated contract."
    )

    # Date when the contract or order becomes active
    effective_date = fields.Date(
        string="Effective Date",
        help="Start date of the contract or purchase order."
    )

    # Date when the contract or order ends
    end_date = fields.Date(
        string="End Date",
        help="End date of the contract or purchase order."
    )

    # User who confirmed the purchase order
    confirm_uid = fields.Many2one(
        'res.users',
        string="Confirmed By",
        readonly=True,
        help="User who confirmed this purchase order."
    )

    # Employee linked to the PO, typically the internal requester or owner
    employee_id = fields.Many2one(
        'hr.employee',
        string="Employee",
        help="Employee associated with this purchase order."
    )

    def button_confirm(self):
        """
        Override of the standard purchase order confirmation method.

        Functionality:
            - Sets the `confirm_uid` field to the current user confirming the order.
            - Then calls the superclass method to execute the standard confirmation flow.
        """
        for order in self:
            order.confirm_uid = self.env.user.id  # Track the user confirming the order
        return super().button_confirm()

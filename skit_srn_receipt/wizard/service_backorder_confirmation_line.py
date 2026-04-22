# -*- coding: utf-8 -*-
from odoo import fields, models


class ServiceBackorderConfirmationLine(models.TransientModel):
    """
    Model: service.backorder.confirmation.line

    Purpose:
    This transient model (i.e., temporary wizard data model) is used within the
    `service.backorder.confirmation` wizard to display each service receipt that
    the user is attempting to validate.

    Each record in this model represents one line (one service receipt) and includes
    a user-defined flag (`to_backorder`) that determines whether the remaining unprocessed
    service lines for that receipt should be backordered.

    This model helps users decide which receipts require backorders and which should
    be marked as fully processed (despite incomplete quantities), giving them granular
    control during the validation process.

    Key Fields:
    -----------
    - service_backorder_confirmation_id: ForeignKey to the parent wizard (`service.backorder.confirmation`)
    - service_receipt_id: Reference to the `service.receipt` model being confirmed.
    - to_backorder: Boolean indicating whether the remaining quantity for the receipt
                    should be backordered (True) or ignored (False).
    """
    _name = 'service.backorder.confirmation.line'
    _description = 'Backorder Confirmation Line'

    # Link to the main backorder confirmation wizard instance.
    service_backorder_confirmation_id = fields.Many2one(
        'service.backorder.confirmation',
        string='Immediate Transfer',
        help="Reference to the parent wizard. All lines belong to a specific confirmation wizard."
    )

    # The specific service receipt (service.receipt) this line is referring to.
    service_receipt_id = fields.Many2one(
        'service.receipt',
        string='Transfer',
        help="Service receipt being validated. This field links the confirmation line to the actual receipt."
    )

    # Whether to create a backorder for this receipt.
    to_backorder = fields.Boolean(
        string='To Backorder',
        help="Enable this option to create a backorder for the unprocessed service lines in this receipt."
    )

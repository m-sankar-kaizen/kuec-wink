# -*- coding: utf-8 -*-
from odoo import api, fields, models, Command
from odoo.tools.float_utils import float_compare


class ServiceBackorderConfirmation(models.TransientModel):
    """
    Transient model used as a confirmation wizard for handling service receipt backorders.

    This wizard allows users to either:
    1. Create a backorder for service receipt lines with remaining quantities.
    2. Cancel the backorder and log a message when received quantities are less than expected.

    Fields:
        - receipt_ids (Many2many): Linked service receipts being confirmed.
        - show_transfers (Boolean): Controls visibility of transfer info (used in the UI wizard).
        - backorder_confirmation_line_ids (One2many): Lines representing each service receipt
          involved in this backorder confirmation, with a flag indicating if it should be backordered.
    """
    _name = 'service.backorder.confirmation'
    _description = 'Backorder Confirmation'

    # List of service receipts involved in this backorder confirmation wizard
    receipt_ids = fields.Many2many(
        'service.receipt',
        'service_receipt_backorder_rel',
        string="Service Receipts"
    )

    # Boolean flag to show/hide transfer section in the wizard UI
    show_transfers = fields.Boolean()

    # One2many line items referencing each receipt in the wizard
    backorder_confirmation_line_ids = fields.One2many(
        'service.backorder.confirmation.line',
        'service_backorder_confirmation_id',
        string="Backorder Confirmation Lines"
    )

    @api.model
    def default_get(self, fields):
        """
        Overrides the default_get method to prepopulate the wizard with backorder lines.

        If `receipt_ids` are provided in the context, the method auto-fills the
        `backorder_confirmation_line_ids` with `to_backorder=True` for each receipt.

        Args:
            fields (list): List of field names to fetch.

        Returns:
            dict: A dictionary of default values for the wizard.
        """
        res = super().default_get(fields)
        if 'backorder_confirmation_line_ids' in fields and res.get(
                'receipt_ids'):
            # Auto-create backorder lines from selected receipts
            res['backorder_confirmation_line_ids'] = [
                Command.create({
                    'to_backorder': True,
                    'service_receipt_id': receipt_id
                })
                for receipt_id in res['receipt_ids'][0][2]
            ]
        return res

    def service_process(self):
        """
        Handles the main backorder logic for service receipts.

        Separates receipts into two categories:
        - `service_to_do`: Receipts that require a backorder.
        - `service_not_to_do`: Receipts where no backorder is required.

        If a receipt is not to be backordered but has unfulfilled demand,
        a log entry is created for traceability.

        Finally, validates the relevant service receipts, skipping backorder creation
        where instructed.

        Returns:
            bool or result of `service_button_validate()` if validation is triggered.
        """
        service_to_do = self.env[
            'service.receipt']  # Receipts requiring backorder
        service_not_to_do = self.env[
            'service.receipt']  # Receipts skipped for backorder

        # Split receipts based on user choice
        for line in self.backorder_confirmation_line_ids:
            if line.to_backorder:
                service_to_do |= line.service_receipt_id
            else:
                service_not_to_do |= line.service_receipt_id

        # Log short deliveries (less quantity received than demanded)
        for pick_id in service_not_to_do:
            moves_to_log = {}
            for move in pick_id.service_receipt_line_ids:
                # Compare demand vs. received quantity with rounding
                if float_compare(move.product_uom_qty, move.quantity_done,
                                 precision_rounding=move.product_uom_id.rounding) > 0:
                    moves_to_log[move] = (
                    move.quantity_done, move.product_uom_qty)
            # Log differences to chatter
            pick_id._log_less_quantities_than_expected(moves_to_log)

        # Validate the receipts based on context (e.g., wizard launched via button)
        service_to_validate = self.env.context.get(
            'button_validate_service_ids')
        if service_to_validate:
            # Skip backorder and exclude specified pickings if needed
            pickings_to_validate = self.env['service.receipt'].browse(
                service_to_validate).with_context(skip_backorder=True)
            if service_not_to_do:
                pickings_to_validate = pickings_to_validate.with_context(
                    picking_ids_not_to_backorder=service_not_to_do.ids)
            return pickings_to_validate.service_button_validate()

        return True

    def service_cancel_backorder(self):
        """
        Shortcut to cancel the backorder entirely.

        This method ensures no backorder is created even if some quantities were not received.
        It skips backorder logic and proceeds with immediate validation.

        Context:
            - `button_validate_service_ids`: list of service receipt IDs to validate.

        Returns:
            bool or result of `service_button_validate()` if triggered.
        """
        service_to_validate = self.env.context.get(
            'button_validate_service_ids')
        if service_to_validate:
            return self.env['service.receipt'] \
                .browse(service_to_validate) \
                .with_context(
                skip_backorder=True,
                picking_ids_not_to_backorder=service_to_validate
            ).service_button_validate()
        return True

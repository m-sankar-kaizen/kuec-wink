# -*- coding: utf-8 -*-
from odoo import models
from odoo.tools.float_utils import float_compare, float_is_zero


class PurchaseOrderLine(models.Model):
    """
    Inherits the `purchase.order.line` model to customize the behavior of
    service product processing during receipt operations.

    This extension provides logic for preparing service move lines to be recorded
    in `service.receipt.line`, including how quantities are allocated, pushed, or linked.
    """
    _inherit = 'purchase.order.line'

    def _prepare_service_moves(self, picking):
        """
        Prepare the service move values (dicts) based on this order line
        to be inserted into `service.receipt.line`.

        Logic:
        - Ensures the line is a service product.
        - Calculates the quantity to attach to existing service lines vs. quantity to push as new.
        - Generates move dicts based on adjusted quantities and UOM.
        - Marks extra move lines without destination links.

        Args:
            picking (recordset): The `service.receipt` record representing the destination.

        Returns:
            list of dict: A list of values ready for creating `service.receipt.line` records.
        """
        self.ensure_one()
        res = []

        # Only proceed for service-type products
        if self.product_id.type not in ['service']:
            return res

        qty = self._get_service_qty_procurement()  # Confirmed demand

        service_dests = self  # Default to current line

        if not service_dests:
            # No existing destination — prepare as fresh move
            self.service_ids.filtered(lambda m: m.state != 'cancel')
            qty_to_attach = 0
            qty_to_push = self.product_qty - qty
        else:
            # Calculate how much is already committed in destination moves
            service_dests_initial_demand = self.product_id.uom_id._compute_quantity(
                sum(service_dests.filtered(lambda m: m.state != 'cancel').mapped('product_qty')),
                self.product_uom, rounding_method='HALF-UP'
            )
            qty_to_attach = service_dests_initial_demand - qty
            qty_to_push = self.product_qty - service_dests_initial_demand

        # Create move for quantity to attach (linked to destination)
        if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(
                qty_to_attach, self.product_id.uom_id
            )
            res.append(self._prepare_service_move_vals(
                picking, product_uom, product_uom_qty, self.price_unit
            ))

        # Create move for quantity to push (unlinked new line)
        if not float_is_zero(qty_to_push, precision_rounding=self.product_uom.rounding):
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(
                qty_to_push, self.product_id.uom_id
            )
            extra_move_vals = self._prepare_service_move_vals(
                picking, product_uom, product_uom_qty, self.price_unit
            )
            extra_move_vals['move_dest_ids'] = False
            res.append(extra_move_vals)

        return res

    def _prepare_service_move_vals(self, picking, product_uom, product_uom_qty, price_unit):
        """
        Generate a dictionary of values used to create a `service.receipt.line` record
        from a purchase order line.

        Args:
            picking (recordset): The service receipt record.
            product_uom (recordset): The UoM to use for the line.
            product_uom_qty (float): Quantity in the adjusted UoM.
            price_unit (float): Price per unit for the service.

        Returns:
            dict: Field values to use in `service.receipt.line.create()`.
        """
        self.ensure_one()
        date_planned = self.date_planned or self.order_id.date_planned

        return {
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'service_receipt_id': picking.id,
            'partner_id': self.order_id.partner_id.id,
            'state': 'assigned',
            'order_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'product_uom_qty': product_uom_qty,
            'product_uom_id': product_uom.id,
            'sequence': self.sequence,
            'quantity_done': product_uom_qty,
            'price_unit': price_unit
        }

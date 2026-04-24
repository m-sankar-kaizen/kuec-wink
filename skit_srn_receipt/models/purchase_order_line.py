# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


# Inherit purchase.order.line model
class PurchaseOrderLine(models.Model):
    """
        Inherits the `purchase.order.line` model to manage service-type product handling
        using `service.receipt.line` instead of regular stock move lines.

        Key Functionalities:
        --------------------
        - Tracks links to related `service.receipt.line` records.
        - Switches quantity tracking logic (`qty_received_method`) to use service receipts.
        - Ensures proper creation and synchronization of service receipt lines on line creation, update, or PO confirmation.
        - Computes quantity received based on the associated `service.receipt.line` records.
        - Handles adjustment of delivery lines when PO line values are changed.

        Fields:
        -------
        - qty_received_method: Uses 'service_line' for service-type products.
        - service_ids: One2many relationship to `service.receipt.line` for this order line.
        """
    _inherit = 'purchase.order.line'

    # Added fields in purchase.order.line model
    qty_received_method = fields.Selection(selection_add=[('service_line',
                                                           'Service Receipt Line')])
    service_ids = fields.One2many('service.receipt.line', 'order_line_id',
                                  string='Reservations', readonly=True,
                                  copy=False)

    def _compute_qty_received_method(self):
        """
        Compute method to set `qty_received_method` for this line.

        If the product type is 'service', use 'service_line' as the method to calculate
        quantity received instead of default stock move-based computation.
        """
        super()._compute_qty_received_method()
        for line in self:
            if line.product_id and line.product_id.type == 'service':
                line.qty_received_method = 'service_line'

    @api.depends('service_ids.order_line_id',
                 'service_ids.state', 'service_ids.product_uom_qty',
                 'service_ids.product_uom_id')
    def _compute_qty_received(self):
        """
        Computes the `qty_received` field using the `service.receipt.line` records
        for lines that are marked with `qty_received_method = 'service_line'`.

        Ignores lines that still use stock moves (non-service products).
        """
        from_service_lines = self.filtered(
            lambda order_line: order_line.qty_received_method == 'service_line')
        super(PurchaseOrderLine, self - from_service_lines)._compute_qty_received()
        for line in self:
            if line.qty_received_method == 'service_line':
                total = 0.0
                for service in line._get_po_line_service_line():
                    if service.state == 'done':
                        total += service.product_uom_id._compute_quantity(service.quantity_done,
                                                                          line.product_uom,
                                                                          rounding_method='HALF-UP')
                line.qty_received = total

    def _get_po_line_service_line(self):
        """
        Filters `service.receipt.line` records linked to this PO line that match the product.

        Applies an optional `accrual_entry_date` context key to filter by service date.

        Returns:
            recordset: Filtered `service.receipt.line` records.
        """
        self.ensure_one()
        service = self.service_ids.filtered(lambda m: m.product_id == self.product_id)
        if self._context.get('accrual_entry_date'):
            service = service.filtered(
                lambda r: fields.Date.context_today(r, r.date) <= self._context[
                    'accrual_entry_date'])
        return service

    def _create_service_moves(self, picking):
        """
        Creates `service.receipt.line` records for this PO line linked to the specified `service.receipt`.

        Args:
            picking (recordset): The `service.receipt` record to attach the lines to.

        Returns:
            recordset: Created `service.receipt.line` records.
        """
        values = []
        for line in self.filtered(lambda l: not l.display_type):
            for val in line._prepare_service_moves(picking):
                values.append(val)
            line.move_dest_ids.created_purchase_line_ids = [Command.clear()]
        return self.env['service.receipt.line'].create(values)

    def _prepare_service_moves(self, picking):
        """
        Prepares dictionary values for creating new `service.receipt.line` records
        based on the order line data and receipt logic.

        Splits into:
        - Quantity that should be attached to existing service receipts.
        - Quantity that should be pushed (new move lines without destination).

        Returns:
            list[dict]: List of value dictionaries for service receipt lines.
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['service']:
            return res
        qty = self._get_service_qty_procurement()
        service_dests = self
        if not service_dests:
            service_dests = self.service_ids.filtered(lambda m: m.state != 'cancel')
            qty_to_attach = 0
            qty_to_push = self.product_qty - qty
        else:
            service_dests_initial_demand = self.product_id.uom_id._compute_quantity(
                sum(service_dests.filtered(lambda m: m.state != 'cancel').mapped('product_qty')),
                self.product_uom, rounding_method='HALF-UP')
            qty_to_attach = service_dests_initial_demand - qty
            qty_to_push = self.product_qty - service_dests_initial_demand

        if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_attach,
                                                                                   self.product_id.uom_id)
            res.append(self._prepare_service_move_vals(picking, product_uom, product_uom_qty))
        if not float_is_zero(qty_to_push, precision_rounding=self.product_uom.rounding):
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_push,
                                                                                   self.product_id.uom_id)
            extra_move_vals = self._prepare_service_move_vals(picking, product_uom, product_uom_qty)
            extra_move_vals['move_dest_ids'] = False
            res.append(extra_move_vals)
        return res

    def _prepare_service_move_vals(self, picking, product_uom, product_uom_qty):
        """
        Constructs a value dictionary used to create a `service.receipt.line`
        based on a service product line.

        Args:
            picking (recordset): Related `service.receipt`.
            product_uom (recordset): UOM object to use.
            product_uom_qty (float): Quantity in that UOM.

        Returns:
            dict: Dictionary of field values.
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
            'quantity_done': product_uom_qty
        }

    @api.model_create_multi
    def create(self, vals_list):
        """
                Overrides the `create` method to ensure that when a new line is added
                to a confirmed purchase order, the related service receipt is updated accordingly.

                Args:
                    vals_list (list[dict]): List of values for the new lines.

                Returns:
                    recordset: Created `purchase.order.line` records.
                """
        lines = super().create(vals_list)
        lines.filtered(lambda l: l.order_id.state == 'purchase')._create_or_update_service_picking()
        return lines

    def _create_or_update_service_picking(self):
        """
        Ensures a service receipt exists for the order line and updates it
        with new or modified service quantities.

        Also handles edge cases:
        - Prevents reduction of ordered quantity below already received.
        - Triggers warnings if more invoiced than ordered.
        """
        for line in self:
            if line.product_id and line.product_id.type == 'service':
                if float_compare(line.product_qty, line.qty_received,
                                 line.product_uom.rounding) < 0:
                    raise UserError(
                        _('You cannot decrease the ordered quantity below the received quantity.\n'
                          'Create a return first.'))

                if float_compare(line.product_qty, line.qty_invoiced,
                                 line.product_uom.rounding) == -1:
                    line.invoice_lines[0].move_id.activity_schedule(
                        'mail.mail_activity_data_warning',
                        note=_(
                            'The quantities on your purchase order indicate less than billed. You should ask for a refund.'))
                pickings = line.order_id.service_receipt_ids.filtered(
                    lambda x: x.state not in ('done', 'cancel'))
                picking = pickings and pickings[0] or False
                if picking and picking.state == 'assigned':
                    existing_receipt_line = picking.service_receipt_line_ids.filtered(
                        lambda r: r.product_id == line.product_id)
                    if existing_receipt_line:
                        existing_receipt_line.write({'product_uom_qty': line.product_qty})
                if not picking:
                    res = line.order_id._service_prepare_picking()
                    picking = self.env['service.receipt'].create(res)
                line._create_service_moves(picking)

    def write(self, values):
        """
        Override write method to manage:
        - Syncing service receipt lines when product quantity changes.
        - Updating deadline dates in related service lines.
        - Preventing changes that violate integrity (e.g., decrease below received qty).

        Args:
            values (dict): Values to be written.

        Returns:
            bool: Result of superclass method.
        """
        if values.get('date_planned'):
            new_date = fields.Datetime.to_datetime(values['date_planned'])
            self.filtered(lambda l: not l.display_type)._update_move_date_deadline(new_date)
        lines = self.filtered(lambda l: l.order_id.state == 'purchase')
        if 'product_packaging_id' in values:
            self.move_ids.filtered(
                lambda m: m.state not in ['cancel', 'done']
            ).product_packaging_id = values['product_packaging_id']
        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        previous_product_qty = {line.id: line.product_qty for line in lines}
        result = super(PurchaseOrderLine, self).write(values)
        if 'product_qty' in values:
            lines = lines.filtered(
                lambda l: float_compare(previous_product_qty[l.id], l.product_qty,
                                        precision_rounding=l.product_uom.rounding) != 0)
            lines.with_context(
                previous_product_qty=previous_product_uom_qty)._create_or_update_service_picking()
        return result

    def _get_service_qty_procurement(self):
        """
        Computes how much of the PO line's quantity has been received
        via `service.receipt.line`, adjusted for UOM.

        Returns:
            float: Received quantity in line's UOM.
        """
        self.ensure_one()
        qty = 0.0
        incoming_moves = self._get_incoming_moves()
        for move in incoming_moves:
            qty += move.product_uom_id._compute_quantity(move.product_uom_qty, self.product_uom,
                                                         rounding_method='HALF-UP')
        return qty

    def _get_incoming_moves(self):
        """
        Returns non-cancelled `service.receipt.line` records for this line
        that match the product.

        Returns:
            recordset: Matching receipt lines.
        """
        incoming_moves = self.service_ids.filtered(
            lambda r: r.state != 'cancel' and self.product_id == r.product_id)
        return incoming_moves

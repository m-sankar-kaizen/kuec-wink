# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, Command


# Inherit purchase order model
class PurchaseOrder(models.Model):
    """
        Inherits the core `purchase.order` model to integrate the handling of service-type products
        through a dedicated `service.receipt` mechanism.

        Key Functionalities:
        --------------------
        - Tracks whether the PO contains service-type products using a `service_product` boolean.
        - Automatically creates a `service.receipt` record when a PO containing service items is confirmed.
        - Provides a computed Many2many link to all related `service.receipt` records.
        - Adds a computed count of related service receipts for quick UI access.
        - Provides a smart button action to open and view service receipts associated with a PO.
        - Overrides PO confirmation and line creation logic to manage service delivery separately.

        Fields:
        -------
        - service_product: Boolean flag to indicate if PO includes service items.
        - service_receipt_ids: Many2many linking to `service.receipt` records.
        - incoming_service_count: Integer count of related service receipts.
        """
    _inherit = "purchase.order"

    # Added fields in purchase order model
    service_product = fields.Boolean("SRN")
    service_receipt_ids = fields.Many2many("service.receipt",
                                           string="Service Receipt",
                                           compute='_compute_service_receipt_ids',
                                           copy=False, store=True)
    incoming_service_count = fields.Integer("Incoming Service count",
                                            compute='_compute_incoming_service_count')

    @api.depends('order_line.service_ids.service_receipt_id')
    def _compute_service_receipt_ids(self):
        """
        Compute method for `service_receipt_ids`.

        Aggregates all `service.receipt` records linked through PO lines (via `service_ids`)
        and assigns them to the PO's `service_receipt_ids` field.
        """

        for order in self:
            order.service_receipt_ids = order.order_line.service_ids.service_receipt_id

    def action_view_product(self):
        """
        Open related `service.receipt` records in a view.

        If multiple receipts are found, opens a list (tree) view.
        If a single receipt is found, opens the form view of that record.

        Returns:
            dict: Action dictionary to trigger the appropriate view in the UI.
        """
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id(
            'skit_srn_receipt.action_service_receipt_all')
        res = self.env.ref('skit_srn_receipt.service_receipt_view_form', False)
        service_receipt = self.service_receipt_ids
        if not service_receipt or len(service_receipt) > 1:
            result['domain'] = [('id', 'in', service_receipt.ids)]
        elif len(service_receipt) == 1:
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [(state, view) for state, view in result.get('views', []) if view != 'form']
            result['res_id'] = service_receipt.id
        return result

    def button_confirm(self):
        """
        Override of the standard purchase order confirmation logic.

        In addition to the default behavior:
        - Identifies lines containing service products.
        - Sets the `service_product` boolean flag.
        - Triggers `_create_service_picking()` to create a `service.receipt` for these lines.

        Returns:
            bool: Result of the superclass method.
        """
        res = super().button_confirm()
        for line in self.order_line:
            service_product_lines = line.filtered(lambda order_line: order_line.product_id.type == 'service')
            line.order_id.service_product = bool(service_product_lines)
            if service_product_lines:
                self._create_service_picking()
        return res

    def _create_service_picking(self):
        """
        Internal method to create a new `service.receipt` record for eligible service-type
        lines in the purchase order. Ensures only one active (not done or cancelled) receipt is created.

        The resulting receipt is stored in the PO's `service_receipt_ids` field.
        """
        ServiceReceipt = self.env['service.receipt']
        for order in self.filtered(lambda po: po.state in ('purchase', 'done')):
            if any(product.type in ['service'] for product in order.order_line.product_id):
                order = order.with_company(order.company_id)
                pickings = order.service_receipt_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                if not pickings:
                    res = order._service_prepare_picking()
                    picking = ServiceReceipt.with_user(SUPERUSER_ID).create(res)
                    pickings = picking
                    self.service_receipt_ids = [Command.link(picking.id)]
                else:
                    picking = pickings[0]
                service = order.order_line._create_service_moves(picking)
                service = service.filtered(lambda x: x.state not in ('done', 'cancel'))
        return True

    def _service_prepare_picking(self):
        """
                Prepares the default dictionary values to initialize a new `service.receipt` record
                based on purchase order header data.

                Ensures that the procurement group is assigned (or created).

                Returns:
                    dict: Dictionary of values for creating `service.receipt`.
                """
        if not self.group_id:
            self.group_id = self.group_id.create({
                'name': self.name,
                'partner_id': self.partner_id.id})
        return {
            'partner_id': self.partner_id.id,
            'po_order_id': self.id,
            'user_id': False,
            'date': self.date_order,
            'origin': self.name,
            'company_id': self.company_id.id,
            'state': 'assigned',
        }

    @api.depends('service_receipt_ids')
    def _compute_incoming_service_count(self):
        """
        Compute method for the `incoming_service_count` field.

        Sets the number of associated `service.receipt` records (excluding done/cancelled).
        """
        for order in self:
            order.incoming_service_count = len(order.service_receipt_ids)

    def get_billed_amount(self):
        """
                Compute the total amount billed on the purchase order based on the invoiced quantity
                relative to the ordered quantity, line by line.

                Returns:
                    float: Total computed billed amount across all PO lines.
                """
        billed_amount = 0
        for line in self.order_line:
            if line.product_uom_qty != 0:
                billed_amount += (line.qty_invoiced / line.product_uom_qty) * line.price_total
        return billed_amount



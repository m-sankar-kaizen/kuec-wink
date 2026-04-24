# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.tools.misc import OrderedSet

PROCUREMENT_PRIORITIES = [('0', 'Normal'), ('1', 'Urgent')]


class ServiceReceiptLine(models.Model):
    """
    Model: service.receipt.line

    This model is used to track
    individual service receipt lines corresponding to
    service-type products in a
    purchase workflow. It supports detailed status tracking,
    scheduling, product quantity management,
     and service backorder logic for split deliveries.

    Key Features:
    - Linked to purchase order lines and service receipts.
    - Tracks quantities demanded, done, and splits for backorders.
    - Supports scheduling, locking, priority, and delivery address.
    - Designed to mimic stock move behavior for services.
    """
    _name = "service.receipt.line"
    _description = 'Service Receipt Line'

    # === Field Definitions ===

    service_receipt_id = fields.Many2one("service.receipt",
                                         string="Service Receipt")
    order_line_id = fields.Many2one(
        'purchase.order.line', 'Purchase Order Line',
        ondelete='set null', index='btree_not_null', readonly=True)
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id')
    group_id = fields.Many2one('procurement.group', 'Procurement Group',
                               index=True)
    additional = fields.Boolean(
        "Whether the move was added after the picking's confirmation",
        default=False)
    state = fields.Selection([
        ('draft', 'New'), ('cancel', 'Cancelled'),
        ('waiting', 'Waiting Another Move'),
        ('confirmed', 'Waiting Availability'),
        ('partially_available', 'Partially Available'),
        ('assigned', 'Available'),
        ('done', 'Done')], string='Status',
        copy=False, default='draft', index=True, readonly=True,
        help="Indicates the current workflow state of the service receipt line.")
    description = fields.Char(string='Description', related='product_id.name')
    product_uom_id = fields.Many2one(
        'uom.uom', "UoM", required=True,
        domain="[('category_id', '=', product_uom_category_id)]",
        compute="_compute_product_uom", store=True, readonly=False,
        precompute=True)
    date_deadline = fields.Datetime(string="Date Deadline", readonly=True,
                                    copy=False)
    is_locked = fields.Boolean(default=True)
    service_lines_count = fields.Integer(compute='_compute_service_lines_count')
    sequence = fields.Integer('Sequence', default=10)
    priority = fields.Selection(PROCUREMENT_PRIORITIES, 'Priority', default='0',
                                store=True)
    date = fields.Datetime('Date Scheduled', default=fields.Datetime.now,
                           index=True, required=True)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env.company,
                                 index=True, required=True)
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True, required=True,
        domain="[('type', 'in', ['service'])]", index=True)
    product_qty = fields.Float(
        'Real Quantity', digits=0, store=True, compute_sudo=True,
        compute='_compute_product_qty')
    backorder_id = fields.Many2one(
        'service.receipt', 'Back Order of',
        copy=False, index='btree_not_null', readonly=True,
        related='service_receipt_id.backorder_id',
        check_company=True)
    product_uom_qty = fields.Float(
        'Demand', digits='Product Unit of Measure', default=1.0, required=True)
    quantity_done = fields.Float('Quantity', digits='Product Unit of Measure',
                                 store=True)
    partner_id = fields.Many2one(
        'res.partner', 'Destination Address')
    origin = fields.Char(string='Source Document')
    service_dest_ids = fields.Many2many(
        'service.receipt.line', 'service_receipt_line_rel', 'service_orig_id',
        'service_dest_id', 'Destination Moves',
        copy=False)
    service_picked = fields.Boolean(
        'Service Picked', compute='_compute_service_picked',
        inverse='_inverse_service_picked', recursive=True,
        store=True, readonly=False, copy=False, default=False)

    # === Compute & Inverse Methods ===

    @api.depends('service_dest_ids.service_picked', 'state')
    def _compute_service_picked(self):
        """
        Compute field that marks the service as picked if it is done or any of its
        destination moves are picked.
        """
        for service in self:
            if service.state == 'done' or any(
                    ml.picked for ml in service.service_dest_ids):
                service.service_picked = True

    def _inverse_service_picked(self):
        """
        Inverse method to update service_picked field on related destination lines.
        """
        for service in self:
            service.service_dest_ids.service_picked = service.service_picked

    @api.depends('product_id')
    def _compute_product_uom(self):
        """
        Compute method to set the product_uom_id field based on the product's default UoM.
        """
        for line in self:
            line.product_uom_id = line.product_id.uom_id.id

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_product_qty(self):
        """
        Compute the product quantity in the default UoM of the product.
        """
        for service in self:
            service.product_qty = service.product_uom_id._compute_quantity(
                service.product_uom_qty, service.product_id.uom_id,
                rounding_method='HALF-UP')

    @api.depends('service_receipt_id')
    def _compute_service_lines_count(self):
        """
        Compute the number of lines in the parent service receipt.
        """
        for lines in self:
            lines.service_lines_count = len(lines.service_receipt_id)

    # === Business Logic Methods ===

    def service_action_done(self, cancel_backorder=False):
        """
        Finalize the service move. If quantity_done < product_uom_qty,
        create backorder entries. If quantity_done > product_uom_qty, raise error.

        :param cancel_backorder: If True, skips backorder creation.
        :return: recordset of processed lines.
        """
        service = self.exists().filtered(
            lambda x: x.state not in ('done', 'cancel'))
        service_ids_todo = OrderedSet()
        for services in service:
            if services.state == 'cancel' or (services.quantity_done <= 0):
                continue
            service_ids_todo |= services._service_create_extra_move().ids

        service_todo = self.browse(service_ids_todo)
        service_todo._check_company()

        backorder_moves_vals = []

        for move in service_todo:
            rounding = self.env['decimal.precision'].precision_get(
                'Product Unit of Measure')
            if not cancel_backorder and float_compare(move.quantity_done, move.product_uom_qty,
                                                      precision_digits=rounding) < 0:
                qty_split = move.product_uom_id._compute_quantity(
                    move.product_uom_qty - move.quantity_done,
                    move.product_id.uom_id,
                    rounding_method='HALF-UP')
                new_move_vals = move._split(qty_split)
                backorder_moves_vals += new_move_vals

        backorder_moves = self.env['service.receipt.line'].create(
            backorder_moves_vals)
        backorder_moves.with_context(moves_todo=service_todo)
        picking = service_todo.mapped('service_receipt_id')

        service_todo.write({'state': 'done', 'date': fields.Datetime.now()})

        if self.env.context.get('is_scrap'):
            return service_todo

        if picking and not cancel_backorder:
            picking._create_service_backorder()

        return service_todo

    def _service_create_extra_move(self):
        """
        Prevents the creation of an extra move if
         quantity_done exceeds planned.
        Enforces integrity by restricting over-processing.

        :return: self (no new move created).
        :raises: UserError if quantity_done > product_uom_qty.
        """
        extra_move = self
        rounding = self.product_uom_id.rounding
        if float_compare(self.quantity_done, self.product_uom_qty,
                         precision_rounding=rounding) > 0:
            raise UserError(
                _('The done quantity must be the'
                  ' same or less than the demand quantity.'))
        return extra_move | self

    def _split(self, qty, restrict_partner_id=False):
        """
        Split a move into a backorder if partial quantity is processed.

        :param qty: float, Quantity to split (in product UoM)
        :param restrict_partner_id: Optional, restricts new move to specific partner.
        :return: list of move value dicts for creating new service.receipt.line
        """
        self.ensure_one()
        if float_is_zero(qty,
                         precision_rounding=self.product_id.uom_id.rounding) or self.product_qty <= qty:
            return []

        decimal_precision = self.env['decimal.precision'].precision_get(
            'Product Unit of Measure')
        uom_qty = self.product_id.uom_id._compute_quantity(qty,
                                                           self.product_uom_id,
                                                           rounding_method='HALF-UP')

        if float_compare(
                qty,
                self.product_uom_id._compute_quantity(uom_qty,
                                                      self.product_id.uom_id,
                                                      rounding_method='HALF-UP'),
                precision_digits=decimal_precision
        ) == 0:
            defaults = self._prepare_move_split_vals(uom_qty)
        else:
            defaults = self.with_context(
                force_split_uom_id=self.product_id.uom_id.id)._prepare_move_split_vals(
                qty)

        if restrict_partner_id:
            defaults['restrict_partner_id'] = restrict_partner_id

        if self.env.context.get('source_location_id'):
            defaults['location_id'] = self.env.context['source_location_id']

        new_move_vals = self.copy_data(defaults)

        new_product_qty = self.product_id.uom_id._compute_quantity(
            self.product_qty - qty, self.product_uom_id, round=False)
        new_product_qty = float_round(new_product_qty,
                                      precision_digits=decimal_precision)

        self.with_context(do_not_unreserve=True).write(
            {'product_uom_qty': new_product_qty})
        return new_move_vals

    def _prepare_move_split_vals(self, uom_qty):
        """
        Prepare values for a split move.

        :param uom_qty: float, Quantity to assign to new move.
        :return: dict of field values for the new move.
        """
        self['order_line_id'] = self.order_line_id.id
        return self._prepare_service_split_vals(uom_qty)

    def _prepare_service_split_vals(self, uom_qty):
        """
        Generic method to prepare split values, used by `_split`.

        :param uom_qty: float, Quantity for the new line.
        :return: dict of values for creating new service receipt line.
        """
        vals = {
            'product_uom_qty': uom_qty,
            'date_deadline': self.date_deadline,
            'quantity_done': uom_qty
        }
        if self.env.context.get('force_split_uom_id'):
            vals['product_uom_id'] = self.env.context['force_split_uom_id']
        return vals

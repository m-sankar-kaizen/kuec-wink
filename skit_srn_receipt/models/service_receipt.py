# -*- coding: utf-8 -*-
from datetime import datetime

from odoo import api, models, fields, _, Command
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare


# Create service.receipt model
class ServiceReceipt(models.Model):
    """
        This model manages service receipt operations for service-type products ordered via purchase orders.
    It functions similarly to stock pickings but is specialized for non-inventory tracked service products.

    Features:
    ---------
    - Tracks end-user and department-level signatures to validate service completion.
    - Manages workflow states: draft, waiting, confirmed, assigned, done, and cancelled.
    - Supports backorder management similar to stock transfers.
    - Includes custom UI logic for smart buttons, wizard interactions, and validation.
    - Integrates tightly with the `purchase.order` and `service.receipt.line` models.

    Inherits:
    ---------
    - mail.thread: Enables chatter logging.
    - mail.activity.mixin: Enables scheduling and tracking activities.

    Key Fields:
    -----------
    - name: Auto-generated reference number.
    - partner_id: Contact associated with the service.
    - po_order_id: Purchase order reference.
    - service_receipt_line_ids: Service receipt lines associated.
    - end_user_signature, procurement_department_signature, department_head_signature: Signature images.
    - state: Workflow state of the receipt.
    - is_backorder, backorder_id, backorder_ids: Backorder linkage.
    """
    _name = "service.receipt"
    _description = 'service receipt'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _compute_user_display_name(self):
        """
                Compute the current user's display name and store in `current_display_name` field.
                Useful for showing who is signing as the current user.
                """
        for record in self:
            record.current_display_name = self.env.user.display_name

    current_display_name = fields.Char(
        string="End User Signature Name",
        compute=_compute_user_display_name)

    # Added fields in service_receipt model
    name = fields.Char('Reference', copy=False, readonly=True)
    partner_id = fields.Many2one(
        'res.partner', 'Contact',
        check_company=True)
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    origin = fields.Char(
        string='Source Document', index='trigram',
        help="Reference of the document")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft',
        copy=False, index=True, readonly=True, store=True, tracking=True,
        help=" * Draft: The transfer is not confirmed yet. Reservation doesn't apply.\n"
             " * Waiting another operation: This transfer is waiting for another operation before being ready.\n"
             " * Waiting: The transfer is waiting for the availability of some products.\n(a) The shipping policy is \"As soon as possible\": no product could be reserved.\n(b) The shipping policy is \"When all products are ready\": not all the products could be reserved.\n"
             " * Ready: The transfer is ready to be processed.\n(a) The shipping policy is \"As soon as possible\": at least one product has been reserved.\n(b) The shipping policy is \"When all products are ready\": all product have been reserved.\n"
             " * Done: The transfer has been processed.\n"
             " * Cancelled: The transfer has been cancelled.")
    priority = fields.Selection(
        [('0', 'Normal'), ('1', 'Urgent')], string='Priority', default='0',
        help="Products will be reserved first for the transfers with the highest priorities.")
    scheduled_date = fields.Datetime(
        'Scheduled Date', index=True, default=fields.Datetime.now,
        tracking=True,
        help="Scheduled time for the first part of the shipment to be processed. Setting manually a value here would set it as expected date for all the stock moves.")
    date_deadline = fields.Datetime(
        "Deadline", default=fields.Datetime.now, store=True, readonly=True,
        help="Date Promise to the customer on the top level document (SO/PO)")
    product_id = fields.Many2one(
        'product.product', 'Product',
        check_company=True)
    product_type = fields.Selection(related='product_id.type', readonly=True)
    product_uom_qty = fields.Float(
        'Demand',
        digits='Product Unit of Measure',
        default=1.0, required=True, readonly=True,
        help="This is the quantity of products from an inventory "
             "point of view. For moves in the state 'done', this is the "
             "quantity of products that were actually moved. For other "
             "moves, this is the quantity of product that is planned to "
             "be moved. Lowering this quantity does not generate a "
             "backorder. Changing this quantity on assigned moves affects "
             "the product reservation, and should be done with care.")
    quantity_done = fields.Float(
        'Quantity', digits='Product Unit of Measure',
        store=True)
    description_picking = fields.Text(string='Description of Picking')
    date = fields.Datetime(
        'Creation Date',
        default=fields.Datetime.now, tracking=True,
        help="Creation Date, usually the time of the order")
    additional = fields.Boolean("Whether the move was added after the picking's confirmation",
                                default=False)
    po_order_id = fields.Many2one('purchase.order')
    po_amount = fields.Float(compute='_compute_po_quantities')
    qty_billed = fields.Float(compute='_compute_po_quantities')
    service_receipt_line_ids = fields.One2many(
        'service.receipt.line', 'service_receipt_id',
        string="Service Receipt not in package", copy=True
    )
    immediate_transfer = fields.Boolean(default=False)
    is_locked = fields.Boolean(default=True)
    user_id = fields.Many2one(
        'res.users', 'Responsible', tracking=True,
        default=lambda self: self.env.user)
    backorder_id = fields.Many2one(
        'service.receipt', 'Back Order of',
        copy=False, index='btree_not_null', readonly=True,
        check_company=True,
        help="If this shipment was split, then this field links to the shipment which contains the already processed part.")
    backorder_ids = fields.One2many('service.receipt', 'backorder_id',
                                    'Back Orders')
    create_backorder = fields.Selection(
        [('ask', 'Ask'), ('always', 'Always'), ('never', 'Never')],
        'Create Backorder', required=True, default='ask',
        help="When validating a transfer:\n"
             " * Ask: users are asked to choose if they want to make a backorder for remaining products\n"
             " * Always: a backorder is automatically created for the remaining products\n"
             " * Never: remaining products are cancelled")
    owner_id = fields.Many2one(
        'res.partner', 'Assign Owner',
        check_company=True,
        help="When validating the transfer, the products will be assigned to this owner.")
    is_backorder = fields.Boolean("Is a Backorder", readonly=True)
    date_done = fields.Datetime('Date of Transfer', copy=False, readonly=True,
                                help="Date at which the transfer has been processed or cancelled.")

    end_user_signature = fields.Image(copy=False, attachment=True)
    end_user_id = fields.Many2one(comodel_name='res.users', string='End User')
    procurement_department_signature = fields.Image(copy=False, attachment=True)
    procurement_department_user_id = fields.Many2one(comodel_name='res.users',
                                                     string='Procurement Department')
    department_head_signature = fields.Image(copy=False, attachment=True)
    department_head_user_id = fields.Many2one(comodel_name='res.users', string='Head of Department')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create method to assign a sequence number to each new service receipt.

        Args:
            vals_list (list): List of dictionaries containing values for new records.

        Returns:
            recordset: Newly created service.receipt records
        """
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('service.receipt') or 'New'
        return super().create(vals_list)

    @api.onchange('end_user_signature')
    def change_end_user_signature(self):
        """
                Automatically assign the current user as the
                 `end_user_id` when the end user signature is added.
                """
        if self.end_user_signature:
            self.end_user_id = self.env.user.id

    @api.onchange('procurement_department_signature')
    def change_procurement_department_user_id(self):
        """
                Automatically assign the current user as
                 the procurement department user when
                 signature is provided.
                """
        if self.procurement_department_signature:
            self.procurement_department_user_id = self.env.user.id

    @api.onchange('department_head_signature')
    def change_department_head_user_id(self):
        """
                Automatically assign the current user
                 as the department head when signature is provided.
                """
        if self.department_head_signature:
            self.department_head_user_id = self.env.user.id

    @api.depends('po_order_id')
    def _compute_po_quantities(self):
        """
                Compute the total PO ordered quantity and total
                 billed quantity for this receipt.
                These help track service receipt coverage versus PO.
                """
        for service in self:
            service.po_amount = sum(service.po_order_id.order_line.mapped('product_qty')) or 0
            service.qty_billed = sum(service.po_order_id.order_line.mapped('qty_invoiced')) or 0

    def service_action_cancel(self):
        """
        Cancel the service receipt by
         setting state to 'cancel' and locking the document.
        """
        self.state = 'cancel'
        self.write({'is_locked': True})

    def service_action_mark_as_todo(self):
        """
        Set the state of the receipt to 'assigned' (ready to process) and
        populate any missing `quantity_done` with the planned demand.
        """
        for line in self.service_receipt_line_ids:
            if line.quantity_done == 0.0:
                line.quantity_done = line.product_uom_qty
        self.state = 'assigned'

    def check_signature(self):
        """
               Ensure all three required signatures (end user, procurement, and department head)
               are present before validation.

               Raises:
                   ValidationError: If any of the required signatures are missing.
               """
        end_user_signature = self.end_user_signature
        department_head_signature = self.department_head_signature
        procurement_department_signature = self.procurement_department_signature
        if not all(
                [end_user_signature, department_head_signature, procurement_department_signature]):
            raise ValidationError("Missing Signature")

    def service_button_validate(self):
        """
        Validate the receipt:
            - Ensures required signatures exist
            - Handles backorder conditions via pre-hooks
            - Sets date_done and transitions state to done

        Returns:
            True if validation passes or a wizard if backorder is required.
        """
        self.check_signature()
        self.date_done = datetime.today()
        for line in self.service_receipt_line_ids:
            if line.quantity_done == 0.0:
                line.quantity_done = line.product_uom_qty
        if not self.env.context.get('button_validate_service_ids'):
            self = self.with_context(button_validate_service_ids=self.ids)
        res = self._pre_service_action_done_hook()
        if res is not True:
            return res
        pickings_not_to_backorder = self.filtered(lambda p: p.create_backorder == 'never')
        if self.env.context.get('picking_ids_not_to_backorder'):
            pickings_not_to_backorder |= self.browse(
                self.env.context['picking_ids_not_to_backorder']).filtered(
                lambda p: p.create_backorder != 'always'
            )
        pickings_to_backorder = self - pickings_not_to_backorder
        pickings_not_to_backorder.with_context(cancel_backorder=True).service_action_done()
        pickings_to_backorder.with_context(cancel_backorder=False).service_action_done()
        return True

    def _pre_service_action_done_hook(self):
        """
        Pre-validation hook to determine if backorder wizard needs to be shown.

        Returns:
            True or an action to open backorder wizard.
        """
        if not self.env.context.get('skip_backorder'):
            service_to_backorder = self._check_backorder_service()
            if service_to_backorder:
                return service_to_backorder._action_service_generate_backorder_wizard(
                    show_transfers=self._should_show_service_transfers())
        return True

    def _should_show_service_transfers(self):
        """
        Determine whether to show individual transfers on the backorder wizard.

        Returns:
            bool: True if more than one receipt in the current batch.
        """
        return len(self) > 1

    def _set_quantities_to_service_reservation(self):
        """
        Force quantity_done to match planned
         quantity and update PO line received qty.
        """
        for receipt_line in self.service_receipt_line_ids:
            receipt_line.update({'quantity_done': receipt_line.product_uom_qty})
            receipt_line.order_line_id.update(
                {
                    'qty_received': receipt_line.order_line_id.qty_received + receipt_line.quantity_done})

    def _action_service_generate_backorder_wizard(self, show_transfers=False):
        """
        Launch the wizard to confirm creation of a service backorder.

        Args:
            show_transfers (bool): Whether to show individual receipts in the wizard.

        Returns:
            dict: Action definition for wizard window.
        """
        view = self.env.ref('skit_srn_receipt.service_view_backorder_confirmation')
        return {
            'name': _('Create Backorder?'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'service.backorder.confirmation',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': dict(self.env.context, default_show_transfers=show_transfers,
                            default_receipt_ids=[Command.link(p.id) for p in self]),
        }

    def _check_backorder_service(self):
        """
        Check if any receipt lines are partially completed and need to be backordered.

        Returns:
            recordset: service.receipt records that require backorder.
        """
        prec = self.env["decimal.precision"].precision_get("Product Unit of Measure")
        backorder_pickings = self.browse()
        for services in self:
            if services.create_backorder != 'ask':
                continue
            quantity_todo = {}
            quantity_done = {}
            for receipt in services.service_receipt_line_ids.filtered(
                    lambda m: m.state != "cancel"):
                quantity_todo.setdefault(receipt.product_id.id, 0)
                quantity_done.setdefault(receipt.product_id.id, 0)
                quantity_todo[receipt.product_id.id] += receipt.product_uom_id._compute_quantity(
                    receipt.product_uom_qty, receipt.product_id.uom_id, rounding_method='HALF-UP')
                quantity_done[receipt.product_id.id] += receipt.product_uom_id._compute_quantity(
                    receipt.quantity_done,
                    receipt.product_id.uom_id,
                    rounding_method='HALF-UP')
            if any(
                    float_compare(quantity_done[x], quantity_todo.get(x, 0),
                                  precision_digits=prec, ) == -1
                    for x in quantity_done
            ):
                backorder_pickings |= services
        return backorder_pickings

    def _create_service_backorder(self):
        """ This method is called when the user choose to create a backorder. It
        will create a new picking, the backorder, and move the
        service.receipt.line that are not `done` or `cancel` into it.
        """
        backorders = self.env['service.receipt']
        for picking in self:
            moves_to_backorder = picking.service_receipt_line_ids.filtered(
                lambda x: x.state not in ('done', 'cancel'))
            if moves_to_backorder:
                backorder_picking = picking.copy({
                    'service_receipt_line_ids': [],
                    'backorder_id': picking.id,
                    'state': 'assigned'
                })
                picking.message_post(
                    body=_('The backorder %s has been created.', backorder_picking._get_html_link())
                )
                moves_to_backorder.write({'service_receipt_id': backorder_picking.id})
                backorders |= backorder_picking
        return backorders

    def service_action_done(self):
        """Call `service_action_done` on the `service.receipt.line` of the
        `service.receipt` in `self` linking them to an existing one or a newly
        created one.

        If the context key `cancel_backorder` is present, backorders won't be
        created.

        :return: True
        :rtype: bool
        """
        todo_moves = self.service_receipt_line_ids.filtered(
            lambda self: self.state in ['draft', 'waiting', 'partially_available', 'assigned',
                                        'confirmed'])
        todo_moves.service_action_done(cancel_backorder=self.env.context.get('cancel_backorder'))
        self.write({'state': 'done', 'date_done': fields.Datetime.now(), 'priority': '0'})
        return True

    def service_completion_report(self):
        """
                Action to generate and download the Service Completion Report as a PDF.

                Returns:
                    dict: Report action to trigger download.
                """
        return self.env.ref(
            'skit_srn_receipt.service_completion_receipt_report_temp_report'
        ).report_action(
            self, config=False)

    def clear_signature(self):
        """
                Clear the signature field as specified by `field_name` in context.
                Used by UI buttons to remove digital signatures.
                """
        field_name = self.env.context.get('field_name')
        if field_name:
            setattr(self, field_name, False)

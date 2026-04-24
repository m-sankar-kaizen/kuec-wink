# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MaterialPurchaseRequisition(models.Model):
    """
        Model: material.purchase.requisition

        Represents a purchase requisition request in an organization.
        This model supports a multi-step approval process (Employee → Department Head → IR → Approval),
        as well as workflows for creating internal stock transfers and purchase orders depending on requisition lines.

        Key Features:
        - Tracks requisition details, source and destination locations.
        - Manages approval/rejection at multiple stages.
        - Automatically generates internal picking or purchase order depending on product lines.
        - Integrates with employee and department records.
        - Supports email notifications during workflow.
        - Tracks state transitions and records user/date metadata.
        """
    _name = 'material.purchase.requisition'
    _description = 'Purchase Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Number',
        index=True,
        readonly=True,
    )
    state = fields.Selection([
        ('draft', 'New'),
        ('dept_confirm', 'Waiting Department Approval'),
        ('ir_approve', 'Waiting IR Approval'),
        ('approve', 'Approved'),
        ('stock', 'Purchase Order Created'),
        ('receive', 'Received'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')],
        default='draft',
        tracking=True
    )
    request_date = fields.Date(
        string='Requisition Date',
        default=lambda self: fields.Date.context_today(self),
        required=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        required=False,
        copy=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid),
                                                             ('company_id', '=', self.env.company.id)],                                             limit=1),
        copy=True,
    )
    approve_manager_id = fields.Many2one(
        'hr.employee',
        string='Department Manager',
        readonly=True,
        copy=False,
    )
    reject_manager_id = fields.Many2one(
        'hr.employee',
        string='Department Manager Reject',
        readonly=True,
    )
    approve_employee_id = fields.Many2one(
        'hr.employee',
        string='Approved by',
        readonly=True,
        copy=False,
    )
    reject_employee_id = fields.Many2one(
        'hr.employee',
        string='Rejected by',
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        copy=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        copy=True,
    )
    requisition_line_ids = fields.One2many(
        'material.purchase.requisition.line',
        'requisition_id',
        string='Purchase Requisitions Line',
        copy=True,
    )
    date_end = fields.Date(
        string='Requisition Deadline',
        readonly=True,
        help='Last date for the product to be needed',
        copy=True,
    )
    date_done = fields.Date(
        string='Date Done',
        readonly=True,
        help='Date of Completion of Purchase Requisition',
    )
    managerapp_date = fields.Date(
        string='Department Approval Date',
        readonly=True,
        copy=False,
    )
    manareject_date = fields.Date(
        string='Department Manager Reject Date',
        readonly=True,
    )
    userreject_date = fields.Date(
        string='Rejected Date',
        readonly=True,
        copy=False,
    )
    userrapp_date = fields.Date(
        string='Approved Date',
        readonly=True,
        copy=False,
    )
    receive_date = fields.Date(
        string='Received Date',
        readonly=True,
        copy=False,
    )
    reason = fields.Text(
        string='Reason for Requisitions',
        required=False,
        copy=True,
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        copy=True,
    )
    dest_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=False,
        copy=True,
    )
    delivery_picking_id = fields.Many2one(
        'stock.picking',
        string='Internal Picking',
        readonly=True,
        copy=False,
    )
    requisiton_responsible_id = fields.Many2one(
        'hr.employee',
        string='Requisition Responsible',
        copy=True,
    )
    employee_confirm_id = fields.Many2one(
        'hr.employee',
        string='Confirmed by',
        readonly=True,
        copy=False,
    )
    confirm_date = fields.Date(
        string='Confirmed Date',
        readonly=True,
        copy=False,
    )

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'custom_requisition_id',
        string='Purchase Ordes',
    )
    custom_picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
               Overrides the default create method to assign a unique sequence number.

               Args:
                   vals_list (list[dict]): Values for the new record.

               Returns:
                   recordset: Newly created requisition.
               """
        for vals in vals_list:
            name = self.env['ir.sequence'].next_by_code('purchase.requisition.seq')
            vals.update({
                'name': name
            })
        return super().create(vals_list)

    def unlink(self):
        """
                Prevents deletion of purchase requisitions unless they are in 'draft', 'cancel', or 'reject' states.

                Raises:
                    UserError: If a requisition is attempted to be deleted in any other state.
                """
        for rec in self:
            if rec.state not in ('draft', 'cancel', 'reject'):
                raise UserError(_('You can not delete Purchase '
                                  'Requisition which is not in draft '
                                  'or cancelled or rejected state.'))
        return super().unlink()

    def requisition_confirm(self):
        """
               Transitions the requisition to 'dept_confirm' state after initial submission by employee.
               Sends email notification to the department manager using template `email_confirm_material_purchase_requistion`.
               """
        for rec in self:
            manager_mail_template = self.env.ref(
                'material_purchase_requisitions.email_confirm_material_purchase_requistion')
            rec.employee_confirm_id = rec.employee_id.id
            rec.confirm_date = fields.Date.today()
            rec.state = 'dept_confirm'
            if manager_mail_template:
                manager_mail_template.send_mail(self.id)

    def requisition_reject(self):
        """
                Marks the requisition as 'reject' and sets metadata for rejection.
                """
        for rec in self:
            rec.state = 'reject'
            rec.reject_employee_id = self.env['hr.employee'].search(
                [('user_id', '=', self.env.uid)], limit=1)
            rec.userreject_date = fields.Date.today()

    def manager_approve(self):
        """
                Approves the requisition at department level and sends notifications to IR user and employee.
                Transitions state to 'ir_approve'.
                """
        for rec in self:
            rec.managerapp_date = fields.Date.today()
            rec.approve_manager_id = self.env['hr.employee'].search([
                ('user_id', '=', self.env.uid)], limit=1)
            employee_mail_template = self.env.ref(
                'material_purchase_requisitions.email_purchase_requisition_iruser_custom')
            email_iruser_template = self.env.ref(
                'material_purchase_requisitions.email_purchase_requisition')
            employee_mail_template.send_mail(self.id)
            email_iruser_template.send_mail(self.id)
            rec.state = 'ir_approve'

    def user_approve(self):
        """
                Final approval step for the requisition, typically by IR user or authorized official.
                """
        for rec in self:
            rec.userrapp_date = fields.Date.today()
            rec.approve_employee_id = self.env['hr.employee'].search([
                ('user_id', '=', self.env.uid)], limit=1)
            rec.state = 'approve'

    def reset_draft(self):
        """
                Resets the requisition to 'draft' state.
                """
        for rec in self:
            rec.state = 'draft'

    @api.model
    def _prepare_pick_vals(self, line=False, stock_id=False):
        """
                Constructs a dictionary of values for creating `stock.move` records.

                Args:
                    line (record): material.purchase.requisition.line
                    stock_id (record): stock.picking

                Returns:
                    dict: move values for internal picking
                """
        pick_vals = {
            'product_id': line.product_id.id,
            'product_uom_qty': line.qty,
            'product_uom': line.uom.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'name': line.product_id.name,
            'picking_type_id': self.custom_picking_type_id.id,
            'picking_id': stock_id.id,
            'custom_requisition_line_id': line.id,
            'company_id': line.requisition_id.company_id.id,
        }
        return pick_vals

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        """
                Prepares purchase order line values based on requisition line and vendor.

                Args:
                    line (record): material.purchase.requisition.line
                    purchase_order (record): purchase.order

                Returns:
                    dict: purchase order line values
                """
        seller = line.product_id._select_seller(
            partner_id=self._context.get('partner_id'),
            quantity=line.qty,
            date=purchase_order.date_order and purchase_order.date_order.date(),
            uom_id=line.uom
        )
        po_line_vals = {
            'product_id': line.product_id.id,
            'name': f"{line.product_id.name}\n{line.description}",
            'product_qty': line.qty,
            'product_uom': line.uom.id,
            'date_planned': fields.Date.today(),
            # 'price_unit': line.product_id.standard_price,
            'price_unit': seller.price or line.product_id.standard_price or 0.0,
            'order_id': purchase_order.id,
            # 'account_analytic_id': self.analytic_account_id.id,
            'analytic_distribution': {
                self.sudo().analytic_account_id.id: 100} if self.analytic_account_id else False,
            'custom_requisition_line_id': line.id
        }
        return po_line_vals

    def request_stock(self):
        """
                Generates either internal stock picking or purchase orders based on the type of requisition lines.
                Validates necessary fields and transitions state to 'stock' after creation.
                """
        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']
        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_('Please create some requisition lines.'))
            if any(line.requisition_type == 'internal' for line in rec.requisition_line_ids):
                if not rec.location_id.id:
                    raise UserError(_('Select Source location under the picking details.'))
                if not rec.custom_picking_type_id.id:
                    raise UserError(_('Select Picking Type under the picking details.'))
                if not rec.dest_location_id:
                    raise UserError(_('Select Destination location under the picking details.'))
                picking_vals = {
                    'partner_id': rec.employee_id.sudo().address_home_id.id,
                    # 'min_date' : fields.Date.today(),
                    'location_id': rec.location_id.id,
                    'location_dest_id': rec.dest_location_id and rec.dest_location_id.id or rec.employee_id.dest_location_id.id or rec.employee_id.department_id.dest_location_id.id,
                    'picking_type_id': rec.custom_picking_type_id.id,  # internal_obj.id,
                    'note': rec.reason,
                    'custom_requisition_id': rec.id,
                    'origin': rec.name,
                    'company_id': rec.company_id.id,

                }
                stock_id = stock_obj.sudo().create(picking_vals)
                delivery_vals = {
                    'delivery_picking_id': stock_id.id,
                }
                rec.write(delivery_vals)

            po_dict = {}
            for line in rec.requisition_line_ids:
                if line.requisition_type == 'internal':
                    pick_vals = rec._prepare_pick_vals(line, stock_id)
                    move_id = move_obj.sudo().create(pick_vals)
                if line.requisition_type == 'purchase':  # 10/12/2019
                    if not line.partner_id:
                        raise UserError(
                            _('Please enter atleast one vendor on Requisition Lines for Requisition Action Purchase'))
                    for partner in line.partner_id:
                        if partner not in po_dict:
                            po_vals = {
                                'partner_id': partner.id,
                                'currency_id': rec.env.user.company_id.currency_id.id,
                                'date_order': fields.Date.today(),
                                'company_id': rec.company_id.id,
                                'custom_requisition_id': rec.id,
                                'origin': rec.name,
                            }
                            purchase_order = purchase_obj.create(po_vals)
                            po_dict.update({partner: purchase_order})
                            po_line_vals = rec.with_context(partner_id=partner)._prepare_po_line(
                                line, purchase_order)
                            purchase_line_obj.sudo().create(po_line_vals)
                        else:
                            purchase_order = po_dict.get(partner)
                            po_line_vals = rec.with_context(partner_id=partner)._prepare_po_line(
                                line, purchase_order)
                            purchase_line_obj.sudo().create(po_line_vals)
                rec.state = 'stock'

    def action_received(self):
        """
               Marks the requisition as received and updates receive date.
               """
        for rec in self:
            rec.receive_date = fields.Date.today()
            rec.state = 'receive'

    def action_cancel(self):
        """
                Cancels the requisition by updating state to 'cancel'.
                """
        for rec in self:
            rec.state = 'cancel'

    @api.onchange('employee_id')
    def set_department(self):
        """
               Automatically sets the department and destination location when employee is selected.
               Prefers employee-level destination location and falls back to department-level.
               """
        for rec in self:
            rec.department_id = rec.employee_id.sudo().department_id.id
            rec.dest_location_id = rec.employee_id.sudo().dest_location_id.id or rec.employee_id.sudo().department_id.dest_location_id.id

    def show_picking(self):
        """
                Opens list view of stock pickings related to this requisition.
                Returns:
                    dict: action window definition
                """
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        res['domain'] = str([('custom_requisition_id', '=', self.id)])
        return res

    def action_show_po(self):
        """
               Opens list view of purchase orders linked to this requisition.
               Returns:
                   dict: action window definition
               """
        self.ensure_one()
        purchase_action = self.env['ir.actions.act_window']._for_xml_id('purchase.purchase_rfq')
        purchase_action['domain'] = str([('custom_requisition_id', '=', self.id)])
        return purchase_action

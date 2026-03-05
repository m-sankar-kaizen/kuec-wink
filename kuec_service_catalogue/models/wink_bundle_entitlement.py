# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _


class WinkBundleEntitlement(models.Model):
    _name = 'wink.bundle.entitlement'
    _description = 'WINK Bundle Entitlement'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
    )
    tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Bundle Tier',
        ondelete='set null',
    )
    service_product_id = fields.Many2one(
        'product.template',
        string='Service',
        required=True,
        ondelete='restrict',
    )
    name = fields.Char(
        string='Description',
        required=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    qty_entitled = fields.Integer(
        string='Entitled Qty',
        default=1,
        help='How many times the customer can activate this service.',
    )
    qty_activated = fields.Integer(
        string='Activated Qty',
        default=0,
        readonly=True,
    )
    state = fields.Selection(
        [
            ('available', 'Available'),
            ('fully_activated', 'Fully Activated'),
            ('expired', 'Expired'),
        ],
        string='Status',
        compute='_compute_state',
        store=True,
    )
    activated_line_ids = fields.One2many(
        'sale.order.line',
        'wink_entitlement_id',
        string='Activated Order Lines',
        readonly=True,
    )
    wink_selected_employee_ids = fields.Many2many(
        'kuec.employee.directory',
        'wink_entitlement_employee_rel',
        'entitlement_id',
        'employee_id',
        string='Selected Employees',
        help='Employees selected for this child service (bundle).',
    )

    def action_add_all_employees(self):
        """Add all employees from the order's company directory to this entitlement (bulk)."""
        self.ensure_one()
        if not self.order_id or not self.order_id.partner_id:
            return
        partner = self.order_id.partner_id.commercial_partner_id
        employees = self.env['kuec.employee.directory'].search([
            ('partner_id', '=', partner.id),
        ])
        if employees:
            self.wink_selected_employee_ids = [(6, 0, employees.ids)]

    @api.depends('qty_entitled', 'qty_activated', 'order_id.state')
    def _compute_state(self):
        for rec in self:
            if rec.order_id and rec.order_id.state == 'cancel':
                rec.state = 'expired'
            elif rec.qty_activated >= rec.qty_entitled:
                rec.state = 'fully_activated'
            else:
                rec.state = 'available'

    # WF-BND-001 / WF-BND-002 / WF-BND-005: per-activation employees & docs
    def action_activate(self, employee_ids=None):
        """
        Customer or coordinator activates one unit of this
        entitlement. Creates a real sale.order.line on the
        confirmed SO, which triggers Odoo's native sale_project
        to create the Project/Task automatically.
        """
        self.ensure_one()
        order = self.order_id

        # No limit on reactivation: customer can activate as many times as needed
        if order.state not in ('sale', 'done'):
            raise UserError(_(
                "The order must be confirmed before activating "
                "bundle services."
            ))

        if self.state == 'expired' or order.state == 'cancel':
            raise UserError(_(
                "This bundle is no longer active. You cannot activate services from a cancelled or expired bundle."
            ))

        # Phase 2: One-Time service activation guard
        if self.service_product_id.request_frequency == 'one_time' and self.qty_activated >= 1:
            raise UserError(_(
                "The service '%s' is a One-Time service and has already been activated."
            ) % self.service_product_id.name)

        # WF-BND-002: Required documents per activated service
        ok_docs, missing_docs = order._wink_required_docs_approved_for_product(
            self.service_product_id
        )
        if not ok_docs:
            raise UserError(_(
                "You cannot activate this service yet because some required "
                "documents are missing or not approved: %s. Please upload "
                "and get approval from the Documents section of your request."
            ) % ", ".join(missing_docs))

        # WF-BND-001: Require employees when service needs selection
        if getattr(self.service_product_id, 'requires_employee_selection', False):
            if not employee_ids:
                raise UserError(_(
                    "Please select at least one employee to activate this service."
                ))

        # Get the product variant
        variant = self.service_product_id.product_variant_ids[:1]
        if not variant:
            raise UserError(_(
                "No product variant found for '%(name)s'."
            ) % {'name': self.service_product_id.name})

        # Create a real SO line — Odoo natively creates
        # Project/Task because the SO is already confirmed.
        # Reactivation: 2nd+ activations get distinct line/task name (e.g. "Service (2)")
        activation_num = self.qty_activated + 1
        line_name = self.name if activation_num <= 1 else _('%s (%s)') % (self.name, activation_num)
        line_vals = {
            'order_id': order.id,
            'product_id': variant.id,
            'product_uom_qty': 1,
            'price_unit': 0.0,
            'name': line_name,
            'wink_entitlement_id': self.id,
        }
        new_line = self.env['sale.order.line'].sudo().create(line_vals)

        # WF-BND-001: store employees per activated line
        if employee_ids:
            new_line.wink_selected_employee_ids = [(6, 0, list(map(int, employee_ids)))]

        self.sudo().write({
            'qty_activated': self.qty_activated + 1,
        })

        # WF-BND-001 / WF-BND-005: log activation with employees
        try:
            employee_names = []
            if employee_ids:
                emps = self.env['kuec.employee.directory'].sudo().browse(
                    list(map(int, employee_ids))
                )
                employee_names = [e.name for e in emps if e.exists()]
            user_name = self.env.user.partner_id.name or self.env.user.name or ''
            msg = (
                "Bundle service <strong>%s</strong> activated "
                "(activation #%s). Order line #%s created."
            ) % (self.name, self.qty_activated, new_line.id)
            if employee_names:
                msg += " Employees: %s." % ", ".join(employee_names)
            if user_name:
                msg += " Activated from portal by %s." % user_name
            order.message_post(
                body=msg,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        except Exception:
            # Never block activation on logging issues
            pass

        return new_line

# -*- coding: utf-8 -*-
# B-8: Audit Trail (mail.thread) on entitlements
# T-3: Activation Idempotency (locking)

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class WinkBundleEntitlement(models.Model):
    _name = 'wink.bundle.entitlement'
    _description = 'WINK Bundle Entitlement'
    # B-8: Add mail.thread for dedicated audit trail per entitlement
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        ondelete='cascade',
        index=True,
        help='Parent sale order this entitlement belongs to.',
    )
    tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Bundle Tier',
        ondelete='set null',
        help='The bundle tier this entitlement was generated from.',
    )
    service_product_id = fields.Many2one(
        'product.template',
        string='Service',
        required=True,
        ondelete='restrict',
        help='The service product template this entitlement represents.',
    )
    name = fields.Char(
        string='Description',
        required=True,
        tracking=True,
        help='Human-readable service description shown on portal.',
    )
    sequence = fields.Integer(
        default=10,
        help='Order of services in the bundle tier listing.',
    )
    qty_entitled = fields.Integer(
        string='Entitled Qty',
        default=1,
        tracking=True,
        help='How many times the customer can activate this service.',
    )
    qty_activated = fields.Integer(
        string='Activated Qty',
        default=0,
        readonly=True,
        tracking=True,
        help='Number of times this service has been activated so far.',
    )
    state = fields.Selection(
        [
            ('available', 'Available'),
            ('pending_gov_payment', 'Pending Gov Payment'),
            ('fully_activated', 'Fully Activated'),
            ('expired', 'Expired'),
        ],
        string='Status',
        compute='_compute_state',
        store=True,
        tracking=True,
        help='Current activation status of this entitlement.',
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

    # GOV-001: Government charge fields
    wink_gov_charge_invoice_id = fields.Many2one(
        'account.move',
        string='Gov Charge Invoice',
        ondelete='set null',
        copy=False,
        help='Pending government charge invoice. Activation is blocked until this invoice is paid.',
    )
    wink_gov_charge_currency_id = fields.Many2one(
        'res.currency',
        related='order_id.currency_id',
        string='Currency',
        readonly=True,
    )
    wink_gov_charge_per_employee = fields.Monetary(
        string='Gov Charge per Employee',
        currency_field='wink_gov_charge_currency_id',
        copy=False,
        help='Actual government charge per employee used for the pending activation invoice.',
    )
    wink_pending_employee_ids = fields.Many2many(
        'kuec.employee.directory',
        'wink_entitlement_pending_emp_rel',
        'entitlement_id',
        'employee_id',
        string='Pending Employees',
        copy=False,
        help='Employees waiting for gov charge payment before activation can proceed.',
    )

    # T-3: Idempotency lock field — prevents concurrent double-activation
    _activation_lock = fields.Boolean(
        default=False,
        help='Internal flag to prevent concurrent activations. Reset after activation completes.',
    )

    def action_gov_charge_paid(self):
        """Called automatically when the gov charge invoice is reconciled/paid.
        Clears the pending invoice, activates using the stored pending employees,
        and cleans up pending fields.
        """
        self.ensure_one()
        employee_ids = self.wink_pending_employee_ids.ids or []
        # Clear pending fields before activating so the guard in action_activate() passes
        self.sudo().write({
            'wink_gov_charge_invoice_id': False,
            'wink_pending_employee_ids': [(5, 0, 0)],
        })
        try:
            self.action_activate(employee_ids=employee_ids if employee_ids else None)
        except Exception:
            _logger.warning(
                "GOV-001: Auto-activation after gov charge payment failed for entitlement %s",
                self.id, exc_info=True,
            )

    def action_coordinator_activate(self):
        """Coordinator activates a sub-service from the backend list.
        Uses wink_selected_employee_ids already set on the entitlement as the employee source.
        """
        self.ensure_one()
        emp_ids = self.wink_selected_employee_ids.ids or []
        return self.action_activate(employee_ids=emp_ids if emp_ids else None)

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

    @api.depends(
        'qty_entitled', 'qty_activated',
        'order_id.state', 'order_id.wink_bundle_cancelled',
        'wink_gov_charge_invoice_id', 'wink_gov_charge_invoice_id.payment_state',
    )
    def _compute_state(self):
        for rec in self:
            if rec.order_id and (rec.order_id.state == 'cancel' or rec.order_id.wink_bundle_cancelled):
                rec.state = 'expired'
            # GOV-001: pending_gov_payment takes priority over fully_activated — a pending
            # gov charge invoice (for any activation, including re-activations) must be paid
            # before the state resolves. This keeps the Pay button visible in the portal.
            elif rec.wink_gov_charge_invoice_id and rec.wink_gov_charge_invoice_id.payment_state not in ('paid', 'in_payment'):
                rec.state = 'pending_gov_payment'
            elif rec.qty_activated >= rec.qty_entitled:
                rec.state = 'fully_activated'
            else:
                rec.state = 'available'

    # WF-BND-001 / WF-BND-002 / WF-BND-005: per-activation employees & docs
    # T-3: Activation Idempotency via SQL-level row lock
    def action_activate(self, employee_ids=None):
        """
        Customer or coordinator activates one unit of this
        entitlement. Creates a real sale.order.line on the
        confirmed SO, which triggers Odoo's native sale_project
        to create the Project/Task automatically.

        T-3: Uses SQL SELECT FOR UPDATE NOWAIT to prevent
        concurrent double-activation from simultaneous portal clicks.
        """
        self.ensure_one()
        order = self.order_id

        # GOV-001: Block activation if a gov charge invoice is pending payment
        if self.wink_gov_charge_invoice_id and self.wink_gov_charge_invoice_id.payment_state not in ('paid', 'in_payment'):
            raise UserError(_(
                "This service has a pending government charge invoice (#%s). "
                "Activation will proceed automatically once the invoice is paid."
            ) % self.wink_gov_charge_invoice_id.name)

        # T-3: Acquire row-level lock to prevent concurrent activation
        try:
            self.env.cr.execute(
                "SELECT id FROM wink_bundle_entitlement WHERE id = %s FOR UPDATE NOWAIT",
                (self.id,)
            )
        except Exception:
            raise UserError(_(
                "This service is currently being activated. Please wait a moment and try again."
            ))

        # Re-read after lock to get latest qty_activated
        self.env.cr.execute(
            "SELECT qty_activated FROM wink_bundle_entitlement WHERE id = %s",
            (self.id,)
        )
        row = self.env.cr.fetchone()
        current_qty_activated = row[0] if row else self.qty_activated

        # No limit on reactivation: customer can activate as many times as needed
        if order.state not in ('sale', 'done'):
            raise UserError(_(
                "The order must be confirmed before activating "
                "bundle services."
            ))

        if self.state == 'expired' or order.state == 'cancel' or order.wink_bundle_cancelled:
            raise UserError(_(
                "This bundle is no longer active. You cannot activate services from a cancelled or expired bundle."
            ))

        if not order.wink_bundle_activated:
            raise UserError(_(
                "This bundle has not been activated yet. "
                "The coordinator will activate it after the confirmation call."
            ))

        # Phase 2: One-Time service activation guard (use locked value)
        if self.service_product_id.request_frequency == 'one_time' and current_qty_activated >= 1:
            raise UserError(_(
                "The service '%s' is a One-Time service and has already been activated."
            ) % self.service_product_id.name)

        # Determine activation number early — needed for line naming
        activation_num = current_qty_activated + 1

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
            # Sync to tasks auto-created by sale_project before employee_ids was set
            linked_tasks = self.env['project.task'].sudo().search([('sale_line_id', '=', new_line.id)])
            if linked_tasks:
                linked_tasks.write({'wink_employee_ids': [(6, 0, list(map(int, employee_ids)))]})

        # I-8: Ensure rating is active on any project created by this activation
        try:
            rating_template = self.env.ref(
                'kuec_service_catalogue.mail_template_wink_rating_request',
                raise_if_not_found=False,
            )
            new_projects = self.env['project.project'].sudo().search(
                [('sale_order_id', '=', order.id)]
            )
            new_projects.filtered(lambda p: not p.rating_active).write({
                'rating_active': True,
                'rating_status': 'stage',
            })
            if rating_template:
                folded_stages = new_projects.mapped('type_ids').filtered(
                    lambda s: s.fold and not s.rating_template_id
                )
                if folded_stages:
                    folded_stages.sudo().write({'rating_template_id': rating_template.id})
        except Exception:
            _logger.warning(
                "Failed to enable ratings after bundle activation for entitlement %s",
                self.id, exc_info=True,
            )

        # T-3: Atomic update using SQL to avoid race condition
        self.env.cr.execute(
            "UPDATE wink_bundle_entitlement SET qty_activated = %s, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = %s",
            (activation_num, self.id)
        )
        self.invalidate_recordset(['qty_activated', 'state'])

        # B-8: Log activation to entitlement's own chatter (audit trail)
        try:
            employee_names = []
            if employee_ids:
                emps = self.env['kuec.employee.directory'].sudo().browse(
                    list(map(int, employee_ids))
                )
                employee_names = [e.name for e in emps if e.exists()]
            user_name = self.env.user.partner_id.name or self.env.user.name or ''
            msg = (
                "Service <strong>%s</strong> activated "
                "(activation #%s). Order line #%s created."
            ) % (self.name, activation_num, new_line.id)
            if employee_names:
                msg += " Employees: %s." % ", ".join(employee_names)
            if user_name:
                msg += " Activated by %s." % user_name

            # B-8: Post to entitlement's own chatter
            self.sudo().message_post(
                body=msg,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            # Also post to order chatter for backward compat
            order.message_post(
                body=msg,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        except Exception:
            # Never block activation on logging issues
            _logger.warning("Failed to log activation for entitlement %s", self.id, exc_info=True)

        return new_line

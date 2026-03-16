# -*- coding: utf-8 -*-

from datetime import date as _date

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProjectTaskWink(models.Model):
    _inherit = 'project.task'

    wink_employee_ids = fields.Many2many(
        'kuec.employee.directory',
        'project_task_employee_rel',
        'task_id',
        'employee_id',
        string='Employees',
        help='Employees linked to this task (from WINK request or added in backend).',
    )
    wink_customer_partner_id = fields.Many2one(
        'res.partner',
        related='sale_order_id.partner_id',
        store=True,
        string='Customer',
        help='Customer partner derived from the linked sale order. Used as domain filter for employee selection.',
    )

    # EPIC-11: SLA reporting — days the task has been open
    wink_days_open = fields.Integer(
        compute='_compute_wink_days_open',
        string='Days Open',
        help='Number of calendar days since this task was created. Used in the Delivery SLA report.',
    )

    def _compute_wink_days_open(self):
        today = _date.today()
        for task in self:
            if task.create_date:
                task.wink_days_open = (today - task.create_date.date()).days
            else:
                task.wink_days_open = 0

    # ── Vendor assignment ────────────────────────────────────────────────────
    wink_vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        tracking=True,
        help='Vendor assigned by the coordinator to deliver this task. '
             'Any contact from res.partner can be selected. '
             'Saving a vendor and clicking "Create RFQ" will auto-generate a draft Purchase Order.',
    )
    wink_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='RFQ / Purchase Order',
        readonly=True,
        ondelete='set null',
        help='Auto-created RFQ when the coordinator assigns a vendor to this task.',
    )
    wink_purchase_order_count = fields.Integer(
        compute='_compute_wink_purchase_order_count',
        string='RFQ / PO Count',
        help='Number of Purchase Orders linked to this task (0 or 1).',
    )

    def _compute_wink_purchase_order_count(self):
        for task in self:
            task.wink_purchase_order_count = 1 if task.wink_purchase_order_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            if not task.sale_order_id or not task.sale_order_id.wink_is_portal_request:
                continue
            order = task.sale_order_id
            # WF-BND-001: prefer employees on activated line (sale_line.wink_selected_employee_ids), else entitlement, else order
            employee_ids = []
            sale_line = getattr(task, 'sale_line_id', None)
            if sale_line and getattr(sale_line, 'wink_entitlement_id', None):
                if getattr(sale_line, 'wink_selected_employee_ids', None) and sale_line.wink_selected_employee_ids:
                    employee_ids = sale_line.wink_selected_employee_ids.ids
                if not employee_ids:
                    employee_ids = sale_line.wink_entitlement_id.wink_selected_employee_ids.ids
            if not employee_ids:
                employee_ids = order.wink_selected_employee_ids.ids
            if employee_ids:
                task.wink_employee_ids = [(6, 0, employee_ids)]
        return tasks

    def write(self, vals):
        res = super().write(vals)

        # When vendor changes, sync rated_partner_id on pending (unconsumed) ratings
        if 'wink_vendor_id' in vals:
            for task in self:
                vendor_id = task.wink_vendor_id.id if task.wink_vendor_id else False
                self.env['rating.rating'].sudo().search([
                    ('res_model', '=', 'project.task'),
                    ('res_id', '=', task.id),
                    ('consumed', '=', False),
                ]).write({'rated_partner_id': vendor_id})

        return res

    # ── Rating: vendor is the rated operator ─────────────────────────────────

    def _send_task_rating_mail(self, **kwargs):
        """Only send rating email for WINK portal tasks that have a vendor assigned.

        Skips silently if:
        - Task has no linked WINK portal order (non-WINK tasks use default behaviour)
        - Task has no wink_vendor_id (vendor not yet assigned — rating email would be meaningless)
        """
        if self.sale_order_id and self.sale_order_id.wink_is_portal_request:
            if not self.wink_vendor_id:
                return
        return super()._send_task_rating_mail(**kwargs)

    def _rating_get_operator(self):
        """Return the assigned vendor as the rated operator so that customer
        ratings are linked to the vendor, not the internal user."""
        self.ensure_one()
        if self.wink_vendor_id:
            return self.wink_vendor_id
        return super()._rating_get_operator()

    # ── Vendor RFQ creation ───────────────────────────────────────────────────

    def action_assign_vendor_rfq(self):
        """Coordinator assigns vendor and creates a draft RFQ for the service product.
        If an RFQ already exists, opens it instead of creating a duplicate."""
        self.ensure_one()
        if not self.wink_vendor_id:
            raise UserError(_('Please select a vendor before creating an RFQ.'))

        # If RFQ already exists, open it
        if self.wink_purchase_order_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id': self.wink_purchase_order_id.id,
                'view_mode': 'form',
                'target': 'current',
            }

        # Resolve service product from task's sale line or order source product
        product = None
        qty = 1.0
        sale_line = getattr(self, 'sale_line_id', None)
        if sale_line and sale_line.product_id:
            product = sale_line.product_id
            qty = sale_line.product_uom_qty or 1.0
        elif self.sale_order_id and self.sale_order_id.wink_source_product_id:
            product = self.sale_order_id.wink_source_product_id.product_variant_ids[:1]

        po_line_vals = []
        if product:
            po_line_vals.append((0, 0, {
                'product_id': product.id,
                'name': product.display_name,
                'product_qty': qty,
                'price_unit': 0.0,
                'date_planned': fields.Datetime.now(),
            }))

        origin = self.sale_order_id.name if self.sale_order_id else self.name
        po = self.env['purchase.order'].sudo().create({
            'partner_id': self.wink_vendor_id.id,
            'origin': origin,
            'notes': _('Auto-generated from WINK task: %s') % self.name,
            'order_line': po_line_vals,
        })
        self.sudo().write({'wink_purchase_order_id': po.id})

        # Sync rated_partner_id on any existing unconsumed ratings
        self.env['rating.rating'].sudo().search([
            ('res_model', '=', 'project.task'),
            ('res_id', '=', self.id),
            ('consumed', '=', False),
        ]).write({'rated_partner_id': self.wink_vendor_id.id})

        self.message_post(
            body=_(
                'Vendor <b>%s</b> assigned. RFQ <b>%s</b> created.'
            ) % (self.wink_vendor_id.name, po.name),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': po.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ── Wizard: Assign Vendor ─────────────────────────────────────────────────

    def action_open_assign_vendor_wizard(self):
        """Opens the Assign Vendor wizard so the coordinator can pick a vendor.
        The wizard will set wink_vendor_id and auto-create the RFQ on confirm."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assign Vendor'),
            'res_model': 'wink.assign.vendor.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_task_id': self.id},
        }

    # ── Smart button: View linked RFQ / PO ───────────────────────────────────

    def action_view_rfq_po(self):
        """Opens the linked Purchase Order / RFQ from the smart button."""
        self.ensure_one()
        if not self.wink_purchase_order_id:
            return
        return {
            'type': 'ir.actions.act_window',
            'name': _('RFQ / Purchase Order'),
            'res_model': 'purchase.order',
            'res_id': self.wink_purchase_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

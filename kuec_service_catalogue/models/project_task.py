# -*- coding: utf-8 -*-

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
    document_submission_ids = fields.One2many(
        'kuec.document.submission',
        'task_id',
        string='Document Submissions',
        help='Compliance documents linked to this task.',
    )

    # ── Vendor assignment ────────────────────────────────────────────────────
    wink_vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        domain=[('supplier_rank', '>', 0)],
        tracking=True,
        help='Vendor assigned by the coordinator to deliver this task. '
             'Saving a vendor and clicking "Create RFQ" will auto-generate a draft Purchase Order.',
    )
    wink_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='RFQ / Purchase Order',
        readonly=True,
        ondelete='set null',
        help='Auto-created RFQ when the coordinator assigns a vendor to this task.',
    )

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
            # Link order documents to this task when order has a single task (standalone)
            if task.project_id:
                order_tasks = self.search([
                    ('sale_order_id', '=', order.id),
                    ('project_id', '=', task.project_id.id),
                ])
                if len(order_tasks) <= 1:
                    order.document_submission_ids.write({'task_id': task.id})
        return tasks

    def write(self, vals):
        if 'stage_id' in vals:
            new_stage = self.env['project.task.type'].browse(vals['stage_id'])
            if not new_stage.exists():
                return super().write(vals)

            for task in self:
                # If we are changing stages, check compliance on WINK portal requests
                if task.sale_order_id and task.sale_order_id.wink_is_portal_request:
                    old_stage = task.stage_id
                    if not old_stage:
                        continue
                    # If moving to a new stage (from the very first stage 'sequence 1-10' typically 'New')
                    if (old_stage.id != new_stage.id
                            and old_stage.sequence <= 10
                            and new_stage.sequence > old_stage.sequence):
                        # WF-BND-003: for activated bundle lines, check docs for that line's product only
                        order = task.sale_order_id
                        all_approved = True
                        pending_names = []
                        sale_line = getattr(task, 'sale_line_id', None)
                        if sale_line and getattr(sale_line, 'wink_entitlement_id', None):
                            product_tmpl = sale_line.product_id.product_tmpl_id
                            all_approved, pending_names = order._wink_required_docs_approved_for_product(product_tmpl)
                        else:
                            # ISSUE-003: pending is always a list of document name strings.
                            all_approved, pending_names = order._wink_all_required_docs_approved()
                        if not all_approved:
                            raise UserError(_(
                                "Compliance Hard-Gate: You cannot move this task out of the 'New' stage because the customer has missing or unapproved documents: %s"
                            ) % ", ".join(pending_names))

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

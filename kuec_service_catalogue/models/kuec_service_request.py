# -*- coding: utf-8 -*-

from odoo import models, fields

class SaleOrderWink(models.Model):
    _inherit = 'sale.order'

    wink_requested_start_date = fields.Date(
        string='Requested Start Date'
    )
    wink_request_notes = fields.Text(
        string='Special Requirements'
    )
    wink_selected_employee_ids = fields.Many2many(
        'kuec.employee.directory',
        'sale_order_employee_rel',
        'order_id', 'employee_id',
        string='Selected Employees'
    )
    wink_is_portal_request = fields.Boolean(
        string='Submitted via WINK Portal',
        default=False
    )
    wink_source_product_id = fields.Many2one(
        'product.template',
        string='Requested Service',
        ondelete='set null'
    )
    wink_price_confirmed = fields.Boolean(
        string='Price Confirmed',
        default=True,
        help="If false, this request requires pricing finalization by the coordinator before the customer can pay."
    )
    wink_bundle_tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Selected Bundle Tier',
        ondelete='set null',
    )
    document_submission_ids = fields.One2many(
        'kuec.document.submission',
        'order_id',
        string='Document Submissions',
    )

    def _wink_get_docs_status(self):
        """Returns dict of requirement_id: submission for all submissions on this order."""
        return {
            s.requirement_id.id: s
            for s in self.document_submission_ids
        }

    def _wink_all_required_docs_approved(self):
        """Returns (bool, list of pending names). True if all required docs are approved."""
        required = self.document_submission_ids.filtered(
            lambda d: d.is_required == 'required'
        )
        pending = required.filtered(
            lambda d: d.state != 'approved'
        )
        return (not bool(pending), pending.mapped('requirement_name'))

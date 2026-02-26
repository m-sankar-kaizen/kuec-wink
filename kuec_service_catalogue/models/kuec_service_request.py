# -*- coding: utf-8 -*-

from odoo import models, fields, api

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
    wink_entitlement_ids = fields.One2many(
        'wink.bundle.entitlement',
        'order_id',
        string='Bundle Entitlements',
    )

    def _wink_get_docs_status(self):
        """Returns dict of requirement_id: submission for all submissions on this order."""
        return {
            s.requirement_id.id: s
            for s in self.document_submission_ids
        }

    def _wink_document_requirements(self):
        """Document requirements to show/collect for this order.
        For bundles: union of all child services' (entitlements') document requirements.
        For standalone: from wink_source_product_id."""
        product = self.wink_source_product_id
        if self.wink_entitlement_ids:
            # Bundle: requirements from each child service (entitlement's service product)
            req_ids = set()
            for ent in self.wink_entitlement_ids:
                if ent.service_product_id:
                    req_ids.update(ent.service_product_id.kuec_document_ids.ids)
            return self.env['kuec.service.document'].browse(sorted(req_ids))
        if product:
            return product.kuec_document_ids
        return self.env['kuec.service.document'].browse()

    def _wink_get_bundle_requirement_ids(self):
        """For bundle orders: required document requirement ids from all child services (entitlements)."""
        requirement_ids = set()
        for ent in self.wink_entitlement_ids:
            if ent.service_product_id:
                for doc in ent.service_product_id.kuec_document_ids:
                    if doc.requirement == 'required':
                        requirement_ids.add(doc.id)
        return requirement_ids

    def _wink_all_required_docs_approved(self):
        """Returns (bool, list of pending names). True if all required docs are approved.
        For bundles, required docs come from child services (entitlements); for standalone, from order product."""
        if self.wink_entitlement_ids:
            # Bundle: required = all required docs from all child services
            requirement_ids = self._wink_get_bundle_requirement_ids()
            if not requirement_ids:
                return (True, [])
            sub_map = {s.requirement_id.id: s for s in self.document_submission_ids}
            pending_names = []
            for rid in requirement_ids:
                sub = sub_map.get(rid)
                if not sub or sub.state != 'approved':
                    req = self.env['kuec.service.document'].browse(rid)
                    pending_names.append(req.name or 'Unknown')
            return (len(pending_names) == 0, pending_names)
        # Standalone: current logic
        required = self.document_submission_ids.filtered(
            lambda d: d.is_required == 'required'
        )
        pending = required.filtered(
            lambda d: d.state != 'approved'
        )
        return (not bool(pending), pending.mapped('requirement_name'))

    def _generate_tier_entitlements(self, tier):
        """Generates the entitlement records for a given tier on this order."""
        self.ensure_one()
        # Clear existing entitlements for this order if any exist
        self.wink_entitlement_ids.unlink()
        
        entitlement_vals = []
        for item in tier.item_ids.sorted('sequence'):
            entitlement_vals.append({
                'order_id': self.id,
                'tier_id': tier.id,
                'service_product_id': item.service_product_id.id,
                'name': item.description or item.service_product_id.name,
                'sequence': item.sequence,
                'qty_entitled': item.qty,
            })
        if entitlement_vals:
            self.env['wink.bundle.entitlement'].sudo().create(entitlement_vals)

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            # If created in backend with a tier
            if order.wink_bundle_tier_id and not order.wink_entitlement_ids:
                order._generate_tier_entitlements(order.wink_bundle_tier_id)
                # Override the name/price of the bundle line if needed
                bundle_line = order.order_line.filtered(
                    lambda l: l.product_id.product_tmpl_id.commercial_structure == 'bundled'
                )[:1]
                if bundle_line:
                    bundle_line.write({
                        'price_unit': order.wink_bundle_tier_id.price,
                        'name': f"{bundle_line.product_id.name} — {order.wink_bundle_tier_id.name}"
                    })
        return orders

    def write(self, vals):
        res = super().write(vals)
        if 'wink_bundle_tier_id' in vals:
            for order in self:
                if order.wink_bundle_tier_id:
                    order._generate_tier_entitlements(order.wink_bundle_tier_id)
                    bundle_line = order.order_line.filtered(
                        lambda l: l.product_id.product_tmpl_id.commercial_structure == 'bundled'
                    )[:1]
                    if bundle_line:
                        bundle_line.write({
                            'price_unit': order.wink_bundle_tier_id.price,
                            'name': f"{bundle_line.product_id.name} — {order.wink_bundle_tier_id.name}"
                        })
                else:
                    # Tier was removed, delete entitlements
                    order.wink_entitlement_ids.unlink()
        return res

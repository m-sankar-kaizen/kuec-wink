# -*- coding: utf-8 -*-
# RET-003

from odoo import models, fields, api, _, exceptions

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
    wink_sale_order_template_id = fields.Many2one(
        'sale.order.template',
        string='Subscription Plan (quotation template)',
        ondelete='set null',
        help='Selected when product has no Recurring Prices; else use Recurring Prices.',
    )
    wink_recurring_pricing_id = fields.Integer(
        string='Recurring pricing ID (Odoo native)',
        copy=False,
        help='ID of the selected product.pricing record (Recurring Prices tab). Stored as integer to avoid read errors when subscription module is not loaded.',
    )
    wink_cancellation_requested = fields.Boolean(
        string='Cancellation Requested',
        default=False,
        tracking=True,
        help='Customer requested to cancel this retainer from the portal.',
    )
    wink_cancellation_requested_date = fields.Datetime(
        string='Cancellation Requested Date',
        tracking=True,
        copy=False,
    )
    wink_cancellation_reason = fields.Text(
        string='Cancellation Reason',
        tracking=True,
        copy=False,
    )
    wink_cancellation_effective_date = fields.Date(
        string='Cancellation Effective Date',
        tracking=True,
        copy=False,
    )
    wink_cancellation_processed_by = fields.Many2one(
        'res.users',
        string='Cancellation Processed By',
        tracking=True,
        copy=False,
    )
    wink_cancellation_processed_date = fields.Datetime(
        string='Cancellation Processed Date',
        tracking=True,
        copy=False,
    )
    wink_cancellation_credit_note_id = fields.Many2one(
        'account.move',
        string='Cancellation Credit Note',
        copy=False,
        readonly=True,
        help='Credit note created when cancellation was processed (refund/wallet policy).',
    )
    wink_change_from_order_id = fields.Many2one(
        'sale.order',
        string='Upgrade/Downgrade From',
        ondelete='set null',
        copy=False,
        help='When this order is a plan upgrade or downgrade, this links to the previous retainer order.',
    )
    # RET-003: Plan change audit fields
    wink_change_type = fields.Selection(
        [('upgrade', 'Upgrade'), ('downgrade', 'Downgrade')],
        string='Plan Change Type',
        tracking=True,
        copy=False,
    )
    wink_proration_credit = fields.Monetary(
        string='Proration Credit',
        currency_field='currency_id',
        tracking=True,
        copy=False,
    )
    wink_proration_charge = fields.Monetary(
        string='Proration Charge',
        currency_field='currency_id',
        tracking=True,
        copy=False,
    )
    wink_plan_change_target_plan_id = fields.Many2one(
        'wink.subscription.plan',
        string='Target Plan',
        tracking=True,
        copy=False,
        ondelete='set null',
    )
    wink_plan_change_effective_date = fields.Date(
        string='Plan Change Effective Date',
        tracking=True,
        copy=False,
    )
    wink_plan_id = fields.Many2one(
        'wink.subscription.plan',
        string='Plan Tier (for proration)',
        ondelete='set null',
        copy=False,
        help='Subscription group plan tier (e.g. Bronze, Silver). Used for proration: remaining value = (plan monthly_std_price ÷ 30) × remaining_days.',
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
    # ISSUE-006: Idempotent cron — store which day-offsets already sent (e.g. "30,14,7").
    wink_expiry_reminder_sent_days = fields.Char(
        string='Expiry reminder sent for days',
        copy=False,
        help='Comma-separated list of remaining-days values for which a reminder was already sent (cron idempotency).',
    )

    def _wink_compute_proration(self, plan_name_hint=None):
        """Compute prorated remaining credit for the current subscription period.

        Multi-service: uses Odoo Recurring Prices when available (per-product price);
        fallback: plan.monthly_std_price.
        Formula: remaining_value = (monthly_price / 30) × remaining_days.

        Returns dict: remaining_days, daily_rate, remaining_value, monthly_std_price, note.
        """
        self.ensure_one()
        product = self.wink_source_product_id
        if not product:
            return None
        group = product.wink_subscription_group_id
        if not group or not group.plan_ids:
            return None

        plan = self.wink_plan_id if self.wink_plan_id and self.wink_plan_id.group_id == group else None
        if not plan and plan_name_hint:
            plan = group.plan_ids.filtered(
                lambda p: p.name.strip().lower() == plan_name_hint.strip().lower()
            )[:1]
        if not plan:
            plan = group.plan_ids.sorted('sequence')[:1]

        end_date = getattr(self, 'next_date', None) or getattr(self, 'next_invoice_date', None)
        from datetime import date
        today = date.today()
        if not end_date or end_date <= today:
            remaining_days = 0
        else:
            remaining_days = (end_date - today).days

        # Resolve monthly price: Odoo pricing (per service) first, else plan.monthly_std_price
        Service = self.env['wink.retainer.change.service'].sudo()
        monthly_price, _ = Service._resolve_monthly_price_for_proration(self, plan, product, pricing_record=None)

        daily_rate = monthly_price / 30.0
        remaining_value = round(daily_rate * remaining_days, 2)

        return {
            'remaining_days': remaining_days,
            'daily_rate': round(daily_rate, 4),
            'remaining_value': remaining_value,
            'monthly_std_price': monthly_price,
            'note': (
                f'Remaining value = ({monthly_price:,.2f} ÷ 30) × {remaining_days} days '
                f'= {remaining_value:,.2f} (from Odoo pricing when available, else plan standard)'
            ),
        }

    def _wink_get_policy(self):
        """Return the wink.subscription.group policy for this order's product, or None."""
        self.ensure_one()
        product = self.wink_source_product_id
        if not product:
            return None
        return product.wink_subscription_group_id or None

    def _wink_remaining_days(self):
        """Return remaining days in current subscription period (0 if not applicable)."""
        self.ensure_one()
        from datetime import date
        today = date.today()
        end_date = getattr(self, 'next_date', None) or getattr(self, 'next_invoice_date', None)
        if end_date and end_date > today:
            return (end_date - today).days
        return 0

    def _wink_can_request_cancel(self):
        """Check if cancellation is allowed by policy (allow_cancellation, min_days_before_cancellation or min_days_before_change).
        Returns (allowed: bool, message: str).
        When remaining_days <= 0 (period ended or not started): allow — min_days rule does not apply."""
        self.ensure_one()
        policy = self._wink_get_policy()
        if not policy:
            return True, ''
        if not policy.allow_cancellation:
            return False, _('Cancellation is not allowed for this subscription.')
        remaining = self._wink_remaining_days()
        min_days = int(policy.min_days_before_cancellation or policy.min_days_before_change or 0)
        # min_days applies only during an active period; when remaining <= 0, allow (period ended or not started)
        if min_days > 0 and remaining > 0 and remaining < min_days:
            return False, _('Plan changes and cancellation require at least %s days before the end of the current period. You have %s days remaining.') % (min_days, remaining)
        return True, ''

    def _wink_can_request_plan_change(self):
        """Check if upgrade/downgrade is allowed by policy (allow_upgrade/allow_downgrade and min_days_before_change).
        Returns (allowed: bool, message: str).
        When remaining_days <= 0 (period ended or not started): allow — min_days rule does not apply."""
        self.ensure_one()
        policy = self._wink_get_policy()
        if not policy:
            return True, ''
        if not policy.allow_upgrade and not policy.allow_downgrade:
            return False, _('Plan changes are not allowed for this subscription.')
        remaining = self._wink_remaining_days()
        min_days = int(policy.min_days_before_change or 0)
        # min_days applies only during an active period; when remaining <= 0, allow
        if min_days > 0 and remaining > 0 and remaining < min_days:
            return False, _('Plan changes require at least %s days before the end of the current period. You have %s days remaining.') % (min_days, remaining)
        return True, ''

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

    # WF-BND-002 / WF-BND-003: required docs per service product only
    def _wink_required_docs_approved_for_product(self, product_tmpl):
        """Return (ok, missing_names) for required docs of given product on this order.

        ok is True when all required documents for product_tmpl are approved for this order.
        missing_names is a list of human-friendly document names that are missing or not approved.
        """
        self.ensure_one()
        if not product_tmpl:
            return True, []
        # Only 'required' documents defined on the product template
        required_docs = product_tmpl.kuec_document_ids.filtered(
            lambda d: getattr(d, 'requirement', '') == 'required'
        )
        if not required_docs:
            return True, []
        required_ids = set(required_docs.ids)
        # Build map requirement_id -> submission for this order
        sub_map = {
            sub.requirement_id.id: sub
            for sub in self.document_submission_ids
            if sub.requirement_id and sub.requirement_id.id in required_ids
        }
        missing_names = []
        for doc in required_docs:
            sub = sub_map.get(doc.id)
            if not sub or sub.state != 'approved':
                missing_names.append(doc.name or _('Unknown'))
        return (len(missing_names) == 0, missing_names)

    def _wink_get_bundle_requirement_ids(self):
        """For bundle orders: required document requirement ids from all child services (entitlements)."""
        requirement_ids = set()
        for ent in self.wink_entitlement_ids:
            if ent.service_product_id:
                for doc in ent.service_product_id.kuec_document_ids:
                    if doc.requirement == 'required':
                        requirement_ids.add(doc.id)
        return requirement_ids

    # ISSUE-003: Return type is always (bool, list of user-friendly document name strings).
    def _wink_all_required_docs_approved(self):
        """Returns (bool, list of pending doc names). True if all required docs are approved.
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
                    pending_names.append(req.name or _('Unknown'))
            return (len(pending_names) == 0, pending_names)
        # Standalone: return list of requirement names (never recordset)
        required = self.document_submission_ids.filtered(
            lambda d: d.is_required == 'required'
        )
        pending = required.filtered(
            lambda d: d.state != 'approved'
        )
        names = [req.requirement_id.name or _('Unknown') for req in pending]
        return (len(pending) == 0, names)

    def _wink_create_cancellation_credit_note(self, remaining_value):
        """Create credit note for retainer cancellation (refund/wallet policy).
        Returns account.move or False if not created. Posts the move so the refund is applied."""
        self.ensure_one()
        if remaining_value <= 0:
            return False
        source = self.wink_source_product_id
        if not source:
            return False
        # Resolve to product.product (account.move.line requires product_id = product.product)
        if source._name == 'product.template':
            product = self.env['product.product'].search(
                [('product_tmpl_id', '=', source.id)], limit=1
            )
        else:
            product = source
        if not product or product._name != 'product.product':
            return False
        account = product.property_account_income_id
        if not account:
            account = product.categ_id.property_account_income_categ_id
        if not account:
            return False
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            return False
        from odoo import fields as odoo_fields
        today = odoo_fields.Date.context_today(self)
        taxes = product.taxes_id or self.env['account.tax']
        line_vals = {
            'name': _('Retainer cancellation credit — %s') % (self.name or ''),
            'product_id': product.id,
            'product_uom_id': product.uom_id.id,
            'quantity': 1.0,
            'price_unit': remaining_value,
            'account_id': account.id,
            'tax_ids': [(6, 0, taxes.ids)],
        }
        move_vals = {
            'move_type': 'out_refund',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'ref': _('Retainer cancellation: %s') % (self.name or ''),
            'currency_id': self.currency_id.id,
            'journal_id': journal.id,
            'invoice_date': today,
            'date': today,
            'company_id': self.company_id.id,
            'invoice_line_ids': [(0, 0, line_vals)],
        }
        credit_note = self.env['account.move'].create(move_vals)
        # Post so the refund is applied (draft credit note does not register as refund)
        if credit_note.state == 'draft':
            try:
                credit_note.action_post()
            except Exception as e:
                self.message_post(
                    body=_('Credit note created but posting failed: %s. Post it manually.') % str(e),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
        return credit_note

    def action_wink_mark_cancellation_processed(self):
        """RET-007: Coordinator marks cancellation as processed.
        Creates credit note when policy is refund or wallet. Multi-record safe."""
        if not self.env.user.has_group('kuec_portal_foundation.group_kuec_coordinator'):
            raise exceptions.UserError(
                _('Only coordinators can mark cancellation as processed.')
            )
        from odoo import fields as odoo_fields
        now = odoo_fields.Datetime.now()
        user_name = self.env.user.name
        for order in self:
            if not order.wink_cancellation_requested:
                continue
            vals = {
                'wink_cancellation_processed_by': self.env.user.id,
                'wink_cancellation_processed_date': now,
            }
            # Create credit note when policy is refund or wallet and no credit note yet
            if not order.wink_cancellation_credit_note_id:
                policy = order._wink_get_policy()
                if policy and policy.cancellation_credit_policy in ('refund', 'wallet'):
                    proration = order._wink_compute_proration()
                    remaining = proration.get('remaining_value', 0) if proration else 0
                    if remaining > 0:
                        try:
                            credit_note = order._wink_create_cancellation_credit_note(remaining)
                            if credit_note:
                                vals['wink_cancellation_credit_note_id'] = credit_note.id
                            else:
                                order.message_post(
                                    body=_(
                                        'Credit note was not created (e.g. missing product variant '
                                        'or income account). Please check the service product configuration.'
                                    ),
                                    message_type='comment',
                                    subtype_xmlid='mail.mt_note',
                                )
                        except Exception as e:
                            order.message_post(
                                body=_('Credit note creation failed: %s') % str(e),
                                message_type='comment',
                                subtype_xmlid='mail.mt_note',
                            )
                            raise exceptions.UserError(
                                _('Credit note creation failed for order %s: %s')
                                % (order.name, str(e))
                            ) from e
                    else:
                        order.message_post(
                            body=_(
                                'No credit note created: remaining value is 0 or proration could not be computed '
                                '(check subscription period / next invoice date).'
                            ),
                            message_type='comment',
                            subtype_xmlid='mail.mt_note',
                        )
            order.write(vals)
            body = _(
                "Coordinator %(user)s marked cancellation as processed on %(when)s."
            ) % {'user': user_name, 'when': now}
            if order.wink_cancellation_credit_note_id:
                body += _(
                    " Credit note <a href='/web#model=account.move&amp;id=%(id)s'>%(name)s</a> created."
                ) % {
                    'id': order.wink_cancellation_credit_note_id.id,
                    'name': order.wink_cancellation_credit_note_id.name or _('Draft'),
                }
            order.message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

    def action_view_source_subscription(self):
        """RET-007: Open source order (plan change from)."""
        self.ensure_one()
        if not self.wink_change_from_order_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'res_id': self.wink_change_from_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_cancellation_credit_note(self):
        """Open cancellation credit note."""
        self.ensure_one()
        if not self.wink_cancellation_credit_note_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.wink_cancellation_credit_note_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_wink_add_all_employees(self):
        """Add all employees from the customer's directory to this order (standalone request)."""
        self.ensure_one()
        if not self.partner_id:
            return
        partner = self.partner_id.commercial_partner_id
        employees = self.env['kuec.employee.directory'].search([
            ('partner_id', '=', partner.id),
        ])
        if employees:
            self.wink_selected_employee_ids = [(6, 0, employees.ids)]

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

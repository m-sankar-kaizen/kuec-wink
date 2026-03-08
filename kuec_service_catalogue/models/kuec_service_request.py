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

    # --- Bundle Lifecycle Fields ---
    wink_bundle_start_date = fields.Date(
        string='Bundle Start Date',
        copy=False,
        help='Date when the current bundle billing period started. Used for pro-rata refund/charge calculations.',
    )
    wink_bundle_end_date = fields.Date(
        string='Bundle End Date / Next Renewal',
        copy=False,
        help='Date when the current bundle billing period ends (next renewal). Used for pro-rata calculations.',
    )
    wink_pending_downgrade_tier_id = fields.Many2one(
        'wink.bundle.tier',
        string='Pending Downgrade Tier',
        ondelete='set null',
        copy=False,
        help='When a downgrade is scheduled for next billing cycle, this holds the target tier until the cycle renews.',
    )
    wink_bundle_change_log_ids = fields.One2many(
        'wink.bundle.change.log',
        'order_id',
        string='Bundle Change History',
        readonly=True,
    )
    wink_bundle_cancelled = fields.Boolean(
        string='Bundle Cancelled (Self-Service)',
        default=False,
        copy=False,
        help='Set True when the bundle was cancelled by the customer via portal self-service. '
             'Independent of order.state so it works even when action_cancel() cannot run '
             '(e.g. order already has posted invoices).',
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

    # =========================================================================
    # BUNDLE LIFECYCLE — P2: Refund calculator + cancel/upgrade/downgrade
    # =========================================================================

    def _wink_bundle_get_policy(self):
        """Return the wink.bundle record for this order's source product, or None."""
        self.ensure_one()
        product = self.wink_source_product_id
        if product and product.wink_bundle_id:
            return product.wink_bundle_id
        return None

    def _wink_bundle_remaining_days(self):
        """Return (remaining_days, total_days) for the CURRENT billing period.
        Period end = next_invoice_date (or wink_bundle_end_date override).
        Period start = end minus the subscription plan duration — so it stays
        accurate after renewal (when start_date would be years in the past).
        Falls back to wink_bundle_start_date / start_date if no plan is set.
        Returns (0, 0) when dates are unavailable or period has elapsed."""
        self.ensure_one()
        from datetime import date as date_cls
        from dateutil.relativedelta import relativedelta
        today = date_cls.today()

        # Period end
        end = self.wink_bundle_end_date or self.next_invoice_date
        if not end or end <= today:
            return 0, 0

        # Period start — derive from plan period so it's correct after renewal
        start = self.wink_bundle_start_date
        if not start:
            plan = self.plan_id
            if plan and plan.billing_period_value and plan.billing_period_unit:
                unit = plan.billing_period_unit  # 'day', 'week', 'month', 'year'
                kwargs = {unit + 's': plan.billing_period_value}
                start = end - relativedelta(**kwargs)
            else:
                start = self.start_date

        if not start:
            return 0, 0
        remaining = (end - today).days
        total = (end - start).days
        return max(remaining, 0), max(total, 1)

    def _wink_bundle_compute_refund(self):
        """Compute prorated refund amount for bundle cancellation based on bundle policy.

        Returns dict with: remaining_days, total_days, refund_amount, policy, note.
        Returns refund_amount=0 when no active period or policy is 'none'.
        """
        self.ensure_one()
        remaining_days, total_days = self._wink_bundle_remaining_days()
        bundle = self._wink_bundle_get_policy()
        tier = self.wink_bundle_tier_id

        if not bundle or not tier:
            return {
                'remaining_days': remaining_days, 'total_days': total_days,
                'refund_amount': 0.0, 'policy': 'none',
                'note': 'No bundle or tier configured.',
            }

        policy = bundle.cancel_refund_policy or 'none'

        if policy == 'none' or remaining_days <= 0:
            return {
                'remaining_days': remaining_days, 'total_days': total_days,
                'refund_amount': 0.0, 'policy': policy,
                'note': 'No refund per policy.' if policy == 'none' else 'No remaining days in period.',
            }

        # Base amount: what the customer actually paid (not the legacy tier.price)
        paid_amount = self.amount_total or 0.0

        if policy == 'monthly_rate':
            # Use standard monthly price — yearly discount is forfeited on cancellation
            monthly_price = tier.price_monthly or 0.0
            if not monthly_price and total_days > 0:
                # Fallback: derive monthly equivalent from actual paid amount
                monthly_price = paid_amount / max(total_days / 30.0, 1)
            daily_rate = monthly_price / 30.0
            refund_amount = round(daily_rate * remaining_days, 2)
            # Never refund more than what was paid
            refund_amount = min(refund_amount, paid_amount)
            note = (
                f'Monthly rate policy: ({monthly_price:.2f} / 30) × {remaining_days} days'
                f' = {refund_amount:.2f} (yearly discount forfeited, capped at paid amount {paid_amount:.2f})'
            )
        else:  # pro_rata
            refund_ratio = remaining_days / total_days
            refund_amount = round(paid_amount * refund_ratio, 2)
            note = (
                f'Pro-rata: {paid_amount:.2f} × ({remaining_days}/{total_days})'
                f' = {refund_amount:.2f}'
            )

        return {
            'remaining_days': remaining_days,
            'total_days': total_days,
            'refund_amount': max(refund_amount, 0.0),
            'policy': policy,
            'note': note,
        }

    def _wink_bundle_compute_upgrade_charge(self, new_tier):
        """Compute pro-rata charge amount for upgrading from current tier to new_tier.
        Returns dict: remaining_days, total_days, charge_amount, note.
        """
        self.ensure_one()
        remaining_days, total_days = self._wink_bundle_remaining_days()
        current_tier = self.wink_bundle_tier_id
        price_delta = (new_tier.price or 0.0) - (current_tier.price if current_tier else 0.0)
        if price_delta <= 0 or remaining_days <= 0 or total_days <= 0:
            return {
                'remaining_days': remaining_days, 'total_days': total_days,
                'charge_amount': 0.0,
                'note': 'No upgrade charge (price delta ≤ 0 or no remaining period).',
            }
        charge_amount = round(price_delta * (remaining_days / total_days), 2)
        return {
            'remaining_days': remaining_days,
            'total_days': total_days,
            'charge_amount': max(charge_amount, 0.0),
            'note': (
                f'Upgrade charge: {price_delta:.2f} × ({remaining_days}/{total_days})'
                f' = {charge_amount:.2f}'
            ),
        }

    def _wink_bundle_compute_downgrade_credit(self, new_tier):
        """Compute pro-rata credit for downgrading from current tier to new_tier.
        Returns dict: remaining_days, total_days, credit_amount, note.
        """
        self.ensure_one()
        bundle = self._wink_bundle_get_policy()
        policy = bundle.downgrade_credit_policy if bundle else 'none'
        remaining_days, total_days = self._wink_bundle_remaining_days()
        current_tier = self.wink_bundle_tier_id
        price_delta = (current_tier.price if current_tier else 0.0) - (new_tier.price or 0.0)
        if policy == 'none' or price_delta <= 0 or remaining_days <= 0 or total_days <= 0:
            return {
                'remaining_days': remaining_days, 'total_days': total_days,
                'credit_amount': 0.0, 'policy': policy,
                'note': 'No downgrade credit per policy.' if policy == 'none' else 'No remaining days.',
            }
        credit_amount = round(price_delta * (remaining_days / total_days), 2)
        return {
            'remaining_days': remaining_days,
            'total_days': total_days,
            'credit_amount': max(credit_amount, 0.0),
            'policy': policy,
            'note': (
                f'Downgrade credit: {price_delta:.2f} × ({remaining_days}/{total_days})'
                f' = {credit_amount:.2f}'
            ),
        }

    def _wink_bundle_create_upgrade_invoice(self, amount, new_tier, description):
        """Create and post a customer invoice (out_invoice) for the upgrade pro-rata charge.
        Returns account.move or False. The invoice is left in 'posted' state so the portal
        payment link is immediately available.
        """
        self.ensure_one()
        if amount <= 0:
            return False
        # Resolve product for accounting (prefer tier's product, fallback to source product)
        product = None
        if new_tier and new_tier.product_variant_id:
            product = new_tier.product_variant_id
        if not product and self.wink_source_product_id:
            src = self.wink_source_product_id
            if src._name == 'product.template':
                product = self.env['product.product'].search(
                    [('product_tmpl_id', '=', src.id)], limit=1
                )
            else:
                product = src
        if not product:
            line = self.order_line[:1]
            product = line.product_id if line else None
        if not product or product._name != 'product.product':
            return False
        account = product.property_account_income_id
        if not account:
            account = product.categ_id.property_account_income_categ_id
        if not account:
            return False
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'), ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            return False
        from odoo import fields as odoo_fields
        today = odoo_fields.Date.context_today(self)
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'ref': description,
            'currency_id': self.currency_id.id,
            'journal_id': journal.id,
            'invoice_date': today,
            'date': today,
            'company_id': self.company_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'quantity': 1.0,
                'price_unit': amount,
                'account_id': account.id,
            })],
        })
        try:
            invoice.action_post()
        except Exception as e:
            self.message_post(
                body=_('Bundle upgrade invoice created but could not be posted: %s') % str(e),
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
        return invoice

    def _wink_bundle_create_credit_note(self, amount, description):
        """Create and post a credit note for the given amount.
        Uses the source product or first SO line product for accounting.
        Returns account.move or False.
        """
        self.ensure_one()
        if amount <= 0:
            return False
        # Resolve product for accounting
        product = None
        src = self.wink_source_product_id
        if src:
            if src._name == 'product.template':
                product = self.env['product.product'].search(
                    [('product_tmpl_id', '=', src.id)], limit=1
                )
            else:
                product = src
        if not product:
            line = self.order_line[:1]
            product = line.product_id if line else None
        if not product or product._name != 'product.product':
            return False
        account = product.property_account_income_id
        if not account:
            account = product.categ_id.property_account_income_categ_id
        if not account:
            return False
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'), ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            return False
        from odoo import fields as odoo_fields
        today = odoo_fields.Date.context_today(self)
        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_id.id,
            'invoice_origin': self.name,
            'ref': description,
            'currency_id': self.currency_id.id,
            'journal_id': journal.id,
            'invoice_date': today,
            'date': today,
            'company_id': self.company_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': description,
                'product_id': product.id,
                'product_uom_id': product.uom_id.id,
                'quantity': 1.0,
                'price_unit': amount,
                'account_id': account.id,
            })],
        })
        try:
            credit_note.action_post()
        except Exception as e:
            self.message_post(
                body=_('Bundle credit note created but could not be posted: %s') % str(e),
                message_type='comment', subtype_xmlid='mail.mt_note',
            )
        return credit_note

    def _wink_bundle_do_cancel(self, reason=''):
        """Portal self-service cancellation.
        Computes refund per policy, creates credit note, cancels the order, logs the event.
        Returns dict: refund_amount, credit_note.
        """
        self.ensure_one()
        bundle = self._wink_bundle_get_policy()
        if bundle and not bundle.allow_self_service_cancel:
            raise exceptions.UserError(
                _('Self-service cancellation is not enabled for this bundle.')
            )
        if self.wink_bundle_cancelled:
            raise exceptions.UserError(
                _('This bundle has already been cancelled.')
            )
        if self.state not in ('sale', 'done'):
            raise exceptions.UserError(
                _('Only confirmed bundle orders can be cancelled.')
            )
        # Compute refund
        refund_info = self._wink_bundle_compute_refund()
        refund_amount = refund_info.get('refund_amount', 0.0)

        # Create credit note
        credit_note = False
        if refund_amount > 0:
            credit_note = self._wink_bundle_create_credit_note(
                refund_amount,
                _('Bundle cancellation credit — %s') % (self.name or ''),
            )

        # Log the event
        from odoo import fields as odoo_fields
        self.env['wink.bundle.change.log'].sudo().create({
            'order_id': self.id,
            'change_type': 'cancel',
            'from_tier_id': self.wink_bundle_tier_id.id if self.wink_bundle_tier_id else False,
            'refund_amount': refund_amount,
            'credit_note_id': credit_note.id if credit_note else False,
            'user_id': self.env.user.id,
            'remaining_days': refund_info.get('remaining_days', 0),
            'total_days': refund_info.get('total_days', 0),
            'note': reason or '',
            'state': 'done',
        })

        # Persist cancellation fields — wink_bundle_cancelled is ALWAYS set True here,
        # independent of whether action_cancel() succeeds below. This ensures the portal
        # reflects the cancelled state even when the order has invoices and cannot be
        # moved to state='cancel' by Odoo.
        now = odoo_fields.Datetime.now()
        self.sudo().write({
            'wink_cancellation_requested': True,
            'wink_cancellation_reason': reason,
            'wink_cancellation_requested_date': now,
            'wink_cancellation_processed_date': now,
            'wink_cancellation_credit_note_id': credit_note.id if credit_note else False,
            'wink_bundle_cancelled': True,
        })

        # Expire all entitlements immediately
        self.sudo().wink_entitlement_ids.write({'qty_entitled': 0})

        # Close the order in the backend using the native subscription mechanism.
        # For subscription orders (is_subscription=True), set_close() correctly sets
        # subscription_state='6_churn' even when posted invoices prevent action_cancel().
        # For non-subscription orders, fall back to action_cancel().
        close_reason = None
        if reason:
            close_reason = self.env['sale.order.close.reason'].sudo().search(
                [('name', '=', reason)], limit=1
            )
        close_reason_id = close_reason.id if close_reason else None
        try:
            if self.is_subscription:
                self.sudo().set_close(close_reason_id=close_reason_id)
            else:
                self.sudo().action_cancel()
        except Exception as e:
            self.message_post(
                body=_('Order state could not be updated: %s. '
                       'The bundle is marked as cancelled in the portal regardless.') % str(e),
                message_type='comment', subtype_xmlid='mail.mt_note',
            )

        # Chatter
        msg = _(
            'Bundle cancelled by customer. Refund: <strong>%(amount)s %(currency)s</strong>.'
        ) % {'amount': f'{refund_amount:,.2f}', 'currency': self.currency_id.name or ''}
        if reason:
            msg += _(' Reason: %s') % reason
        if credit_note:
            msg += _(
                ' Credit note <a href="/web#model=account.move&amp;id=%(id)s">%(name)s</a> created.'
            ) % {'id': credit_note.id, 'name': credit_note.name or _('Draft')}
        self.sudo().message_post(body=msg, message_type='comment', subtype_xmlid='mail.mt_note')

        return {'refund_amount': refund_amount, 'credit_note': credit_note}

    def _wink_bundle_do_upgrade(self, new_tier_id):
        """Portal self-service tier upgrade.
        Charges pro-rata price delta, swaps tier, regenerates entitlements, logs event.
        Returns dict: charge_amount, new_tier.
        """
        self.ensure_one()
        bundle = self._wink_bundle_get_policy()
        if bundle and not bundle.allow_self_service_upgrade:
            raise exceptions.UserError(
                _('Self-service upgrade is not enabled for this bundle.')
            )
        if self.state not in ('sale', 'done'):
            raise exceptions.UserError(
                _('Only confirmed bundle orders can be upgraded.')
            )
        new_tier = self.env['wink.bundle.tier'].sudo().browse(int(new_tier_id))
        if not new_tier.exists():
            raise exceptions.UserError(_('Invalid tier selected.'))
        current_tier = self.wink_bundle_tier_id
        if current_tier and new_tier.id not in current_tier.upgrade_to_ids.ids:
            raise exceptions.UserError(
                _('Upgrade to "%s" is not configured for this tier.') % new_tier.name
            )

        # Compute charge
        charge_info = self._wink_bundle_compute_upgrade_charge(new_tier)
        charge_amount = charge_info.get('charge_amount', 0.0)

        # Create SO line for the upgrade charge (for order record keeping)
        charge_line = False
        upgrade_desc = _(
            'Bundle upgrade to %(tier)s — pro-rata %(days)s days'
        ) % {'tier': new_tier.name, 'days': charge_info.get('remaining_days', 0)}
        if charge_amount > 0:
            variant = new_tier.product_variant_id
            if not variant and self.wink_source_product_id:
                variant = self.wink_source_product_id.product_variant_ids[:1]
            if variant:
                charge_line = self.env['sale.order.line'].sudo().create({
                    'order_id': self.id,
                    'product_id': variant.id,
                    'name': upgrade_desc,
                    'product_uom_qty': 1,
                    'price_unit': charge_amount,
                })

        # Create a payable invoice for the upgrade charge so customer can pay immediately
        upgrade_invoice = False
        if charge_amount > 0:
            upgrade_invoice = self._wink_bundle_create_upgrade_invoice(
                charge_amount, new_tier, upgrade_desc
            )

        # Log
        self.env['wink.bundle.change.log'].sudo().create({
            'order_id': self.id,
            'change_type': 'upgrade',
            'from_tier_id': current_tier.id if current_tier else False,
            'to_tier_id': new_tier.id,
            'charge_amount': charge_amount,
            'charge_line_id': charge_line.id if charge_line else False,
            'user_id': self.env.user.id,
            'remaining_days': charge_info.get('remaining_days', 0),
            'total_days': charge_info.get('total_days', 0),
            'note': charge_info.get('note', ''),
            'state': 'done',
        })

        # Swap tier and regenerate entitlements
        self.sudo().with_context(skip_tier_entitlements=True).write(
            {'wink_bundle_tier_id': new_tier.id}
        )
        self.sudo().wink_entitlement_ids.unlink()
        self._generate_tier_entitlements(new_tier)

        # Chatter
        self.sudo().message_post(
            body=_(
                'Bundle upgraded from <strong>%(old)s</strong> to <strong>%(new)s</strong>.'
                ' Pro-rata charge: <strong>%(amount)s %(currency)s</strong>.'
            ) % {
                'old': current_tier.name if current_tier else '—',
                'new': new_tier.name,
                'amount': f'{charge_amount:,.2f}',
                'currency': self.currency_id.name or '',
            },
            message_type='comment', subtype_xmlid='mail.mt_note',
        )

        return {'charge_amount': charge_amount, 'new_tier': new_tier, 'invoice': upgrade_invoice}

    def _wink_bundle_do_downgrade(self, new_tier_id):
        """Portal self-service tier downgrade.
        Issues pro-rata credit note for price delta (per policy), swaps tier,
        regenerates entitlements, logs event.
        Returns dict: credit_amount, credit_note, new_tier.
        """
        self.ensure_one()
        bundle = self._wink_bundle_get_policy()
        if bundle and not bundle.allow_self_service_downgrade:
            raise exceptions.UserError(
                _('Self-service downgrade is not enabled for this bundle.')
            )
        if self.state not in ('sale', 'done'):
            raise exceptions.UserError(
                _('Only confirmed bundle orders can be downgraded.')
            )
        new_tier = self.env['wink.bundle.tier'].sudo().browse(int(new_tier_id))
        if not new_tier.exists():
            raise exceptions.UserError(_('Invalid tier selected.'))
        current_tier = self.wink_bundle_tier_id
        if current_tier and new_tier.id not in current_tier.downgrade_to_ids.ids:
            raise exceptions.UserError(
                _('Downgrade to "%s" is not configured for this tier.') % new_tier.name
            )

        # Compute credit
        credit_info = self._wink_bundle_compute_downgrade_credit(new_tier)
        credit_amount = credit_info.get('credit_amount', 0.0)

        # Create credit note
        credit_note = False
        if credit_amount > 0:
            credit_note = self._wink_bundle_create_credit_note(
                credit_amount,
                _('Bundle downgrade credit — %(old)s → %(new)s — %(order)s') % {
                    'old': current_tier.name if current_tier else '—',
                    'new': new_tier.name,
                    'order': self.name or '',
                },
            )

        # Log
        self.env['wink.bundle.change.log'].sudo().create({
            'order_id': self.id,
            'change_type': 'downgrade',
            'from_tier_id': current_tier.id if current_tier else False,
            'to_tier_id': new_tier.id,
            'refund_amount': credit_amount,
            'credit_note_id': credit_note.id if credit_note else False,
            'user_id': self.env.user.id,
            'remaining_days': credit_info.get('remaining_days', 0),
            'total_days': credit_info.get('total_days', 0),
            'note': credit_info.get('note', ''),
            'state': 'done',
        })

        # Swap tier and regenerate entitlements
        self.sudo().with_context(skip_tier_entitlements=True).write(
            {'wink_bundle_tier_id': new_tier.id}
        )
        self.sudo().wink_entitlement_ids.unlink()
        self._generate_tier_entitlements(new_tier)

        # Chatter
        self.sudo().message_post(
            body=_(
                'Bundle downgraded from <strong>%(old)s</strong> to <strong>%(new)s</strong>.'
                ' Credit: <strong>%(amount)s %(currency)s</strong>.'
            ) % {
                'old': current_tier.name if current_tier else '—',
                'new': new_tier.name,
                'amount': f'{credit_amount:,.2f}',
                'currency': self.currency_id.name or '',
            },
            message_type='comment', subtype_xmlid='mail.mt_note',
        )

        return {'credit_amount': credit_amount, 'credit_note': credit_note, 'new_tier': new_tier}

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
        if 'wink_bundle_tier_id' in vals and not self.env.context.get('skip_tier_entitlements'):
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

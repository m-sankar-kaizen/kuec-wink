# -*- coding: utf-8 -*-
# RET-004, RET-009
"""Service layer for retainer plan change and cancellation.
Business logic centralized here; controllers stay thin.

Proration price source (multi-service support):
- Primary: Odoo Recurring Prices (product.pricing) — each service has its own price
- Fallback: plan.monthly_std_price — when no Odoo pricing linked
"""
from datetime import date
from odoo import _, models


class WinkRetainerChangeService(models.AbstractModel):
    """Service for plan change and cancellation proration."""
    _name = 'wink.retainer.change.service'
    _description = 'WINK Retainer Plan Change Service'

    def _monthly_price_from_pricing_line(self, product, pricing_line):
        """Resolve monthly-equivalent price from Odoo pricing line.
        Returns float or 0. Uses product._recurrence_duration_months for normalization."""
        if not product or not pricing_line:
            return 0.0
        price = getattr(pricing_line, 'price', None) or getattr(pricing_line, 'recurring_price', None) or 0
        price = float(price or 0)
        if price <= 0:
            return 0.0
        rec = getattr(pricing_line, 'recurrence_id', None) or getattr(pricing_line, 'plan_id', None) or getattr(pricing_line, 'recurring_plan_id', None)
        months = getattr(product, '_recurrence_duration_months', lambda r: 1)(rec) or 1
        return price / months if months else price

    def _resolve_monthly_price_for_proration(self, order, plan, product, pricing_record=None):
        """Resolve monthly price for proration. Multi-service: uses Odoo pricing when available.
        Returns (monthly_price, source_label) — source_label for audit."""
        if not product:
            fallback = float(plan.monthly_std_price or 0) if plan else 0.0
            return fallback, 'plan_fallback'
        # 1) From pricing_record (target plan's Odoo pricing)
        if pricing_record and getattr(pricing_record, 'exists', lambda: False)() and pricing_record.exists():
            monthly = self._monthly_price_from_pricing_line(product, pricing_record)
            if monthly > 0:
                return monthly, 'odoo_pricing'
        # 2) From order's current pricing (wink_recurring_pricing_id)
        pid = getattr(order, 'wink_recurring_pricing_id', None)
        if pid and product._wink_recurring_plan_lines():
            for line in product._wink_recurring_plan_lines():
                if getattr(line, 'id', None) == pid:
                    monthly = self._monthly_price_from_pricing_line(product, line)
                    if monthly > 0:
                        return monthly, 'odoo_pricing'
                    break
        # 3) Fallback: plan.monthly_std_price
        fallback = float(plan.monthly_std_price or 0) if plan else 0.0
        return fallback, 'plan_fallback'

    def _resolve_plan_pricing_record(self, product, plan, current_recurrence_id=None):
        """Resolve pricing record for plan on product. Returns (pricing_record, recurrence_id) or (None, None)."""
        if not product or not plan:
            return None, None
        lines = product._wink_recurring_plan_lines() if hasattr(product, '_wink_recurring_plan_lines') else []
        if not lines:
            return None, None
        if plan.pricing_model and plan.pricing_id:
            try:
                rec = self.env[plan.pricing_model].sudo().browse(plan.pricing_id)
                prod_ref = getattr(rec, 'product_tmpl_id', None) or getattr(rec, 'product_template_id', None)
                if rec.exists() and prod_ref == product:
                    rec_id = getattr(getattr(rec, 'recurrence_id', None), 'id', None) or getattr(getattr(rec, 'plan_id', None), 'id', None)
                    return rec, rec_id
            except (KeyError, AttributeError):
                pass
        hint = (plan.recurrence_name_hint or '').strip().lower()
        for line in lines:
            rec = getattr(line, 'recurrence_id', None) or getattr(line, 'plan_id', None) or getattr(line, 'recurring_plan_id', None)
            if not rec:
                continue
            rec_name = (getattr(rec, 'name', None) or '').strip().lower()
            if hint and rec_name and hint in rec_name:
                return line, rec.id
        if current_recurrence_id:
            for line in lines:
                rec = getattr(line, 'recurrence_id', None) or getattr(line, 'plan_id', None)
                if rec and rec.id == current_recurrence_id:
                    return line, current_recurrence_id
        line = lines[0]
        rec = getattr(line, 'recurrence_id', None) or getattr(line, 'plan_id', None)
        return line, rec.id if rec else None

    def _get_end_date(self, order):
        """Return subscription period end date (next_date or next_invoice_date)."""
        order.ensure_one()
        end = getattr(order, 'next_date', None) or getattr(order, 'next_invoice_date', None)
        return end

    def _get_start_date(self, order):
        """Return subscription period start date."""
        order.ensure_one()
        return order.wink_requested_start_date or (order.date_order.date() if order.date_order else None)

    def classify_change(self, source_plan, target_plan):
        """RET-004: Classify upgrade vs downgrade by sequence.
        Returns 'upgrade' or 'downgrade' or None if same plan."""
        if not source_plan or not target_plan or source_plan.id == target_plan.id:
            return None
        src_seq = getattr(source_plan, 'sequence', 0) or 0
        tgt_seq = getattr(target_plan, 'sequence', 0) or 0
        if tgt_seq > src_seq:
            return 'upgrade'
        if tgt_seq < src_seq:
            return 'downgrade'
        return None

    def compute_proration(self, source_order, target_plan, effective_policy='immediate'):
        """RET-004: Compute proration for plan change.
        Formula: (monthly_price / 30) * remaining_days.
        Multi-service: uses Odoo Recurring Prices when available (per-product price);
        fallback: plan.monthly_std_price.

        Returns dict:
            remaining_days, current_monthly_std_price, target_monthly_std_price,
            proration_credit, proration_charge, net_amount, effective_date,
            currency, error (str or None)
        """
        source_order.ensure_one()
        target_plan.ensure_one()

        product = source_order.wink_source_product_id
        result = {
            'remaining_days': 0,
            'current_monthly_std_price': 0.0,
            'target_monthly_std_price': float(target_plan.monthly_std_price or 0),
            'proration_credit': 0.0,
            'proration_charge': 0.0,
            'net_amount': 0.0,
            'effective_date': None,
            'currency': source_order.currency_id,
            'error': None,
        }

        end_date = self._get_end_date(source_order)
        today = date.today()
        if not end_date or end_date <= today:
            result['error'] = _('No active subscription period remaining.')
            return result

        remaining_days = (end_date - today).days
        result['remaining_days'] = remaining_days

        source_plan = source_order.wink_plan_id
        if not source_plan:
            group = product and product.wink_subscription_group_id
            if group and group.plan_ids:
                source_plan = group.plan_ids.sorted('sequence')[:1]

        # Resolve monthly prices: Odoo pricing (per service) first, else plan.monthly_std_price
        current_monthly, _ = self._resolve_monthly_price_for_proration(source_order, source_plan, product, pricing_record=None)
        target_pricing, _ = self._resolve_plan_pricing_record(product, target_plan)
        target_monthly, _ = self._resolve_monthly_price_for_proration(source_order, target_plan, product, pricing_record=target_pricing)

        result['current_monthly_std_price'] = current_monthly
        result['target_monthly_std_price'] = target_monthly

        currency = source_order.currency_id
        daily_current = current_monthly / 30.0
        daily_target = target_monthly / 30.0
        proration_credit = currency.round(daily_current * remaining_days)
        proration_charge = currency.round(daily_target * remaining_days)
        result['proration_credit'] = proration_credit
        result['proration_charge'] = proration_charge
        result['net_amount'] = currency.round(proration_charge - proration_credit)

        if effective_policy == 'immediate':
            result['effective_date'] = today
        else:
            result['effective_date'] = end_date

        return result

    def validate_policy(self, source_order, target_plan, change_type):
        """RET-004, RET-009: Validate policy allows change.
        Returns (ok: bool, user_message: str).
        Blocks: pending change exists, cancellation requested, min_days, allow_*."""
        source_order.ensure_one()
        policy = source_order._wink_get_policy()
        if not policy:
            return True, ''

        if change_type == 'upgrade' and not policy.allow_upgrade:
            return False, _('Upgrades are not allowed for this subscription.')
        if change_type == 'downgrade' and not policy.allow_downgrade:
            return False, _('Downgrades are not allowed for this subscription.')

        remaining = source_order._wink_remaining_days()
        min_days = int(policy.min_days_before_change or 0)
        # min_days applies only during an active period; when remaining <= 0, allow
        if min_days > 0 and remaining > 0 and remaining < min_days:
            return False, _(
                'Plan changes require at least %s days before the end of the current period. You have %s days remaining.'
            ) % (min_days, remaining)

        # RET-009: Block if pending change exists
        pending = self.env['sale.order'].sudo().search([
            ('wink_change_from_order_id', '=', source_order.id),
            ('state', 'in', ['draft', 'sent']),
        ], limit=1)
        if pending:
            return False, _('A plan change request is already pending. Please wait for coordinator approval.')

        # RET-009: Block if cancellation requested
        if getattr(source_order, 'wink_cancellation_requested', False):
            return False, _('Cannot change plan while a cancellation request is pending.')

        return True, ''

    def create_plan_change_order(
        self,
        source_order,
        target_plan,
        change_type,
        proration_credit,
        proration_charge,
        effective_date,
        pricing_record=None,
        recurrence_id=None,
    ):
        """RET-004: Create new sale.order for plan change.
        Sets wink_change_from_order_id, wink_change_type, proration fields.
        message_post on both source and new order."""
        source_order.ensure_one()
        target_plan.ensure_one()

        product = source_order.wink_source_product_id
        if not product:
            raise ValueError(_('Source order has no product.'))

        variant = product.product_variant_id
        price_unit = 0.0
        if pricing_record and getattr(pricing_record, 'exists', lambda: False)() and pricing_record.exists():
            price_unit = getattr(pricing_record, 'price', None) or getattr(pricing_record, 'recurring_price', None) or 0
        price_unit = float(price_unit or 0)

        net = proration_charge - proration_credit
        if net > 0:
            price_unit = float(source_order.currency_id.round(price_unit + net))
        elif net < 0:
            price_unit = max(0, float(source_order.currency_id.round(price_unit + net)))

        line_vals = {
            'product_id': variant.id,
            'product_uom_qty': 1,
            'price_unit': price_unit,
            'name': product.name,
        }
        order_vals = {
            'partner_id': source_order.partner_id.id,
            'order_line': [(0, 0, line_vals)],
            'wink_is_portal_request': True,
            'wink_source_product_id': product.id,
            'wink_change_from_order_id': source_order.id,
            'wink_change_type': change_type,
            'wink_proration_credit': proration_credit,
            'wink_proration_charge': proration_charge,
            'wink_plan_change_target_plan_id': target_plan.id,
            'wink_plan_change_effective_date': effective_date,
            'wink_plan_id': target_plan.id,
            'origin': 'WINK Portal — Plan Change',
        }
        if recurrence_id and 'recurrence_id' in self.env['sale.order']._fields:
            order_vals['recurrence_id'] = recurrence_id
        if 'is_subscription' in self.env['sale.order']._fields:
            order_vals['is_subscription'] = True
        if pricing_record and getattr(pricing_record, 'id', None):
            order_vals['wink_recurring_pricing_id'] = pricing_record.id

        order = self.env['sale.order'].sudo().create(order_vals)

        target_label = target_plan.name or str(target_plan.id)
        source_order.sudo().message_post(
            body=_(
                "Plan change requested: %(change_type)s to %(target)s. "
                "New request: <a href='/my/requests/%(new_id)s'>%(new_name)s</a>"
            ) % {
                'change_type': change_type,
                'target': target_label,
                'new_id': order.id,
                'new_name': order.name,
            },
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        order.sudo().message_post(
            body=_(
                "Plan change from <a href='/my/requests/%(old_id)s'>%(old_name)s</a>. "
                "Proration credit: %(credit)s, charge: %(charge)s."
            ) % {
                'old_id': source_order.id,
                'old_name': source_order.name,
                'credit': proration_credit,
                'charge': proration_charge,
            },
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return order

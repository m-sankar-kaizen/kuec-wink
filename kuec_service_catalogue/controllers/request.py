# -*- coding: utf-8 -*-
# RET-005, RET-008, RET-009
from datetime import date
from odoo import http, _
from odoo.http import request
from werkzeug.exceptions import NotFound
from odoo.addons.sale.controllers.portal import CustomerPortal
import werkzeug.urls


def _get_product_pricing_browse(env, ids=None):
    """Return product.pricing recordset or a sentinel that .exists() is False when model is not installed."""
    try:
        return env['product.pricing'].sudo().browse(ids or [])
    except KeyError:
        return _EmptyPricing()


class _EmptyPricing:
    """Sentinel when product.pricing model is not installed (e.g. subscription addon not present)."""

    def exists(self):
        return False

    def __bool__(self):
        return False


class WinkRequest(http.Controller):

    def _parse_product_id(self, value):
        """Parse product_id from request; returns int or None on invalid."""
        if not value:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_request_form_vals(self, product, errors=None, post=None):
        """Build template values for wink_request_form (used by new_request and on validation error)."""
        employees = request.env['kuec.employee.directory'].sudo().search([
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)
        ])
        vals = {
            'product': product,
            'employees': employees,
            'show_registration_banner': False,
            'wink_is_bundle': False,
            'errors': errors or {},
            'post': post or {},
        }
        if product.commercial_structure == 'bundled' and product.wink_bundle_id:
            bundle = product.wink_bundle_id
            tiers = bundle.tier_ids.sorted('sequence')
            tier_data = []
            for tier in tiers:
                tier_data.append({'tier': tier, 'items': tier.item_ids.sorted('sequence')})
            vals.update({'wink_is_bundle': True, 'bundle': bundle, 'tier_data': tier_data})

        # Plan selection: Odoo subscription only (Recurring Prices tab)
        recurring_lines = product._wink_recurring_plan_lines()
        if recurring_lines:
            vals['recurring_plan_lines'] = recurring_lines
            vals['use_recurring_prices'] = True

        is_sub = bool(getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer')
        vals['is_subscription_service'] = is_sub
        if is_sub:
            subscription_plans = product._wink_subscription_plans_dicts(pricelist_id=False)
            vals['subscription_plans'] = subscription_plans
            vals['selected_plan'] = None  # bundles must NOT pre-select

            if product.commercial_structure == 'bundled':
                # Build billing_cycles (unique recurring plans, ordered by duration)
                seen_cycles = {}
                billing_cycles = []
                for p in subscription_plans:
                    rid = p.get('recurrence_id')
                    if rid and rid not in seen_cycles:
                        seen_cycles[rid] = True
                        billing_cycles.append({
                            'recurrence_id': rid,
                            'recurrence_id_str': str(rid),
                            'name': p.get('plan_name', ''),
                            'period_label': p.get('period_label', ''),
                        })
                # pricing_matrix keyed by "recurrence_id|variant_id" -> plan dict
                pricing_matrix = {}
                for p in subscription_plans:
                    rid = p.get('recurrence_id')
                    vid = p.get('variant_id')
                    if rid:
                        if vid:
                            pricing_matrix['%s|%s' % (rid, vid)] = p
                        # Also index by variant attribute names (lowercase) for robust matching
                        for attr_name in p.get('variant_attribute_names', []):
                            pricing_matrix['%s|%s' % (rid, attr_name.lower().strip())] = p
                vals['billing_cycles'] = billing_cycles
                vals['pricing_matrix'] = pricing_matrix
        return vals

    @http.route(['/services/<int:service_id>/request'], type='http', auth='user', website=True)
    def service_request_form(self, service_id, **kwargs):
        """GET: Show request form with plan pre-selected from ?plan=<recurrence_id>. Validates plan; defaults to first if invalid."""
        product = request.env['product.template'].sudo().search([
            ('id', '=', service_id),
            ('available_on_wink', '=', True),
        ], limit=1)
        if not product:
            raise NotFound()
        # Edge case 10.3: already has active subscription for this service
        # UI-BUG-005e (FB-005.7): Exclude cancelled so user can submit new request after cancel
        if getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer':
            Order = request.env['sale.order'].sudo()
            partner = request.env.user.partner_id.commercial_partner_id
            active = Order.search([
                ('partner_id', 'child_of', partner.id),
                ('state', '!=', 'cancel'),
                ('is_subscription', '=', True),
                ('subscription_state', '=', '3_progress'),
                ('order_line.product_id.product_tmpl_id', '=', product.id),
            ], limit=1)
            if active:
                # Pre-compute policy flags and enforce min_days_before_change (effective date policy)
                _allow_upgrade = True
                _allow_downgrade = True
                _allow_cancel = True
                _min_days = 0
                _change_disallowed_message = ''
                try:
                    policy = active._wink_get_policy()
                    if policy:
                        _min_days = int(policy.min_days_before_change or 0)
                        remaining = active._wink_remaining_days()
                        if _min_days > 0 and remaining < _min_days:
                            _allow_upgrade = False
                            _allow_downgrade = False
                            _allow_cancel = False
                            _change_disallowed_message = _(
                                'Plan changes and cancellation require at least %s days before the end of the current period. You have %s days remaining.'
                            ) % (_min_days, remaining)
                        else:
                            _allow_upgrade = bool(policy.allow_upgrade)
                            _allow_downgrade = bool(policy.allow_downgrade)
                            _allow_cancel = bool(policy.allow_cancellation)
                except Exception:
                    pass
                return request.render('kuec_service_catalogue.wink_request_already_subscription', {
                    'product': product,
                    'order': active,
                    'allow_upgrade': _allow_upgrade,
                    'allow_downgrade': _allow_downgrade,
                    'allow_cancel': _allow_cancel,
                    'min_days_notice': _min_days,
                    'change_disallowed_message': _change_disallowed_message,
                })

        # Phase 2: One-Time request frequency guard
        if product.request_frequency == 'one_time':
            Order = request.env['sale.order'].sudo()
            partner = request.env.user.partner_id.commercial_partner_id
            # 1. Check for existing confirmed orders or active requests
            existing = Order.search([
                ('partner_id', 'child_of', partner.id),
                ('state', 'not in', ['cancel']),
                ('order_line.product_id.product_tmpl_id', '=', product.id),
            ], limit=1)
            
            # 2. Check for bundle entitlements (available or activated)
            if not existing:
                Entitlement = request.env['wink.bundle.entitlement'].sudo()
                ent = Entitlement.search([
                    ('order_id.partner_id', 'child_of', partner.id),
                    ('order_id.state', 'not in', ['draft', 'sent', 'cancel']),
                    ('service_product_id', '=', product.id),
                ], limit=1)
                if ent:
                    existing = ent.order_id
            
            if existing:
                return request.render('kuec_service_catalogue.wink_request_already_requested', {
                    'product': product,
                    'order': existing,
                })
        pricing_param = kwargs.get('pricing_id') or kwargs.get('plan')
        pricing_id = None
        if pricing_param is not None:
            try:
                pricing_id = int(pricing_param)
            except (TypeError, ValueError):
                pricing_id = None
        subscription_plans = product._wink_subscription_plans_dicts(pricelist_id=False)
        selected_plan = None
        if subscription_plans:
            if pricing_id is not None:
                for p in subscription_plans:
                    if p.get('pricing_id') == pricing_id or p['recurrence_id'] == pricing_id:
                        selected_plan = p
                        break
            if not selected_plan:
                selected_plan = subscription_plans[0]
        vals = self._get_request_form_vals(product, errors={}, post=kwargs)
        vals['is_subscription_service'] = bool(getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer')
        vals['subscription_plans'] = subscription_plans
        vals['selected_plan'] = selected_plan
        vals['post'] = dict(kwargs, selected_pricing_id=selected_plan['pricing_id'] if selected_plan else None)
        return request.render('kuec_service_catalogue.wink_request_form', vals)

    def _wizard_draft_key(self):
        return 'wink_request_wizard_draft'

    def _wizard_get_draft(self):
        return request.session.get(self._wizard_draft_key()) or {}

    def _wizard_set_draft(self, data):
        request.session[self._wizard_draft_key()] = data

    def _wizard_clear_draft(self):
        request.session.pop(self._wizard_draft_key(), None)

    @http.route('/my/requests/new', type='http', auth='public', website=True, methods=['GET', 'POST'])
    def new_request(self, product_id=None, **kwargs):
        # CR-1: Wizard steps 0–3; step=0 = choose service (no product_id required when authenticated)
        step = kwargs.get('step')
        if step is not None:
            try:
                step = int(step)
            except (TypeError, ValueError):
                step = None
        is_post = request.httprequest.method == 'POST'
        next_step = kwargs.get('next_step') if is_post else None

        # POST: save draft and redirect to next step
        if is_post and next_step:
            try:
                next_step = int(next_step)
            except (TypeError, ValueError):
                next_step = None
            pid = self._parse_product_id(kwargs.get('product_id') or request.httprequest.form.get('product_id'))
            if next_step == 2 and pid:
                _tier_kw = kwargs.get('tier_id', '')
                _tier_form = request.httprequest.form.get('tier_id', '')
                _pricing_kw = kwargs.get('selected_pricing_id', '')
                _pricing_form = request.httprequest.form.get('selected_pricing_id', '')
                import logging
                _logger = logging.getLogger('wink.wizard.debug')
                _logger.info(
                    'WIZARD STEP1→2 POST: tier_id(kw=%s, form=%s) pricing(kw=%s, form=%s) all_form_keys=%s',
                    _tier_kw, _tier_form, _pricing_kw, _pricing_form,
                    list(request.httprequest.form.keys())
                )
                draft = {
                    'product_id': pid,
                    'start_date': kwargs.get('start_date') or request.httprequest.form.get('start_date') or '',
                    'notes': kwargs.get('notes') or request.httprequest.form.get('notes') or '',
                    'selected_pricing_id': _pricing_kw or _pricing_form or '',
                    'tier_id': _tier_kw or _tier_form or '',
                    'change_from_id': kwargs.get('change_from_id') or request.httprequest.form.get('change_from_id') or '',
                }
                self._wizard_set_draft(draft)
                # UI-BUG-003 (FB-003): Skip Employees step when product does not require employee selection
                product_for_skip = request.env['product.template'].sudo().search([
                    ('id', '=', pid), ('available_on_wink', '=', True)
                ], limit=1)
                if product_for_skip and not product_for_skip.requires_employee_selection:
                    draft['employee_ids'] = []
                    self._wizard_set_draft(draft)
                    return request.redirect('/my/requests/new?product_id=%s&step=3' % pid)
                return request.redirect('/my/requests/new?product_id=%s&step=2' % pid)
            if next_step == 3 and pid:
                employee_ids = request.httprequest.form.getlist('employee_ids')
                employee_ids = [int(e) for e in employee_ids if str(e).isdigit()]
                draft = self._wizard_get_draft()
                draft['employee_ids'] = employee_ids
                draft['product_id'] = pid
                self._wizard_set_draft(draft)
                return request.redirect('/my/requests/new?product_id=%s&step=3' % pid)
            if next_step and next_step not in (2, 3):
                next_step = None

        # No product_id: show step 0 (choose service) only when authenticated
        if not product_id:
            if request.env.user._is_public():
                return request.redirect('/web/login?redirect=%s' % werkzeug.urls.url_quote('/my/requests/new'))
            # Step 0: service grid (optional search)
            Product = request.env['product.template'].sudo()
            domain = [
                ('available_on_wink', '=', True),
                ('sale_ok', '=', True),
                ('active', '=', True),
            ]
            search = kwargs.get('search')
            if search:
                domain.append(('name', 'ilike', search))
            products = Product.search(domain)
            short_descs = {}
            for p in products:
                if p.wink_description:
                    text = html2plaintext(p.wink_description).strip()
                    short_descs[p.id] = text[:117] + '...' if len(text) > 120 else text
                else:
                    short_descs[p.id] = ''
            product_dept_slugs = {}
            for p in products:
                if p.department_ids:
                    slug = p.department_ids[0].name.lower().replace(' ', '-').replace('&', 'and')
                    product_dept_slugs[p.id] = slug
                else:
                    product_dept_slugs[p.id] = ''
            return request.render('kuec_service_catalogue.wink_request_wizard', {
                'step': 0,
                'products': products,
                'short_descs': short_descs,
                'product_dept_slugs': product_dept_slugs,
                'search': kwargs.get('search'),
            })

        pid = self._parse_product_id(product_id)
        if pid is None:
            return request.redirect('/services')

        product = request.env['product.template'].sudo().search([
            ('id', '=', pid),
            ('available_on_wink', '=', True)
        ], limit=1)

        if not product:
            return request.redirect('/services')

        # Default step=1 when product_id present
        if step is None:
            step = 1
        if step not in (1, 2, 3):
            step = 1

        # UI-BUG-003 (FB-003): Redirect from step 2 to step 3 when product does not require employees
        # Phase 6: Also skip for all bundles (employees selected at activation)
        is_bundle_config = (product.commercial_structure == 'bundled' or getattr(product, 'wink_is_bundle', False))
        if step == 2 and product and (not product.requires_employee_selection or is_bundle_config):
            draft = self._wizard_get_draft()
            if not draft.get('employee_ids'):
                draft['employee_ids'] = []
            draft['product_id'] = product.id
            self._wizard_set_draft(draft)
            return request.redirect('/my/requests/new?product_id=%s&step=3' % product.id)

        if not request.env.user._is_public():
            # User is authenticated
            employees = request.env['kuec.employee.directory'].sudo().search([
                ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)
            ])

            # change_from: ID of existing retainer order being upgraded/downgraded
            # Parse early so we can bypass the "already subscribed" guard when this is set
            change_from_id = None
            change_from_order = None
            change_from_plan_label = ''
            try:
                change_from_id = int(kwargs.get('change_from') or 0) or None
            except (TypeError, ValueError):
                change_from_id = None
            if change_from_id:
                partner = request.env.user.partner_id.commercial_partner_id
                change_from_order = request.env['sale.order'].sudo().search([
                    ('id', '=', change_from_id),
                    ('partner_id', 'child_of', partner.id),
                    ('wink_is_portal_request', '=', True),
                ], limit=1)
                if not change_from_order:
                    change_from_id = None
                else:
                    # Enforce policy: plan change allowed (upgrade/downgrade) and min_days_before_change
                    allowed_change, change_msg = change_from_order._wink_can_request_plan_change()
                    if not allowed_change:
                        return request.redirect(
                            '/my/requests/%s?error=change_not_allowed&message=%s'
                            % (change_from_order.id, werkzeug.urls.url_quote(change_msg or ''))
                        )
                    # Pre-compute plan label safely
                    try:
                        pricing_id = change_from_order.wink_recurring_pricing_id
                        if pricing_id:
                            pricing = _get_product_pricing_browse(request.env, [pricing_id])
                            if pricing.exists():
                                change_from_plan_label = (
                                    getattr(getattr(pricing, 'recurrence_id', None), 'name', None)
                                    or getattr(pricing, 'name', None)
                                    or ''
                                )
                    except Exception:
                        change_from_plan_label = ''

            # Edge case 10.3: already has active retainer for this service
            # UI-BUG-005e (FB-005.7): Exclude cancelled orders so new request after cancel is allowed
            if not change_from_id and (getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer'):
                partner_chk = request.env.user.partner_id.commercial_partner_id
                active_sub = request.env['sale.order'].sudo().search([
                    ('partner_id', 'child_of', partner_chk.id),
                    ('state', '!=', 'cancel'),
                    ('is_subscription', '=', True),
                    ('subscription_state', '=', '3_progress'),
                    ('order_line.product_id.product_tmpl_id', '=', product.id),
                ], limit=1)
                if active_sub:
                    _allow_upgrade = True
                    _allow_downgrade = True
                    _allow_cancel = True
                    _min_days = 0
                    _change_disallowed_message = ''
                    try:
                        policy = active_sub._wink_get_policy()
                        if policy:
                            _min_days = int(policy.min_days_before_change or 0)
                            remaining = active_sub._wink_remaining_days()
                            if _min_days > 0 and remaining < _min_days:
                                _allow_upgrade = False
                                _allow_downgrade = False
                                _allow_cancel = False
                                _change_disallowed_message = _(
                                    'Plan changes and cancellation require at least %s days before the end of the current period. You have %s days remaining.'
                                ) % (_min_days, remaining)
                            else:
                                _allow_upgrade = bool(policy.allow_upgrade)
                                _allow_downgrade = bool(policy.allow_downgrade)
                                _allow_cancel = bool(policy.allow_cancellation)
                    except Exception:
                        pass
                    return request.render('kuec_service_catalogue.wink_request_already_subscription', {
                        'product': product,
                        'order': active_sub,
                        'allow_upgrade': _allow_upgrade,
                        'allow_downgrade': _allow_downgrade,
                        'allow_cancel': _allow_cancel,
                        'min_days_notice': _min_days,
                        'change_disallowed_message': _change_disallowed_message,
                    })

            # Story 1.12 — proration and policy for upgrade/downgrade
            change_proration = None          # dict from _compute_remaining_credit or None
            change_policy = None             # wink.subscription.group record or None
            change_policy_allow_upgrade = True
            change_policy_allow_downgrade = True
            change_policy_allow_cancellation = True
            change_policy_credit_label = ''
            change_policy_effective_label = ''
            if change_from_order:
                try:
                    change_policy = change_from_order._wink_get_policy()
                    if change_policy:
                        change_policy_allow_upgrade = change_policy.allow_upgrade
                        change_policy_allow_downgrade = change_policy.allow_downgrade
                        change_policy_allow_cancellation = change_policy.allow_cancellation
                        credit_sel = dict(change_policy._fields['downgrade_credit_policy'].selection)
                        cancel_sel = dict(change_policy._fields['cancellation_credit_policy'].selection)
                        change_policy_credit_label = credit_sel.get(change_policy.downgrade_credit_policy, '')
                        change_policy_effective_label = dict(
                            change_policy._fields['effective_date_policy'].selection
                        ).get(change_policy.effective_date_policy, '')
                except Exception:
                    change_policy = None
                try:
                    change_proration = change_from_order._wink_compute_proration()
                except Exception:
                    change_proration = None

            wizard_draft = self._wizard_get_draft() if step in (1, 2, 3) else {}
            post_data = dict(kwargs)
            if wizard_draft and step in (1, 2, 3):
                post_data.update({k: v for k, v in wizard_draft.items() if v and k != 'employee_ids'})
            # CR-6: review step display (type_label, tier_name, plan_name, employee_names)
            # CR-6: review step display (type_label, tier_name, plan_name, employee_names, price_str)
            review_display = {
                'type_label': '', 
                'tier_name': '', 
                'plan_name': '', 
                'employee_names': [],
                'price_str': '',
                'currency_symbol': 'AED',
            }
            if step == 3 and wizard_draft:
                wink_is_bundle = (product.commercial_structure == 'bundled' or getattr(product, 'wink_is_bundle', False)) and product.wink_bundle_id
                if wink_is_bundle:
                    review_display['type_label'] = 'Bundle'
                    tier_id = wizard_draft.get('tier_id')
                    if tier_id:
                        try:
                            tier = request.env['wink.bundle.tier'].sudo().browse(int(tier_id))
                            review_display['tier_name'] = tier.name if tier.exists() else ''
                        except Exception:
                            review_display['tier_name'] = ''
                    else:
                        review_display['tier_name'] = ''
                    
                    # UI-013: Map plan name and price for bundles
                    rec_id = wizard_draft.get('selected_pricing_id') or wizard_draft.get('bundle_recurrence_id')
                    if rec_id:
                        try:
                            plan_found = False
                            # 1. Try native subscription plans
                            plans = product._wink_subscription_plans_dicts(pricelist_id=False)
                            for p in (plans or []):
                                if str(p.get('pricing_id')) == str(rec_id) or str(p.get('recurrence_id')) == str(rec_id):
                                    review_display['plan_name'] = p.get('plan_name', '')
                                    review_display['price_str'] = p.get('price_str') or '{:,.2f}'.format(p.get('price', 0.0))
                                    review_display['currency_symbol'] = p.get('currency_symbol', 'AED')
                                    plan_found = True
                                    break
                            # 2. Try fallback group plans
                            if not plan_found and product.wink_subscription_group_id:
                                for p in product.wink_subscription_group_id.plan_ids:
                                    if str(p.id) == str(rec_id):
                                        review_display['plan_name'] = p.name
                                        months = 1
                                        nl = p.name.lower()
                                        if 'annual' in nl or 'year' in nl: months = 12
                                        elif 'quarter' in nl: months = 3
                                        tier_id = wizard_draft.get('tier_id')
                                        t_price = 0.0
                                        if tier_id:
                                            tier = request.env['wink.bundle.tier'].sudo().browse(int(tier_id))
                                            t_price = tier.price if tier.exists() else 0.0
                                        price = float(p.monthly_std_price or t_price or 0.0) * months
                                        review_display['price_str'] = '{:,.2f}'.format(price)
                                        review_display['currency_symbol'] = 'AED'
                                        break
                        except Exception:
                            pass
                else:
                    review_display['tier_name'] = ''
                    if getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer':
                        review_display['type_label'] = 'Retainer'
                        rec_id = wizard_draft.get('selected_pricing_id')
                        plan_name = ''
                        price_str = ''
                        try:
                            plans = product._wink_subscription_plans_dicts(pricelist_id=False)
                            for p in (plans or []):
                                if str(p.get('pricing_id')) == str(rec_id) or str(p.get('recurrence_id')) == str(rec_id):
                                    plan_name = p.get('plan_name', '')
                                    price_str = '{:,.2f}'.format(p.get('price', 0.0))
                                    review_display['currency_symbol'] = p.get('currency_symbol', 'AED')
                                    break
                        except Exception:
                            pass
                        review_display['plan_name'] = plan_name
                        review_display['price_str'] = price_str
                    else:
                        review_display['type_label'] = 'One-time'
                        review_display['plan_name'] = ''
                        price = product.list_price or 0.0
                        review_display['price_str'] = '{:,.2f}'.format(price)
                        review_display['currency_symbol'] = request.website.currency_id.symbol if request.website else request.env.company.currency_id.symbol if request.env.company else 'AED'
                emp_ids = wizard_draft.get('employee_ids') or []
                if emp_ids:
                    emps = request.env['kuec.employee.directory'].sudo().browse(emp_ids)
                    review_display['employee_names'] = [e.name for e in emps if e.exists()]
                else:
                    review_display['employee_names'] = []
            render_vals = {
                'product': product,
                'employees': employees,
                'show_registration_banner': kwargs.get('registered') == '1',
                'wink_is_bundle': False,
                'errors': {},
                'post': post_data,
                'step': step,
                'wizard_draft': wizard_draft,
                'review_display': review_display,
                'change_from_id': change_from_id,
                'change_from_order': change_from_order,
                'change_from_plan_label': change_from_plan_label,
                # Story 1.12 proration + policy
                'change_proration': change_proration,
                'change_policy_allow_upgrade': change_policy_allow_upgrade,
                'change_policy_allow_downgrade': change_policy_allow_downgrade,
                'change_policy_allow_cancellation': change_policy_allow_cancellation,
                'change_policy_credit_label': change_policy_credit_label,
                'change_policy_effective_label': change_policy_effective_label,
            }

            # Bundle tier data; UI-BUG-005f (FB-005.8): bundle total for selected tier
            is_bundle_config = (product.commercial_structure == 'bundled' or getattr(product, 'wink_is_bundle', False))
            if is_bundle_config and product.wink_bundle_id:
                bundle = product.wink_bundle_id
                tiers = bundle.tier_ids.sorted('sequence')
                tier_data = []
                for tier in tiers:
                    tier_data.append({
                        'tier': tier,
                        'items': tier.item_ids.sorted('sequence'),
                    })
                post_tier_id = post_data.get('tier_id')
                selected_tier_for_total = None
                if tier_data and post_tier_id:
                    for td in tier_data:
                        if str(td['tier'].id) == str(post_tier_id):
                            selected_tier_for_total = td['tier']
                            break
                if not selected_tier_for_total and tier_data:
                    selected_tier_for_total = tier_data[0]['tier']
                render_vals.update({
                    'wink_is_bundle': True,
                    'bundle': bundle,
                    'tier_data': tier_data,
                    'bundle_total_tier': selected_tier_for_total,
                })
            # Plan selection: Odoo subscription only (Recurring Prices tab)
            recurring_lines = product._wink_recurring_plan_lines()
            if recurring_lines:
                render_vals['recurring_plan_lines'] = recurring_lines
                render_vals['use_recurring_prices'] = True

            is_sub = bool(getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer')
            render_vals['is_subscription_service'] = is_sub
            if is_sub:
                subscription_plans = product._wink_subscription_plans_dicts(pricelist_id=False)
                render_vals['subscription_plans'] = subscription_plans
                render_vals['selected_plan'] = None  # bundles never pre-select

                if is_bundle_config:
                    seen_cycles = {}
                    billing_cycles = []
                    pricing_matrix = {}
                    
                    if not subscription_plans and product.wink_subscription_group_id:
                        # Fallback: construct cycles and matrix from Group plans and Tier legacy prices
                        for p in product.wink_subscription_group_id.plan_ids:
                            billing_cycles.append({
                                'recurrence_id': p.id,
                                'recurrence_id_str': str(p.id),
                                'name': p.name,
                                'period_label': '/' + p.name.lower(),
                            })
                            if tier_data:
                                for td in tier_data:
                                    tier = td['tier']
                                    vid = str(tier.product_variant_id.id) if tier.product_variant_id else 'None'
                                    months = 1
                                    name_lower = p.name.lower()
                                    if 'annual' in name_lower or 'year' in name_lower:
                                        months = 12
                                    elif 'quarter' in name_lower:
                                        months = 3
                                    
                                    price = float(p.monthly_std_price or tier.price or 0.0) * months
                                    
                                    fake_plan = {
                                        'plan_name': p.name,
                                        'price': price,
                                        'price_str': '{:,.2f}'.format(price),
                                        'period_label': '/' + p.name.lower(),
                                        'currency_symbol': 'AED',
                                        'pricing_id': p.id,
                                        'recurrence_id': p.id, # needed for JS matching
                                    }
                                    if vid != 'None':
                                        pricing_matrix['%s|%s' % (p.id, vid)] = fake_plan
                                    pricing_matrix['%s|%s' % (p.id, tier.name.lower().strip())] = fake_plan
                    else:
                        for p in subscription_plans:
                            rid = p.get('recurrence_id')
                            if rid and rid not in seen_cycles:
                                seen_cycles[rid] = True
                                billing_cycles.append({
                                    'recurrence_id': rid,
                                    'recurrence_id_str': str(rid),
                                    'name': p.get('plan_name', ''),
                                    'period_label': p.get('period_label', ''),
                                })
                        for p in subscription_plans:
                            rid = p.get('recurrence_id')
                            vid = p.get('variant_id')
                            if rid:
                                if vid:
                                    pricing_matrix['%s|%s' % (rid, vid)] = p
                                # Also index by variant attribute names (lowercase) for robust matching
                                for attr_name in p.get('variant_attribute_names', []):
                                    pricing_matrix['%s|%s' % (rid, attr_name.lower().strip())] = p
                    
                    render_vals['billing_cycles'] = billing_cycles
                    render_vals['pricing_matrix'] = pricing_matrix
                    
                    # Pre-identify cycles for the toggle
                    monthly = None
                    annual = None
                    for c in billing_cycles:
                        name = (c.get('name') or '').lower()
                        if 'month' in name:
                            monthly = c
                        elif 'annual' in name or 'year' in name:
                            annual = c
                    if not monthly and billing_cycles:
                        monthly = billing_cycles[0]
                    render_vals['monthly_cycle'] = monthly
                    render_vals['annual_cycle'] = annual
                    if not render_vals.get('selected_plan') and subscription_plans:
                        render_vals['selected_plan'] = subscription_plans[0]

            return request.render('kuec_service_catalogue.wink_request_form', render_vals)
        else:
            # User is anonymous
            return request.render('kuec_service_catalogue.wink_registration_form', {
                'product': product,
                'errors': {},
                'post': kwargs
            })

    @http.route('/my/requests/register/thanks', type='http', auth='public', website=True)
    def register_thanks(self, redirect=None, **kwargs):
        """UI-BUG-002 (FB-002): Thank-you page after registration so user is not sent to login
        and prompted to sign up again (avoids duplicate data entry)."""
        login_url = '/web/login'
        if redirect:
            login_url = f"/web/login?redirect={werkzeug.urls.url_quote(redirect)}"
        return request.render('kuec_service_catalogue.wink_register_thanks', {
            'redirect': redirect or '',
            'login_url': login_url,
        })

    @http.route('/my/requests/register', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def register_and_request(self, **post):
        product_id = post.get('product_id')
        pid = self._parse_product_id(product_id)
        product = request.env['product.template'].sudo().search([
            ('id', '=', pid),
            ('available_on_wink', '=', True)
        ], limit=1) if pid is not None else None

        if not product:
            return request.redirect('/services')

        errors = {}
        required_fields = ['company_name', 'contact_name', 'contact_email', 'contact_phone']
        for field in required_fields:
            if not post.get(field):
                errors[field] = _("This field is required.")

        if not errors:
            existing_partner = request.env['res.partner'].sudo().search([
                ('email', '=ilike', post.get('contact_email'))
            ], limit=1)

            if existing_partner:
                errors['contact_email'] = _("An account with this email already exists. Please sign in.")

        if errors:
            return request.render('kuec_service_catalogue.wink_registration_form', {
                'product': product,
                'errors': errors,
                'post': post
            })

        # Step 2 — Create company partner
        company = request.env['res.partner'].sudo().create({
            'name': post['company_name'],
            'is_company': True,
            'company_type': 'company',
            'email': post.get('company_email') or False,
            'trade_license_number': post.get('trade_license') or False,
            'tax_license_number': post.get('tax_license') or False,
        })

        # Step 3 — Save company type for classification (legal_entity_type matches form option values)
        company_type = post.get('company_type')
        if company_type:
            company.sudo().write({'legal_entity_type': company_type})

        # Step 4 — Create contact person
        contact = request.env['res.partner'].sudo().create({
            'name': post['contact_name'],
            'email': post['contact_email'],
            'phone': post['contact_phone'],
            'parent_id': company.id,
            'type': 'contact',
        })

        # Step 5 — Create portal user account
        portal_group = request.env.ref('base.group_portal')
        new_user = request.env['res.users'].sudo().create({
            'name': contact.name,
            'login': contact.email,
            'partner_id': contact.id,
            'groups_id': [(6, 0, [portal_group.id])],
        })

        # Step 6 — Send password reset email (uses branded WINK template with token)
        try:
            # signup_prepare generates the token and expiry date on the user/partner
            new_user.sudo().partner_id.signup_prepare()
            reset_url = new_user.sudo().partner_id.signup_url
            
            welcome_template = request.env.ref('kuec_service_catalogue.kuec_portal_welcome_email_v5', raise_if_not_found=False)
            if welcome_template:
                welcome_template.sudo().with_context(reset_url=reset_url).send_mail(new_user.partner_id.id, force_send=True)
            else:
                # Fallback to native if custom template missing
                new_user.sudo().action_reset_password()
        except Exception:
            pass  # Non-blocking: user can always reset later

        # Step 7 — UI-BUG-002 (FB-002): Redirect to thank-you page instead of login directly,
        # so user is not prompted to "sign up" again (avoids duplicate data entry confusion).
        redirect_url = werkzeug.urls.url_quote(
            f"/my/requests/new?product_id={post.get('product_id', '')}&registered=1"
        )
        return request.redirect(
            f"/my/requests/register/thanks?redirect={redirect_url}"
        )

    @http.route('/my/requests/submit', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def submit_request(self, **post):
        product_id = self._parse_product_id(post.get('product_id'))
        if product_id is None:
            return request.redirect('/services')
        product = request.env['product.template'].sudo().search([
            ('id', '=', product_id),
            ('available_on_wink', '=', True),
        ], limit=1)
        if not product:
            return request.redirect('/services')

        partner = request.env.user.partner_id.commercial_partner_id

        # Upgrade/downgrade: link new order to old retainer order
        change_from_id = None
        change_from_order = None
        try:
            change_from_id = int(post.get('change_from_id') or 0) or None
        except (TypeError, ValueError):
            change_from_id = None
        if change_from_id:
            change_from_order = request.env['sale.order'].sudo().search([
                ('id', '=', change_from_id),
                ('partner_id', 'child_of', partner.id),
                ('wink_is_portal_request', '=', True),
            ], limit=1)
            if not change_from_order:
                change_from_id = None

        from datetime import date
        notes = post.get('notes') or False
        start_date = post.get('start_date') or date.today().strftime('%Y-%m-%d')
        if start_date:
            try:
                from datetime import datetime
                datetime.strptime(start_date, '%Y-%m-%d')
            except (ValueError, TypeError):
                start_date = date.today().strftime('%Y-%m-%d')
        employee_ids = request.httprequest.form.getlist('employee_ids')
        employee_ids = [int(e) for e in employee_ids if str(e).isdigit()]

        wink_is_bundle = (
            (product.commercial_structure == 'bundled' or getattr(product, 'wink_is_bundle', False))
            and product.wink_bundle_id
        )

        tier = None
        try:
            tier_id = int(post.get('tier_id', 0))
        except (TypeError, ValueError):
            tier_id = 0
        if wink_is_bundle and tier_id:
            tier = request.env['wink.bundle.tier'].sudo().browse(tier_id)

        variant = product.product_variant_id
        if wink_is_bundle and getattr(tier, 'exists', lambda: False)() and tier.exists() and tier.product_variant_id:
            variant = tier.product_variant_id

        # Plan: Odoo subscription only (Recurring Prices)
        recurring_lines = product._wink_recurring_plan_lines()
        use_recurring_prices = bool(recurring_lines)
        is_subscription_service = bool(getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer')

        # v2: validate selected_pricing_id (from request form) — price always from server
        selected_pricing_id = None
        try:
            # Check both field names as they might vary between standalone and bundle forms
            selected_pricing_id = int(post.get('selected_pricing_id') or post.get('selected_recurrence_id') or 0) or None
        except (TypeError, ValueError):
            pass
        
        selected_recurrence_id = None
        # FIX: Allow processing selected_pricing_id even if product doesn't have direct recurring lines (e.g. bundle tiers)
        if (is_subscription_service or wink_is_bundle) and selected_pricing_id is not None:
            # Find pricing line by ID primarily
            pricing_line = None
            
            # If it's a bundle, the pricing lines might come from child services or related matrix
            # But we can try to browse it directly if we have the ID and it's a valid pricing model
            if not recurring_lines and wink_is_bundle:
                # For bundles, selected_pricing_id is expected to be a product.pricing or sale.subscription.pricing ID
                # We try to browse commonly used pricing models
                # WF-BUNDLE-PLAN-002: Add wink.subscription.plan to the list of models
                for model in ['product.pricing', 'sale.subscription.pricing', 'wink.subscription.plan']:
                    try:
                        p = request.env[model].sudo().browse(selected_pricing_id)
                        if p.exists():
                            pricing_line = p
                            break
                    except Exception:
                        continue
            else:
                for line in recurring_lines:
                    # If exact pricing match
                    if line.id == selected_pricing_id:
                        pricing_line = line
                        break
                    # Fallback to recurrence ID if legacy
                    rec_id = getattr(line, 'recurrence_id', getattr(line, 'plan_id', getattr(line, 'recurring_plan_id', None)))
                    if getattr(rec_id, 'id', rec_id) == selected_pricing_id:
                        pricing_line = line
                        break

            if pricing_line:
                selected_pricing = pricing_line
                # Force variant overwrite if pricing line maps to a specific variant
                if hasattr(selected_pricing, 'product_variant_ids') and selected_pricing.product_variant_ids:
                    if variant.id not in selected_pricing.product_variant_ids.ids:
                        variant = selected_pricing.product_variant_ids[0]
                elif getattr(selected_pricing, 'product_id', False) and selected_pricing.product_id.id != variant.id:
                    variant = selected_pricing.product_id
                    
                # WF-BUNDLE-PLAN-002: If pricing_line is wink.subscription.plan, it is the recurrence ref
                if getattr(pricing_line, '_name', None) == 'wink.subscription.plan':
                    recurrence_ref = pricing_line
                else:
                    recurrence_ref = getattr(pricing_line, 'recurrence_id', getattr(pricing_line, 'plan_id', getattr(pricing_line, 'recurring_plan_id', None)))
                selected_recurrence_id = getattr(recurrence_ref, 'id', recurrence_ref)
                selected_plan = recurrence_ref
            elif use_recurring_prices:
                # If it's a subscription but no valid plan found
                vals = self._get_request_form_vals(product, errors={'subscription_plan': _('Invalid plan selected — please choose a plan to continue.')}, post=post)
                vals['recurring_plan_lines'] = recurring_lines
                vals['use_recurring_prices'] = True
                vals['is_subscription_service'] = True
                vals['subscription_plans'] = product._wink_subscription_plans_dicts(pricelist_id=False)
                vals['selected_plan'] = vals['subscription_plans'][0] if vals['subscription_plans'] else None
                return request.render('kuec_service_catalogue.wink_request_form', vals)
        elif is_subscription_service and use_recurring_prices and not selected_pricing_id:
            # Plan required but not provided
            vals = self._get_request_form_vals(product, errors={'subscription_plan': _('Please select a billing plan to continue.')}, post=post)
            vals['recurring_plan_lines'] = recurring_lines
            vals['use_recurring_prices'] = True
            vals['is_subscription_service'] = True
            vals['subscription_plans'] = product._wink_subscription_plans_dicts(pricelist_id=False)
            vals['selected_plan'] = None
            return request.render('kuec_service_catalogue.wink_request_form', vals)

        # Validate selected plan/pricing (product.pricing or sale.subscription.plan) — legacy recurring_pricing_id
        # NOTE: only reset selected_plan/selected_pricing when the v2 recurrence_id path was NOT taken.
        # If selected_recurrence_id was provided, selected_pricing and selected_plan were already
        # set above (lines 345-346) and must NOT be overwritten here.
        if selected_recurrence_id is None:
            selected_plan = None
            selected_pricing = _get_product_pricing_browse(request.env)
        # UI-BUG-003 (FB-003): Require plan only for subscription/retainer, not for project-based
        if is_subscription_service and use_recurring_prices and selected_recurrence_id is None:
            try:
                chosen_id = int(post.get('recurring_pricing_id') or 0)
            except (TypeError, ValueError):
                chosen_id = 0
            if not chosen_id or (hasattr(recurring_lines, 'ids') and chosen_id not in recurring_lines.ids):
                vals = self._get_request_form_vals(product, errors={'subscription_plan': _('Please select a plan.')}, post=post)
                vals['recurring_plan_lines'] = recurring_lines
                vals['use_recurring_prices'] = True
                return request.render('kuec_service_catalogue.wink_request_form', vals)
            if getattr(recurring_lines, '_name', None) == 'sale.subscription.plan':
                selected_plan = request.env['sale.subscription.plan'].sudo().browse(chosen_id)
                if not selected_plan.exists():
                    selected_plan = None
            else:
                # Recurring lines are from a pricing model (product.pricing, sale.subscription.pricing, etc.)
                # Browse the chosen id on the same model as recurring_lines
                try:
                    pricing_model = getattr(recurring_lines, '_name', None)
                    if pricing_model and chosen_id in (recurring_lines.ids or []):
                        selected_pricing = request.env[pricing_model].sudo().browse(chosen_id)
                        if selected_pricing.exists():
                            selected_plan = getattr(selected_pricing, 'recurring_plan_id', None) or getattr(selected_pricing, 'plan_id', None) or getattr(selected_pricing, 'recurrence_id', None)
                    else:
                        selected_pricing = _get_product_pricing_browse(request.env, [chosen_id])
                        if selected_pricing.exists():
                            selected_plan = getattr(selected_pricing, 'recurring_plan_id', None) or getattr(selected_pricing, 'plan_id', None)
                except KeyError:
                    selected_pricing = _get_product_pricing_browse(request.env, [chosen_id])
                    if selected_pricing.exists():
                        selected_plan = getattr(selected_pricing, 'recurring_plan_id', None) or getattr(selected_pricing, 'plan_id', None)

        # Validation: employees required when product or child service requires selection
        # Phase 6: Only for standalone at this stage; bundles collect at activation
        if not wink_is_bundle:
            if product.requires_employee_selection and not employee_ids:
                vals = self._get_request_form_vals(product, errors={'employee_ids': _('Please select at least one employee for this service.')}, post=post)
                return request.render('kuec_service_catalogue.wink_request_form', vals)
        else:
            # Bundle: skip employee validation at request stage
            pass

        # variant is already determined above based on tier
        price_unit = variant.list_price if variant else product.list_price
        if wink_is_bundle and 'tier' in locals() and tier and getattr(tier, 'exists', lambda: False)() and tier.price:
            price_unit = tier.price

        if use_recurring_prices or wink_is_bundle:
            if getattr(recurring_lines, '_name', None) == 'sale.subscription.plan' and selected_plan:
                # Legacy sale.subscription.plan path
                price_unit = getattr(selected_plan, 'price', None) or getattr(selected_plan, 'list_price', None) or price_unit
                # v2: selected_pricing is the pricing record (product.pricing, sale.subscription.pricing, or wink.subscription.plan)
                # Odoo 18 often uses 'price' (related/computed) or 'recurring_price'
                price_unit = getattr(selected_pricing, 'price', 0.0) or getattr(selected_pricing, 'recurring_price', 0.0)
                
                # Fallback: if selected_pricing is wink.subscription.plan, normalize to the period
                if not price_unit and getattr(selected_pricing, '_name', None) == 'wink.subscription.plan':
                    months = 1
                    name_lower = selected_pricing.name.lower()
                    if 'annual' in name_lower or 'year' in name_lower:
                        months = 12
                    elif 'quarter' in name_lower:
                        months = 3
                    price_unit = float(selected_pricing.monthly_std_price or 0.0) * months
                
                price_unit = price_unit or getattr(selected_pricing, 'list_price', 0.0) or price_unit


        line_vals = {
            'product_id': variant.id,
            'product_uom_qty': 1,
            'price_unit': price_unit,
            'name': product.name,
        }

        order_vals = {
            'partner_id': partner.id,
            'order_line': [(0, 0, line_vals)],
            'wink_request_notes': notes,
            'wink_requested_start_date': start_date,
            'wink_is_portal_request': True,
            'wink_source_product_id': product.id,
            'origin': 'WINK Portal',
        }

        if product.wink_payment_term_id:
            order_vals['payment_term_id'] = product.wink_payment_term_id.id

        # Quote flow: when price is hidden or not set, create Quotation (draft) so coordinator
        # can set the price; only then can the customer see price and approve/reject/pay.
        price_not_set = price_unit is None or (isinstance(price_unit, (int, float)) and price_unit == 0)
        if product.price_visibility == 'hidden' or price_not_set:
            order_vals['wink_price_confirmed'] = False
        else:
            order_vals['wink_price_confirmed'] = True

        order = request.env['sale.order'].sudo().create(order_vals)

        # Upgrade/downgrade: link new order → old order and post chatter note on both
        if change_from_order:
            order.sudo().write({'wink_change_from_order_id': change_from_order.id})
            new_plan_label = ''
            try:
                if selected_recurrence_id and selected_pricing and getattr(selected_pricing, 'exists', lambda: False)() and selected_pricing.exists():
                    new_plan_label = getattr(getattr(selected_pricing, 'recurrence_id', None), 'name', None) or ''
            except Exception:
                pass
            change_from_order.sudo().message_post(
                body=_("Customer requested a plan change from this retainer. "
                       "New request: <a href='/my/requests/%(new_id)s'>%(new_name)s</a>%(plan_info)s") % {
                    'new_id': order.id,
                    'new_name': order.name,
                    'plan_info': f' — New plan: {new_plan_label}' if new_plan_label else '',
                },
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            order.sudo().message_post(
                body=_("This is a plan change request. Previous retainer: "
                       "<a href='/my/requests/%(old_id)s'>%(old_name)s</a>") % {
                    'old_id': change_from_order.id,
                    'old_name': change_from_order.name,
                },
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

        # Employees: for standalone set on order; for bundle set per entitlement below
        if not wink_is_bundle and employee_ids:
            order.sudo().wink_selected_employee_ids = [(6, 0, employee_ids)]

        # --- Set plan_id (sale.subscription.plan), recurrence_id, is_subscription, wink_recurring_pricing_id on order ---
        if use_recurring_prices or wink_is_bundle:
            if selected_plan and getattr(selected_plan, '_name', None) == 'sale.subscription.plan':
                write_vals = {}
                if hasattr(order, 'plan_id'):
                    write_vals['plan_id'] = selected_plan.id
                if hasattr(order, 'recurring_plan_id'):
                    write_vals['recurring_plan_id'] = selected_plan.id
                if write_vals:
                    order.sudo().write(write_vals)
                if order.order_line:
                    line = order.order_line[0]
                    if hasattr(line, 'plan_id'):
                        line.sudo().write({'plan_id': selected_plan.id})
                    elif hasattr(line, 'recurring_plan_id'):
                        line.sudo().write({'recurring_plan_id': selected_plan.id})
            # v2: Odoo 18 subscription — recurrence_id + is_subscription
            if selected_recurrence_id:
                sub_vals = {}
                is_fake_plan = getattr(selected_plan, '_name', None) == 'wink.subscription.plan'
                if hasattr(order, 'recurrence_id') and not is_fake_plan:
                    sub_vals['recurrence_id'] = selected_recurrence_id
                if hasattr(order, 'is_subscription'):
                    sub_vals['is_subscription'] = True
                if sub_vals:
                    order.sudo().write(sub_vals)
            if getattr(selected_pricing, 'exists', lambda: False)() and selected_pricing:
                order.sudo().write({'wink_recurring_pricing_id': selected_pricing.id})
            # RET-008: Set wink_plan_id for proration (match recurrence to group plan)
            group = product.wink_subscription_group_id
            if group and group.plan_ids and selected_recurrence_id:
                rec_name = ''
                try:
                    rec = getattr(selected_pricing, 'recurrence_id', None) or getattr(selected_pricing, 'plan_id', None)
                    if rec:
                        rec_name = (getattr(rec, 'name', None) or '').strip().lower()
                except Exception:
                    pass
                matched_plan = None
                for p in group.plan_ids:
                    hint = (p.recurrence_name_hint or '').strip().lower()
                    if hint and rec_name and hint in rec_name:
                        matched_plan = p
                        break
                    if p.pricing_model and p.pricing_id and getattr(selected_pricing, 'id', None) == p.pricing_id:
                        matched_plan = p
                        break
                if not matched_plan and group.plan_ids:
                    matched_plan = group.plan_ids.sorted('sequence')[:1]
                if matched_plan:
                    order.sudo().write({'wink_plan_id': matched_plan.id})

        # --- Bundle tier handling ---
        tier = None
        bundle_line = None

        if wink_is_bundle:
            try:
                tier_id = int(post.get('tier_id', 0))
            except (TypeError, ValueError):
                tier_id = 0
            tier = request.env['wink.bundle.tier'].sudo().browse(tier_id)
            if not tier.exists() or tier.bundle_id != product.wink_bundle_id:
                return request.redirect('/services')

            # Find the bundle product line and override name (keep price_unit native pricing)
            bundle_line = order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.id == product.id
            )[:1]
            if bundle_line:
                bundle_line_name = f"{variant.name}" if variant and variant.name != product.name else product.name
                
                bundle_line.sudo().write({
                    'name': f"{bundle_line_name} — {tier.name}",
                })
                # if pricing is not subscription and tier has legacy price and variant list_price is 0
                if not use_recurring_prices and tier.price and not (variant and variant.list_price):
                    bundle_line.sudo().write({
                        'price_unit': tier.price,
                    })

            # Save tier on order
            order.sudo().write({
                'wink_bundle_tier_id': tier.id,
            })

            # Create entitlement records (no SO lines yet —
            # real lines are created when customer activates).
            # Employees and documents are linked to each child service (entitlement).
            for idx, item in enumerate(tier.item_ids.sorted('sequence')):
                ent_vals = {
                    'order_id': order.id,
                    'tier_id': tier.id,
                    'service_product_id': item.service_product_id.id,
                    'name': (item.description
                             or item.service_product_id.name),
                    'sequence': item.sequence,
                    'qty_entitled': item.qty,
                }
                ent = request.env['wink.bundle.entitlement'].sudo().create(ent_vals)
                # Per–child-service employee selection (from form employee_ids_tierId_index)
                emp_ids = request.httprequest.form.getlist('employee_ids_%s_%s' % (tier.id, idx))
                emp_ids = [int(e) for e in emp_ids if str(e).isdigit()]
                if emp_ids:
                    ent.sudo().wink_selected_employee_ids = [(6, 0, emp_ids)]


        # Only auto-confirm when price is visible and set (customer can pay immediately).
        # When price is hidden or not set we keep the order as Quotation; coordinator sets
        # price and unlocks; then customer can approve/reject or pay.
        is_auto_confirm = order.wink_price_confirmed and (
            (product.commercial_structure == 'standalone' and product.request_frequency == 'one_time')
            or is_subscription_service
            or wink_is_bundle
        )
        if is_auto_confirm:
            try:
                order.sudo().action_confirm()
            except (ValueError, Exception) as e:
                # Odoo 18 bug: project template with 0 tasks causes ValueError
                # in project_task.create() — order is still created, coordinator
                # can confirm manually.
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning("Auto-confirm failed for order %s: %s", order.name, e)

        order.sudo().message_post(
            body=f"Service request submitted via WINK portal by {request.env.user.partner_id.name}.",
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        template = request.env.ref('kuec_service_catalogue.kuec_coordinator_notification_email_v5', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(order.id, force_send=True)
        customer_confirmation = request.env.ref('kuec_service_catalogue.kuec_request_confirmation_template', raise_if_not_found=False)
        if customer_confirmation:
            customer_confirmation.sudo().send_mail(order.id, force_send=True)

        # UI-013: Redirect with submitted=1 to show Request Submitted success block
        self._wizard_clear_draft()
        # Phase 6 & 7.1: If price is confirmed, redirect directly to WINK payment page
        if order.wink_price_confirmed:
            return request.redirect(f'/my/requests/{order.id}/pay')
        return request.redirect(f'/my/requests/{order.id}?submitted=1')

    @http.route('/my/requests/<int:order_id>', type='http', auth='user', website=True)
    def request_detail(self, order_id, **kwargs):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)

        if not order:
            raise NotFound()

        product = order.wink_source_product_id or (order.order_line[0].product_id.product_tmpl_id if order.order_line else False)

        # Document compliance: for bundle = child services' docs; for standalone = product's docs
        requirements = order._wink_document_requirements()
        submissions = request.env['kuec.document.submission'].sudo().search([
            ('order_id', '=', order_id)
        ])
        sub_map = {s.requirement_id.id: s for s in submissions}

        # Build per-entitlement prereqs for activation modal (docs + employees)
        entitlement_prereqs = {}
        if order.wink_entitlement_ids:
            partner_emp = order.partner_id.commercial_partner_id
            modal_employees = request.env['kuec.employee.directory'].sudo().search([
                ('partner_id', '=', partner_emp.id)
            ])
            for ent in order.wink_entitlement_ids:
                docs_ok, _missing = order._wink_required_docs_approved_for_product(ent.service_product_id)
                doc_items = []
                if ent.service_product_id:
                    for req in ent.service_product_id.kuec_document_ids.filtered(
                        lambda d: getattr(d, 'requirement', '') == 'required'
                    ):
                        sub = sub_map.get(req.id)
                        doc_items.append({
                            'req_id': req.id,
                            'name': req.name or '',
                            'state': sub.state if sub else 'draft',
                            'filename': sub.filename if sub else '',
                            'notes': (sub.coordinator_notes or '') if sub else '',
                        })
                requires_emps = bool(getattr(ent.service_product_id, 'requires_employee_selection', False))
                entitlement_prereqs[ent.id] = {
                    'docs_ok': docs_ok,
                    'doc_items': doc_items,
                    'requires_employees': requires_emps,
                    'employees': modal_employees,
                    'can_activate': docs_ok,
                }

        is_retainer = product and product.delivery_model == 'retainer'
        recurring_lines = product._wink_recurring_plan_lines() if product else []
        # Current plan: order.plan_id (sale.subscription.plan) or pricing record from wink_recurring_pricing_id
        retainer_plan = False
        if getattr(order, 'plan_id', None):
            try:
                if order.plan_id and getattr(order.plan_id, 'id', None):
                    retainer_plan = order.plan_id
            except (KeyError, AttributeError):
                pass
        
        # WF-BUNDLE-PLAN-002: Bundles store their plan in wink_plan_id, which avoids modifying the native recurrence fields
        if not retainer_plan and getattr(order, 'wink_plan_id', None):
            if order.wink_plan_id and getattr(order.wink_plan_id, 'id', None):
                retainer_plan = order.wink_plan_id

        if not retainer_plan:
            pid = getattr(order, 'wink_recurring_pricing_id', None) or 0
            if pid and recurring_lines and pid in (recurring_lines.ids or []):
                try:
                    rec = request.env[recurring_lines._name].sudo().browse(pid)
                    if rec.exists():
                        retainer_plan = rec
                except KeyError:
                    pass
            if not retainer_plan and pid:
                rec = _get_product_pricing_browse(request.env, [pid])
                if rec.exists():
                    retainer_plan = rec
                else:
                    # Final fallback: maybe it was a wink.subscription.plan stored in wink_recurring_pricing_id
                    try:
                        rec = request.env['wink.subscription.plan'].sudo().browse(pid)
                        if rec.exists():
                            retainer_plan = rec
                    except Exception:
                        pass
        retainer_plans_for_change = recurring_lines
        # RET-006: Allow plan change when subscription group has multiple tiers
        group = product.wink_subscription_group_id if product else None
        retainer_allow_plan_change = bool(group and len(group.plan_ids) > 1)

        # Pre-compute ALL ORM-derived display values as plain Python strings.
        # NEVER let QWeb templates access Many2one descriptors — in Odoo 18 they
        # return None instead of raising AttributeError, causing TypeError in QWeb.
        retainer_plan_label = ''
        retainer_plan_price_str = ''
        retainer_plan_currency_sym = 'AED'
        if retainer_plan:
            try:
                retainer_plan_label = (
                    getattr(getattr(retainer_plan, 'recurrence_id', None), 'name', None)
                    or getattr(getattr(retainer_plan, 'recurring_plan_id', None), 'name', None)
                    or getattr(getattr(retainer_plan, 'plan_id', None), 'name', None)
                    or getattr(retainer_plan, 'name', None)
                    or ''
                )
            except Exception:
                retainer_plan_label = ''
            try:
                price_val = (
                    getattr(retainer_plan, 'price', None)
                    or getattr(retainer_plan, 'list_price', None)
                    or getattr(retainer_plan, 'recurring_price', None)
                    or 0
                )
                if price_val:
                    retainer_plan_price_str = '{:,.2f}'.format(float(price_val))
            except Exception:
                retainer_plan_price_str = ''
            try:
                cur = order.currency_id
                if cur and cur.id:
                    retainer_plan_currency_sym = cur.symbol or 'AED'
            except Exception:
                retainer_plan_currency_sym = 'AED'

        # Bundle tier label — pre-computed to avoid triple-chained ORM in template
        bundle_tier_label = ''
        bundle_bundle_name = ''
        try:
            tier = order.wink_bundle_tier_id
            if tier and tier.id:
                bundle_tier_label = tier.name or ''
                try:
                    bundle_bundle_name = tier.bundle_id.name or ''
                except Exception:
                    bundle_bundle_name = ''
        except Exception:
            bundle_tier_label = ''
            bundle_bundle_name = ''

        # WF-BND-004: activation completion per activated line (tasks closed)
        bundle_activation_map = {}
        try:
            entitlements = order.wink_entitlement_ids
            all_lines = entitlements.mapped('activated_line_ids')
            line_completion = {}
            if all_lines:
                tasks = request.env['project.task'].sudo().search([
                    ('sale_line_id', 'in', all_lines.ids),
                ])
                tasks_by_line = {}
                for t in tasks:
                    tasks_by_line.setdefault(t.sale_line_id.id, []).append(t)
                for line in all_lines:
                    line_tasks = tasks_by_line.get(line.id, [])
                    if not line_tasks:
                        complete = False
                    else:
                        def _task_done(task):
                            stage = getattr(task, 'stage_id', None)
                            if not stage:
                                return False
                            if getattr(stage, 'fold', False):
                                return True
                            # Fallback: stage name suggests done (backend "Done" may not have fold set)
                            name = (stage.name or '').lower()
                            return any(x in name for x in ('done', 'cancelled', 'closed', 'complete'))
                        complete = all(_task_done(t) for t in line_tasks)
                    line_completion[line.id] = complete
            for ent in entitlements:
                lines = ent.activated_line_ids
                bundle_activation_map[ent.id] = [
                    {
                        'line_id': line.id,
                        'name': line.name or line.product_id.name or '',
                        'is_complete': line_completion.get(line.id, False),
                        'index': idx + 1,
                    }
                    for idx, line in enumerate(lines)
                ]
        except Exception:
            bundle_activation_map = {}

        # Portal must reflect when coordinator has closed/cancelled the order or subscription.
        # sale.order.state can stay 'sale' when subscription is churned (subscription_state = '6_churn').
        is_order_cancelled = order.state == 'cancel'
        subscription_state = getattr(order, 'subscription_state', None)
        is_subscription_churned = subscription_state == '6_churn'
        is_closed_or_cancelled = is_order_cancelled or is_subscription_churned
        close_reason_name = ''
        if is_closed_or_cancelled:
            try:
                close_reason = getattr(order, 'close_reason_id', None)
                if close_reason and close_reason.id:
                    close_reason_name = close_reason.name or _('Cancelled')
                else:
                    close_reason_name = _('Cancelled') if is_order_cancelled else _('Closed')
            except Exception:
                close_reason_name = _('Cancelled')

        # Cancellation proration and policy (for retainer: show refund amount per policy)
        cancellation_proration = None
        cancellation_credit_policy_label = ''
        if is_retainer and product and getattr(order, 'wink_cancellation_requested', False):
            try:
                cancellation_proration = order._wink_compute_proration()
                policy = order._wink_get_policy()
                if policy:
                    cancel_sel = dict(policy._fields['cancellation_credit_policy'].selection)
                    cancellation_credit_policy_label = cancel_sel.get(policy.cancellation_credit_policy, '')
            except Exception:
                pass

        # Policy error messages (from redirect params)
        quote_message = kwargs.get('message', '')

        # Payment status (for banner: confirm only after payment; retainer: show manage only when paid)
        tx_paid = order.transaction_ids.filtered(lambda tx: tx.state in ('authorized', 'done', 'pending'))
        inv_paid = order.invoice_ids.filtered(lambda inv: inv.state == 'posted' and inv.payment_state in ('in_payment', 'paid'))
        is_paid = bool(tx_paid or inv_paid)

        # UI-BUG-004 (FB-004): Remaining amount due and next due date for partial payment plans
        amount_due_display = order.amount_total
        amount_paid_display = 0.0
        has_partial_payment = False
        next_due_date = None
        try:
            posted_invs = order.invoice_ids.filtered(lambda m: m.state == 'posted')
            if posted_invs:
                amount_due_display = sum(posted_invs.mapped('amount_residual'))
                amount_paid_display = float(order.amount_total) - amount_due_display
                if amount_paid_display > 0 and amount_due_display > 0:
                    has_partial_payment = True
                unpaid_invs = posted_invs.filtered(lambda m: getattr(m, 'amount_residual', 0) > 0)
                if unpaid_invs and hasattr(unpaid_invs[0], 'invoice_date_due'):
                    dates = [inv.invoice_date_due for inv in unpaid_invs if inv.invoice_date_due]
                    next_due_date = min(dates) if dates else None
        except Exception:
            pass

        # UI-011: Delivery progress current step (1=Submitted..5=Completed)
        delivery_stage = 1
        if order.state in ('draft', 'sent'):
            delivery_stage = 2  # Quote Review
        elif order.state == 'sale' and not is_paid:
            delivery_stage = 3  # Payment
        elif order.state == 'sale' and is_paid:
            delivery_stage = 4  # In Progress
        elif order.state == 'done' or is_closed_or_cancelled:
            delivery_stage = 5  # Completed

        # UI-012: Activity timeline (last 5 messages or synthetic entries)
        activity_items = []
        try:
            strip_html = getattr(request.env['mail.message'], '_strip_html', None) or (lambda x: (x or '').replace('<', ' ')[:80])
            for msg in order.message_ids.sorted('date', reverse=True)[:5]:
                body = (msg.body or '')
                if strip_html and callable(strip_html):
                    try:
                        body = strip_html(body)[:80]
                    except Exception:
                        body = body.replace('<', ' ')[:80]
                else:
                    body = body.replace('<', ' ')[:80]
                activity_items.append({'text': body or _('Update'), 'date': msg.date, 'icon': 'fa-comment', 'type': 'message'})
        except Exception:
            pass
        if not activity_items:
            activity_items = [
                {'text': _('Request submitted for %s') % (product.name if product else order.name), 'date': order.create_date, 'icon': 'fa-paper-plane', 'type': 'user'},
                {'text': _('Awaiting coordinator price confirmation') if not order.wink_price_confirmed else _('Quote ready for approval'), 'date': order.write_date, 'icon': 'fa-cog', 'type': 'system'},
            ]

        return request.render('kuec_service_catalogue.wink_request_confirmation', {
            'order': order,
            'product': product,
            'payment_pending': kwargs.get('payment') == 'pending',
            'bundle_requested': kwargs.get('bundle_requested') == '1',
            'requirements': requirements,
            'sub_map': sub_map,
            'is_retainer': is_retainer,
            'retainer_plan': retainer_plan,
            'retainer_plan_label': retainer_plan_label,
            'retainer_plan_price_str': retainer_plan_price_str,
            'retainer_plan_currency_sym': retainer_plan_currency_sym,
            'retainer_plans_for_change': retainer_plans_for_change,
            'retainer_allow_plan_change': retainer_allow_plan_change,
            'retainer_plan_has_price': bool(retainer_plan_price_str),
            'bundle_tier_label': bundle_tier_label,
            'bundle_bundle_name': bundle_bundle_name,
            'bundle_activation_map': bundle_activation_map,
            'retainer_cancelled': kwargs.get('retainer_cancelled') == '1',
            'quote_rejected': kwargs.get('rejected') == '1',
            'quote_error': kwargs.get('error'),
            'quote_message': quote_message,
            'is_closed_or_cancelled': is_closed_or_cancelled,
            'close_reason_name': close_reason_name,
            'cancellation_proration': cancellation_proration,
            'cancellation_credit_policy_label': cancellation_credit_policy_label,
            'is_paid': is_paid,
            'delivery_stage': delivery_stage,  # UI-011
            'activity_items': activity_items,  # UI-012
            'submitted': kwargs.get('submitted') == '1',  # UI-013
            # WF-BND-002: activation error message when activation blocked (docs/employees)
            'activation_error': kwargs.get('activation_error') or request.params.get('activation_error', '') or '',
            # Activation modal state
            'entitlement_prereqs': entitlement_prereqs,
            'open_modal': kwargs.get('open_modal', ''),
            'doc_uploaded': kwargs.get('doc_uploaded') == '1',
            # UI-BUG-004 (FB-004): partial payment display
            'amount_due_display': amount_due_display,
            'amount_paid_display': amount_paid_display,
            'has_partial_payment': has_partial_payment,
            'next_due_date': next_due_date,
        })

    @http.route('/my/requests/<int:order_id>/approve', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def request_approve_quote(self, order_id, **post):
        """Customer approves the quotation (confirm order). Only when quote is sent and price is confirmed."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        if order.state not in ('draft', 'sent'):
            return request.redirect(f'/my/requests/{order_id}')
        if not order.wink_price_confirmed:
            return request.redirect(f'/my/requests/{order_id}?error=price_not_confirmed')
        try:
            order.sudo().action_confirm()
            order.sudo().message_post(
                body=_("Customer approved this quote from the portal."),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        except Exception:
            pass
        return request.redirect(f'/my/requests/{order_id}')

    @http.route('/my/requests/<int:order_id>/reject', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def request_reject_quote(self, order_id, **post):
        """Customer rejects the quotation (cancel). Only when quote is draft or sent."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        if order.state not in ('draft', 'sent'):
            return request.redirect(f'/my/requests/{order_id}')
        order.sudo().action_cancel()
        order.sudo().message_post(
            body=_("Customer rejected this quote from the portal."),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return request.redirect(f'/my/requests/{order_id}?rejected=1')

    def _resolve_plan_pricing(self, product, plan, current_recurrence_id=None):
        """Resolve pricing record for a wink.subscription.plan + product.
        RET-009: Returns (pricing_record, recurrence_id, price_visible)."""
        lines = product._wink_recurring_plan_lines() if product else []
        if not lines:
            return None, None, False
        # Try plan.pricing_model/pricing_id first
        if plan.pricing_model and plan.pricing_id:
            try:
                rec = request.env[plan.pricing_model].sudo().browse(plan.pricing_id)
                prod_ref = getattr(rec, 'product_tmpl_id', None) or getattr(rec, 'product_template_id', None)
                if rec.exists() and prod_ref == product:
                    rec_id = getattr(getattr(rec, 'recurrence_id', None), 'id', None) or getattr(getattr(rec, 'plan_id', None), 'id', None)
                    price = getattr(rec, 'price', None) or getattr(rec, 'recurring_price', None) or 0
                    return rec, rec_id, bool(price is not None and float(price or 0) > 0)
            except (KeyError, AttributeError):
                pass
        # Match by recurrence_name_hint
        hint = (plan.recurrence_name_hint or '').strip().lower()
        for line in lines:
            rec = getattr(line, 'recurrence_id', None) or getattr(line, 'plan_id', None) or getattr(line, 'recurring_plan_id', None)
            if not rec:
                continue
            rec_name = (getattr(rec, 'name', None) or '').strip().lower()
            if hint and rec_name and hint in rec_name:
                price = getattr(line, 'price', None) or getattr(line, 'recurring_price', None) or 0
                return line, rec.id, bool(price is not None and float(price or 0) > 0)
        # Use current recurrence if provided
        if current_recurrence_id:
            for line in lines:
                rec = getattr(line, 'recurrence_id', None) or getattr(line, 'plan_id', None)
                if rec and rec.id == current_recurrence_id:
                    price = getattr(line, 'price', None) or getattr(line, 'recurring_price', None) or 0
                    return line, current_recurrence_id, bool(price is not None and float(price or 0) > 0)
        # First line as fallback
        line = lines[0]
        rec = getattr(line, 'recurrence_id', None) or getattr(line, 'plan_id', None)
        price = getattr(line, 'price', None) or getattr(line, 'recurring_price', None) or 0
        return line, rec.id if rec else None, bool(price is not None and float(price or 0) > 0)

    @http.route('/my/requests/<int:order_id>/retainer/change-plan', type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def retainer_change_plan(self, order_id, **kwargs):
        """RET-005: GET=plan comparison page; POST=submit plan change."""
        if request.httprequest.method == 'POST':
            return self._retainer_change_plan_submit(order_id, **kwargs)
        return self._retainer_change_plan_page(order_id, **kwargs)

    def _retainer_change_plan_page(self, order_id, **kwargs):
        """RET-005: Plan comparison page with proration preview."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        product = order.wink_source_product_id
        if not product or product.delivery_model != 'retainer':
            return request.redirect(f'/my/requests/{order_id}')
        group = product.wink_subscription_group_id
        if not group or not group.plan_ids:
            return request.redirect(f'/my/requests/{order_id}?error=change_not_allowed&message=%s' % werkzeug.urls.url_quote(_('Plan configuration incomplete — please contact support.')))
        ok, msg = order._wink_can_request_plan_change()
        if not ok:
            return request.redirect(f'/my/requests/{order_id}?error=change_not_allowed&message=%s' % werkzeug.urls.url_quote(msg or ''))

        Service = request.env['wink.retainer.change.service'].sudo()
        source_plan = order.wink_plan_id or group.plan_ids.sorted('sequence')[:1]
        current_recurrence_id = None
        pid = getattr(order, 'wink_recurring_pricing_id', None)
        if pid and product._wink_recurring_plan_lines():
            for line in product._wink_recurring_plan_lines():
                if getattr(line, 'id', None) == pid:
                    rec = getattr(line, 'recurrence_id', None) or getattr(line, 'plan_id', None)
                    if rec:
                        current_recurrence_id = rec.id
                    break

        wink_is_bundle = ((product.commercial_structure == 'bundled' or getattr(product, 'wink_is_bundle', False)) and product.wink_bundle_id)
        current_tier = order.wink_bundle_tier_id if wink_is_bundle else None

        target_plans_data = []

        if wink_is_bundle:
            # Bundle: Cross all available tiers with all available plans
            tiers = product.wink_bundle_id.tier_ids.sorted('sequence')
            for tier in tiers:
                for plan in group.plan_ids:
                    # Skip the exact current combination
                    if plan.id == source_plan.id and current_tier and tier.id == current_tier.id:
                        continue
                    
                    # For upgrade/downgrade classification, if plan is the same, use tier price to determine.
                    # As a shortcut, the service uses source_plan and target_plan; we'll enrich this in the engine later or just rely on price difference in 'change_type'.
                    # For UI presentation, we can evaluate proration directly.
                    change_type = Service.classify_change(source_plan, plan) # Note: this standard classification only checks freq length. For tiers it might say 'same'.
                    
                    # Determine pseudo change_type based on tier sequence if plan is the same
                    if change_type == 'same' and current_tier:
                        if tier.sequence > current_tier.sequence:
                            change_type = 'upgrade'
                        elif tier.sequence < current_tier.sequence:
                            change_type = 'downgrade'

                    if not change_type:
                        continue

                    # Overwrite pricing record search to simulate "tier + plan"
                    # Pricing line must match tier.product_variant_id and plan
                    pricing_rec, rec_id, price_visible = self._resolve_plan_pricing(product, plan, current_recurrence_id)
                    # We actually need to re-resolve pricing specific to the tier's variant
                    tier_variant = tier.product_variant_id or product.product_variant_id
                    
                    actual_pricing_line = None
                    for line in product._wink_recurring_plan_lines():
                        if hasattr(line, 'product_id') and line.product_id and line.product_id.id != tier_variant.id:
                            continue
                        r_id = getattr(getattr(line, 'recurrence_id', None), 'id', None) or getattr(getattr(line, 'plan_id', None), 'id', None) or getattr(getattr(line, 'recurring_plan_id', None), 'id', None)
                        
                        target_r_id = getattr(getattr(plan, 'pricing_id', None), 'recurrence_id', None)
                        plan_r_id = getattr(getattr(plan.pricing_id, 'recurrence_id', None), 'id', None) if plan.pricing_id else None
                        
                        # Match by recurrence
                        if r_id and ((rec_id and r_id == rec_id) or (plan.recurrence_name_hint and plan.recurrence_name_hint.lower() in getattr(getattr(line, 'recurrence_id', None), 'name', '').lower())):
                            actual_pricing_line = line
                            break

                    monthly_price = 0
                    if actual_pricing_line:
                        price_val = getattr(actual_pricing_line, 'price', None) or getattr(actual_pricing_line, 'recurring_price', None) or 0
                        recurrence = getattr(actual_pricing_line, 'recurrence_id', None) or getattr(actual_pricing_line, 'plan_id', None)
                        months = product._recurrence_duration_months(recurrence)
                        if months:
                            monthly_price = price_val / months
                    
                    # If we couldn't find a pricing line for this tier+plan combination, skip it
                    if not actual_pricing_line:
                        continue

                    class DummyPlan:
                        def __init__(self, p, t, mp):
                            self.id = p.id
                            self.name = f"{t.name} — {p.name}"
                            self.monthly_std_price = mp
                            self._original_plan = p
                    
                    dummy_plan = DummyPlan(plan, tier, monthly_price)
                    
                    # Temporary override for validation/proration
                    ok_pol, pol_msg = Service.validate_policy(order, plan, change_type)
                    
                    # We must pass the variant to compute_proration if WINK supports it, or let it rely on standard
                    # Actually compute_proration takes `target_plan` and uses its `monthly_std_price`. We will monkey-patch target_plan or let it use the base plan and just display approximate credit here.
                    proration = Service.compute_proration(order, plan, group.effective_date_policy or 'immediate') if ok_pol else None
                    
                    policy = group
                    credit_label = dict(policy._fields['downgrade_credit_policy'].selection).get(policy.downgrade_credit_policy, '') if change_type == 'downgrade' else ''
                    
                    target_plans_data.append({
                        'plan': dummy_plan,
                        'tier_id': tier.id,
                        'change_type': change_type,
                        'proration': proration,
                        'policy_ok': ok_pol,
                        'policy_message': pol_msg,
                        'pricing_record': actual_pricing_line,
                        'recurrence_id': rec_id,
                        'price_visible': price_visible and (not product.price_visibility or product.price_visibility == 'visible'),
                        'credit_policy_label': credit_label,
                        'effective_date_policy': group.effective_date_policy or 'immediate',
                    })

        else:
            for plan in group.plan_ids:
                if plan.id == source_plan.id:
                    continue
                change_type = Service.classify_change(source_plan, plan)
                if not change_type:
                    continue
                ok_pol, pol_msg = Service.validate_policy(order, plan, change_type)
                proration = Service.compute_proration(order, plan, group.effective_date_policy or 'immediate') if ok_pol else None
                pricing_rec, rec_id, price_visible = self._resolve_plan_pricing(product, plan, current_recurrence_id)
                policy = group
                credit_label = dict(policy._fields['downgrade_credit_policy'].selection).get(policy.downgrade_credit_policy, '') if change_type == 'downgrade' else ''
                target_plans_data.append({
                    'plan': plan,
                    'tier_id': None,
                    'change_type': change_type,
                    'proration': proration,
                    'policy_ok': ok_pol,
                    'policy_message': pol_msg,
                    'pricing_record': pricing_rec,
                    'recurrence_id': rec_id,
                    'price_visible': price_visible and (not product.price_visibility or product.price_visibility == 'visible'),
                    'credit_policy_label': credit_label,
                    'effective_date_policy': group.effective_date_policy or 'immediate',
                })

        return request.render('kuec_service_catalogue.wink_retainer_change_plan', {
            'order': order,
            'product': product,
            'source_plan': source_plan,
            'target_plans_data': target_plans_data,
            'policy': group,
        })

    def _retainer_change_plan_submit(self, order_id, **post):
        """RET-005: Submit plan change."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        product = order.wink_source_product_id
        if not product or product.delivery_model != 'retainer':
            return request.redirect(f'/my/requests/{order_id}')
        try:
            target_plan_id = int(post.get('target_plan_id') or 0)
        except (TypeError, ValueError):
            return request.redirect(f'/my/requests/{order_id}/retainer/change-plan?error=invalid_plan')
        target_plan = request.env['wink.subscription.plan'].sudo().browse(target_plan_id)
        if not target_plan.exists() or target_plan.group_id != product.wink_subscription_group_id:
            return request.redirect(f'/my/requests/{order_id}/retainer/change-plan?error=invalid_plan')

        target_tier = None
        if product.commercial_structure == 'bundled' and product.wink_bundle_id:
            try:
                target_tier_id = int(post.get('target_tier_id') or 0)
                if target_tier_id:
                    target_tier = request.env['wink.bundle.tier'].sudo().browse(target_tier_id)
                    if not target_tier.exists() or target_tier.bundle_id != product.wink_bundle_id:
                        return request.redirect(f'/my/requests/{order_id}/retainer/change-plan?error=invalid_tier')
            except (TypeError, ValueError):
                pass

        Service = request.env['wink.retainer.change.service'].sudo()
        source_plan = order.wink_plan_id or product.wink_subscription_group_id.plan_ids.sorted('sequence')[:1]
        change_type = Service.classify_change(source_plan, target_plan)

        if target_tier:
            current_tier = order.wink_bundle_tier_id
            if change_type == 'same' and current_tier:
                if target_tier.sequence > current_tier.sequence:
                    change_type = 'upgrade'
                elif target_tier.sequence < current_tier.sequence:
                    change_type = 'downgrade'

        if not change_type:
            return request.redirect(f'/my/requests/{order_id}/retainer/change-plan?error=invalid_change')
        ok, msg = Service.validate_policy(order, target_plan, change_type)
        if not ok:
            return request.redirect(f'/my/requests/{order_id}/retainer/change-plan?error=policy&message=%s' % werkzeug.urls.url_quote(msg or ''))

        proration = Service.compute_proration(order, target_plan, product.wink_subscription_group_id.effective_date_policy or 'immediate')
        if proration.get('error'):
            return request.redirect(f'/my/requests/{order_id}/retainer/change-plan?error=proration')

        pricing_rec, recurrence_id, _ = self._resolve_plan_pricing(product, target_plan)

        # Overwrite pricing if bundle
        if target_tier:
            tier_variant = target_tier.product_variant_id or product.product_variant_id
            for line in product._wink_recurring_plan_lines():
                if hasattr(line, 'product_id') and line.product_id and line.product_id.id != tier_variant.id:
                    continue
                r_id = getattr(getattr(line, 'recurrence_id', None), 'id', None) or getattr(getattr(line, 'plan_id', None), 'id', None) or getattr(getattr(line, 'recurring_plan_id', None), 'id', None)
                if recurrence_id and r_id == recurrence_id:
                    pricing_rec = line
                    break

        if not pricing_rec and not recurrence_id:
            return request.redirect(f'/my/requests/{order_id}/retainer/change-plan?error=no_pricing')

        policy = product.wink_subscription_group_id
        requires_approval = (change_type == 'upgrade' and policy.upgrade_requires_approval) or (change_type == 'downgrade' and policy.downgrade_requires_approval)
        price_hidden = product.price_visibility == 'hidden' or not (pricing_rec and getattr(pricing_rec, 'price', None))
        if price_hidden:
            requires_approval = True

        new_order = Service.create_plan_change_order(
            source_order=order,
            target_plan=target_plan,
            change_type=change_type,
            proration_credit=proration['proration_credit'],
            proration_charge=proration['proration_charge'],
            effective_date=proration['effective_date'],
            pricing_record=pricing_rec,
            recurrence_id=recurrence_id,
        )
        if requires_approval or price_hidden:
            new_order.sudo().write({'wink_price_confirmed': False})
            
        if target_tier:
            new_order.sudo().write({'wink_bundle_tier_id': target_tier.id})
            # Override line title based on bundle tier variant or name
            bundle_line = new_order.order_line.filtered(lambda l: l.product_id.product_tmpl_id.id == product.id)[:1]
            if bundle_line:
                variant = target_tier.product_variant_id
                bundle_line_name = variant.name if variant and variant.name != product.name else product.name
                bundle_line.sudo().write({
                    'product_id': variant.id if variant else bundle_line.product_id.id,
                    'name': f"{bundle_line_name} — {target_tier.name}",
                })

            # Create new entitlement records for the new tier on the upgraded/downgraded order
            for idx, item in enumerate(target_tier.item_ids.sorted('sequence')):
                ent_vals = {
                    'order_id': new_order.id,
                    'tier_id': target_tier.id,
                    'service_product_id': item.service_product_id.id,
                    'name': (item.description or item.service_product_id.name),
                    'sequence': item.sequence,
                    'qty_entitled': item.qty,
                    'qty_activated': 0,
                }
                request.env['wink.bundle.entitlement'].sudo().create(ent_vals)

        # Notify coordinator and customer of plan change
        try:
            coord_template = request.env.ref('kuec_service_catalogue.kuec_coordinator_notification_email_v5', raise_if_not_found=False)
            if coord_template:
                coord_template.sudo().send_mail(new_order.id, force_send=True)
            cust_template = request.env.ref('kuec_service_catalogue.kuec_request_confirmation_template', raise_if_not_found=False)
            if cust_template:
                cust_template.sudo().send_mail(new_order.id, force_send=True)
        except Exception:
            pass

        return request.redirect(f'/my/requests/{new_order.id}?plan_change_submitted=1')

    @http.route('/my/requests/<int:order_id>/retainer/cancel/preview', type='http', auth='user', website=True)
    def retainer_cancel_preview(self, order_id, **kwargs):
        """RET-005: Cancellation preview with refund amount."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        product = order.wink_source_product_id
        if not product or product.delivery_model != 'retainer':
            return request.redirect(f'/my/requests/{order_id}')
        allowed, msg = order._wink_can_request_cancel()
        if not allowed:
            return request.redirect(f'/my/requests/{order_id}?error=cancel_not_allowed&message=%s' % werkzeug.urls.url_quote(msg or ''))

        proration = order._wink_compute_proration()
        policy = order._wink_get_policy()
        cancel_sel = dict(policy._fields['cancellation_credit_policy'].selection).get(policy.cancellation_credit_policy, '') if policy else ''
        end_date = getattr(order, 'next_date', None) or getattr(order, 'next_invoice_date', None)
        show_refund = policy and policy.cancellation_credit_policy != 'no_refund'

        return request.render('kuec_service_catalogue.wink_retainer_cancel_preview', {
            'order': order,
            'product': product,
            'proration': proration,
            'policy_label': cancel_sel,
            'end_date': end_date,
            'show_refund': show_refund,
            'effective_date_policy': (policy and policy.effective_date_policy) or 'immediate',
        })

    @http.route('/my/requests/<int:order_id>/retainer/cancel', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def retainer_request_cancel(self, order_id, **post):
        """RET-005: Customer requests cancellation. Sets fields, timestamps, optional reason."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        product = order.wink_source_product_id
        if not product or product.delivery_model != 'retainer':
            return request.redirect(f'/my/requests/{order_id}')
        allowed, msg = order._wink_can_request_cancel()
        if not allowed:
            return request.redirect(f'/my/requests/{order_id}?error=cancel_not_allowed&message=%s' % werkzeug.urls.url_quote(msg or 'Not allowed'))

        from odoo import fields as odoo_fields
        policy = order._wink_get_policy()
        end_date = getattr(order, 'next_date', None) or getattr(order, 'next_invoice_date', None)
        effective_date = date.today() if (policy and policy.effective_date_policy == 'immediate') else (end_date if end_date else date.today())

        order.sudo().write({
            'wink_cancellation_requested': True,
            'wink_cancellation_requested_date': odoo_fields.Datetime.now(),
            'wink_cancellation_reason': post.get('reason', '').strip() or False,
            'wink_cancellation_effective_date': effective_date,
        })
        order.sudo().message_post(
            body=_("Customer requested cancellation of this retainer from the portal. Effective date: %s. Reason: %s") % (
                effective_date,
                post.get('reason', '').strip() or _('(none)'),
            ),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        # Notify coordinator and customer of cancellation request
        try:
            coord_template = request.env.ref('kuec_service_catalogue.kuec_coordinator_cancellation_notification', raise_if_not_found=False)
            if coord_template:
                coord_template.sudo().send_mail(order.id, force_send=True)
            cust_template = request.env.ref('kuec_service_catalogue.kuec_cancellation_confirmation_template', raise_if_not_found=False)
            if cust_template:
                cust_template.sudo().send_mail(order.id, force_send=True)
        except Exception:
            pass

        return request.redirect(f'/my/requests/{order_id}?retainer_cancelled=1')

    @http.route('/my/requests/<int:order_id>/pay', type='http', auth='user', website=True)
    def request_payment(self, order_id, **kwargs):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)

        if not order:
            raise NotFound()

        source_product = order.wink_source_product_id
        if order.state != 'sale' or (not order.wink_price_confirmed and source_product and source_product.price_visibility == 'hidden'):
            return request.redirect(f'/my/requests/{order.id}?error=payment_not_available')

        # Use native Odoo CustomerPortal controller to fetch payment providers/tokens
        portal_controller = CustomerPortal()
        payment_values = portal_controller._get_payment_values(
            order,
            force_auth=True,
            submit_tx_url='/shop/payment/transaction/{order.id}',
        )

        # --- Epic 6: Upfront Deposits; UI-BUG-004: use remaining amount when partially paid ---
        amount_remaining = order.amount_total
        try:
            posted_invs = order.invoice_ids.filtered(lambda m: m.state == 'posted')
            if posted_invs:
                amount_remaining = sum(posted_invs.mapped('amount_residual'))
        except Exception:
            pass
        if amount_remaining > 0 and amount_remaining < order.amount_total:
            # Partial payment already made: charge the remaining balance
            payment_values['amount'] = order.currency_id.round(amount_remaining)
        elif order.payment_term_id and order.payment_term_id.line_ids:
            first_term_line = order.payment_term_id.line_ids[0]
            if first_term_line.value == 'percent' and first_term_line.value_amount < 100:
                deposit_amt = order.currency_id.round(order.amount_total * (first_term_line.value_amount / 100.0))
                payment_values['amount'] = deposit_amt

        # Override the landing route so Odoo returns to the request details, not sale portal
        payment_values['landing_route'] = f'/my/requests/{order.id}'

        render_values = {
            'order': order,
            **payment_values
        }

        return request.render('kuec_service_catalogue.wink_payment_page_v2', render_values)

    @http.route('/my/requests/<int:order_id>/documents', type='http', auth='user', website=True)
    def request_documents(self, order_id, **kw):
        """Portal page listing document requirements and upload forms."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        # Document requirements: for bundle = child services'; for standalone = product's
        requirements = order._wink_document_requirements()
        submissions = request.env['kuec.document.submission'].sudo().search([
            ('order_id', '=', order_id)
        ])
        sub_map = {s.requirement_id.id: s for s in submissions}

        return request.render('kuec_service_catalogue.wink_document_upload_page', {
            'order': order,
            'requirements': requirements,
            'sub_map': sub_map,
            'doc_uploaded': kw.get('doc_uploaded') == '1',
            'doc_error': kw.get('doc_error', False),
        })

    @http.route('/my/requests/<int:order_id>/documents/upload', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def upload_document(self, order_id, **post):
        """Handle document file upload from portal."""
        import base64
        from odoo import fields as odoo_fields

        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        try:
            requirement_id = int(post.get('requirement_id', 0))
        except (TypeError, ValueError):
            requirement_id = 0
        requirement = request.env['kuec.service.document'].sudo().browse(requirement_id)
        if not requirement.exists():
            raise NotFound()

        # Ensure the requirement is one of this order's (product or bundle child services)
        allowed_requirement_ids = order._wink_document_requirements().ids
        if allowed_requirement_ids and requirement_id not in allowed_requirement_ids:
            raise NotFound()

        uploaded = request.httprequest.files.get('doc_file')
        if not uploaded or not uploaded.filename:
            return request.redirect(
                f'/my/requests/{order_id}/documents?doc_error=no_file'
            )

        allowed_mimetypes = {
            'application/pdf',
            'image/jpeg',
            'image/png',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        if uploaded.mimetype not in allowed_mimetypes:
            return request.redirect(
                f'/my/requests/{order_id}/documents?doc_error=bad_type'
            )

        file_data = base64.b64encode(uploaded.read())

        attachment = request.env['ir.attachment'].sudo().create({
            'name': uploaded.filename,
            'datas': file_data,
            'res_model': 'kuec.document.submission',
            'mimetype': uploaded.mimetype,
            'type': 'binary',
        })

        existing = request.env['kuec.document.submission'].sudo().search([
            ('order_id', '=', order_id),
            ('requirement_id', '=', requirement_id),
        ], limit=1)

        now = odoo_fields.Datetime.now()

        if existing:
            existing.sudo().write({
                'attachment_id': attachment.id,
                'filename': uploaded.filename,
                'state': 'under_review',
                'submitted_date': now,
                'coordinator_notes': False,
                'reviewed_date': False,
                'reviewed_by': False,
            })
        else:
            request.env['kuec.document.submission'].sudo().create({
                'order_id': order_id,
                'requirement_id': requirement_id,
                'partner_id': request.env.user.partner_id.id,
                'attachment_id': attachment.id,
                'filename': uploaded.filename,
                'state': 'under_review',
                'submitted_date': now,
            })

        # Allow redirect back to activation modal when upload came from there
        redirect_to = post.get('redirect_to', '')
        if redirect_to and redirect_to.startswith('/my/requests/'):
            return request.redirect(redirect_to)
        return request.redirect(
            f'/my/requests/{order_id}/documents?doc_uploaded=1'
        )

    # ── Bundle Activation Route ──
    # WF-BND-001 / WF-BND-002 / WF-BND-005: bundle activation with per-activation employees & docs
    @http.route(
        '/my/requests/<int:order_id>/bundle/'
        '<int:entitlement_id>/activate',
        type='http', auth='user', website=True,
        methods=['GET', 'POST'], csrf=True)
    def bundle_activate_request(
        self, order_id, entitlement_id, **post
    ):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of',
             request.env.user.partner_id
             .commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        entitlement = request.env['wink.bundle.entitlement'].sudo().search([
            ('id', '=', entitlement_id),
            ('order_id', '=', order_id),
        ], limit=1)
        if not entitlement:
            raise NotFound()
        # No limit on reactivation: customer can activate as many times as needed

        # GET: redirect back to request detail — activation is now handled inline via modal
        if request.httprequest.method == 'GET':
            return request.redirect(f'/my/requests/{order_id}?open_modal={entitlement_id}')

        # POST: perform activation
        employee_ids = []
        for val in request.httprequest.form.getlist('employee_ids'):
            if str(val).isdigit():
                employee_ids.append(int(val))

        try:
            entitlement.action_activate(employee_ids=employee_ids)
        except Exception as e:
            from odoo.exceptions import UserError
            msg = ''
            if isinstance(e, UserError):
                # UserError has no .name; use str() for message (safe for redirect param)
                msg = str(e) if e else ''
            else:
                import logging
                logging.getLogger(__name__).warning(
                    "Bundle activation failed for entitlement %s: %s",
                    entitlement_id, e,
                )
                msg = _('Activation failed due to an unexpected error.')
            return request.redirect(
                f'/my/requests/{order_id}'
                f'?activation_error={werkzeug.urls.url_quote(msg or "")}'
            )

        return request.redirect(
            f'/my/requests/{order_id}'
            f'?bundle_requested=1'
        )

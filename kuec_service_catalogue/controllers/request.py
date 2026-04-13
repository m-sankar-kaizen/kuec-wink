# -*- coding: utf-8 -*-
# RET-005, RET-008, RET-009
from datetime import date
from odoo import http, fields, _
from odoo.http import request
from werkzeug.exceptions import NotFound
from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.tools import html2plaintext
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
        _is_bundle_product = product.wink_is_bundle or product.commercial_structure == 'bundled'
        if _is_bundle_product:
            bundle = product.wink_bundle_id
            if not bundle:
                # Fallback: product predates auto-create — look up via reverse relation
                bundle = request.env['wink.bundle'].sudo().search(
                    [('product_tmpl_id', '=', product.id)], limit=1
                )
            if bundle:
                tiers = bundle.tier_ids.sorted('sequence')
                tier_data = [{'tier': t, 'items': t.item_ids.sorted('sequence')} for t in tiers]
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

            if product.commercial_structure == 'bundled' or product.wink_is_bundle:
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
                            'savings_pct': p.get('savings_pct', 0),
                            'show_savings': p.get('show_savings', False),
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
                # Identify monthly and annual cycles for JS toggle
                monthly_cycle = None
                annual_cycle = None
                for c in billing_cycles:
                    cname = (c.get('name') or '').lower()
                    if 'month' in cname:
                        monthly_cycle = c
                    elif 'annual' in cname or 'year' in cname:
                        annual_cycle = c
                if not monthly_cycle and billing_cycles:
                    monthly_cycle = billing_cycles[0]
                vals['monthly_cycle'] = monthly_cycle
                vals['annual_cycle'] = annual_cycle
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
        vals['step'] = 1  # Show the journey stepper on the request form
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
            # Exclude child/sub-services (commercial_structure='bundled' but NOT a bundle template)
            Product = request.env['product.template'].sudo()
            domain = [
                ('available_on_wink', '=', True),
                ('sale_ok', '=', True),
                ('active', '=', True),
                '|',
                ('wink_is_bundle', '=', True),
                ('commercial_structure', '!=', 'bundled'),
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
                _rb = product.wink_bundle_id or (
                    request.env['wink.bundle'].sudo().search([('product_tmpl_id', '=', product.id)], limit=1)
                    if (product.commercial_structure == 'bundled' or getattr(product, 'wink_is_bundle', False)) else False
                )
                wink_is_bundle = bool(_rb)
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
            _step1_bundle = product.wink_bundle_id
            if is_bundle_config and not _step1_bundle:
                _step1_bundle = request.env['wink.bundle'].sudo().search(
                    [('product_tmpl_id', '=', product.id)], limit=1
                )
            if is_bundle_config and _step1_bundle:
                bundle = _step1_bundle
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

                    if subscription_plans:
                        for p in subscription_plans:
                            rid = p.get('recurrence_id')
                            if rid and rid not in seen_cycles:
                                seen_cycles[rid] = True
                                billing_cycles.append({
                                    'recurrence_id': rid,
                                    'recurrence_id_str': str(rid),
                                    'name': p.get('plan_name', ''),
                                    'period_label': p.get('period_label', ''),
                                    'savings_pct': p.get('savings_pct', 0),
                                    'show_savings': p.get('show_savings', False),
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

        # Step 6 — Send password reset email (uses portal template with token)
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

        _is_bundle_flag = product.commercial_structure == 'bundled' or getattr(product, 'wink_is_bundle', False)
        _bundle_rec = product.wink_bundle_id
        if _is_bundle_flag and not _bundle_rec:
            _bundle_rec = request.env['wink.bundle'].sudo().search(
                [('product_tmpl_id', '=', product.id)], limit=1
            )
        wink_is_bundle = bool(_is_bundle_flag and _bundle_rec)

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
                for model in ['product.pricing', 'sale.subscription.pricing']:
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
            'origin': 'Service Portal',
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

        # F2: Server-side guard — block submission if required documents were not uploaded.
        # The template marks required file inputs with the HTML `required` attribute for
        # client-side enforcement; this is the server-side safety net.
        if not wink_is_bundle and product:
            req_docs = product.kuec_document_ids.filtered(lambda d: d.requirement == 'required')
            if req_docs:
                doc_files = request.httprequest.files
                missing = [
                    d.name for d in req_docs
                    if not any(f.filename for f in doc_files.getlist(f'doc_file_{d.id}'))
                ]
                if missing:
                    return request.redirect(
                        f'/my/requests/new?product_id={product.id}'
                        f'&error=missing_docs&missing={",".join(missing[:3])}'
                    )

        order = request.env['sale.order'].sudo().create(order_vals)

        # Gov charges — Standalone known mode:
        # Add the gov charge line immediately so the full amount is visible upfront
        # and the customer can pay everything in one shot without coordinator input.
        # Bundle mode skips this — charges are added per-entitlement during activation.
        # Unknown mode skips this — coordinator confirms the amount later.
        if not wink_is_bundle and getattr(product, 'requires_government_charges', False):
            if getattr(product, 'gov_charge_is_known', False):
                gov_base = getattr(product, 'gov_charge_amount', 0.0)
                gov_per_emp = getattr(product, 'gov_charge_per_employee', 0.0)
                num_emp = len(employee_ids) if employee_ids else 0
                total_gov = gov_base + (num_emp * gov_per_emp)
                if total_gov > 0:
                    gov_product = request.env.company.sudo().wink_gov_charge_product_id
                    request.env['sale.order.line'].sudo().create({
                        'order_id': order.id,
                        'product_id': gov_product.id if gov_product else variant.id,
                        'product_uom_qty': 1,
                        'price_unit': total_gov,
                        'name': product.name,
                        'is_gov_charge_pending': True,
                    })

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
            # Sync to any tasks already created (auto-confirm creates tasks before employees are set)
            linked_tasks = request.env['project.task'].sudo().search([('sale_order_id', '=', order.id)])
            if linked_tasks:
                linked_tasks.write({'wink_employee_ids': [(6, 0, employee_ids)]})

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
                if hasattr(order, 'recurrence_id'):
                    sub_vals['recurrence_id'] = selected_recurrence_id
                if hasattr(order, 'is_subscription'):
                    sub_vals['is_subscription'] = True
                if sub_vals:
                    order.sudo().write(sub_vals)
            if getattr(selected_pricing, 'exists', lambda: False)() and selected_pricing:
                order.sudo().write({'wink_recurring_pricing_id': selected_pricing.id})
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

            # Save tier on order — skip_tier_entitlements prevents the write() hook
            # from also calling _generate_tier_entitlements; we create records below.
            order.sudo().with_context(skip_tier_entitlements=True).write({
                'wink_bundle_tier_id': tier.id,
            })

            # Clear any stale entitlements then create once (avoids duplication with hook)
            order.sudo().wink_entitlement_ids.unlink()
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


        # Only auto-confirm when price is visible/confirmed AND there are no required documents
        # pending upload/approval. When required docs exist, the order stays as Quotation so the
        # customer can upload docs; coordinator reviews them; then customer can approve/pay.
        #
        # Auto-confirm rules (EPIC-8 / Story 8.1-A):
        #   • delivery_model = 'retainer' (subscription)  → always confirm to sale.order
        #   • delivery_model = 'project' + price set      → confirm to sale.order
        #   • delivery_model = 'project' + no price       → stay as quotation (wink_price_confirmed=False)
        #   • wink_is_bundle                              → always confirm to sale.order
        has_required_docs = bool(product.kuec_document_ids.filtered(
            lambda d: getattr(d, 'requirement', '') == 'required'
        )) if not wink_is_bundle else False
        is_auto_confirm = order.wink_price_confirmed and not has_required_docs and (
            product.delivery_model == 'project'
            or is_subscription_service
            or wink_is_bundle
        )
        if is_auto_confirm:
            try:
                # mail_notrack=True: prevents Odoo from sending the native
                # sale order confirmation chatter notification to followers —
                # we send our own kuec_request_confirmation_template below.
                order.sudo().with_context(mail_notrack=True).action_confirm()
            except (ValueError, Exception) as e:
                # Odoo 18 bug: project template with 0 tasks causes ValueError
                # in project_task.create() — order is still created, coordinator
                # can confirm manually.
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning("Auto-confirm failed for order %s: %s", order.name, e)

        order.sudo().message_post(
            body=_('Service request submitted via portal by %s.') % request.env.user.partner_id.name,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        template = request.env.ref('kuec_service_catalogue.kuec_coordinator_notification_email_v5', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(order.id, force_send=True)
        customer_confirmation = request.env.ref('kuec_service_catalogue.kuec_request_confirmation_template', raise_if_not_found=False)
        if customer_confirmation:
            customer_confirmation.sudo().send_mail(order.id, force_send=True)

        # Process any doc files uploaded directly in the wizard form
        if not wink_is_bundle:
            import base64 as _b64
            doc_files = request.httprequest.files
            # Look for keys like doc_file_<doc_id>
            for key in list(doc_files.keys()):
                if not key.startswith('doc_file_'):
                    continue
                doc_id_str = key[len('doc_file_'):]
                req_name = post.get(f'doc_req_name_{doc_id_str}', doc_id_str.replace('_', ' '))
                uploaded = doc_files.getlist(key)
                for uf in uploaded:
                    if uf and uf.filename:
                        content = uf.read()
                        if content:
                            request.env['ir.attachment'].sudo().create({
                                'name': uf.filename,
                                'res_model': 'sale.order',
                                'res_id': order.id,
                                'datas': _b64.b64encode(content).decode(),
                                'mimetype': uf.content_type or 'application/octet-stream',
                                'description': f'Required doc: {req_name}',
                            })

        self._wizard_clear_draft()
        if has_required_docs:
            return request.redirect(f'/my/requests/{order.id}?submitted=1&needs_docs=1')
        # Bundles: show order summary + T&C + Accept & Pay before going to payment
        if wink_is_bundle and is_auto_confirm:
            return request.redirect(f'/my/requests/{order.id}?bundle_review=1')
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

        # GOV-001: Lazy activation heal — fire for any entitlement whose gov charge invoice
        # is paid but wink_gov_charge_invoice_id is still set (activation hook missed or
        # concurrent race rolled back). Covers payment gateway returns, backend payments,
        # and Request Again flows. No qty check — action_gov_charge_paid clears the link
        # as its first step so this is idempotent across concurrent page loads.
        # IMPORTANT: use cr.savepoint() so a DB-level error (e.g. SerializationFailure)
        # rolls back only this operation — not the whole transaction — allowing the page
        # to continue rendering normally.
        if order.wink_entitlement_ids:
            for _ent in order.wink_entitlement_ids.sudo():
                inv = _ent.wink_gov_charge_invoice_id
                if inv and inv.payment_state in ('paid', 'in_payment'):
                    try:
                        with request.env.cr.savepoint():
                            _ent.sudo().action_gov_charge_paid()
                    except Exception:
                        pass

        # Build per-entitlement prereqs for activation modal (docs info + employees)
        entitlement_prereqs = {}
        if order.wink_entitlement_ids:
            partner_emp = order.partner_id.commercial_partner_id
            modal_employees = request.env['kuec.employee.directory'].sudo().search([
                ('partner_id', '=', partner_emp.id)
            ])
            for ent in order.wink_entitlement_ids:
                next_activation = (ent.qty_activated or 0) + 1
                doc_items = []
                if ent.service_product_id:
                    for req in ent.service_product_id.kuec_document_ids:
                        doc_items.append({
                            'req_id': req.id,
                            'name': req.name or '',
                        })
                requires_emps = bool(getattr(ent.service_product_id, 'requires_employee_selection', False))
                svc = ent.service_product_id
                has_gov = bool(getattr(svc, 'wink_has_gov_charge', False))
                gov_charge_per_emp = float(getattr(svc, 'wink_default_gov_charge', 0.0) or 0.0)
                entitlement_prereqs[ent.id] = {
                    'docs_ok': True,
                    'doc_items': doc_items,
                    'requires_employees': requires_emps,
                    'employees': modal_employees,
                    'can_activate': True,
                    'next_activation': next_activation,
                    'has_gov_charge': has_gov,
                    'gov_charge_per_employee': gov_charge_per_emp,
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
        retainer_plans_for_change = recurring_lines
        retainer_allow_plan_change = False  # Subscription group removed

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
                # Exclude gov charge lines — they are separate sibling records;
                # build a lookup from service line id → its gov charge sibling.
                gov_by_service = {
                    l.wink_service_line_id.id: l
                    for l in ent.activated_line_ids
                    if l.is_gov_charge_pending and l.wink_service_line_id
                }
                lines = ent.activated_line_ids.filtered(lambda l: not l.is_gov_charge_pending)
                rows = []
                for idx, line in enumerate(lines):
                    gov = gov_by_service.get(line.id)
                    gov_state = 'none'
                    gov_amount = 0.0
                    gov_currency = order.currency_id.name if order.currency_id else ''
                    if gov:
                        if gov.qty_invoiced > 0:
                            gov_state = 'paid'
                        elif gov.price_unit > 0:
                            gov_state = 'confirmed'
                        else:
                            gov_state = 'pending'
                        gov_amount = gov.price_unit
                    rows.append({
                        'line_id': line.id,
                        'name': line.name or line.product_id.name or '',
                        'is_complete': line_completion.get(line.id, False),
                        'index': idx + 1,
                        'gov_state': gov_state,
                        'gov_amount': gov_amount,
                        'gov_currency': gov_currency,
                    })
                bundle_activation_map[ent.id] = rows
        except Exception:
            bundle_activation_map = {}

        # Per-entitlement rating map {ent_id: rating_record} — shown on the service row
        bundle_rating_map = {}
        try:
            entitlements = order.wink_entitlement_ids
            if entitlements:
                all_lines = entitlements.mapped('activated_line_ids')
                if all_lines:
                    ent_tasks = request.env['project.task'].sudo().search([
                        ('sale_line_id', 'in', all_lines.ids),
                    ])
                    if ent_tasks:
                        ratings = request.env['rating.rating'].sudo().search([
                            ('res_model', '=', 'project.task'),
                            ('res_id', 'in', ent_tasks.ids),
                            ('consumed', '=', True),
                        ])
                        rating_by_task = {r.res_id: r for r in ratings}
                        tasks_by_line = {}
                        for t in ent_tasks:
                            tasks_by_line.setdefault(t.sale_line_id.id, []).append(t)
                        for ent in entitlements:
                            for line in ent.activated_line_ids:
                                for task in tasks_by_line.get(line.id, []):
                                    if task.id in rating_by_task:
                                        bundle_rating_map[ent.id] = rating_by_task[task.id]
                                        break
                                if ent.id in bundle_rating_map:
                                    break
        except Exception:
            bundle_rating_map = {}

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
        # 'pending' is intentionally excluded — it means the customer visited the payment page
        # but the transaction is not confirmed yet. Including it caused the payment block to
        # disappear prematurely when a payment was initiated but failed (e.g. card declined).
        tx_paid = order.transaction_ids.filtered(lambda tx: tx.state in ('authorized', 'done'))
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

        # Gov charges: compute display state for portal
        # 'none'      — no gov charge lines on this order
        # 'pending'   — charge flagged but coordinator has not yet set the amount
        # 'confirmed' — amount set, customer can pay
        # 'paid'      — gov charge invoice paid
        gov_charge_state = 'none'
        gov_charge_total = 0.0
        gov_charge_currency = order.currency_id.name if order.currency_id else ''
        try:
            gov_lines = order.order_line.filtered(lambda l: l.is_gov_charge_pending)
            if gov_lines:
                # Only consider lines not yet invoiced — each re-request creates a new
                # gov charge line; already-paid lines must be ignored so the new
                # unpaid line drives the state correctly.
                uninvoiced = gov_lines.filtered(lambda l: l.qty_invoiced == 0)
                if not uninvoiced:
                    # All gov charge lines have been invoiced and paid
                    gov_charge_state = 'paid'
                else:
                    unpriced = uninvoiced.filtered(lambda l: l.price_unit == 0)
                    priced = uninvoiced.filtered(lambda l: l.price_unit > 0)
                    if unpriced:
                        gov_charge_state = 'pending'
                    elif priced:
                        gov_charge_total = sum(priced.mapped('price_unit'))
                        gov_charge_state = 'confirmed'
        except Exception:
            pass

        # Bundle flag — used in template render context below
        wink_is_bundle = bool(product and getattr(product, 'wink_is_bundle', False))

        # Portal stage string — drives the 5-step stepper and action bar
        # Option B: completed when all linked project tasks are in a closed stage.
        # sale_project adds tasks_count + closed_task_count on sale.order.
        def _all_tasks_done(so):
            """Return True when every project task linked to the SO is in a closed stage."""
            try:
                count = so.sudo().tasks_count
                closed = so.sudo().closed_task_count
                return count > 0 and closed >= count
            except Exception:
                return False

        if order.state == 'cancel' or is_closed_or_cancelled:
            portal_stage = 'cancelled'
        elif order.state == 'done' or (order.state == 'sale' and not wink_is_bundle and _all_tasks_done(order)):
            portal_stage = 'completed'
        elif order.state == 'sale':
            if wink_is_bundle or is_retainer:
                # Bundle + retainer: require coordinator activation call before going live
                if getattr(order, 'wink_bundle_activated', False):
                    portal_stage = 'active'          # coordinator activated → fully live
                else:
                    portal_stage = 'pending_activation'  # paid but awaiting confirmation call
            else:
                # Project-based: pending_activation until paid, then confirmed
                portal_stage = 'confirmed' if is_paid else 'pending_activation'
        elif order.wink_price_confirmed:
            portal_stage = 'ready_for_payment'
        else:
            # Submitted → Processing only when product has required documents
            _has_req_docs = bool(
                product and product.kuec_document_ids.filtered(
                    lambda d: d.requirement == 'required'
                )
            ) if not wink_is_bundle else False
            portal_stage = 'processing' if _has_req_docs else 'submitted'

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

        # Safe recurrence name — try multiple sources (subscription module may/may not be installed)
        recurrence_name = ''
        try:
            # 1. Native recurrence_id (sale_subscription)
            rec = getattr(order, 'recurrence_id', None)
            if rec:
                recurrence_name = rec.name or ''
            # 2. Fallback: look up via wink_recurring_pricing_id (integer ID)
            if not recurrence_name and order.wink_recurring_pricing_id:
                for _model in ('product.pricing', 'sale.subscription.pricing'):
                    try:
                        pricing = request.env[_model].sudo().browse(order.wink_recurring_pricing_id)
                        if pricing.exists():
                            rec_ref = getattr(pricing, 'recurrence_id', None) or getattr(pricing, 'plan_id', None)
                            recurrence_name = (rec_ref and rec_ref.name) or ''
                            if recurrence_name:
                                break
                    except Exception:
                        pass
            # 3. Fallback: plan_id / recurring_plan_id on the order
            if not recurrence_name:
                plan = getattr(order, 'plan_id', None) or getattr(order, 'recurring_plan_id', None)
                if plan:
                    recurrence_name = getattr(plan, 'name', '') or ''
        except Exception:
            pass

        required_docs = product.kuec_document_ids.sorted('sequence') if product and not wink_is_bundle else request.env['kuec.service.document']
        has_required_docs = bool(required_docs.filtered(lambda d: d.requirement == 'required'))

        # UI-PROC-001: Fetch document submissions for the processing stage status card
        doc_submissions = request.env['kuec.document.submission']
        if portal_stage == 'processing':
            doc_submissions = request.env['kuec.document.submission'].sudo().search([
                ('order_id', '=', order.id),
            ])

        # Project-based standalone: fetch tasks + project for the detail card
        pb_tasks = request.env['project.task']
        pb_project = None
        if product and not wink_is_bundle and not is_retainer:
            try:
                pb_tasks = request.env['project.task'].sudo().search([
                    ('sale_order_id', '=', order.id),
                ])
                if pb_tasks:
                    pb_project = pb_tasks[0].project_id
                elif order.sudo().project_ids:
                    pb_project = order.sudo().project_ids[0]
            except Exception:
                pass

        # I-4: Rating token for "Rate this Service" button on completed standalone
        rating_token = None
        if portal_stage == 'completed' and pb_tasks:
            try:
                unconsumed = request.env['rating.rating'].sudo().search([
                    ('res_model', '=', 'project.task'),
                    ('res_id', 'in', pb_tasks.ids),
                    ('consumed', '=', False),
                ], limit=1)
                if unconsumed:
                    rating_token = unconsumed.access_token
            except Exception:
                pass

        return request.render('kuec_service_catalogue.wink_request_confirmation', {
            'order': order,
            'product': product,
            'payment_pending': kwargs.get('payment') == 'pending',
            'bundle_requested': kwargs.get('bundle_requested') == '1',
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
            'bundle_rating_map': bundle_rating_map,
            'retainer_cancelled': kwargs.get('retainer_cancelled') == '1',
            'quote_rejected': kwargs.get('rejected') == '1',
            'quote_error': kwargs.get('error'),
            'quote_message': quote_message,
            'is_closed_or_cancelled': is_closed_or_cancelled,
            'close_reason_name': close_reason_name,
            'cancellation_proration': cancellation_proration,
            'cancellation_credit_policy_label': cancellation_credit_policy_label,
            'is_paid': is_paid,
            'portal_stage': portal_stage,
            'wink_is_bundle': wink_is_bundle,
            'required_docs': required_docs,
            'has_required_docs': has_required_docs,
            'doc_submissions': doc_submissions,
            'recurrence_name': recurrence_name,
            'activity_items': activity_items,  # UI-012
            'submitted': kwargs.get('submitted') == '1',  # UI-013
            # show bundle T&C + Accept & Pay: on first submission OR any time bundle is confirmed but unpaid
            'bundle_review': (
                kwargs.get('bundle_review') == '1'
                or (wink_is_bundle and order.state == 'sale' and not is_paid)
            ),
            'needs_docs': kwargs.get('needs_docs') == '1',  # UI-013: show doc upload CTA on review page
            # WF-BND-002: activation error message when activation blocked (docs/employees)
            'activation_error': kwargs.get('activation_error') or request.params.get('activation_error', '') or '',
            'activation_pending': kwargs.get('activation_pending') == '1',
            # GOV-001: gov charge payment status messages
            'gov_charge_pending': kwargs.get('gov_charge_pending') == '1',
            'gov_wallet_paid': kwargs.get('gov_wallet_paid') == '1',
            'gov_paid': kwargs.get('gov_paid') == '1',
            'gov_charge_error': kwargs.get('gov_charge_error') or '',
            'gov_charge_error_balance': kwargs.get('balance') or '',
            'gov_charge_error_required': kwargs.get('required') or '',
            # Activation modal state
            'entitlement_prereqs': entitlement_prereqs,
            'open_modal': kwargs.get('open_modal', ''),
            'doc_uploaded': kwargs.get('doc_uploaded') == '1',
            # UI-BUG-004 (FB-004): partial payment display
            'amount_due_display': amount_due_display,
            'amount_paid_display': amount_paid_display,
            'has_partial_payment': has_partial_payment,
            'next_due_date': next_due_date,
            'pb_tasks': pb_tasks,
            'pb_project': pb_project,
            'rating_token': rating_token,
            'gov_charge_state': gov_charge_state,
            'gov_charge_total': gov_charge_total,
            'gov_charge_currency': gov_charge_currency,
        })

    @http.route('/my/requests/<int:order_id>/pay-gov-charges', type='http', auth='user', website=True, methods=['GET'])
    def request_pay_gov_charges(self, order_id, **kwargs):
        """Create (or find) an invoice for confirmed gov charge lines and redirect to payment.

        Workflow:
            1. Validate the order belongs to the current portal user.
            2. Find gov charge lines with a confirmed price (price_unit > 0).
            3. If an unpaid invoice already exists for those lines, use it.
            4. Otherwise create and post a new invoice for the gov charge lines only.
            5. Redirect the customer to the standard Odoo invoice portal page.
        """
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        # Use qty_to_invoice > 0 — our _compute_qty_to_invoice override already
        # sets this correctly: gov lines with price>0 get qty_to_invoice = qty - qty_invoiced.
        # This naturally excludes lines already fully invoiced and lines with no price yet.
        priced_gov_lines = order.order_line.filtered(
            lambda l: l.is_gov_charge_pending and l.qty_to_invoice > 0
        )
        if not priced_gov_lines:
            return request.redirect(f'/my/requests/{order_id}?error=gov_charge_not_ready')

        # Reuse an existing invoice ONLY if every one of its lines
        # maps exclusively to gov charge lines — never reuse a full-order invoice.
        gov_line_ids = set(priced_gov_lines.ids)
        existing_inv = None
        for inv in order.invoice_ids.filtered(lambda i: i.state != 'cancel'):
            product_lines = inv.invoice_line_ids.filtered(
                lambda il: il.display_type not in ('line_section', 'line_note')
            )
            if not product_lines:
                continue
            all_gov = all(
                il.sale_line_ids and all(sl.id in gov_line_ids for sl in il.sale_line_ids)
                for il in product_lines
            )
            if all_gov:
                existing_inv = inv
                break

        if existing_inv:
            invoice = existing_inv.sudo()
        else:
            # Build a targeted invoice for ONLY the confirmed gov charge lines.
            # Using _prepare_invoice() + _prepare_invoice_line() ensures correct
            # accounts, taxes, journal, and partner are set via standard Odoo logic
            # without pulling in any other invoiceable lines from the order.
            inv_vals = order.sudo()._prepare_invoice()
            inv_vals['invoice_line_ids'] = [
                (0, 0, line.sudo()._prepare_invoice_line())
                for line in priced_gov_lines
            ]
            invoice = request.env['account.move'].sudo().create(inv_vals)

        if invoice.state == 'draft':
            invoice.sudo().action_post()

        return request.redirect(f'/my/requests/{order_id}/gov-charges-payment?invoice_id={invoice.id}')

    @http.route('/my/requests/<int:order_id>/gov-charges-payment', type='http', auth='user', website=True, methods=['GET'])
    def request_gov_charges_payment_page(self, order_id, invoice_id=None, **kwargs):
        """Show payment method choice page for government charge invoice.

        Displays the invoice amount alongside the customer's eWallet balance and
        lets them choose between eWallet payment (instant, no redirect) or
        standard card payment (Odoo native invoice page).
        """
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        invoice = None
        if invoice_id:
            try:
                invoice = request.env['account.move'].sudo().browse(int(invoice_id))
                if not invoice.exists() or invoice.partner_id.commercial_partner_id != order.partner_id.commercial_partner_id:
                    invoice = None
            except Exception:
                invoice = None

        if not invoice:
            return request.redirect(f'/my/requests/{order_id}')

        partner = request.env.user.partner_id.commercial_partner_id
        wallet_balance = partner.wink_wallet_balance if hasattr(partner, 'wink_wallet_balance') else 0.0
        wallet_journal = request.env['account.journal'].sudo().search(
            [('is_ewallet_journal', '=', True), ('company_id', '=', request.env.company.id)], limit=1
        )
        ewallet_available = bool(wallet_journal)
        error = kwargs.get('error', '')
        success = kwargs.get('success', '')

        return request.render('kuec_service_catalogue.wink_gov_charges_payment_page', {
            'order': order,
            'invoice': invoice,
            'wallet_balance': wallet_balance,
            'wallet_currency': order.currency_id.name if order.currency_id else '',
            'ewallet_available': ewallet_available,
            'error': error,
            'success': success,
        })

    @http.route('/my/requests/<int:order_id>/gov-charges-payment/wallet', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def request_gov_charges_pay_wallet(self, order_id, invoice_id=None, **post):
        """Process eWallet payment for a government charge invoice.

        Workflow:
            1. Validate the invoice belongs to this order and is unpaid.
            2. Check the customer has sufficient wallet balance.
            3. Register payment via the WEWL journal (account.payment.register).
            4. Create a kuec.wallet.transaction debit record.
            5. Redirect back to the request page with a success message.
        """
        import logging as _log
        _logger_w = _log.getLogger(__name__)

        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        try:
            invoice = request.env['account.move'].sudo().browse(int(invoice_id or 0))
            if not invoice.exists():
                raise ValueError('Invoice not found')
        except Exception:
            return request.redirect(f'/my/requests/{order_id}')

        # Security: verify the invoice belongs to this order — prevents IDOR where a portal
        # user submits a forged invoice_id from another customer's order.
        if invoice.id not in order.invoice_ids.ids:
            raise NotFound()

        base_url = f'/my/requests/{order_id}/gov-charges-payment?invoice_id={invoice.id}'

        partner = request.env.user.partner_id.commercial_partner_id
        wallet_balance = partner.wink_wallet_balance if hasattr(partner, 'wink_wallet_balance') else 0.0
        amount_due = invoice.amount_residual

        if amount_due <= 0:
            return request.redirect(f'{base_url}&success=already_paid')

        if wallet_balance < amount_due:
            return request.redirect(
                f'{base_url}&error=insufficient_balance'
            )

        wallet_journal = request.env['account.journal'].sudo().search(
            [('is_ewallet_journal', '=', True), ('company_id', '=', request.env.company.id)], limit=1
        )
        if not wallet_journal:
            return request.redirect(f'{base_url}&error=no_wallet_journal')

        try:
            memo = _('Gov. Charges — %s') % (invoice.name or order.name)
            payment_register = request.env['account.payment.register'].sudo().with_context(
                active_model='account.move',
                active_ids=invoice.ids,
            ).create({
                'journal_id': wallet_journal.id,
                'amount': amount_due,
                'currency_id': invoice.currency_id.id,
                'communication': memo,
                'payment_date': fields.Date.today(),
            })
            payment_register.action_create_payments()

            payment = invoice.reconciled_payment_ids.filtered(
                lambda p: p.journal_id == wallet_journal
            ).sorted('id', reverse=True)[:1]
            move_id = payment.move_id.id if payment and payment.move_id else False

            request.env['kuec.wallet.transaction'].sudo().create({
                'partner_id': partner.id,
                'transaction_type': 'payment',
                'amount': -amount_due,
                'description': memo,
                'currency_id': invoice.currency_id.id,
                'order_id': order.id,
                'move_id': move_id,
            })
        except Exception:
            _logger_w.warning('eWallet payment failed for invoice %s', invoice.id, exc_info=True)
            return request.redirect(f'{base_url}&error=payment_failed')

        return request.redirect(f'/my/requests/{order_id}?gov_paid=1')

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
        # Block approval when required documents are not yet approved (bundles: no document restriction)
        try:
            order.sudo().action_confirm()
            order.sudo().message_post(
                body=_("Customer approved this quote from the portal."),
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
        except Exception:
            pass
        # UI-REV-003: skip the intermediate confirmed page; go straight to payment when amount > 0
        if order.amount_total > 0:
            return request.redirect(f'/my/requests/{order_id}/pay')
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
        reject_reason = post.get('reason', '').strip()
        body = _("Customer rejected this quote from the portal.")
        if reject_reason:
            body += _(" Reason: %s") % reject_reason
        order.sudo().message_post(
            body=body,
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
        """RET-005: Plan comparison page with proration preview.
        Subscription group support removed — redirect to request detail."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        product = order.wink_source_product_id
        if not product or product.delivery_model != 'retainer':
            return request.redirect(f'/my/requests/{order_id}')
        return request.redirect(f'/my/requests/{order_id}?error=change_not_available&message=%s' % werkzeug.urls.url_quote(_('Plan change is not available for this service.')))

    def _retainer_change_plan_submit(self, order_id, **post):
        """RET-005: Submit plan change. Subscription group removed — redirect."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        product = order.wink_source_product_id
        if not product or product.delivery_model != 'retainer':
            return request.redirect(f'/my/requests/{order_id}')
        return request.redirect(f'/my/requests/{order_id}?error=change_not_available&message=%s' % werkzeug.urls.url_quote(_('Plan change is not available for this service.')))

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
        end_date = getattr(order, 'next_date', None) or getattr(order, 'next_invoice_date', None)
        start_date = getattr(order, 'start_date', None) or getattr(order, 'wink_bundle_start_date', None)
        show_refund = bool(proration and proration.get('remaining_value', 0) > 0)
        close_reasons = request.env['sale.order.close.reason'].sudo().search([], order='id')

        return request.render('kuec_service_catalogue.wink_retainer_cancel_preview', {
            'order': order,
            'product': product,
            'proration': proration,
            'policy_label': '',
            'end_date': end_date,
            'start_date': start_date,
            'show_refund': show_refund,
            'effective_date_policy': 'immediate',
            'close_reasons': close_reasons,
            'error': kwargs.get('error', ''),
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

        confirm = post.get('confirm_cancel')
        if not confirm:
            return request.redirect(f'/my/requests/{order_id}/retainer/cancel/preview?error=confirm_required')

        reason = post.get('cancel_reason', '').strip() or False
        order.sudo().write({
            'wink_cancellation_requested': True,
            'wink_cancellation_requested_date': odoo_fields.Datetime.now(),
            'wink_cancellation_reason': reason,
            'wink_cancellation_effective_date': effective_date,
        })
        order.sudo().message_post(
            body=_("Customer requested cancellation of this retainer from the portal. Effective date: %s. Reason: %s") % (
                effective_date,
                reason or _('(none)'),
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

        # Wallet balance for the logged-in customer's commercial partner
        wallet_balance = 0.0
        try:
            commercial = request.env.user.partner_id.commercial_partner_id
            wallet_balance = commercial.sudo().wink_wallet_balance or 0.0
        except Exception:
            pass
        render_values['wallet_balance'] = wallet_balance
        wallet_amount_due = payment_values.get('amount', order.amount_total)
        render_values['wallet_sufficient'] = wallet_balance >= wallet_amount_due
        render_values['wallet_amount_due'] = wallet_amount_due

        return request.render('kuec_service_catalogue.wink_payment_page_v2', render_values)

    @http.route('/my/requests/<int:order_id>/pay-wallet', type='http', auth='user', website=True, methods=['POST'])
    def request_pay_wallet(self, order_id, **kwargs):
        """Process eWallet payment: deduct balance, create invoice + payment, mark order paid."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        if order.state != 'sale':
            return request.redirect(f'/my/requests/{order_id}?error=payment_not_available')

        commercial = request.env.user.partner_id.commercial_partner_id
        wallet_balance = commercial.sudo().wink_wallet_balance or 0.0
        amount_due = order.amount_total

        # Compute actual amount due (minus any partial payments)
        try:
            posted_invs = order.invoice_ids.filtered(lambda m: m.state == 'posted')
            if posted_invs:
                amount_due = sum(posted_invs.mapped('amount_residual'))
        except Exception:
            pass

        if wallet_balance < amount_due:
            return request.redirect(f'/my/requests/{order_id}/pay?error=insufficient_wallet')

        if amount_due <= 0:
            # Invoice already fully paid — skip payment, just record wallet debit if needed
            return request.redirect(f'/my/requests/{order_id}?payment=success')

        # Always resolve the eWallet journal via is_ewallet_journal flag — never via env.ref()
        # because env.ref() returns the original XML-created journal even after the coordinator
        # changes which journal is the active eWallet journal.
        journal = request.env['account.journal'].sudo().search([
            ('is_ewallet_journal', '=', True), ('company_id', '=', order.company_id.id)
        ], limit=1)
        if not journal:
            return request.redirect(f'/my/requests/{order_id}/pay?error=wallet_journal_missing')

        try:
            # Create invoice if none exists — all ops via sudo (portal user has no accounting access)
            invoices = order.sudo().invoice_ids.filtered(lambda inv: inv.state != 'cancel')
            if not invoices:
                order.sudo()._create_invoices(final=True)
                invoices = order.sudo().invoice_ids.filtered(lambda inv: inv.state != 'cancel')

            invoice = invoices[0].sudo()
            if invoice.state == 'draft':
                invoice.action_post()

            # Verify there is still an outstanding balance on this invoice
            if invoice.amount_residual <= 0:
                return request.redirect(f'/my/requests/{order_id}?payment=success')

            # Snapshot the amount before posting so wallet debit matches payment exactly
            payment_amount = invoice.amount_residual

            # Ensure the payment method line has a payment_account_id so Odoo 18
            # can compute outstanding_account_id and generate the journal entry.
            pm_line = journal.inbound_payment_method_line_ids.filtered(
                lambda l: l.code == 'manual'
            )[:1]
            if pm_line and not pm_line.payment_account_id and journal.default_account_id:
                pm_line.sudo().write({'payment_account_id': journal.default_account_id.id})

            payment = request.env['account.payment'].sudo().create({
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': order.partner_id.id,
                'amount': payment_amount,
                'journal_id': journal.id,
                'currency_id': order.currency_id.id,
                'memo': f'eWallet — {order.name}',
                'payment_method_line_id': pm_line.id if pm_line else False,
            })
            payment.action_post()

            # Reconcile payment with invoice receivable lines
            receivable_lines = invoice.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            )
            payment_receivable = payment.move_id.line_ids.filtered(
                lambda l: l.account_id.account_type == 'asset_receivable' and not l.reconciled
            ) if payment.move_id else request.env['account.move.line']
            if receivable_lines and payment_receivable:
                (receivable_lines + payment_receivable).reconcile()

            # Record wallet debit inside the try block so it only persists if the
            # payment posted and reconciled successfully. move_id links the GL entry
            # for full audit traceability.
            request.env['kuec.wallet.transaction'].sudo().create({
                'partner_id': commercial.id,
                'transaction_type': 'payment',
                'amount': -payment_amount,
                'description': f'eWallet — {order.name}',
                'order_id': order.id,
                'currency_id': order.currency_id.id,
                'move_id': payment.move_id.id if payment.move_id else False,
            })

        except Exception as e:
            _logger = __import__('logging').getLogger(__name__)
            _logger.error('eWallet payment failed for order %s: %s', order.name, e, exc_info=True)
            return request.redirect(f'/my/requests/{order_id}/pay?error=wallet_payment_failed')

        order.sudo().message_post(
            body=f'Payment of {order.currency_id.symbol}{amount_due:,.2f} processed via WINK eWallet.',
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        return request.redirect(f'/my/requests/{order_id}?payment=success')

    @http.route('/my/requests/<int:order_id>/documents', type='http', auth='user', website=True)
    def request_documents(self, order_id, **kw):
        """Legacy document page — redirect to request detail (documents now go to chatter)."""
        return request.redirect(f'/my/requests/{order_id}')

    @http.route('/my/requests/<int:order_id>/documents/upload', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def upload_document(self, order_id, **post):
        """Upload one or more files for a document requirement — stored as M2M ir.attachment on the order."""
        import base64

        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        doc_req_name = post.get('doc_req_name', '').strip()

        # Support multi-file (name="doc_files") and legacy single-file (name="doc_file")
        uploaded_files = request.httprequest.files.getlist('doc_files') or []
        if not uploaded_files:
            single = request.httprequest.files.get('doc_file')
            if single and single.filename:
                uploaded_files = [single]

        if not uploaded_files:
            return request.redirect(f'/my/requests/{order_id}')

        # Find task(s) linked to this order — attachments should live on the task
        tasks = request.env['project.task'].sudo().search([
            ('sale_order_id', '=', order_id),
        ])
        target = tasks[0] if tasks else order

        attachment_ids = []
        file_names = []
        for uploaded in uploaded_files:
            if not uploaded or not uploaded.filename:
                continue
            file_data = base64.b64encode(uploaded.read())
            att = request.env['ir.attachment'].sudo().create({
                'name': uploaded.filename,
                'datas': file_data,
                'res_model': target._name,
                'res_id': target.id,
                'mimetype': uploaded.content_type or 'application/octet-stream',
                'type': 'binary',
            })
            attachment_ids.append(att.id)
            file_names.append(uploaded.filename)

        if attachment_ids:
            label = doc_req_name or _('Document')
            body = _('Document(s) uploaded for <b>%(req)s</b>: %(files)s') % {
                'req': label,
                'files': ', '.join(file_names),
            }
            target.sudo().message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
                attachment_ids=attachment_ids,
            )
            # Also notify on order chatter if attachments went to task
            if target._name == 'project.task':
                order.sudo().message_post(
                    body=_('Document(s) uploaded for <b>%(req)s</b> and linked to task <b>%(task)s</b>: %(files)s') % {
                        'req': label,
                        'task': target.name,
                        'files': ', '.join(file_names),
                    },
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
        return request.redirect(f'/my/requests/{order_id}?doc_uploaded=1')

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
        # GET: redirect back to detail page (activation happens via modal POST)
        if request.httprequest.method == 'GET':
            return request.redirect(f'/my/requests/{order_id}')

        # POST: perform sub-service activation
        employee_ids = []
        for val in request.httprequest.form.getlist('employee_ids'):
            if str(val).isdigit():
                employee_ids.append(int(val))

        # Create new employee from inline form if provided
        new_emp_name = (post.get('new_emp_name') or '').strip()
        if new_emp_name:
            partner = request.env.user.partner_id.commercial_partner_id
            new_emp = request.env['kuec.employee.directory'].sudo().create({
                'name': new_emp_name,
                'job_title': (post.get('new_emp_job') or '').strip() or False,
                'email': (post.get('new_emp_email') or '').strip() or False,
                'mobile': (post.get('new_emp_mobile') or '').strip() or False,
                'partner_id': partner.id,
            })
            employee_ids.append(new_emp.id)

        # Collect inline attachment uploads (bnd_attach_<req_id>_<ent_id>)
        uploaded_attachments = []
        for key, file_storage in request.httprequest.files.items():
            if key.startswith('bnd_attach_') and file_storage and file_storage.filename:
                parts = key.split('_')
                req_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
                file_content = file_storage.read()
                if file_content and req_id:
                    uploaded_attachments.append({
                        'req_id': req_id,
                        'filename': file_storage.filename,
                        'content': file_content,
                        'mimetype': file_storage.content_type or 'application/octet-stream',
                    })

        # GOV-001: If a gov charge invoice already exists, handle before creating a new one.
        # IMPORTANT: Do NOT call action_gov_charge_paid() here — the _reconcile_after_done()
        # hook may be running concurrently, and two simultaneous calls cause a PostgreSQL
        # SerializationFailure on the M2M delete. Let the lazy heal on page load handle it.
        existing_inv = entitlement.wink_gov_charge_invoice_id
        if existing_inv:
            if existing_inv.payment_state in ('paid', 'in_payment'):
                # Invoice already paid — redirect back; lazy heal on page load will activate.
                return request.redirect(f'/my/requests/{order_id}?bundle_requested=1')
            else:
                # Invoice pending payment — tell customer to pay it first.
                return request.redirect(f'/my/requests/{order_id}?gov_charge_pending=1')

        # GOV-001: If service requires government charges, create invoice instead of activating directly
        svc_product = entitlement.service_product_id
        if getattr(svc_product, 'wink_has_gov_charge', False):
            gov_charge_per_emp = float(getattr(svc_product, 'wink_default_gov_charge', 0.0) or 0.0)
            num_employees = max(len(employee_ids), 1)
            total_gov_charge = gov_charge_per_emp * num_employees
            variant = svc_product.product_variant_ids[:1]
            inv_line = {
                'name': 'Government Charges: %s' % entitlement.name,
                'quantity': 1,
                'price_unit': total_gov_charge,
                'tax_ids': [(5, 0, 0)],
            }
            if variant:
                inv_line['product_id'] = variant.id
            # Link invoice line to first SO line so invoice appears in SO's invoice smart button
            if order.order_line:
                inv_line['sale_line_ids'] = [(4, order.order_line[:1].id)]
            gov_invoice = request.env['account.move'].sudo().create({
                'move_type': 'out_invoice',
                'partner_id': order.partner_id.id,
                'invoice_date': date.today(),
                'invoice_origin': order.name,
                'ref': 'Gov Charge - %s - %s' % (entitlement.name, order.name),
                'invoice_line_ids': [(0, 0, inv_line)],
            })
            try:
                gov_invoice.sudo().action_post()
            except Exception:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "GOV-001: Failed to post gov charge invoice for entitlement %s",
                    entitlement.id, exc_info=True,
                )
            entitlement.sudo().write({
                'wink_gov_charge_invoice_id': gov_invoice.id,
                'wink_gov_charge_per_employee': gov_charge_per_emp,
                'wink_pending_employee_ids': [(6, 0, employee_ids)] if employee_ids else [(5, 0, 0)],
            })
            order.sudo().message_post(
                body=_(
                    'Government charge invoice <b>%(inv)s</b> created for <b>%(svc)s</b>. '
                    'Amount: %(total)s AED. Activation is pending payment.'
                ) % {
                    'inv': gov_invoice.name or '',
                    'svc': entitlement.name or '',
                    'total': '%.2f' % total_gov_charge,
                },
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )
            return request.redirect(f'/my/requests/{order_id}?gov_charge_pending=1')

        try:
            entitlement.action_activate(employee_ids=employee_ids)

            # Post uploaded attachments — always target the task, fall back to order
            if uploaded_attachments:
                import base64
                # Find task linked to this order (most reliable lookup)
                task = request.env['project.task'].sudo().search([
                    ('sale_order_id', '=', order.id),
                ], limit=1)
                chatter_record = task if task else order

                for att in uploaded_attachments:
                    attachment = request.env['ir.attachment'].sudo().create({
                        'name': att['filename'],
                        'datas': base64.b64encode(att['content']),
                        'mimetype': att['mimetype'],
                        'res_model': chatter_record._name,
                        'res_id': chatter_record.id,
                    })
                    chatter_record.sudo().message_post(
                        body=_('Document uploaded: <b>%s</b>') % att['filename'],
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                        attachment_ids=[attachment.id],
                    )
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

        # Known gov charges: redirect straight to payment so the customer
        # can pay the government charge invoice immediately after activation.
        product = entitlement.service_product_id
        if (getattr(product, 'requires_government_charges', False) and
                getattr(product, 'gov_charge_is_known', False)):
            return request.redirect(f'/my/requests/{order_id}/pay-gov-charges')

        return request.redirect(
            f'/my/requests/{order_id}'
            f'?bundle_requested=1'
        )

    # ── GOV-001: eWallet payment for government charge invoice ──
    @http.route(
        '/my/requests/<int:order_id>/gov-charge/<int:entitlement_id>/wallet-pay',
        type='http', auth='user', website=True,
        methods=['POST'], csrf=True)
    def gov_charge_wallet_pay(self, order_id, entitlement_id, **post):
        """Pay the pending government charge invoice using the customer's eWallet balance.

        Workflow:
            1. Validate access and locate the gov charge invoice.
            2. Check wallet balance is sufficient to cover the invoice amount.
            3. Register an account.payment via the eWallet journal (WEWL).
            4. Record a kuec.wallet.transaction debit linked to the payment JV.
            5. Redirect to the request detail page.
        """
        import logging as _log
        _logger = _log.getLogger(__name__)

        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of',
             request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        entitlement = request.env['wink.bundle.entitlement'].sudo().search([
            ('id', '=', entitlement_id),
            ('order_id', '=', order_id),
        ], limit=1)
        if not entitlement:
            raise NotFound()

        invoice = entitlement.wink_gov_charge_invoice_id
        if not invoice or not invoice.exists():
            return request.redirect(f'/my/requests/{order_id}?gov_charge_error=no_invoice')

        if invoice.payment_state in ('paid', 'in_payment'):
            return request.redirect(f'/my/requests/{order_id}?gov_charge_error=already_paid')

        partner = order.partner_id
        wallet_balance = getattr(partner, 'wink_wallet_balance', 0.0) or 0.0
        amount_due = invoice.amount_residual or 0.0

        if amount_due <= 0:
            return request.redirect(f'/my/requests/{order_id}?gov_charge_error=already_paid')

        if wallet_balance < amount_due:
            return request.redirect(
                f'/my/requests/{order_id}'
                f'?gov_charge_error=insufficient_balance'
                f'&balance={werkzeug.urls.url_quote("%.2f" % wallet_balance)}'
                f'&required={werkzeug.urls.url_quote("%.2f" % amount_due)}'
            )

        wallet_journal = request.env['account.journal'].sudo().search(
            [('is_ewallet_journal', '=', True),
             ('company_id', '=', request.env.company.id)],
            limit=1,
        )
        if not wallet_journal:
            return request.redirect(f'/my/requests/{order_id}?gov_charge_error=no_wallet_journal')

        try:
            memo = 'Gov Charge (eWallet) - %s - %s' % (entitlement.name, order.name)
            payment_register = request.env['account.payment.register'].sudo().with_context(
                active_model='account.move',
                active_ids=invoice.ids,
            ).create({
                'journal_id': wallet_journal.id,
                'amount': amount_due,
                'currency_id': invoice.currency_id.id,
                'communication': memo,
                'payment_date': date.today(),
            })
            payment_register.action_create_payments()

            payment = invoice.reconciled_payment_ids.filtered(
                lambda p: p.journal_id == wallet_journal
            ).sorted('id', reverse=True)[:1]
            move_id = payment.move_id.id if payment and payment.move_id else False

            request.env['kuec.wallet.transaction'].sudo().create({
                'partner_id': partner.id,
                'transaction_type': 'payment',
                'amount': -amount_due,
                'description': memo,
                'currency_id': invoice.currency_id.id,
                'order_id': order.id,
                'move_id': move_id,
            })

            # GOV-001: Explicitly trigger activation here — do NOT rely on write() hook alone.
            # Reason: Odoo 18 flushes stored computed fields (payment_state) via _write(),
            # bypassing our write() override. entitlement.state also re-computes to 'available'
            # immediately after payment, so checking state is unreliable.
            # Instead: check wink_gov_charge_invoice_id directly — if still set, not yet activated.
            entitlement.invalidate_recordset(['wink_gov_charge_invoice_id'])
            if entitlement.wink_gov_charge_invoice_id:
                entitlement.sudo().action_gov_charge_paid()

        except Exception:
            _logger.warning(
                "GOV-001: eWallet payment failed for gov charge invoice %s (entitlement %s)",
                invoice.id, entitlement_id, exc_info=True,
            )
            return request.redirect(f'/my/requests/{order_id}?gov_charge_error=payment_failed')

        return request.redirect(f'/my/requests/{order_id}?gov_wallet_paid=1')


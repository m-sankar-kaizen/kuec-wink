# -*- coding: utf-8 -*-

import base64
import logging
import re
import werkzeug
from werkzeug.urls import url_encode
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html2plaintext
from werkzeug.exceptions import NotFound


_logger = logging.getLogger(__name__)


class WinkCatalogue(http.Controller):

    @http.route(['/services'], type='http', auth='public', website=True, sitemap=True)
    def service_catalogue(self, **kwargs):
        Product = request.env['product.template'].sudo()

        # Fix 4: "Packages Only" toggle
        bundles_only = kwargs.get('bundles_only') == '1'
        # "In Your Bundle" toggle — shows only services the user has bundle entitlements for
        bundle_included = kwargs.get('bundle_included') == '1'

        # Base domain — all users see all available services
        # Exclude child/sub-services (commercial_structure='bundled' but NOT a bundle template).
        # Those are only accessible inside a bundle activation, not as standalone catalog items.
        domain = [
            ('available_on_wink', '=', True),
            ('sale_ok', '=', True),
            ('active', '=', True),
            '|',
            ('wink_is_bundle', '=', True),
            ('commercial_structure', '!=', 'bundled'),
        ]

        if bundles_only:
            domain.append(('wink_is_bundle', '=', True))

        # URL Filters
        department_ids = request.httprequest.args.getlist('department_ids')
        if department_ids:
            domain.append(('department_ids', 'in', [int(d) for d in department_ids if d.isdigit()]))
            
        nature_id = request.httprequest.args.get('nature_id')
        if nature_id and nature_id.isdigit():
            domain.append(('nature_id', '=', int(nature_id)))

        delivery_model = kwargs.get('delivery_model')
        if delivery_model:
            domain.append(('delivery_model', '=', delivery_model))

        search = kwargs.get('search')
        if search:
            domain.append(('name', 'ilike', search))
        domain.append(('company_id', 'in', [False, request.website.company_id.id]))

        products = Product.search(domain)

        # Build short descriptions dictionary for template
        short_descs = {}
        for p in products:
            if p.wink_description:
                text = html2plaintext(p.wink_description).strip()
                short_descs[p.id] = text[:117] + '...' if len(text) > 120 else text
            else:
                short_descs[p.id] = ''

        # Sidebar data (CAT-4, CAT-5: departments with product count per department)
        departments = request.env['kuec.department'].sudo().search([('active', '=', True)])
        base_domain = [
            ('available_on_wink', '=', True),
            ('sale_ok', '=', True),
            ('active', '=', True),
            '|',
            ('wink_is_bundle', '=', True),
            ('commercial_structure', '!=', 'bundled'),
        ]
        # Build dept_counts in a single query: fetch all matching products once,
        # then count per department in Python — avoids 1 search_count per department.
        all_products = Product.search(base_domain, order='id asc')
        dept_counts = {dept.id: 0 for dept in departments}
        for p in all_products:
            for dept in p.department_ids:
                if dept.id in dept_counts:
                    dept_counts[dept.id] += 1
        natures = request.env['kuec.service.nature'].sudo().search([('active', '=', True)])
        delivery_models = Product._fields['delivery_model'].selection

        cur_dept = [int(d) for d in department_ids if d.isdigit()]
        cur_nature = int(nature_id) if nature_id and nature_id.isdigit() else None
        active_filter_count = len(cur_dept) + (1 if cur_nature else 0) + (1 if delivery_model else 0)

        # CAT-5: department slug per product for strip/badge color class; slugify robustly
        product_dept_slugs = {}
        for p in products:
            if p.department_ids:
                raw = (p.department_ids[0].name or '').lower()
                slug = raw.replace('&', 'and').replace(' ', '-')
                slug = re.sub(r'[^a-z0-9-]', '', slug)
                slug = re.sub(r'-+', '-', slug).strip('-')
                product_dept_slugs[p.id] = slug or 'other'
            else:
                product_dept_slugs[p.id] = ''

        # Bundle entitlement map: {product_tmpl_id: entitlement_record}
        # Dedup priority: an 'available' entitlement always beats a 'fully_activated' one
        # for the same product so the card surfaces the Activate CTA instead of the
        # "Activated" badge when the user still has an unused slot.
        entitlement_map = {}
        user = request.env.user
        if not user._is_public():
            partner = user.partner_id.commercial_partner_id
            entitlements = request.env['wink.bundle.entitlement'].sudo().search([
                ('order_id.partner_id', 'child_of', partner.id),
                ('order_id.state', '=', 'sale'),
                ('order_id.subscription_state', '!=', '6_churn'),
                ('order_id.wink_bundle_cancelled', '=', False),
                ('state', 'in', ('available', 'fully_activated')),
            ])
            for ent in entitlements:
                if not ent.service_product_id:
                    continue
                pid = ent.service_product_id.id
                existing = entitlement_map.get(pid)
                if existing is None or (existing.state == 'fully_activated' and ent.state == 'available'):
                    entitlement_map[pid] = ent

        # "In Your Bundle" filter — applied as a domain clause so other active filters
        # (department, nature, delivery_model, search) intersect with it instead of being
        # overridden. Rerun the search with the bundle constraint added.
        if bundle_included and entitlement_map:
            bundle_ids = list(entitlement_map.keys())
            # Drop the bundle/standalone OR clause from the base domain — restricting by
            # id already implies the inclusion semantics, and bundled-only child services
            # would otherwise be excluded by ('commercial_structure', '!=', 'bundled').
            bundle_domain = [
                ('available_on_wink', '=', True),
                ('sale_ok', '=', True),
                ('active', '=', True),
                ('id', 'in', bundle_ids),
            ]
            if bundles_only:
                bundle_domain.append(('wink_is_bundle', '=', True))
            if department_ids:
                bundle_domain.append(('department_ids', 'in', [int(d) for d in department_ids if d.isdigit()]))
            if nature_id and nature_id.isdigit():
                bundle_domain.append(('nature_id', '=', int(nature_id)))
            if delivery_model:
                bundle_domain.append(('delivery_model', '=', delivery_model))
            if search:
                bundle_domain.append(('name', 'ilike', search))
            products = Product.search(bundle_domain)
            # Refresh derived dicts for any newly added bundled-only services
            for p in products:
                if p.id not in short_descs:
                    if p.wink_description:
                        text = html2plaintext(p.wink_description).strip()
                        short_descs[p.id] = text[:117] + '...' if len(text) > 120 else text
                    else:
                        short_descs[p.id] = ''
                if p.id not in product_dept_slugs:
                    if p.department_ids:
                        raw = (p.department_ids[0].name or '').lower()
                        slug = raw.replace('&', 'and').replace(' ', '-')
                        slug = re.sub(r'[^a-z0-9-]', '', slug)
                        slug = re.sub(r'-+', '-', slug).strip('-')
                        product_dept_slugs[p.id] = slug or 'other'
                    else:
                        product_dept_slugs[p.id] = ''
            active_filter_count += 1
        elif entitlement_map:
            # Filter is off — keep the original behaviour of surfacing entitled services
            # (including bundled-only children) on the catalogue so the "In Your Bundle"
            # badge appears next to them.
            bundle_svc_ids = list(entitlement_map.keys())
            bundle_svcs = Product.search([
                ('id', 'in', bundle_svc_ids),
                ('active', '=', True),
            ])
            existing_ids = set(products.ids)
            extra = bundle_svcs.filtered(lambda p: p.id not in existing_ids)
            if extra:
                products = products | extra
                for p in extra:
                    if p.wink_description:
                        text = html2plaintext(p.wink_description).strip()
                        short_descs[p.id] = text[:117] + '...' if len(text) > 120 else text
                    if p.department_ids:
                        raw = (p.department_ids[0].name or '').lower()
                        slug = raw.replace('&', 'and').replace(' ', '-')
                        slug = re.sub(r'[^a-z0-9-]', '', slug)
                        slug = re.sub(r'-+', '-', slug).strip('-')
                        product_dept_slugs[p.id] = slug or 'other'

        # Encoded query string of the non-toggle filters (department, nature, delivery,
        # search). Used by the pill buttons so toggling "All Services" / "In Your Bundle"
        # preserves whatever the user has already selected.
        pill_params = []
        for _d in cur_dept:
            pill_params.append(('department_ids', _d))
        if cur_nature:
            pill_params.append(('nature_id', cur_nature))
        if delivery_model:
            pill_params.append(('delivery_model', delivery_model))
        if search:
            pill_params.append(('search', search))
        pill_qs_base = url_encode(pill_params) if pill_params else ''

        values = {
            'products': products,
            'product_dept_slugs': product_dept_slugs,
            'departments': departments,
            'dept_counts': dept_counts,
            'natures': natures,
            'entitlement_map': entitlement_map,
            'delivery_models': delivery_models,
            'current_filters': {
                'department_ids': cur_dept,
                'nature_id': cur_nature,
                'delivery_model': delivery_model,
            },
            'active_filter_count': active_filter_count,
            'search': search,
            'short_descs': short_descs,
            'bundles_only': bundles_only,
            'bundle_included': bundle_included,
            'pill_qs_base': pill_qs_base,
        }
        return request.render('kuec_service_catalogue.wink_catalogue_page', values)

    @http.route(['/wink/packages'], type='http', auth='public', website=True, sitemap=False)
    def wink_packages(self, **kwargs):
        """Smart packages landing page.

        Workflow:
            1. Query all active bundle products visible on Wink.
            2. If exactly 1 bundle → 302 redirect directly to its tier-selection page.
            3. If 2+ bundles → render the dedicated packages listing page.
            4. If 0 bundles → render the listing page (shows empty state).
        """
        Product = request.env['product.template'].sudo()
        bundles = Product.search([
            ('available_on_wink', '=', True),
            ('sale_ok', '=', True),
            ('active', '=', True),
            ('wink_is_bundle', '=', True),
        ], order='name asc')
        if len(bundles) == 1:
            return request.redirect(f'/my/requests/new?product_id={bundles.id}', code=302)
        return request.render('kuec_service_catalogue.wink_packages_page', {
            'bundles': bundles,
            'page_name': 'packages',
        })

    @http.route(['/services/<int:product_id>'], type='http', auth='public', website=True, sitemap=True)
    def service_detail(self, product_id, **kwargs):
        Product = request.env['product.template'].sudo()
        product = Product.search([
            ('id', '=', product_id),
            ('available_on_wink', '=', True),
            ('sale_ok', '=', True)
        ], limit=1)

        if not product:
            raise NotFound()

        user = request.env.user
        is_authenticated = not user._is_public()

        _period_nice = {
            'per month': 'Monthly', 'per year': 'Yearly',
            'per quarter': 'Quarterly', 'per 6 months': '6-Monthly',
        }

        is_subscription_service = bool(
            getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer'
        )
        allow_plan_fallback = bool(product.wink_is_bundle or product.commercial_structure == 'bundled')
        subscription_plans = []
        selected_plan_id = None
        display_plan = None
        unique_periods = []
        active_period = None

        if is_subscription_service:
            subscription_plans = product._wink_subscription_plans_dicts(
                pricelist_id=False,
                allow_plan_fallback=allow_plan_fallback,
            )
            if subscription_plans:
                # Handle ?plan= pre-selection (e.g. returning from wizard via "Change Plan")
                plan_param = kwargs.get('plan') or kwargs.get('pricing_id')
                selected_plan_id = None
                if plan_param:
                    try:
                        plan_id = int(plan_param)
                        for p in subscription_plans:
                            if p['recurrence_id'] == plan_id or p.get('pricing_id') == plan_id:
                                selected_plan_id = p['recurrence_id']
                                break
                    except (TypeError, ValueError):
                        pass
                if not selected_plan_id:
                    selected_plan_id = subscription_plans[0]['recurrence_id']
                display_plan = next(
                    (p for p in subscription_plans if p['recurrence_id'] == selected_plan_id),
                    subscription_plans[0]
                )
                # Compute unique periods server-side (preserves insertion order)
                seen = set()
                for p in subscription_plans:
                    label = p['period_label']
                    if label not in seen:
                        seen.add(label)
                        unique_periods.append({
                            'label': label,
                            'nice': _period_nice.get(label, label.replace('per ', '').title()),
                            'has_savings': any(
                                pp.get('savings_pct', 0) > 0
                                for pp in subscription_plans
                                if pp['period_label'] == label
                            ),
                        })
                active_period = display_plan['period_label']

        # Bundle entitlement: check if authenticated user has an entitlement for this service.
        # entitlement          → available (activate button shown)
        # entitlement_activated → fully_activated (service already active; show status badge)
        entitlement = False
        entitlement_activated = False
        bundle_employees = request.env['kuec.employee.directory']
        if is_authenticated:
            partner = request.env.user.partner_id.commercial_partner_id
            _base_domain = [
                ('service_product_id', '=', product.id),
                ('order_id.partner_id', 'child_of', partner.id),
                ('order_id.state', '=', 'sale'),
                ('order_id.subscription_state', '!=', '6_churn'),
                ('order_id.wink_bundle_cancelled', '=', False),
            ]
            entitlement = request.env['wink.bundle.entitlement'].sudo().search(
                _base_domain + [('state', '=', 'available')], limit=1
            )
            if not entitlement:
                # No available slot — check if already fully activated.
                # For non-one-time services we still want to offer re-activation
                # (e.g. add more employees), so pass entitlement_activated separately
                # so the template can show the appropriate Activate Again button.
                entitlement_activated = request.env['wink.bundle.entitlement'].sudo().search(
                    _base_domain + [('state', '=', 'fully_activated')], limit=1
                )
            if entitlement and getattr(product, 'requires_employee_selection', False):
                bundle_employees = request.env['kuec.employee.directory'].sudo().search([
                    ('partner_id', 'child_of', partner.id)
                ])

        is_bundled_child_service = bool(
            product.commercial_structure == 'bundled' and not product.wink_is_bundle
        )
        if is_bundled_child_service and not (entitlement or entitlement_activated):
            raise NotFound()

        values = {
            'product': product,
            'is_authenticated': is_authenticated,
            'redirect_url': '/services/%s' % product_id,
            'is_subscription_service': is_subscription_service,
            'subscription_plans': subscription_plans,
            'selected_plan_id': selected_plan_id,
            'display_plan': display_plan,
            'unique_periods': unique_periods,
            'active_period': active_period,
            'entitlement': entitlement,
            'entitlement_activated': entitlement_activated,
            'bundle_employees': bundle_employees,
            'bundle_requested': kwargs.get('bundle_requested') == '1',
            'activation_error': kwargs.get('activation_error', ''),
        }
        return request.render('kuec_service_catalogue.wink_service_detail_page', values)

    @http.route(
        '/services/<int:product_id>/activate/<int:entitlement_id>',
        type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True,
    )
    def service_activate_page(self, product_id, entitlement_id, **post):
        """Dedicated full-page activation flow for bundle-included services.

        GET  — render the activation page (service info + employee picker + gov charge info).
        POST — process activation, then redirect to payment or success.
        """
        partner = request.env.user.partner_id.commercial_partner_id

        # Verify the entitlement belongs to this user and is activatable.
        # Accept both 'available' and 'fully_activated' states — non-one-time services
        # allow re-activation (e.g. additional employees) even after all entitled slots are used.
        entitlement = request.env['wink.bundle.entitlement'].sudo().search([
            ('id', '=', entitlement_id),
            ('service_product_id', '=', product_id),
            ('order_id.partner_id', 'child_of', partner.id),
            ('order_id.state', '=', 'sale'),
            ('order_id.subscription_state', '!=', '6_churn'),
            ('order_id.wink_bundle_cancelled', '=', False),
            ('state', 'in', ('available', 'fully_activated')),
        ], limit=1)
        if not entitlement:
            raise NotFound()

        product = entitlement.service_product_id
        order = entitlement.order_id
        requires_employees = bool(getattr(product, 'requires_employee_selection', False))

        def _activation_redirect_error(message):
            err = werkzeug.urls.url_quote(message or '')
            return request.redirect(
                f'/services/{product_id}/activate/{entitlement_id}?error={err}'
            )

        def _create_activation_attachments(uploaded_docs):
            for doc in uploaded_docs:
                request.env['ir.attachment'].sudo().create({
                    'name': doc['filename'],
                    'res_model': 'wink.bundle.entitlement',
                    'res_id': entitlement.id,
                    'datas': base64.b64encode(doc['content']).decode(),
                    'mimetype': doc['mimetype'],
                    'description': doc['description'],
                })

        # Gov charge detection — two separate systems:
        #   wink_has_gov_charge    → standalone request flow: invoice created immediately, amount always known
        #   requires_government_charges → bundle entitlement flow: may or may not have a known amount
        _wink_gov = bool(getattr(product, 'wink_has_gov_charge', False))
        _req_gov = bool(getattr(product, 'requires_government_charges', False))
        has_gov_charge = _wink_gov or _req_gov

        # Resolve charge amount and known-flag
        # gov_charge_base    — fixed component (charged once regardless of employee count)
        # gov_charge_per_unit — variable component multiplied by number of employees
        # gov_charge_per_emp  — combined display amount for 1 employee (base + per_unit)
        if _wink_gov:
            gov_charge_base = 0.0
            gov_charge_per_unit = float(getattr(product, 'wink_default_gov_charge', 0.0) or 0.0)
            gov_charge_per_emp = gov_charge_per_unit
            gov_charge_is_known = True
        elif _req_gov:
            gov_charge_is_known = bool(getattr(product, 'gov_charge_is_known', False))
            gov_charge_base = float(getattr(product, 'gov_charge_amount', 0.0) or 0.0)
            gov_charge_per_unit = float(getattr(product, 'gov_charge_per_employee', 0.0) or 0.0)
            gov_charge_per_emp = gov_charge_base + gov_charge_per_unit
        else:
            gov_charge_base = 0.0
            gov_charge_per_unit = 0.0
            gov_charge_per_emp = 0.0
            gov_charge_is_known = False

        employees = request.env['kuec.employee.directory'].sudo().search([
            ('partner_id', 'child_of', partner.id)
        ])

        # ── Double-billing guard: entitlement has a paid invoice from a previous attempt ──
        # This happens when action_gov_charge_paid() was called, cleared pending employees,
        # called action_activate() which failed silently, but now keeps the invoice reference.
        # If invoice is paid we must NOT show the form again (it would create a 2nd invoice).
        # Instead retry activation and redirect to the request page.
        if entitlement.wink_gov_charge_invoice_id:
            _guard_inv = entitlement.wink_gov_charge_invoice_id
            if _guard_inv.payment_state in ('paid', 'in_payment'):
                try:
                    entitlement.sudo().action_gov_charge_paid()
                except Exception:
                    _logger.exception(
                        "Activation retry after paid gov-charge invoice failed for "
                        "entitlement %s from order %s.",
                        entitlement.id, order.id,
                    )
                return request.redirect(f'/my/requests/{order.id}')

        # ── POST: process activation ──────────────────────────────────────────
        if request.httprequest.method == 'POST':
            # POST-level double-billing guard: if an existing paid invoice is on the
            # entitlement, don't create a new one — retry activation or redirect to pay.
            if entitlement.wink_gov_charge_invoice_id:
                _post_inv = entitlement.wink_gov_charge_invoice_id
                if _post_inv.payment_state in ('paid', 'in_payment'):
                    try:
                        entitlement.sudo().action_gov_charge_paid()
                    except Exception:
                        _logger.exception(
                            "POST activation retry after paid gov-charge invoice failed "
                            "for entitlement %s from order %s.",
                            entitlement.id, order.id,
                        )
                    return request.redirect(f'/my/requests/{order.id}')
                else:
                    # Unpaid invoice already exists — send customer back to pay it
                    return request.redirect(
                        f'/my/requests/{order.id}/gov-charges-payment?invoice_id={_post_inv.id}'
                    )

            employee_ids = []
            for val in request.httprequest.form.getlist('employee_ids'):
                if str(val).isdigit():
                    employee_ids.append(int(val))

            # Create new employees from the inline multi-row form.
            # Fields use array notation (new_emp_name[]) so getlist() returns all rows.
            _form = request.httprequest.form
            _new_names = _form.getlist('new_emp_name[]')
            _new_jobs = _form.getlist('new_emp_job[]')
            _new_emails = _form.getlist('new_emp_email[]')
            _new_mobiles = _form.getlist('new_emp_mobile[]')
            for _i, _raw_name in enumerate(_new_names):
                _name = (_raw_name or '').strip()
                if not _name:
                    continue  # blank row — skip
                new_emp = request.env['kuec.employee.directory'].sudo().create({
                    'name': _name,
                    'job_title': (_new_jobs[_i] if _i < len(_new_jobs) else '').strip() or False,
                    'email': (_new_emails[_i] if _i < len(_new_emails) else '').strip() or False,
                    'mobile': (_new_mobiles[_i] if _i < len(_new_mobiles) else '').strip() or False,
                    'partner_id': partner.id,
                })
                employee_ids.append(new_emp.id)

            if employee_ids:
                unique_employee_ids = list(dict.fromkeys(employee_ids))
                valid_employees = request.env['kuec.employee.directory'].sudo().search([
                    ('id', 'in', unique_employee_ids),
                    ('partner_id', 'child_of', partner.id),
                ])
                if len(valid_employees) != len(unique_employee_ids):
                    return _activation_redirect_error(_(
                        "One or more selected employees are no longer available. "
                        "Please refresh the page and try again."
                    ))
                employee_ids = valid_employees.ids

            # Collect uploaded documents, then save them only after activation/invoice success.
            uploaded_docs = []
            uploaded_doc_ids = set()
            product_docs = product.kuec_document_ids
            product_doc_ids = set(product_docs.ids)
            _doc_files = request.httprequest.files
            for _key in list(_doc_files.keys()):
                if not _key.startswith('doc_file_'):
                    continue
                _doc_id_str = _key[len('doc_file_'):]
                if not _doc_id_str.isdigit():
                    continue
                _doc_id = int(_doc_id_str)
                if _doc_id not in product_doc_ids:
                    continue
                _doc = product_docs.filtered(lambda d: d.id == _doc_id)[:1]
                for _uf in _doc_files.getlist(_key):
                    if _uf and getattr(_uf, 'filename', None):
                        _content = _uf.read()
                        if _content:
                            uploaded_doc_ids.add(_doc_id)
                            uploaded_docs.append({
                                'filename': _uf.filename,
                                'content': _content,
                                'mimetype': _uf.content_type or 'application/octet-stream',
                                'description': 'Activation document: %s' % (_doc.name or _doc_id),
                            })

            required_docs = product_docs.filtered(lambda d: d.requirement == 'required')
            missing_docs = required_docs.filtered(lambda d: d.id not in uploaded_doc_ids)
            if missing_docs:
                return _activation_redirect_error(
                    _('Please attach a file for: %s') % ', '.join(missing_docs.mapped('name')[:3])
                )

            # ── Gov charge path A: wink_has_gov_charge (standalone-style, invoice-first) ──
            # Or requires_government_charges + gov_charge_is_known (known amount upfront)
            _create_invoice_now = (
                (_wink_gov and not entitlement.wink_gov_charge_invoice_id) or
                (_req_gov and gov_charge_is_known and not entitlement.wink_gov_charge_invoice_id)
            )

            if _create_invoice_now:
                from datetime import date as _date
                num_employees = max(len(employee_ids), 1)
                if _wink_gov:
                    total_gov = float(getattr(product, 'wink_default_gov_charge', 0.0) or 0.0) * num_employees
                else:
                    # requires_government_charges + gov_charge_is_known
                    _base = float(getattr(product, 'gov_charge_amount', 0.0) or 0.0)
                    _per = float(getattr(product, 'gov_charge_per_employee', 0.0) or 0.0)
                    total_gov = _base + (_per * num_employees)
                gov_product = request.env.company.sudo().wink_gov_charge_product_id
                variant = product.product_variant_ids[:1]
                inv_line = {
                    'name': 'Government Charges: %s' % entitlement.name,
                    'quantity': 1,
                    'price_unit': total_gov,
                    'tax_ids': [(5, 0, 0)],
                }
                if gov_product:
                    inv_line['product_id'] = gov_product.id
                elif variant:
                    inv_line['product_id'] = variant.id
                if order.order_line:
                    inv_line['sale_line_ids'] = [(4, order.order_line[:1].id)]
                gov_invoice = request.env['account.move'].sudo().create({
                    'move_type': 'out_invoice',
                    'partner_id': order.partner_id.id,
                    'invoice_date': _date.today(),
                    'invoice_origin': order.name,
                    'ref': 'Gov Charge - %s - %s' % (entitlement.name, order.name),
                    'invoice_line_ids': [(0, 0, inv_line)],
                })
                try:
                    gov_invoice.sudo().action_post()
                except Exception:
                    _logger.exception(
                        "Failed to post gov-charge invoice %s for entitlement %s "
                        "from order %s.",
                        gov_invoice.id, entitlement.id, order.id,
                    )
                entitlement.sudo().write({
                    'wink_gov_charge_invoice_id': gov_invoice.id,
                    'wink_gov_charge_per_employee': total_gov / max(num_employees, 1),
                    'wink_pending_employee_ids': [(6, 0, employee_ids)] if employee_ids else [(5, 0, 0)],
                })
                _create_activation_attachments(uploaded_docs)
                # Send customer directly to the payment page — show invoice amount + pay options
                return request.redirect(
                    f'/my/requests/{order.id}/gov-charges-payment?invoice_id={gov_invoice.id}'
                )

            # ── Gov charge path B: requires_government_charges, amount NOT yet known ──
            # Call action_activate() which creates an is_gov_charge_pending=True sale order line.
            # The coordinator will confirm the amount; show customer a clear "pending" message.
            _pending_gov_charges = _req_gov and not gov_charge_is_known

            # ── Direct activation path (no gov charges, or pending-coordinator path) ──
            try:
                with request.env.cr.savepoint():
                    entitlement.sudo().action_activate(employee_ids=employee_ids)
                    _create_activation_attachments(uploaded_docs)
            except (UserError, ValidationError) as e:
                return _activation_redirect_error(str(e))
            except Exception:
                _logger.exception(
                    "Catalogue activation failed for entitlement %s, product %s, "
                    "order %s, partner %s.",
                    entitlement.id, product.id, order.id, partner.id,
                )
                return _activation_redirect_error(_(
                    "Activation failed due to an unexpected technical error. "
                    "The issue has been logged."
                ))

            # Show dedicated success + next-steps page
            # Pass gov_charges_pending=True so the template can show the
            # "coordinator will contact you about charges" message
            return request.render('kuec_service_catalogue.wink_service_activate_success', {
                'product': product,
                'order': order,
                'entitlement': entitlement,
                'gov_charges_pending': _pending_gov_charges,
            })

        # ── GET: render activation page ───────────────────────────────────────
        return request.render('kuec_service_catalogue.wink_service_activate_page', {
            'product': product,
            'entitlement': entitlement,
            'order': order,
            'requires_employees': requires_employees,
            'has_gov_charge': has_gov_charge,
            'gov_charge_is_known': gov_charge_is_known,
            'gov_charge_per_emp': gov_charge_per_emp,
            'gov_charge_base': gov_charge_base,
            'gov_charge_per_unit': gov_charge_per_unit,
            'employees': employees,
            'error': request.httprequest.args.get('error', '') or '',
        })

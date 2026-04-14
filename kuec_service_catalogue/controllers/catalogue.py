# -*- coding: utf-8 -*-

import re
import werkzeug
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError
from odoo.tools import html2plaintext
from werkzeug.exceptions import NotFound


class WinkCatalogue(http.Controller):

    @http.route(['/services'], type='http', auth='public', website=True, sitemap=True)
    def service_catalogue(self, **kwargs):
        Product = request.env['product.template'].sudo()

        # Fix 4: "Packages Only" toggle
        bundles_only = kwargs.get('bundles_only') == '1'

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

        # Bundle entitlement map: show bundled services to users who have an active bundle
        entitlement_map = {}  # {product_tmpl_id: entitlement_record}
        user = request.env.user
        if not user._is_public():
            partner = user.partner_id.commercial_partner_id
            entitlements = request.env['wink.bundle.entitlement'].sudo().search([
                ('order_id.partner_id', 'child_of', partner.id),
                ('order_id.state', '=', 'sale'),
                ('order_id.subscription_state', '!=', '6_churn'),
                ('order_id.wink_bundle_cancelled', '=', False),
                ('state', '=', 'available'),
            ])
            for ent in entitlements:
                if ent.service_product_id:
                    pid = ent.service_product_id.id
                    if pid not in entitlement_map:
                        entitlement_map[pid] = ent
            # Include bundled services that have available entitlements in the product list
            if entitlement_map:
                bundle_svc_ids = list(entitlement_map.keys())
                bundle_svcs = request.env['product.template'].sudo().search([
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
        subscription_plans = []
        selected_plan_id = None
        display_plan = None
        unique_periods = []
        active_period = None

        if is_subscription_service:
            subscription_plans = product._wink_subscription_plans_dicts(pricelist_id=False)
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

        # Bundle entitlement: check if authenticated user has an available entitlement for this service
        entitlement = False
        bundle_employees = request.env['kuec.employee.directory']
        if is_authenticated:
            partner = request.env.user.partner_id.commercial_partner_id
            entitlement = request.env['wink.bundle.entitlement'].sudo().search([
                ('service_product_id', '=', product.id),
                ('order_id.partner_id', 'child_of', partner.id),
                ('order_id.state', '=', 'sale'),
                ('order_id.subscription_state', '!=', '6_churn'),
                ('order_id.wink_bundle_cancelled', '=', False),
                ('state', '=', 'available'),
            ], limit=1)
            if entitlement and getattr(product, 'requires_employee_selection', False):
                bundle_employees = request.env['kuec.employee.directory'].sudo().search([
                    ('partner_id', 'child_of', partner.id)
                ])

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

        # Verify the entitlement belongs to this user and is still available
        entitlement = request.env['wink.bundle.entitlement'].sudo().search([
            ('id', '=', entitlement_id),
            ('service_product_id', '=', product_id),
            ('order_id.partner_id', 'child_of', partner.id),
            ('order_id.state', '=', 'sale'),
            ('order_id.subscription_state', '!=', '6_churn'),
            ('order_id.wink_bundle_cancelled', '=', False),
            ('state', '=', 'available'),
        ], limit=1)
        if not entitlement:
            raise NotFound()

        product = entitlement.service_product_id
        order = entitlement.order_id
        requires_employees = bool(getattr(product, 'requires_employee_selection', False))

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

        # ── POST: process activation ──────────────────────────────────────────
        if request.httprequest.method == 'POST':
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

            # ── Save uploaded activation documents as attachments on the entitlement ──
            import base64 as _b64
            _doc_files = request.httprequest.files
            for _key in list(_doc_files.keys()):
                if not _key.startswith('doc_file_'):
                    continue
                for _uf in _doc_files.getlist(_key):
                    if _uf and getattr(_uf, 'filename', None):
                        _content = _uf.read()
                        if _content:
                            request.env['ir.attachment'].sudo().create({
                                'name': _uf.filename,
                                'res_model': 'wink.bundle.entitlement',
                                'res_id': entitlement.id,
                                'datas': _b64.b64encode(_content).decode(),
                                'mimetype': _uf.content_type or 'application/octet-stream',
                                'description': 'Activation document',
                            })

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
                    pass
                entitlement.sudo().write({
                    'wink_gov_charge_invoice_id': gov_invoice.id,
                    'wink_gov_charge_per_employee': total_gov / max(num_employees, 1),
                    'wink_pending_employee_ids': [(6, 0, employee_ids)] if employee_ids else [(5, 0, 0)],
                })
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
                entitlement.sudo().action_activate(employee_ids=employee_ids)
            except UserError as e:
                err = werkzeug.urls.url_quote(str(e))
                return request.redirect(
                    f'/services/{product_id}/activate/{entitlement_id}?error={err}'
                )
            except Exception:
                err = werkzeug.urls.url_quote(_('Activation failed. Please try again.'))
                return request.redirect(
                    f'/services/{product_id}/activate/{entitlement_id}?error={err}'
                )

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

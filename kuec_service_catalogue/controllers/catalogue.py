# -*- coding: utf-8 -*-

import re
from odoo import http
from odoo.http import request
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

        values = {
            'products': products,
            'product_dept_slugs': product_dept_slugs,
            'departments': departments,
            'dept_counts': dept_counts,
            'natures': natures,
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
        }
        return request.render('kuec_service_catalogue.wink_service_detail_page', values)

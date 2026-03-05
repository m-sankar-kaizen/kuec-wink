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
        
        # Base domain — all users see all available services
        domain = [
            ('available_on_wink', '=', True),
            ('sale_ok', '=', True),
            ('active', '=', True)
        ]

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
            ('active', '=', True)
        ]
        dept_counts = {}
        for dept in departments:
            dept_domain = base_domain + [('department_ids', 'in', [dept.id])]
            dept_counts[dept.id] = Product.search_count(dept_domain)
        natures = request.env['kuec.service.nature'].sudo().search([('active', '=', True)])
        delivery_models = Product._fields['delivery_model'].selection

        cur_dept = [int(d) for d in department_ids if d.isdigit()]
        cur_nature = int(nature_id) if nature_id and nature_id.isdigit() else None
        active_filter_count = len(cur_dept) + len(cur_nature) + (1 if delivery_model else 0)

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
        }
        return request.render('kuec_service_catalogue.wink_catalogue_page', values)

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

        # Subscription/retainer: show plan selector when recurring_invoice or delivery_model is retainer
        is_subscription_service = bool(
            getattr(product, 'recurring_invoice', False) or product.delivery_model == 'retainer'
        )
        subscription_plans = []
        selected_plan_id = None
        display_plan = None  # FB-005: plan to show in main price (selected or first)
        if is_subscription_service:
            subscription_plans = product._wink_subscription_plans_dicts(pricelist_id=False)
            if subscription_plans:
                selected_plan_id = subscription_plans[0]['recurrence_id']
                display_plan = subscription_plans[0]
                for p in subscription_plans:
                    if p['recurrence_id'] == selected_plan_id:
                        display_plan = p
                        break

        values = {
            'product': product,
            'is_authenticated': is_authenticated,
            'redirect_url': '/services/%s' % product_id,
            'is_subscription_service': is_subscription_service,
            'subscription_plans': subscription_plans,
            'selected_plan_id': selected_plan_id,
            'display_plan': display_plan,
        }
        return request.render('kuec_service_catalogue.wink_service_detail_page', values)

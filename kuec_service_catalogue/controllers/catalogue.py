# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.tools import html2plaintext
from werkzeug.exceptions import NotFound

class WinkCatalogue(http.Controller):

    @http.route(['/services'], type='http', auth='public', website=True, sitemap=True)
    def service_catalogue(self, **kwargs):
        Product = request.env['product.template'].sudo()
        
        # Base domain
        domain = [
            ('available_on_wink', '=', True),
            ('sale_ok', '=', True),
            ('active', '=', True)
        ]

        # Eligibility filter
        user = request.env.user
        if user._is_public():
            eligibility_domain = ['|', ('eligibility_ids.code', '=', 'all'), ('eligibility_ids', '=', False)]
        else:
            partner = user.partner_id.commercial_partner_id
            allowed_codes = request.env['kuec.eligibility.rule'].sudo().get_accessible_codes(partner)
            allowed_codes_list = list(allowed_codes)
            allowed_codes_list.append('all')
            eligibility_domain = ['|', ('eligibility_ids.code', 'in', allowed_codes_list), ('eligibility_ids', '=', False)]

        # URL Filters
        department_ids = request.httprequest.args.getlist('department_ids')
        if department_ids:
            domain.append(('department_ids', 'in', [int(d) for d in department_ids if d.isdigit()]))
            
        nature_ids = request.httprequest.args.getlist('nature_ids')
        if nature_ids:
            domain.append(('nature_ids', 'in', [int(n) for n in nature_ids if n.isdigit()]))

        delivery_model = kwargs.get('delivery_model')
        if delivery_model:
            domain.append(('delivery_model', '=', delivery_model))

        commercial_structure = kwargs.get('commercial_structure')
        if commercial_structure:
            domain.append(('commercial_structure', '=', commercial_structure))

        search = kwargs.get('search')
        if search:
            domain.append(('name', 'ilike', search))

        # Combine domains
        final_domain = expression.AND([domain, eligibility_domain])
        products = Product.search(final_domain)

        # Build short descriptions dictionary for template
        short_descs = {}
        for p in products:
            if p.wink_description:
                text = html2plaintext(p.wink_description).strip()
                short_descs[p.id] = text[:117] + '...' if len(text) > 120 else text
            else:
                short_descs[p.id] = ''

        # Sidebar data
        departments = request.env['kuec.department'].sudo().search([('active', '=', True)])
        natures = request.env['kuec.service.nature'].sudo().search([('active', '=', True)])
        delivery_models = Product._fields['delivery_model'].selection
        commercial_structures = Product._fields['commercial_structure'].selection

        values = {
            'products': products,
            'departments': departments,
            'natures': natures,
            'delivery_models': delivery_models,
            'commercial_structures': commercial_structures,
            'current_filters': {
                'department_ids': [int(d) for d in department_ids if d.isdigit()],
                'nature_ids': [int(n) for n in nature_ids if n.isdigit()],
                'delivery_model': delivery_model,
                'commercial_structure': commercial_structure,
            },
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

        values = {
            'product': product,
            'is_authenticated': is_authenticated,
            'redirect_url': '/services/%s' % product_id,
        }
        return request.render('kuec_service_catalogue.wink_service_detail_page', values)

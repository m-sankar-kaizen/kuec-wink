# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.osv import expression

class KuecWebsiteSale(WebsiteSale):

    def _get_partner_eligibility_codes(self, partner):
        return list(request.env['kuec.eligibility.rule']\
            .get_accessible_codes(partner))

    def _get_shop_domain(self, search, category, attrib_values, search_in_description=True):
        domain = super()._get_shop_domain(search, category, attrib_values, search_in_description)
        
        # Enforce Eligibility Rules for KUEC Services
        user = request.env.user
        if user._is_public():
            # Anonymous users see 'all'
            eligibility_domain = ['|', ('eligibility_ids.code', '=', 'all'), ('eligibility_ids', '=', False)]
        else:
            partner = user.partner_id.commercial_partner_id
            allowed_codes = self._get_partner_eligibility_codes(partner)
            allowed_codes.append('all') # Everyone sees 'all'
            eligibility_domain = ['|', ('eligibility_ids.code', 'in', allowed_codes), ('eligibility_ids', '=', False)]
            
        return expression.AND([domain, eligibility_domain])

    @http.route(['/shop/checkout'], type='http', auth="public", website=True, sitemap=False)
    def shop_checkout(self, **post):
        order = request.website.sale_get_order()
        if order:
            has_hidden = any(line.product_id.product_tmpl_id.price_visibility == 'hidden' for line in order.order_line)
            if has_hidden and not order.wink_price_confirmed:
                return request.redirect('/shop/cart')
        return super(KuecWebsiteSale, self).shop_checkout(**post)

    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def shop_payment(self, **post):
        order = request.website.sale_get_order()
        if order:
            has_hidden = any(line.product_id.product_tmpl_id.price_visibility == 'hidden' for line in order.order_line)
            if has_hidden and not order.wink_price_confirmed:
                return request.redirect('/shop/cart')
        return super(KuecWebsiteSale, self).shop_payment(**post)

    @http.route(['/shop/confirm_order'], type='http', auth="public", website=True, sitemap=False)
    def shop_confirm_order(self, **post):
        order = request.website.sale_get_order()
        if order:
            has_hidden = any(line.product_id.product_tmpl_id.price_visibility == 'hidden' for line in order.order_line)
            if has_hidden and not order.wink_price_confirmed:
                return request.redirect('/shop/cart')
        return super(KuecWebsiteSale, self).shop_confirm_order(**post)

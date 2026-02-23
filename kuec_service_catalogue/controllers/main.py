# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale


class KuecWebsiteSale(WebsiteSale):

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

# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo.http import route, request
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo import _


class TenderPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        website = request.website
        company_id = website.company_id.id if website and website.company_id else request.env.company.id
        TenderBid = request.env['tender.bid'].sudo()
        if 'rfq_count' in counters:
            values['tender_bid_count'] = TenderBid.search_count(
                [('company_id', '=', company_id), ('bid_user_id', '=', request.env.user.id)])
        return values

    def _get_tender_bid_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
        }

    def _render_portal(self, template, page, date_begin, date_end, sortby, filterby, domain,
                       searchbar_filters, default_filter, url, history, page_name, key):
        values = self._prepare_portal_layout_values()
        TenderBid = request.env['tender.bid'].sudo()

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = self._get_tender_bid_searchbar_sortings()
        # default sort
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if searchbar_filters:
            # default filter
            if not filterby:
                filterby = default_filter
            domain += searchbar_filters[filterby]['domain']

        # count for pager
        count = TenderBid.search_count(domain)

        # make pager
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,
                      'filterby': filterby},
            total=count,
            page=page,
            step=self._items_per_page
        )

        # search the purchase orders to display, according to the pager data
        orders = TenderBid.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session[history] = orders.ids[:100]

        values.update({
            'date': date_begin,
            key: orders,
            'page_name': page_name,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': url,
        })
        return request.render(template, values)

    @route(['/my/tender/bid', '/my/tender/bid/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None,
                                  filterby=None, **kw):
        website = request.website
        company_id = website.company_id.id if website and website.company_id else request.env.company.id
        return self._render_portal(
            "kaz_vendor_management.portal_my_tender_bids",
            page, date_begin, date_end, sortby, filterby,
            [('company_id', '=', company_id), ('bid_user_id', '=', request.env.user.id)],
            {
                'all': {'label': _('All'),
                        'domain': [('state', 'in',
                                    ['draft', 'pre_qualify', 'evaluation', 'bid_evaluated',
                                     'bafo_selected', 'awarded', 'rejected']), ], },
                'pre_qualify': {'label': _('Pre-Qualified'),
                                'domain': [('state', '=', 'pre_qualify')]},
                'evaluation': {'label': _('Evaluation'), 'domain': [('state', '=', 'evaluation')]},
                'bid_evaluated': {'label': _('Evaluated'),
                                  'domain': [('state', '=', 'bid_evaluated')]},
                'bafo_selected': {'label': _('BAFO Selected'),
                                  'domain': [('state', '=', 'bafo_selected')]},
                'awarded': {'label': _('Awarded'), 'domain': [('state', '=', 'awarded')]},
                'rejected': {'label': _('Rejected'), 'domain': [('state', '=', 'rejected')]},
            },
            'all',
            "/my/tender/bid",
            'my_tender_bid_history',
            'tender_bid',
            'tender_bids'
        )

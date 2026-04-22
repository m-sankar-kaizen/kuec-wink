# -*- coding: utf-8 -*-
import base64

from datetime import timedelta

from odoo.http import Controller, route, request, Response
from odoo import fields, SUPERUSER_ID, Command


class TenderManagement(Controller):

    @route(['/get/tenders'], type='http', auth="public", website=True)
    def get_tenders(self, **kw):
        if request.env.user._is_public():
            return request.render('kaz_vendor_management.no_access_tender_view_template', {})
        website = request.website
        company_id = website.company_id.id if website and website.company_id else request.env.company.id
        props = {
            'company_id': company_id,
            'user_id': request.env.user.id,
        }
        return request.render('kaz_vendor_management.tender_view_template', {'props': props})

    @route('/get/tender/basic-info', type='json', auth="public")
    def get_tender_basic_info(self, company_id, user_id, **kw):
        partner_categories = request.env['partner.category'].sudo().search_read(
            domain=[('company_id', '=', company_id)],
            fields=['id', 'name'],
        )
        user = request.env['res.users'].sudo().search_read(
            domain=[('id', '=', user_id), ('share', '=', True)],
            fields=['id', 'name', 'partner_id'],
        )
        return {
            "partner_categories": partner_categories,
            "user": user,
        }

    @route('/get/tender/items', type='json', auth="public")
    def get_tender_items(self, **kw):
        Tender = request.env['tender.rfq'].sudo()

        company_id = kw.get('company_id')
        category_ids = kw.get('category_ids', [])
        user_id = kw.get('user_id')
        closing_day = kw.get('closing_day', 'all')
        state = kw.get('state')
        search = kw.get('name', '')
        limit = int(kw.get('limit', 20))
        offset = int(kw.get('offset', 0))
        sort_field = kw.get('sort_field', 'create_date')
        sort_order = kw.get('sort_order', 'desc')

        domain = [('company_id', '=', company_id)]

        if category_ids:
            domain += [('partner_category_ids', 'in', category_ids)]

        if state == "active":
            domain += [('state', '=', 'active')]
        elif state == "pre_qualified":
            domain += [('state', '=', 'pre_qualified')]
        elif state == "closed":
            domain += [('state', '=', 'closed')]
        elif state == "under_review":
            domain += [('state', '=', 'under_review')]
        elif state == "awarded":
            domain += [('state', '=', 'awarded')]
        else:
            domain += [('state', '=', 'active')]

        if search:
            domain += ['|',
                       ('name', 'ilike', search),
                       ('title', 'ilike', search)
                       ]

        if closing_day and closing_day != 'all':
            try:
                days = int(closing_day)
                today = fields.Date.today()
                end_date = today + timedelta(days=days)
                domain += [('bid_end_date', '<=', end_date)]
            except ValueError:
                pass

        order = f"{sort_field} {sort_order}"
        fields_to_read = [
            'id', 'name', 'version', 'title', 'create_date',
            'bid_start_date', 'bid_end_date', 'partner_ids',
            'state', 'partner_category_ids', 'is_exclusive',
            'total_amount', 'currency_id', 'submission_date',
        ]
        total = Tender.search_count(domain)
        tenders = Tender.search_read(domain, fields=fields_to_read, limit=limit, offset=offset,
                                     order=order)
        return {
            "total": total,
            "tenders": tenders,
        }

    def _check_user_tender_access_and_read(self, tender_id, user_id, read_for_website=False):
        tender_read = {}
        tender = request.env['tender.rfq'].sudo().browse(tender_id)
        user = request.env['res.users'].sudo().search_fetch(
            domain=[('id', '=', user_id), ('share', '=', True)],
            field_names=['id', 'name', 'partner_id'],
        )
        partner = user.partner_id
        deny_access = False
        tender_exist = tender.exists()

        if partner.state != 'approved':
            deny_access = True
        if tender_exist and (
                (tender.is_exclusive and partner.id not in tender.partner_ids.ids) or (
                tender.state in [
            'draft'])):
            deny_access = True

        if read_for_website:
            tender_read = tender._read_tender_for_website()

        response = {
            'tender_exists': tender_exist,
            'deny_access': deny_access,
            'tender': tender_read,
            'partner': partner.id,
        }
        return response

    @route(['/get/tender/<int:tender_id>'], type='http', auth="public", website=True)
    def get_tender(self, tender_id, **kw):
        user = request.env.user
        if user._is_public():
            return request.render('kaz_vendor_management.no_access_tender_view_template', {})
        response = self._check_user_tender_access_and_read(tender_id, user.id)
        if not response.get('tender_exists'):
            return request.not_found()
        else:
            if response.get('deny_access', False):
                return request.render('kaz_vendor_management.no_access_tender_info_view_template',
                                      {})

        website = request.website
        company_id = website.company_id.id if website and website.company_id else request.env.company.id
        partner = response.get('partner', False)
        props = {
            'tender_id': tender_id,
            'user_id': user.id,
            'partner_id': partner,
            'company_id': company_id,
            'tender_bid': {},
        }
        tender_bid = request.env['tender.bid'].sudo().search_read(
            domain=[('tender_rfq_id', '=', tender_id),
                    ('company_id', '=', company_id),
                    ('bid_user_id', '=', user.id)],
            fields=['id', 'name'],
            limit=1
        )
        if tender_bid:
            props['tender_bid'] = tender_bid[0]

        return request.render('kaz_vendor_management.register_tender_view_template',
                              {'props': props})

    @route(['/fetch/tender'], type='json', auth="public")
    def fetch_tender(self, tender_id, user_id, company_id, **kw):
        response = self._check_user_tender_access_and_read(tender_id, user_id,
                                                           read_for_website=True)
        return response

    @route('/download/bid/attachment/<int:doc_id>', type='http', auth='public',
           website=True)
    def download_bid_attachment(self, doc_id, **kwargs):
        doc = request.env['tender.bid.required.attachment'].sudo().browse(doc_id)

        # Check document exists
        if not doc.exists():
            return request.not_found()

        if not doc.attachment_id:
            return request.not_found()

        # Prepare file download
        file_content = base64.b64decode(doc.attachment_id or "")
        file_name = doc.file_name or doc.name or "document.bin"

        return Response(
            file_content,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', f'attachment; filename="{file_name}"')
            ],
            status=200
        )

    @route('/download/tender/attachment/<int:doc_id>', type='http', auth='public',
           website=True)
    def download_tender_attachment(self, doc_id, **kwargs):
        doc = request.env['tender.rfq.document'].sudo().browse(doc_id)

        # Check document exists
        if not doc.exists():
            return request.not_found()

        # Check online availability
        if not doc.available_online:
            return request.not_found()

        # Prepare file download
        file_content = base64.b64decode(doc.attachment_id or "")
        file_name = doc.file_name or doc.name or "document.bin"

        return Response(
            file_content,
            headers=[
                ('Content-Type', 'application/octet-stream'),
                ('Content-Disposition', f'attachment; filename="{file_name}"')
            ],
            status=200
        )

    @route(
        ['/tender/<int:tender_id>/bid',
         '/tender/<int:tender_id>/bid/<int:bid_id>'],
        type='http', auth='public', website=True)
    def tender_bid(self, tender_id, bid_id=None, **kwargs):
        website = request.website
        company_id = website.company_id.id if website and website.company_id else request.env.company.id
        user = request.env.user
        partner = user.partner_id
        if user._is_public():
            return request.render('kaz_vendor_management.no_access_tender_view_template', {})

        tender = request.env['tender.rfq'].sudo().search_fetch(
            domain=[('id', '=', tender_id)],
            field_names=['id', 'name', 'title', 'tender_rfq_line_ids', 'is_exclusive',
                         'partner_ids', 'currency_id'],
            limit=1)

        deny_access = False
        tender_exist = tender.exists()
        if not tender_exist:
            raise request.not_found()
        if partner.state != 'approved':
            deny_access = True
        if tender_exist and (
                (tender.is_exclusive and partner.id not in tender.partner_ids.ids) or (
                tender.state in [
            'draft'])):
            deny_access = True
        if deny_access:
            return request.render('kaz_vendor_management.no_access_tender_info_view_template', )
        active_bid = False

        if bid_id:
            active_bid = request.env['tender.bid'].sudo().search_fetch(
                domain=[('id', '=', bid_id)],
                field_names=['id', 'name', 'total_amount'],
                limit=1)
            if not active_bid:
                raise request.not_found()
        else:
            active_bid = request.env['tender.bid'].sudo().search_fetch(
                domain=[
                    ('tender_rfq_id', '=', tender_id),
                    ('bid_user_id', '=', user.id),
                    ('company_id', '=', company_id)
                ],
                field_names=['id', 'name'],
                limit=1)
            if active_bid:
                raise request.not_found()

        tender_lines = tender.tender_rfq_line_ids.read(
            ['id', 'name', 'product_id', 'qty', 'account_id', 'analytic_distribution', 'price_unit',
             'uom_id', 'currency_id']
        )
        required_attachments = tender.tender_required_attachment_ids.read(
            ['id', 'name', 'sequence']
        )
        props = {
            'tender_id': tender.id,
            'tender_name': tender.name,
            'tender_title': tender.title,
            'total_amount': tender.total_amount,
            'active_bid': active_bid.id if active_bid else False,
            'tender_lines': tender_lines,
            'required_attachments': required_attachments,
            'is_readonly': bool(active_bid),
            'company_id': company_id,
            'currency_id': tender.currency_id.read(['id', 'name', 'symbol'])[0],
            'user_id': user.id,
        }
        return request.render('kaz_vendor_management.tender_bid_template', {
            'props': props
        })

    @route(['/fetch/tender/bid'], type='json', auth="user")
    def fetch_tender_bid(self, tender_bid_id, user_id, company_id, **kw):
        tender_bid = request.env['tender.bid'].sudo().search_read(
            domain=[('id', '=', tender_bid_id), ('company_id', '=', company_id),
                    ('bid_user_id', '=', user_id)],
            fields=['id', 'name', 'title', 'tender_rfq_id', 'state', 'create_date', 'currency_id'],
            limit=1
        )
        if tender_bid:
            tender_bid = tender_bid[0]
            tender_bid['tender_bid_rfq_line_ids'] = request.env[
                'tender.bid.rfq.line'].sudo().search_read(
                domain=[('tender_bid_id', '=', tender_bid_id)],
                fields=['id', 'name', 'required_qty', 'account_id', 'analytic_distribution', 'qty',
                        'price_unit', 'expected_price_unit', 'currency_id', 'product_id', 'uom_id'],
            )
            tender_bid['tender_bid_required_attachment_ids'] = request.env[
                'tender.bid.required.attachment'].sudo().search_read(
                domain=[('tender_bid_id', '=', tender_bid_id)],
                fields=['id', 'name', 'sequence'],
            )
            return tender_bid
        return {}

    @route(['/submit/bid'], type='json', auth="user")
    def submit_tender_bid(self, tender_rfq_id, user_id, tender_bid_rfq_line_ids,
                          tender_bid_required_attachment_ids, company_id, currency_id, **kw):
        response = self._check_user_tender_access_and_read(tender_rfq_id, user_id)

        if response.get('deny_access'):
            return {
                'success': False,
                'message': "You don't have access to this tender",
            }
        tender_bid = request.env['tender.bid'].sudo().search_fetch(
            domain=[('tender_rfq_id', '=', tender_rfq_id),
                    ('company_id', '=', company_id),
                    ('bid_user_id', '=', user_id)],
            field_names=['id', 'name'],
            limit=1
        )
        if tender_bid:
            return {
                'success': False,
                'message': "You already have a bid for this Tender",
            }
        else:
            try:
                tender_bid = request.env['tender.bid'].with_user(SUPERUSER_ID).sudo().create({
                    'tender_rfq_id': tender_rfq_id,
                    'bid_user_id': user_id,
                    'company_id': company_id,
                    'currency_id': currency_id,
                    'is_portal': True,
                    'tender_bid_rfq_line_ids': [
                        Command.create({
                            'product_id': rec.get('product_id')[0],
                            'account_id': rec.get('account_id')[0] if rec.get(
                                'account_id') else False,
                            'analytic_distribution': rec.get('analytic_distribution'),
                            'qty': rec.get('user_qty'),
                            'required_qty': rec.get('qty'),
                            'price_unit': rec.get('user_price_unit'),
                            'expected_price_unit': rec.get('price_unit'),
                        }) for rec in tender_bid_rfq_line_ids if rec.get('product_id')
                    ],
                    'tender_bid_required_attachment_ids': [
                        Command.create({
                            'sequence': idx + 1,
                            'name': att.get('name'),
                            'file_name': att.get('file_name'),
                            'attachment_id': att.get('attachment_id'),
                        }) for idx, att in enumerate(tender_bid_required_attachment_ids)
                    ],
                })
                return {
                    'success': True,
                    'message': "You have successfully created this Tender",
                    'tender_bid': tender_bid.id,
                }
            except Exception as e:
                return {
                    'success': False,
                    'message': "Something went wrong",
                    'details': str(e)
                }

# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect

class WinkRequest(http.Controller):

    @http.route('/my/requests/new', type='http', auth='public', website=True)
    def new_request(self, product_id=None, **kwargs):
        if not product_id:
            return request.redirect('/services')
        
        product = request.env['product.template'].sudo().search([
            ('id', '=', int(product_id)),
            ('available_on_wink', '=', True)
        ], limit=1)
        
        if not product:
            return request.redirect('/services')

        if not request.env.user._is_public():
            # User is authenticated
            employees = request.env['kuec.employee.directory'].sudo().search([
                ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)
            ])
            return request.render('kuec_service_catalogue.wink_request_form', {
                'product': product,
                'employees': employees,
                'show_registration_banner': kwargs.get('registered') == '1'
            })
        else:
            # User is anonymous
            return request.render('kuec_service_catalogue.wink_registration_form', {
                'product': product,
                'errors': {},
                'post': kwargs
            })

    @http.route('/my/requests/register', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def register_and_request(self, **post):
        product_id = post.get('product_id')
        product = request.env['product.template'].sudo().search([
            ('id', '=', int(product_id)),
            ('available_on_wink', '=', True)
        ], limit=1) if product_id else None

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

        # Step 3 — Assign eligibility tag
        company_type = post.get('company_type')
        mapping = {
            'ku': 'ku',
            'kuec': 'kuec',
            'uae': 'uae',
            'outside': 'abroad'
        }
        
        if company_type in mapping:
            rule = request.env['kuec.eligibility.rule'].sudo().search([('code', '=', mapping[company_type])], limit=1)
            if rule:
                company.eligibility_tag_ids = [(4, rule.id)]

        # Step 4 — Create contact person
        contact = request.env['res.partner'].sudo().create({
            'name': post['contact_name'],
            'email': post['contact_email'],
            'phone': post['contact_phone'],
            'parent_id': company.id,
            'type': 'contact',
        })

        # Step 5 — Create portal user account
        contact.sudo().signup_prepare(signup_type='reset')

        # Step 6 — Send welcome email
        template = request.env.ref('kuec_service_catalogue.kuec_portal_welcome_email', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(contact.id, force_send=True)

        # Step 7 — Auto-login the new user
        request.env['res.users'].sudo()._signup_create_user({
            'name': contact.name,
            'login': contact.email,
            'partner_id': contact.id,
        })
        
        try:
            request.session.authenticate(request.db, contact.email, False)
        except Exception:
            # Fallback redirect if authenticate fails
            pass

        # Step 8 — Redirect to request form
        if not request.session.uid:
            return request.redirect(f'/web/login?login={contact.email}&redirect=/my/requests/new?product_id={product_id}&registered=1')
            
        return request.redirect(f'/my/requests/new?product_id={product_id}&registered=1')

    @http.route('/my/requests/submit', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def submit_request(self, **post):
        product_id = int(post.get('product_id', 0))
        product = request.env['product.template'].sudo().search([
            ('id', '=', product_id),
            ('available_on_wink', '=', True),
        ], limit=1)
        if not product:
            return request.redirect('/services')

        partner = request.env.user.partner_id.commercial_partner_id

        qty = float(post.get('qty') or 1)
        notes = post.get('notes') or False
        start_date = post.get('start_date') or False
        employee_ids = request.httprequest.form.getlist('employee_ids')
        employee_ids = [int(e) for e in employee_ids if str(e).isdigit()]

        variant = product.product_variant_id
        line_vals = {
            'product_id': variant.id,
            'product_uom_qty': qty,
            'price_unit': product.list_price,
            'name': product.name,
        }

        order_vals = {
            'partner_id': partner.id,
            'order_line': [(0, 0, line_vals)],
            'wink_request_notes': notes,
            'wink_requested_start_date': start_date,
            'wink_is_portal_request': True,
            'wink_source_product_id': product.id,
            'origin': 'WINK Portal',
        }

        if product.wink_payment_term_id:
            order_vals['payment_term_id'] = product.wink_payment_term_id.id

        if product.delivery_model == 'retainer':
            if hasattr(product, 'plan_id') and product.plan_id:
                order_vals['plan_id'] = product.plan_id.id

        if product.price_visibility == 'hidden':
            order_vals['wink_price_confirmed'] = False
        else:
            order_vals['wink_price_confirmed'] = True

        order = request.env['sale.order'].sudo().create(order_vals)

        if employee_ids:
            order.sudo().wink_selected_employee_ids = [(6, 0, employee_ids)]

        is_auto_confirm = (
            product.commercial_structure == 'standalone'
            and product.request_frequency == 'one_time'
        )
        if is_auto_confirm:
            order.sudo().action_confirm()

        order.sudo().message_post(
            body=f"Service request submitted via WINK portal by {request.env.user.partner_id.name}.",
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        template = request.env.ref('kuec_service_catalogue.kuec_coordinator_notification_email', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(order.id, force_send=True)

        return request.redirect(f'/my/requests/{order.id}')


    @http.route('/my/requests/<int:order_id>', type='http', auth='user', website=True)
    def request_detail(self, order_id, **kwargs):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        
        if not order:
            raise NotFound()
            
        product = order.order_line[0].product_id.product_tmpl_id if order.order_line else False
            
        return request.render('kuec_service_catalogue.wink_request_confirmation', {
            'order': order,
            'product': product,
            'payment_pending': kwargs.get('payment') == 'pending'
        })


    @http.route('/my/requests/<int:order_id>/pay', type='http', auth='user', website=True)
    def request_payment(self, order_id, **kwargs):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        
        if not order:
            raise NotFound()
            
        if order.state != 'sale' or (not order.wink_price_confirmed and order.wink_source_product_id.price_visibility == 'hidden'):
            return request.redirect(f'/my/requests/{order.id}?error=payment_not_available')
            
        return request.render('kuec_service_catalogue.wink_payment_page', {
            'order': order
        })

    @http.route('/my/requests/<int:order_id>/confirm-manual', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def confirm_manual_payment(self, order_id, **post):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        
        if not order:
            raise NotFound()

        order.sudo().message_post(
            body="Customer has indicated manual payment has been made. Awaiting coordinator confirmation.",
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        template = request.env.ref('kuec_service_catalogue.kuec_coordinator_notification_email', raise_if_not_found=False)
        if template:
            template.sudo().send_mail(order.id, force_send=True)

        return request.redirect(f'/my/requests/{order_id}?payment=pending')

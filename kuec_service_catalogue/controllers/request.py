# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from werkzeug.exceptions import NotFound
from odoo.addons.sale.controllers.portal import CustomerPortal
import werkzeug.urls

class WinkRequest(http.Controller):

    def _parse_product_id(self, value):
        """Parse product_id from request; returns int or None on invalid."""
        if not value:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @http.route('/my/requests/new', type='http', auth='public', website=True)
    def new_request(self, product_id=None, **kwargs):
        if not product_id:
            return request.redirect('/services')
        pid = self._parse_product_id(product_id)
        if pid is None:
            return request.redirect('/services')

        product = request.env['product.template'].sudo().search([
            ('id', '=', pid),
            ('available_on_wink', '=', True)
        ], limit=1)

        if not product:
            return request.redirect('/services')

        if not request.env.user._is_public():
            # User is authenticated
            employees = request.env['kuec.employee.directory'].sudo().search([
                ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)
            ])

            render_vals = {
                'product': product,
                'employees': employees,
                'show_registration_banner': kwargs.get('registered') == '1',
                'is_bundle': False,
            }

            # Bundle tier data
            if product.commercial_structure == 'bundled' and product.wink_bundle_id:
                bundle = product.wink_bundle_id
                tiers = bundle.tier_ids.sorted('sequence')
                tier_data = []
                for tier in tiers:
                    tier_data.append({
                        'tier': tier,
                        'items': tier.item_ids.sorted('sequence'),
                    })
                render_vals.update({
                    'is_bundle': True,
                    'bundle': bundle,
                    'tier_data': tier_data,
                })

            return request.render('kuec_service_catalogue.wink_request_form', render_vals)
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
        pid = self._parse_product_id(product_id)
        product = request.env['product.template'].sudo().search([
            ('id', '=', pid),
            ('available_on_wink', '=', True)
        ], limit=1) if pid is not None else None

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

        # Step 3 — Save company type for classification
        company_type = post.get('company_type')
        if company_type:
            company.sudo().write({'wink_company_type': company_type})

        # Step 4 — Create contact person
        contact = request.env['res.partner'].sudo().create({
            'name': post['contact_name'],
            'email': post['contact_email'],
            'phone': post['contact_phone'],
            'parent_id': company.id,
            'type': 'contact',
        })

        # Step 5 — Create portal user account
        portal_group = request.env.ref('base.group_portal')
        new_user = request.env['res.users'].sudo().create({
            'name': contact.name,
            'login': contact.email,
            'partner_id': contact.id,
            'groups_id': [(6, 0, [portal_group.id])],
        })

        # Step 6 — Send password reset email (uses Odoo's native reset flow)
        try:
            new_user.sudo().action_reset_password()
        except Exception:
            pass  # Non-blocking: user can always reset later

        # Step 7 — Redirect to login page
        redirect_url = werkzeug.urls.url_quote(
            f"/my/requests/new?product_id={post.get('product_id', '')}&registered=1"
        )
        return request.redirect(
            f"/web/login?redirect={redirect_url}"
        )

    @http.route('/my/requests/submit', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def submit_request(self, **post):
        product_id = self._parse_product_id(post.get('product_id'))
        if product_id is None:
            return request.redirect('/services')
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



        if product.price_visibility == 'hidden':
            order_vals['wink_price_confirmed'] = False
        else:
            order_vals['wink_price_confirmed'] = True

        order = request.env['sale.order'].sudo().create(order_vals)

        if employee_ids:
            order.sudo().wink_selected_employee_ids = [(6, 0, employee_ids)]

        # --- Bundle tier handling ---
        is_bundle = (
            product.commercial_structure == 'bundled'
            and product.wink_bundle_id
        )
        tier = None
        bundle_line = None

        if is_bundle:
            try:
                tier_id = int(post.get('tier_id', 0))
            except (TypeError, ValueError):
                tier_id = 0
            tier = request.env['wink.bundle.tier'].sudo().browse(tier_id)
            if not tier.exists() or tier.bundle_id != product.wink_bundle_id:
                return request.redirect('/services')

            # Find the bundle product line and override name/price
            bundle_line = order.order_line.filtered(
                lambda l: l.product_id.product_tmpl_id.id == product.id
            )[:1]
            if bundle_line:
                bundle_line.sudo().write({
                    'price_unit': tier.price,
                    'name': f"{product.name} — {tier.name}",
                })

            # Save tier on order
            order.sudo().write({
                'wink_bundle_tier_id': tier.id,
            })

            # Create entitlement records (no SO lines yet —
            # real lines are created when customer activates)
            for item in tier.item_ids.sorted('sequence'):
                request.env['wink.bundle.entitlement'].sudo().create({
                    'order_id': order.id,
                    'tier_id': tier.id,
                    'service_product_id': item.service_product_id.id,
                    'name': (item.description
                             or item.service_product_id.name),
                    'sequence': item.sequence,
                    'qty_entitled': item.qty,
                })


        is_auto_confirm = (
            product.commercial_structure == 'standalone'
            and product.request_frequency == 'one_time'
        )
        if is_auto_confirm:
            try:
                order.sudo().action_confirm()
            except (ValueError, Exception) as e:
                # Odoo 18 bug: project template with 0 tasks causes ValueError
                # in project_task.create() — order is still created, coordinator
                # can confirm manually.
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning("Auto-confirm failed for order %s: %s", order.name, e)

        order.sudo().message_post(
            body=f"Service request submitted via WINK portal by {request.env.user.partner_id.name}.",
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )

        template = request.env.ref('kuec_service_catalogue.kuec_coordinator_notification_email_v5', raise_if_not_found=False)
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

        # Document compliance context
        requirements = product.kuec_document_ids if product else request.env['kuec.service.document'].browse()
        submissions = request.env['kuec.document.submission'].sudo().search([
            ('order_id', '=', order_id)
        ])
        sub_map = {s.requirement_id.id: s for s in submissions}

        return request.render('kuec_service_catalogue.wink_request_confirmation', {
            'order': order,
            'product': product,
            'payment_pending': kwargs.get('payment') == 'pending',
            'bundle_requested': kwargs.get('bundle_requested') == '1',
            'requirements': requirements,
            'sub_map': sub_map,
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

        # Use native Odoo CustomerPortal controller to fetch payment providers/tokens
        portal_controller = CustomerPortal()
        payment_values = portal_controller._get_payment_values(
            order,
            force_auth=True,
            submit_tx_url='/shop/payment/transaction/{order.id}',
        )

        # --- Epic 6: Upfront Deposits Custom Logic ---
        # Modify the payment amount if the payment term defines a fractional upfront deposit
        if order.payment_term_id and order.payment_term_id.line_ids:
            first_term_line = order.payment_term_id.line_ids[0]
            # Odoo 18 uses 'value' = 'percent' and 'value_amount' for percentage
            if first_term_line.value == 'percent' and first_term_line.value_amount < 100:
                # Calculate the exact fractional deposit from the total amount
                deposit_amt = order.currency_id.round(order.amount_total * (first_term_line.value_amount / 100.0))
                payment_values['amount'] = deposit_amt

        # Override the landing route so Odoo returns to the request details, not sale portal
        payment_values['landing_route'] = f'/my/requests/{order.id}'

        render_values = {
            'order': order,
            **payment_values
        }

        return request.render('kuec_service_catalogue.wink_payment_page_v2', render_values)

    @http.route('/my/requests/<int:order_id>/documents', type='http', auth='user', website=True)
    def request_documents(self, order_id, **kw):
        """Portal page listing document requirements and upload forms."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        product = order.wink_source_product_id
        requirements = product.kuec_document_ids if product else request.env['kuec.service.document'].browse()
        submissions = request.env['kuec.document.submission'].sudo().search([
            ('order_id', '=', order_id)
        ])
        sub_map = {s.requirement_id.id: s for s in submissions}

        return request.render('kuec_service_catalogue.wink_document_upload_page', {
            'order': order,
            'requirements': requirements,
            'sub_map': sub_map,
            'doc_uploaded': kw.get('doc_uploaded') == '1',
            'doc_error': kw.get('doc_error', False),
        })

    @http.route('/my/requests/<int:order_id>/documents/upload', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def upload_document(self, order_id, **post):
        """Handle document file upload from portal."""
        import base64
        from odoo import fields as odoo_fields

        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        try:
            requirement_id = int(post.get('requirement_id', 0))
        except (TypeError, ValueError):
            requirement_id = 0
        requirement = request.env['kuec.service.document'].sudo().browse(requirement_id)
        if not requirement.exists():
            raise NotFound()

        uploaded = request.httprequest.files.get('doc_file')
        if not uploaded or not uploaded.filename:
            return request.redirect(
                f'/my/requests/{order_id}/documents?doc_error=no_file'
            )

        allowed_mimetypes = {
            'application/pdf',
            'image/jpeg',
            'image/png',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        if uploaded.mimetype not in allowed_mimetypes:
            return request.redirect(
                f'/my/requests/{order_id}/documents?doc_error=bad_type'
            )

        file_data = base64.b64encode(uploaded.read())

        attachment = request.env['ir.attachment'].sudo().create({
            'name': uploaded.filename,
            'datas': file_data,
            'res_model': 'kuec.document.submission',
            'mimetype': uploaded.mimetype,
            'type': 'binary',
        })

        existing = request.env['kuec.document.submission'].sudo().search([
            ('order_id', '=', order_id),
            ('requirement_id', '=', requirement_id),
        ], limit=1)

        now = odoo_fields.Datetime.now()

        if existing:
            existing.sudo().write({
                'attachment_id': attachment.id,
                'filename': uploaded.filename,
                'state': 'under_review',
                'submitted_date': now,
                'coordinator_notes': False,
                'reviewed_date': False,
                'reviewed_by': False,
            })
        else:
            request.env['kuec.document.submission'].sudo().create({
                'order_id': order_id,
                'requirement_id': requirement_id,
                'partner_id': request.env.user.partner_id.id,
                'attachment_id': attachment.id,
                'filename': uploaded.filename,
                'state': 'under_review',
                'submitted_date': now,
            })

        return request.redirect(
            f'/my/requests/{order_id}/documents?doc_uploaded=1'
        )

    # ── Bundle Activation Route ──
    @http.route(
        '/my/requests/<int:order_id>/bundle/'
        '<int:entitlement_id>/activate',
        type='http', auth='user', website=True,
        methods=['POST'], csrf=True)
    def bundle_activate_request(
        self, order_id, entitlement_id, **post
    ):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of',
             request.env.user.partner_id
             .commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()

        entitlement = request.env[
            'wink.bundle.entitlement'
        ].sudo().search([
            ('id', '=', entitlement_id),
            ('order_id', '=', order_id),
            ('state', '=', 'available'),
        ], limit=1)
        if not entitlement:
            raise NotFound()

        try:
            entitlement.action_activate()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(
                "Bundle activation failed for entitlement %s: %s",
                entitlement_id, e,
            )
            return request.redirect(
                f'/my/requests/{order_id}'
                f'?error=activation_failed'
            )

        return request.redirect(
            f'/my/requests/{order_id}'
            f'?bundle_requested=1'
        )

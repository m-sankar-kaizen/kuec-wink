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

    def _get_request_form_vals(self, product, errors=None, post=None):
        """Build template values for wink_request_form (used by new_request and on validation error)."""
        employees = request.env['kuec.employee.directory'].sudo().search([
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id)
        ])
        vals = {
            'product': product,
            'employees': employees,
            'show_registration_banner': False,
            'is_bundle': False,
            'errors': errors or {},
            'post': post or {},
        }
        if product.commercial_structure == 'bundled' and product.wink_bundle_id:
            bundle = product.wink_bundle_id
            tiers = bundle.tier_ids.sorted('sequence')
            tier_data = []
            for tier in tiers:
                tier_data.append({
                    'tier': tier,
                    'items': tier.item_ids.sorted('sequence'),
                })
            vals.update({
                'is_bundle': True,
                'bundle': bundle,
                'tier_data': tier_data,
            })
        # Prefer Odoo native Recurring Prices (Recurring Plan + Recurring Price tab); else quotation templates
        recurring_lines = product._wink_recurring_plan_lines()
        if recurring_lines:
            vals['recurring_plan_lines'] = recurring_lines
            vals['use_recurring_prices'] = True
        elif product.wink_subscription_plan_ids:
            vals['subscription_plan_ids'] = product.wink_subscription_plan_ids
        return vals

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
                'errors': {},
                'post': kwargs,
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
            recurring_lines = product._wink_recurring_plan_lines()
            if recurring_lines:
                render_vals['recurring_plan_lines'] = recurring_lines
                render_vals['use_recurring_prices'] = True
            elif product.wink_subscription_plan_ids:
                render_vals['subscription_plan_ids'] = product.wink_subscription_plan_ids

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

        # Service request is per service, no quantity (always 1)
        notes = post.get('notes') or False
        start_date = post.get('start_date') or False
        if start_date:
            try:
                from datetime import datetime
                datetime.strptime(start_date, '%Y-%m-%d')
            except (ValueError, TypeError):
                start_date = False
        employee_ids = request.httprequest.form.getlist('employee_ids')
        employee_ids = [int(e) for e in employee_ids if str(e).isdigit()]

        is_bundle = (
            product.commercial_structure == 'bundled'
            and product.wink_bundle_id
        )

        # Plan: prefer Odoo native Recurring Prices; else quotation templates
        recurring_lines = product._wink_recurring_plan_lines()
        use_recurring_prices = bool(recurring_lines)
        has_subscription_plans = not use_recurring_prices and bool(product.wink_subscription_plan_ids)

        if use_recurring_prices:
            try:
                pricing_id = int(post.get('recurring_pricing_id') or 0)
            except (TypeError, ValueError):
                pricing_id = 0
            pricing = request.env['product.pricing'].sudo().browse(pricing_id)
            if not pricing.exists() or pricing.id not in recurring_lines.ids:
                vals = self._get_request_form_vals(product, errors={'subscription_plan': _('Please select a plan.')}, post=post)
                vals['recurring_plan_lines'] = recurring_lines
                vals['use_recurring_prices'] = True
                return request.render('kuec_service_catalogue.wink_request_form', vals)
        elif has_subscription_plans:
            try:
                template_id = int(post.get('subscription_plan_id') or 0)
            except (TypeError, ValueError):
                template_id = 0
            template = request.env['sale.order.template'].sudo().browse(template_id)
            if not template.exists() or template.id not in product.wink_subscription_plan_ids.ids:
                vals = self._get_request_form_vals(product, errors={'subscription_plan': _('Please select a plan.')}, post=post)
                vals.setdefault('subscription_plan_ids', product.wink_subscription_plan_ids)
                return request.render('kuec_service_catalogue.wink_request_form', vals)

        # Validation: employees required when product or child service requires selection
        if not is_bundle:
            if product.requires_employee_selection and not employee_ids:
                vals = self._get_request_form_vals(product, errors={'employee_ids': _('Please select at least one employee for this service.')}, post=post)
                return request.render('kuec_service_catalogue.wink_request_form', vals)
        else:
            try:
                tier_id = int(post.get('tier_id', 0))
            except (TypeError, ValueError):
                tier_id = 0
            tier = request.env['wink.bundle.tier'].sudo().browse(tier_id)
            if tier.exists() and tier.bundle_id == product.wink_bundle_id:
                missing = []
                for idx, item in enumerate(tier.item_ids.sorted('sequence')):
                    if item.service_product_id and item.service_product_id.requires_employee_selection:
                        emp_ids = request.httprequest.form.getlist('employee_ids_%s_%s' % (tier.id, idx))
                        emp_ids = [int(e) for e in emp_ids if str(e).isdigit()]
                        if not emp_ids:
                            missing.append(item.description or item.service_product_id.name)
                if missing:
                    vals = self._get_request_form_vals(product, errors={
                        'employee_ids_bundle': _('Please select at least one employee for: %s') % ', '.join(missing)
                    }, post=post)
                    return request.render('kuec_service_catalogue.wink_request_form', vals)

        variant = product.product_variant_id
        price_unit = product.list_price
        selected_pricing = request.env['product.pricing'].browse()
        if use_recurring_prices:
            try:
                pricing_id = int(post.get('recurring_pricing_id') or 0)
            except (TypeError, ValueError):
                pricing_id = 0
            selected_pricing = request.env['product.pricing'].sudo().browse(pricing_id)
            if selected_pricing.exists() and selected_pricing.id in recurring_lines.ids:
                price_unit = getattr(selected_pricing, 'price', price_unit) or price_unit

        line_vals = {
            'product_id': variant.id,
            'product_uom_qty': 1,
            'price_unit': price_unit,
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

        # Employees: for standalone set on order; for bundle set per entitlement below
        if not is_bundle and employee_ids:
            order.sudo().wink_selected_employee_ids = [(6, 0, employee_ids)]

        # --- Set Odoo native Recurring Prices: store selected pricing and plan on order ---
        if use_recurring_prices and selected_pricing.exists():
            order.sudo().write({'wink_recurring_pricing_id': selected_pricing.id})
            plan = getattr(selected_pricing, 'recurring_plan_id', None) or getattr(selected_pricing, 'plan_id', None)
            if plan:
                write_vals = {}
                if hasattr(order, 'recurring_plan_id'):
                    write_vals['recurring_plan_id'] = plan.id
                if hasattr(order, 'plan_id'):
                    write_vals['plan_id'] = plan.id
                if write_vals:
                    order.sudo().write(write_vals)
                if order.order_line:
                    line = order.order_line[0]
                    if hasattr(line, 'recurring_plan_id'):
                        line.sudo().write({'recurring_plan_id': plan.id})
                    elif hasattr(line, 'plan_id'):
                        line.sudo().write({'plan_id': plan.id})

        # --- Set quotation template when product uses subscription plans (no Recurring Prices) ---
        if has_subscription_plans:
            try:
                template_id = int(post.get('subscription_plan_id') or 0)
            except (TypeError, ValueError):
                template_id = 0
            template = request.env['sale.order.template'].sudo().browse(template_id)
            if template.exists() and template_id in product.wink_subscription_plan_ids.ids:
                order.sudo().write({'wink_sale_order_template_id': template.id})
                if hasattr(order, 'sale_order_template_id'):
                    order.sudo().write({'sale_order_template_id': template.id})
                if hasattr(order, '_apply_order_template'):
                    try:
                        order.sudo()._apply_order_template()
                    except Exception:
                        pass

        # --- Bundle tier handling ---
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
            # real lines are created when customer activates).
            # Employees and documents are linked to each child service (entitlement).
            for idx, item in enumerate(tier.item_ids.sorted('sequence')):
                ent_vals = {
                    'order_id': order.id,
                    'tier_id': tier.id,
                    'service_product_id': item.service_product_id.id,
                    'name': (item.description
                             or item.service_product_id.name),
                    'sequence': item.sequence,
                    'qty_entitled': item.qty,
                }
                ent = request.env['wink.bundle.entitlement'].sudo().create(ent_vals)
                # Per–child-service employee selection (from form employee_ids_tierId_index)
                emp_ids = request.httprequest.form.getlist('employee_ids_%s_%s' % (tier.id, idx))
                emp_ids = [int(e) for e in emp_ids if str(e).isdigit()]
                if emp_ids:
                    ent.sudo().wink_selected_employee_ids = [(6, 0, emp_ids)]


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

        product = order.wink_source_product_id or (order.order_line[0].product_id.product_tmpl_id if order.order_line else False)

        # Document compliance: for bundle = child services' docs; for standalone = product's docs
        requirements = order._wink_document_requirements()
        submissions = request.env['kuec.document.submission'].sudo().search([
            ('order_id', '=', order_id)
        ])
        sub_map = {s.requirement_id.id: s for s in submissions}

        is_retainer = product and product.delivery_model == 'retainer'
        # Current plan: from Recurring Prices (native) or quotation template
        retainer_plan = order.wink_recurring_pricing_id or order.wink_sale_order_template_id
        recurring_lines = product._wink_recurring_plan_lines() if product else request.env['product.pricing'].browse()
        if recurring_lines:
            retainer_plans_for_change = recurring_lines
        else:
            retainer_plans_for_change = (product.wink_subscription_plan_ids if product else request.env['sale.order.template'].browse())
        retainer_plan_has_price = bool(getattr(retainer_plan, 'price', None)) if retainer_plan else False

        return request.render('kuec_service_catalogue.wink_request_confirmation', {
            'order': order,
            'product': product,
            'payment_pending': kwargs.get('payment') == 'pending',
            'bundle_requested': kwargs.get('bundle_requested') == '1',
            'requirements': requirements,
            'sub_map': sub_map,
            'is_retainer': is_retainer,
            'retainer_plan': retainer_plan,
            'retainer_plans_for_change': retainer_plans_for_change,
            'retainer_plan_has_price': retainer_plan_has_price,
            'retainer_cancelled': kwargs.get('retainer_cancelled') == '1',
        })


    @http.route('/my/requests/<int:order_id>/retainer/cancel', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def retainer_request_cancel(self, order_id, **post):
        """Customer requests cancellation of a retainer. Sets flag; coordinator can confirm cancel."""
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)
        if not order:
            raise NotFound()
        product = order.wink_source_product_id
        if not product or product.delivery_model != 'retainer':
            return request.redirect(f'/my/requests/{order_id}')
        order.sudo().write({'wink_cancellation_requested': True})
        order.sudo().message_post(
            body=_("Customer requested cancellation of this retainer from the portal."),
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return request.redirect(f'/my/requests/{order_id}?retainer_cancelled=1')

    @http.route('/my/requests/<int:order_id>/pay', type='http', auth='user', website=True)
    def request_payment(self, order_id, **kwargs):
        order = request.env['sale.order'].sudo().search([
            ('id', '=', order_id),
            ('partner_id', 'child_of', request.env.user.partner_id.commercial_partner_id.id),
        ], limit=1)

        if not order:
            raise NotFound()

        source_product = order.wink_source_product_id
        if order.state != 'sale' or (not order.wink_price_confirmed and source_product and source_product.price_visibility == 'hidden'):
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

        # Document requirements: for bundle = child services'; for standalone = product's
        requirements = order._wink_document_requirements()
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

        # Ensure the requirement is one of this order's (product or bundle child services)
        allowed_requirement_ids = order._wink_document_requirements().ids
        if allowed_requirement_ids and requirement_id not in allowed_requirement_ids:
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

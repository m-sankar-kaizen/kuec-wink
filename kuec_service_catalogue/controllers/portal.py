from odoo import http, Command
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
try:
    from odoo.addons.account_payment.controllers.payment import PaymentPortal as AccountPaymentPortal

    class WinkInvoicePaymentFix(AccountPaymentPortal):
        """Odoo 18 hotfix: invoice_transaction() requires access_token as a positional
        argument, but authenticated portal users access invoices without a token in the
        URL, so the payment form renders without data-access-token and the RPC call
        omits it.  We make the argument optional and generate it on the fly."""

        @http.route('/invoice/transaction/<int:invoice_id>', type='json', auth='public')
        def invoice_transaction(self, invoice_id, access_token=None, **kwargs):
            if not access_token:
                invoice = request.env['account.move'].sudo().browse(invoice_id)
                if invoice.exists():
                    access_token = invoice._portal_ensure_token()
            return super().invoice_transaction(invoice_id, access_token, **kwargs)

except ImportError:
    pass  # account_payment not installed

class KuecCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id.commercial_partner_id
        
        # Odoo 18 frontend workaround: Prevent /my/counters from returning custom
        # counts that crash the JS if the UI spans (.o_portal_request_count) are missing.
        if request.httprequest.path == '/my/counters':
            return values
        
        # Employee Directory Counter
        if (not counters or 'employee_count' in counters) and partner.employee_directory_enabled:
            domain = [('partner_id', '=', partner.id)]
            employee_count = request.env['kuec.employee.directory'].sudo().search_count(domain)
            values['employee_count'] = employee_count
            
        # WINK Service Requests Counter
        if not counters or 'request_count' in counters:
            request_domain = [
                ('message_partner_ids', 'child_of', [partner.id]),
                ('wink_is_portal_request', '=', True),
                ('state', 'in', ['draft', 'sent', 'sale', 'done'])
            ]
            request_count = request.env['sale.order'].sudo().search_count(request_domain)
            values['request_count'] = request_count

        # V-1: Vendor Ratings Counter — shown only when user is a vendor (has received POs)
        if not counters or 'vendor_rating_count' in counters:
            vendor_partner = request.env.user.partner_id.commercial_partner_id
            vendor_rating_count = request.env['rating.rating'].sudo().search_count([
                ('rated_partner_id', 'child_of', vendor_partner.id),
                ('consumed', '=', True),
                ('res_model', '=', 'project.task'),
            ])
            values['vendor_rating_count'] = vendor_rating_count

        # U-3: My Bundles Counter (confirmed + self-service-cancelled orders with entitlements)
        if not counters or 'bundle_count' in counters:
            bundle_domain = [
                ('message_partner_ids', 'child_of', [partner.id]),
                ('wink_is_portal_request', '=', True),
                '|',
                ('state', 'in', ['sale', 'done']),
                ('wink_bundle_cancelled', '=', True),
                ('wink_entitlement_ids', '!=', False),
            ]
            bundle_count = request.env['sale.order'].sudo().search_count(bundle_domain)
            values['bundle_count'] = bundle_count

        return values

    @http.route(['/my/requests', '/my/requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id.commercial_partner_id
        SaleOrder = request.env['sale.order'].sudo()

        # Epic4-MR: base domain (include cancel when status filter is cancel)
        status_filter = kw.get('status', '').strip()
        if status_filter == 'cancel':
            domain = [
                ('message_partner_ids', 'child_of', [partner.id]),
                ('wink_is_portal_request', '=', True),
                ('state', '=', 'cancel'),
            ]
        else:
            # UI-BUG-005d (FB-005.6): Include cancelled so cancellation status is reflected on portal
            domain = [
                ('message_partner_ids', 'child_of', [partner.id]),
                ('wink_is_portal_request', '=', True),
                ('state', 'in', ['draft', 'sent', 'sale', 'done', 'cancel']),
            ]

        search = kw.get('search', '').strip()
        if search:
            domain.append('|')
            domain.append(('name', 'ilike', search))
            if hasattr(SaleOrder, 'wink_source_product_id'):
                domain.append(('wink_source_product_id.name', 'ilike', search))
            else:
                domain.append(('name', 'ilike', search))
        if status_filter == 'quotation':
            domain.append(('state', 'in', ['draft', 'sent']))
        elif status_filter == 'sale':
            domain.append(('state', '=', 'sale'))
        elif status_filter == 'done':
            domain.append(('state', '=', 'done'))
        type_filter = kw.get('type', '').strip()
        if type_filter == 'retainer' and hasattr(SaleOrder, 'is_subscription'):
            domain.append(('is_subscription', '=', True))
        elif type_filter == 'onetime' and hasattr(SaleOrder, 'is_subscription'):
            domain.append(('is_subscription', '=', False))
        payment_filter = kw.get('payment', '').strip()

        searchbar_sortings = {
            'date': {'label': 'Latest', 'order': 'date_order desc'},
            'date_asc': {'label': 'Oldest', 'order': 'date_order asc'},
            'name': {'label': 'Reference', 'order': 'name'},
            'stage': {'label': 'Stage', 'order': 'state'},
        }
        sort_param = kw.get('sort', '').strip() or 'latest'
        if sort_param == 'oldest':
            sortby = 'date_asc'
        elif sort_param == 'latest':
            sortby = 'date'
        elif sort_param in searchbar_sortings:
            sortby = sort_param
        if not sortby or sortby not in searchbar_sortings:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        request_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url="/my/requests",
            url_args={'sortby': sortby, 'search': search, 'status': status_filter, 'type': type_filter, 'payment': payment_filter, 'sort': sort_param},
            total=request_count,
            page=page,
            step=20
        )

        requests = SaleOrder.search(domain, order=order, limit=20, offset=pager['offset'])

        # Pre-compute subscription badge data as plain Python dicts — keyed by order id.
        # This avoids any ORM field descriptor access in QWeb (which crashes in Odoo 18
        # when computed Many2one fields like recurrence_id or is_subscription return None
        # via their __get__ descriptor instead of raising AttributeError).
        subscription_info = {}
        for req in requests:
            try:
                is_sub = bool(req.is_subscription) if hasattr(req, 'is_subscription') else False
            except Exception:
                is_sub = False
            rec_name = None
            if is_sub:
                try:
                    rec = req.recurrence_id
                    if rec and rec.id:
                        rec_name = rec.name or None
                except Exception:
                    rec_name = None
            if is_sub and rec_name:
                subscription_info[req.id] = rec_name

        # UI-005: Type (One-time/Retainer) and Payment (Locked/Due/Paid) per request
        request_extra = {}
        for req in requests:
            try:
                is_sub = bool(req.is_subscription) if hasattr(req, 'is_subscription') else False
            except Exception:
                is_sub = False
            tx_paid = req.transaction_ids.filtered(lambda t: t.state in ('authorized', 'done', 'pending'))
            inv_paid = req.invoice_ids.filtered(lambda i: i.state == 'posted' and i.payment_state in ('in_payment', 'paid'))
            paid = bool(tx_paid or inv_paid)
            if req.state in ('draft', 'sent') and not getattr(req, 'wink_price_confirmed', True):
                payment = 'locked'
            elif req.state == 'sale' and not paid:
                payment = 'due'
            else:
                payment = 'paid' if paid else 'due'
            request_extra[req.id] = {'type': 'retainer' if is_sub else 'onetime', 'payment': payment}
        values = {
            'requests': requests,
            'subscription_info': subscription_info,
            'request_extra': request_extra,
            'page_name': 'my_requests',
            'pager': pager,
            'default_url': '/my/requests',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'partner': partner,
            'filter_search': search,
            'filter_status': status_filter,
            'filter_type': type_filter,
            'filter_payment': payment_filter,
            'filter_sort': sort_param,
        }
        return request.render("kuec_service_catalogue.portal_my_requests", values)

    @http.route(['/my/employees', '/my/employee', '/my/employees/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_employees(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id.commercial_partner_id

        EmployeeDirectory = request.env['kuec.employee.directory'].sudo()
        domain = [('partner_id', '=', partner.id)]

        searchbar_sortings = {
            'name': {'label': 'Name', 'order': 'name asc'},
            'job_title': {'label': 'Job Title', 'order': 'job_title asc'},
            'uae_status': {'label': 'UAE Status', 'order': 'uae_status asc'},
        }
        if not sortby or sortby not in searchbar_sortings:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']

        employee_count = EmployeeDirectory.search_count(domain)
        pager = portal_pager(
            url="/my/employees",
            url_args={'sortby': sortby},
            total=employee_count,
            page=page,
            step=20
        )

        employees = EmployeeDirectory.search(domain, order=order, limit=20, offset=pager['offset'])

        values = {
            'employees': employees,
            'page_name': 'employee_directory',
            'pager': pager,
            'default_url': '/my/employees',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'partner': partner,
        }
        return request.render("kuec_service_catalogue.portal_my_employees", values)

    @http.route(['/my/employee/<int:employee_id>'], type='http', auth="user", website=True)
    def portal_my_employee_detail(self, employee_id, **kw):
        partner = request.env.user.partner_id.commercial_partner_id

        employee = request.env['kuec.employee.directory'].sudo().browse(employee_id)
        if not employee.exists() or employee.partner_id.id != partner.id:
            return request.redirect('/my/employees')

        values = {
            'employee': employee,
            'page_name': 'employee_directory',
            'countries': request.env['res.country'].sudo().search([]),
        }
        return request.render("kuec_service_catalogue.portal_my_employee_detail", values)

    @http.route(['/my/employee/new'], type='http', auth="user", website=True)
    def portal_my_employee_new(self, **kw):
        partner = request.env.user.partner_id.commercial_partner_id

        values = {
            'page_name': 'employee_directory',
            'countries': request.env['res.country'].sudo().search([]),
        }
        return request.render("kuec_service_catalogue.portal_my_employee_detail", values)

    @http.route(['/my/employee/save'], type='http', auth="user", website=True, methods=['POST'], csrf=True)
    def portal_my_employee_save(self, employee_id=None, **post):
        partner = request.env.user.partner_id.commercial_partner_id

        EmployeeDirectory = request.env['kuec.employee.directory'].sudo()
        vals = {
            'name': post.get('name'),
            'full_name_arabic': post.get('full_name_arabic'),
            'email': post.get('email'),
            'mobile': post.get('mobile'),
            'gender': post.get('gender'),
            'date_of_birth': post.get('date_of_birth') or False,
            'place_of_birth': post.get('place_of_birth'),
            'marital_status': post.get('marital_status'),
            'nationality_id': int(post.get('nationality_id')) if post.get('nationality_id') else False,
            'passport_number': post.get('passport_number'),
            'passport_issue_date': post.get('passport_issue_date') or False,
            'passport_expiry_date': post.get('passport_expiry_date') or False,
            'passport_place_of_issue': post.get('passport_place_of_issue'),
            'current_location': post.get('current_location'),
            'uae_status': post.get('uae_status'),
            'previous_uae_visa': True if post.get('previous_uae_visa') else False,
            'uid_number': post.get('uid_number'),
            'emirates_id': post.get('emirates_id'),
            'visa_expiry_date': post.get('visa_expiry_date') or False,
        }

        if employee_id:
            employee = EmployeeDirectory.browse(int(employee_id))
            if employee.exists() and employee.partner_id.id == partner.id:
                employee.write(vals)
        else:
            vals['partner_id'] = partner.id
            EmployeeDirectory.create(vals)

        return request.redirect('/my/employees')

    # UI-LOV-019 New Support Ticket (Lovable parity)
    @http.route(['/my/ticket/new'], type='http', auth='user', website=True)
    def portal_my_ticket_new(self, **kw):
        """Show New Support Ticket form (portal UI only)."""
        ticket_categories = []
        try:
            ticket_categories = request.env['helpdesk.ticket.type'].sudo().search([])
        except (KeyError, AttributeError):
            pass
        return request.render('kuec_service_catalogue.wink_portal_new_ticket', {
            'page_name': 'new_ticket',
            'ticket_categories': ticket_categories,
        })

    @http.route(['/my/ticket/submit'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_my_ticket_submit(self, **post):
        """Epic4-NT: Create helpdesk ticket with Category, Priority, attachment (file type/size validation)."""
        import base64
        partner = request.env.user.partner_id
        subject = (post.get('subject') or '').strip()
        description = (post.get('description') or '').strip()
        if not subject or not description:
            return request.redirect('/my/ticket/new?error=required')
        MAX_SIZE = 10 * 1024 * 1024  # 10 MB
        ALLOWED_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx')
        attachment = post.get('attachment')
        if attachment and hasattr(attachment, 'read'):
            filename = getattr(attachment, 'filename', None) or ''
            ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
            if '.' + ext not in ALLOWED_EXTENSIONS:
                return request.redirect('/my/ticket/new?error=file_type')
            data = attachment.read()
            if len(data) > MAX_SIZE:
                return request.redirect('/my/ticket/new?error=file_type')
            attachment.seek(0)
        try:
            Ticket = request.env['helpdesk.ticket'].sudo()
            vals = {
                'name': subject[:200],
                'description': description,
                'partner_id': partner.id,
            }
            if post.get('priority') is not None:
                try:
                    vals['priority'] = int(post.get('priority'))
                except (TypeError, ValueError):
                    pass
            if post.get('category_id'):
                try:
                    vals['ticket_type_id'] = int(post['category_id'])
                except (TypeError, ValueError):
                    pass
            ticket = Ticket.create(vals)
            attachment = post.get('attachment')
            if attachment and hasattr(attachment, 'read'):
                request.env['ir.attachment'].sudo().create({
                    'name': getattr(attachment, 'filename', None) or 'attachment',
                    'datas': base64.b64encode(attachment.read()),
                    'res_model': 'helpdesk.ticket',
                    'res_id': ticket.id,
                })
            return request.redirect('/my/tickets')
        except Exception:
            return request.redirect('/my/ticket/new?error=create')

    # U-3: Entitlement Dashboard — /my/bundles
    @http.route(['/my/bundles'], type='http', auth='user', website=True)
    def portal_my_bundles(self, **kw):
        """Dedicated entitlement dashboard — activate services, track progress, view tasks."""
        partner = request.env.user.partner_id.commercial_partner_id
        SaleOrder = request.env['sale.order'].sudo()
        domain = [
            ('message_partner_ids', 'child_of', [partner.id]),
            ('wink_is_portal_request', '=', True),
            '|',
            ('state', 'in', ['sale', 'done']),
            ('wink_bundle_cancelled', '=', True),
            ('wink_entitlement_ids', '!=', False),
        ]
        orders = SaleOrder.search(domain, order='date_order desc')

        # Employees for this partner (shared across all modals)
        modal_employees = request.env['kuec.employee.directory'].sudo().search([
            ('partner_id', '=', partner.id)
        ])

        # Build per-entitlement prereqs (docs + employees) for activation modals
        entitlement_prereqs = {}

        # Build bundle data
        bundle_data = []
        total_services = 0
        total_activated = 0

        for order in orders:
            entitlements = order.wink_entitlement_ids.sorted(key=lambda e: e.sequence)
            total = len(entitlements)
            activated_count = len(entitlements.filtered(lambda e: e.qty_activated > 0))
            progress_pct = int((activated_count / total * 100)) if total > 0 else 0
            tier_name = order.wink_bundle_tier_id.name if order.wink_bundle_tier_id else ''
            bundle_name = ''
            if order.wink_source_product_id and order.wink_source_product_id.wink_bundle_id:
                bundle_name = order.wink_source_product_id.wink_bundle_id.name

            total_services += total
            total_activated += activated_count

            # Per-entitlement task map (use savepoint so a SQL error doesn't
            # abort the outer transaction and cascade into subsequent queries)
            ent_activation_map = {}
            try:
                with request.env.cr.savepoint():
                    all_lines = entitlements.mapped('activated_line_ids')
                    line_completion = {}
                    if all_lines:
                        tasks = request.env['project.task'].sudo().search([
                            ('sale_line_id', 'in', all_lines.ids),
                        ])
                        tasks_by_line = {}
                        for t in tasks:
                            tasks_by_line.setdefault(t.sale_line_id.id, []).append(t)
                        for line in all_lines:
                            line_tasks = tasks_by_line.get(line.id, [])
                            if not line_tasks:
                                complete = False
                            else:
                                def _task_done(task):
                                    stage = getattr(task, 'stage_id', None)
                                    if not stage:
                                        return False
                                    if getattr(stage, 'fold', False):
                                        return True
                                    name = (stage.name or '').lower()
                                    return any(x in name for x in ('done', 'cancelled', 'closed', 'complete'))
                                complete = all(_task_done(t) for t in line_tasks)
                            line_completion[line.id] = complete
                    for ent in entitlements:
                        ent_activation_map[ent.id] = [
                            {
                                'name': line.name or '',
                                'is_complete': line_completion.get(line.id, False),
                                'index': idx + 1,
                            }
                            for idx, line in enumerate(ent.activated_line_ids)
                        ]
            except Exception:
                ent_activation_map = {}

            # Activation modals removed from template — skip prereq computation
            for ent in entitlements:
                entitlement_prereqs[ent.id] = {'order_id': order.id}

            bundle_obj = None
            if order.wink_source_product_id and order.wink_source_product_id.wink_bundle_id:
                bundle_obj = order.wink_source_product_id.wink_bundle_id

            # I-3: Build per-entitlement rating map {ent_id: rating_record or None}
            ent_rating_map = {}
            try:
                all_ent_lines = entitlements.mapped('activated_line_ids')
                if all_ent_lines:
                    ent_tasks = request.env['project.task'].sudo().search([
                        ('sale_line_id', 'in', all_ent_lines.ids),
                    ])
                    if ent_tasks:
                        ratings = request.env['rating.rating'].sudo().search([
                            ('res_model', '=', 'project.task'),
                            ('res_id', 'in', ent_tasks.ids),
                            ('consumed', '=', True),
                        ])
                        # Map task_id → rating
                        rating_by_task = {r.res_id: r for r in ratings}
                        # Map line_id → tasks
                        tasks_by_line = {}
                        for t in ent_tasks:
                            tasks_by_line.setdefault(t.sale_line_id.id, []).append(t)
                        for ent in entitlements:
                            ent_ratings = []
                            for line in ent.activated_line_ids:
                                for t in tasks_by_line.get(line.id, []):
                                    r = rating_by_task.get(t.id)
                                    if r:
                                        ent_ratings.append(r)
                            ent_rating_map[ent.id] = ent_ratings
            except Exception:
                pass

            bundle_data.append({
                'order': order,
                'bundle': bundle_obj,
                'entitlements': entitlements,
                'total': total,
                'activated': activated_count,
                'progress_pct': progress_pct,
                'tier_name': tier_name,
                'bundle_name': bundle_name or (order.wink_source_product_id.name if order.wink_source_product_id else order.name),
                'ent_activation_map': ent_activation_map,
                'ent_rating_map': ent_rating_map,
            })

        open_modal = kw.get('open_modal', '')
        doc_uploaded = kw.get('doc_uploaded') == '1'

        kpi_live = len([
            b for b in bundle_data
            if b['order'].wink_bundle_activated
            and b['order'].state in ('sale', 'done')
            and not b['order'].wink_bundle_cancelled
            and getattr(b['order'], 'subscription_state', None) != '6_churn'
        ])
        kpi_awaiting = len([
            b for b in bundle_data
            if not b['order'].wink_bundle_activated
            and b['order'].state in ('sale', 'done')
            and not b['order'].wink_bundle_cancelled
            and getattr(b['order'], 'subscription_state', None) != '6_churn'
        ])

        values = {
            'bundle_data': bundle_data,
            'entitlement_prereqs': entitlement_prereqs,
            'open_modal': open_modal,
            'doc_uploaded': doc_uploaded,
            'page_name': 'my_bundles',
            'partner': partner,
            # KPI totals
            'kpi_bundles': len(bundle_data),
            'kpi_total_services': total_services,
            'kpi_activated': total_activated,
            'kpi_pending': total_services - total_activated,
            'kpi_live': kpi_live,
            'kpi_awaiting': kpi_awaiting,
        }
        return request.render('kuec_service_catalogue.portal_my_bundles', values)

    # -------------------------------------------------------------------------
    # Bundle Lifecycle — helper to load + authorize a bundle order
    # -------------------------------------------------------------------------
    def _wink_get_bundle_order(self, order_id):
        """Load the bundle sale order for the current portal user.
        Returns (order, error_redirect). error_redirect is non-None when access denied.
        Also accepts self-service-cancelled bundle orders (wink_bundle_cancelled=True)."""
        partner = request.env.user.partner_id.commercial_partner_id
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return None, request.redirect('/my/bundles')
        # Ownership check
        if order.partner_id.commercial_partner_id.id != partner.id:
            return None, request.redirect('/my/bundles')
        # Must have entitlements (bundle order)
        if not order.wink_entitlement_ids:
            return None, request.redirect('/my/bundles')
        return order, None

    # -------------------------------------------------------------------------
    # P3 — Cancel
    # -------------------------------------------------------------------------
    @http.route(['/my/bundles/<int:order_id>/cancel'], type='http', auth='user', website=True, methods=['GET'])
    def portal_bundle_cancel_page(self, order_id, **kw):
        """Show cancel preview page with refund calculation."""
        order, err = self._wink_get_bundle_order(order_id)
        if err:
            return err
        if order.wink_bundle_cancelled or order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        bundle = order._wink_bundle_get_policy()
        if bundle and not bundle.allow_self_service_cancel:
            return request.redirect('/my/bundles?error=cancel_not_allowed')

        refund_info = order._wink_bundle_compute_refund()
        close_reasons = request.env['sale.order.close.reason'].sudo().search([], order='id')
        return request.render('kuec_service_catalogue.wink_bundle_cancel_page', {
            'order': order,
            'bundle': bundle,
            'refund_info': refund_info,
            'tier': order.wink_bundle_tier_id,
            'close_reasons': close_reasons,
            'page_name': 'my_bundles',
            'error': kw.get('error', ''),
        })

    @http.route(['/my/bundles/<int:order_id>/cancel'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_bundle_cancel_submit(self, order_id, **post):
        """Execute bundle cancellation."""
        order, err = self._wink_get_bundle_order(order_id)
        if err:
            return err
        if order.wink_bundle_cancelled or order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        reason = (post.get('cancel_reason') or '').strip()
        confirm = post.get('confirm_cancel')
        if not confirm:
            return request.redirect(f'/my/bundles/{order_id}/cancel?error=confirm_required')
        try:
            result = order._wink_bundle_do_cancel(reason=reason)
            refund_amount = result.get('refund_amount', 0.0)
            credit_note = result.get('credit_note')
            return request.render('kuec_service_catalogue.wink_bundle_cancel_done', {
                'order': order,
                'refund_amount': refund_amount,
                'credit_note': credit_note,
                'currency': order.currency_id,
                'page_name': 'my_bundles',
            })
        except Exception as e:
            return request.redirect(f'/my/bundles/{order_id}/cancel?error={str(e)[:80]}')

    # -------------------------------------------------------------------------
    # P4 — Upgrade
    # -------------------------------------------------------------------------
    @http.route(['/my/bundles/<int:order_id>/upgrade'], type='http', auth='user', website=True, methods=['GET'])
    def portal_bundle_upgrade_page(self, order_id, **kw):
        """Show available upgrade tiers with pro-rata charges."""
        order, err = self._wink_get_bundle_order(order_id)
        if err:
            return err
        if order.wink_bundle_cancelled or order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        bundle = order._wink_bundle_get_policy()
        if bundle and not bundle.allow_self_service_upgrade:
            return request.redirect('/my/bundles?error=upgrade_not_allowed')

        current_tier = order.wink_bundle_tier_id
        upgrade_tiers = []
        if current_tier:
            for tier in current_tier.upgrade_to_ids:
                charge_info = order._wink_bundle_compute_upgrade_charge(tier)
                upgrade_tiers.append({
                    'tier': tier,
                    'charge_amount': charge_info.get('charge_amount', 0.0),
                    'remaining_days': charge_info.get('remaining_days', 0),
                    'note': charge_info.get('note', ''),
                })

        return request.render('kuec_service_catalogue.wink_bundle_upgrade_page', {
            'order': order,
            'bundle': bundle,
            'current_tier': current_tier,
            'upgrade_tiers': upgrade_tiers,
            'currency': order.currency_id,
            'page_name': 'my_bundles',
            'error': kw.get('error', ''),
        })

    @http.route(['/my/bundles/<int:order_id>/upgrade'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_bundle_upgrade_submit(self, order_id, **post):
        """Execute tier upgrade."""
        order, err = self._wink_get_bundle_order(order_id)
        if err:
            return err
        if order.wink_bundle_cancelled or order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        tier_id = post.get('tier_id')
        if not tier_id:
            return request.redirect(f'/my/bundles/{order_id}/upgrade?error=no_tier')
        try:
            result = order._wink_bundle_do_upgrade(int(tier_id))
            charge_amount = result.get('charge_amount', 0.0)
            new_tier = result.get('new_tier')
            upgrade_invoice = result.get('invoice')
            return request.render('kuec_service_catalogue.wink_bundle_change_done', {
                'order': order,
                'change_type': 'upgrade',
                'new_tier': new_tier,
                'amount': charge_amount,
                'amount_label': 'Pro-rata charge',
                'currency': order.currency_id,
                'page_name': 'my_bundles',
                'upgrade_invoice': upgrade_invoice,
            })
        except Exception as e:
            return request.redirect(f'/my/bundles/{order_id}/upgrade?error={str(e)[:80]}')

    # -------------------------------------------------------------------------
    # P5 — Downgrade
    # -------------------------------------------------------------------------
    @http.route(['/my/bundles/<int:order_id>/downgrade'], type='http', auth='user', website=True, methods=['GET'])
    def portal_bundle_downgrade_page(self, order_id, **kw):
        """Show available downgrade tiers with pro-rata credits."""
        order, err = self._wink_get_bundle_order(order_id)
        if err:
            return err
        if order.wink_bundle_cancelled or order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        bundle = order._wink_bundle_get_policy()
        if bundle and not bundle.allow_self_service_downgrade:
            return request.redirect('/my/bundles?error=downgrade_not_allowed')

        current_tier = order.wink_bundle_tier_id
        downgrade_tiers = []
        if current_tier:
            for tier in current_tier.downgrade_to_ids:
                credit_info = order._wink_bundle_compute_downgrade_credit(tier)
                downgrade_tiers.append({
                    'tier': tier,
                    'credit_amount': credit_info.get('credit_amount', 0.0),
                    'remaining_days': credit_info.get('remaining_days', 0),
                    'policy': credit_info.get('policy', 'none'),
                    'note': credit_info.get('note', ''),
                })

        return request.render('kuec_service_catalogue.wink_bundle_downgrade_page', {
            'order': order,
            'bundle': bundle,
            'current_tier': current_tier,
            'downgrade_tiers': downgrade_tiers,
            'currency': order.currency_id,
            'page_name': 'my_bundles',
            'error': kw.get('error', ''),
        })

    @http.route(['/my/bundles/<int:order_id>/downgrade'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_bundle_downgrade_submit(self, order_id, **post):
        """Execute tier downgrade."""
        order, err = self._wink_get_bundle_order(order_id)
        if err:
            return err
        if order.wink_bundle_cancelled or order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        tier_id = post.get('tier_id')
        if not tier_id:
            return request.redirect(f'/my/bundles/{order_id}/downgrade?error=no_tier')
        try:
            result = order._wink_bundle_do_downgrade(int(tier_id))
            credit_amount = result.get('credit_amount', 0.0)
            new_tier = result.get('new_tier')
            return request.render('kuec_service_catalogue.wink_bundle_change_done', {
                'order': order,
                'change_type': 'downgrade',
                'new_tier': new_tier,
                'amount': credit_amount,
                'amount_label': 'Credit note issued',
                'currency': order.currency_id,
                'page_name': 'my_bundles',
            })
        except Exception as e:
            return request.redirect(f'/my/bundles/{order_id}/downgrade?error={str(e)[:80]}')

    # ─── EPIC7-DASH-001: Customer Portal Dashboard ────────────────────────────

    @http.route('/my/dashboard', type='http', auth='user', website=True)
    def portal_dashboard(self, **kw):
        """EPIC7-DASH-001: Customer-facing KPI dashboard — full enhanced version.
        Scoped strictly to the customer's commercial_partner_id."""
        from datetime import timedelta
        from odoo import fields

        partner = request.env.user.partner_id.commercial_partner_id
        SaleOrder = request.env['sale.order'].sudo()
        today = fields.Date.today()
        in_30 = today + timedelta(days=30)

        base_domain = [
            ('message_partner_ids', 'child_of', [partner.id]),
            ('wink_is_portal_request', '=', True),
        ]

        # ── KPI Row 1: Requests ─────────────────────────────────────────────
        kpi_orders = SaleOrder.search_count(base_domain + [
            ('state', 'in', ['draft', 'sent', 'sale']),
        ])
        kpi_quotes = SaleOrder.search_count(base_domain + [
            ('state', '=', 'sent'),
        ])
        kpi_subscriptions = SaleOrder.search_count(base_domain + [
            ('state', '=', 'sale'),
            '|',
            ('wink_entitlement_ids', '!=', False),
            ('is_subscription', '=', True),
        ])
        kpi_project_based = SaleOrder.search_count(base_domain + [
            ('state', 'in', ['draft', 'sent', 'sale']),
            ('is_subscription', '=', False),
            ('wink_entitlement_ids', '=', False),
        ])
        kpi_completed = SaleOrder.search_count(base_domain + [
            ('state', '=', 'done'),
        ])
        kpi_renewals = SaleOrder.search_count(base_domain + [
            ('state', '=', 'sale'),
            '|',
            '&', ('wink_bundle_end_date', '>=', today), ('wink_bundle_end_date', '<=', in_30),
            '&', ('next_invoice_date', '>=', today), ('next_invoice_date', '<=', in_30),
        ])

        # Request breakdown by status (for mini-chart)
        status_breakdown = {
            'quotation': SaleOrder.search_count(base_domain + [('state', 'in', ['draft', 'sent'])]),
            'active':    SaleOrder.search_count(base_domain + [('state', '=', 'sale')]),
            'done':      SaleOrder.search_count(base_domain + [('state', '=', 'done')]),
            'cancelled': SaleOrder.search_count(base_domain + [('state', '=', 'cancel')]),
        }
        status_total = sum(status_breakdown.values()) or 1

        # ── KPI Row 2: Finance ───────────────────────────────────────────────
        kpi_dr = 0.0
        kpi_cr = 0.0
        kpi_overdue = 0.0
        kpi_open_invoices = 0
        next_payment_date = None
        recent_payments = []
        currency = request.env.company.currency_id
        try:
            AccountMove = request.env['account.move'].sudo()
            inv_base = [('partner_id', 'child_of', [partner.id]), ('state', '=', 'posted')]

            invoices = AccountMove.search(inv_base + [
                ('move_type', '=', 'out_invoice'),
                ('payment_state', 'in', ['not_paid', 'partial']),
            ])
            kpi_dr = sum(inv.amount_residual for inv in invoices)
            kpi_open_invoices = len(invoices)
            if invoices:
                currency = invoices[0].currency_id or currency
                # Next payment due date
                due_dates = [inv.invoice_date_due for inv in invoices if inv.invoice_date_due]
                if due_dates:
                    next_payment_date = min(due_dates)
                # Overdue: past due today
                kpi_overdue = sum(
                    inv.amount_residual for inv in invoices
                    if inv.invoice_date_due and inv.invoice_date_due < today
                )

            credit_notes = AccountMove.search(inv_base + [
                ('move_type', '=', 'out_refund'),
                ('payment_state', 'in', ['not_paid', 'partial']),
            ])
            kpi_cr = sum(cn.amount_residual for cn in credit_notes)
            if not invoices and credit_notes:
                currency = credit_notes[0].currency_id or currency

            # Recent payments (inbound, posted)
            Payment = request.env['account.payment'].sudo()
            recent_payments = Payment.search([
                ('partner_id', 'child_of', [partner.id]),
                ('payment_type', '=', 'inbound'),
                ('state', '=', 'posted'),
            ], order='date desc', limit=5)
        except Exception:
            pass

        # ── KPI Row 3: Projects & Tasks ──────────────────────────────────────
        kpi_projects = 0
        kpi_tasks = 0
        kpi_tasks_done = 0
        task_progress_pct = 0
        try:
            Project = request.env['project.project'].sudo()
            kpi_projects = Project.search_count([
                ('partner_id', 'child_of', [partner.id]),
                ('last_update_status', '!=', 'done'),
            ])
        except Exception:
            pass
        try:
            Task = request.env['project.task'].sudo()
            task_domain = [('partner_id', 'child_of', [partner.id])]
            total_tasks = Task.search_count(task_domain)
            kpi_tasks_done = Task.search_count(task_domain + [('stage_id.fold', '=', True)])
            kpi_tasks = total_tasks - kpi_tasks_done
            if total_tasks:
                task_progress_pct = round(kpi_tasks_done * 100 / total_tasks)
        except Exception:
            pass

        # Pending documents removed — attachments go directly to chatter
        pending_docs = []
        kpi_pending_docs = 0

        # ── Quotes awaiting approval ─────────────────────────────────────────
        quotes_to_approve = SaleOrder.search(base_domain + [('state', '=', 'sent')], limit=5)

        # ── Overdue invoices list ─────────────────────────────────────────────
        overdue_invoices = []
        try:
            overdue_invoices = request.env['account.move'].sudo().search([
                ('partner_id', 'child_of', [partner.id]),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial']),
                ('invoice_date_due', '<', today),
            ], order='invoice_date_due asc', limit=5)
        except Exception:
            pass

        # ── Bundle entitlement usage ─────────────────────────────────────────
        bundle_entitlements = []
        try:
            Entitlement = request.env['wink.bundle.entitlement'].sudo()
            active_ents = Entitlement.search([
                ('order_id', 'in', SaleOrder.search(base_domain + [('state', '=', 'sale')]).ids),
                ('state', 'in', ['available', 'fully_activated']),
                ('qty_entitled', '>', 0),
            ], limit=8)
            for ent in active_ents:
                pct = round(ent.qty_activated * 100 / ent.qty_entitled) if ent.qty_entitled else 0
                bundle_entitlements.append({
                    'name': ent.service_product_id.name,
                    'activated': ent.qty_activated,
                    'entitled': ent.qty_entitled,
                    'pct': pct,
                    'order_id': ent.order_id.id,
                })
        except Exception:
            pass

        # ── Employee directory count ──────────────────────────────────────────
        kpi_employees = 0
        try:
            kpi_employees = request.env['kuec.employee.directory'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('active', '=', True),
            ])
        except Exception:
            pass

        # ── eWallet balance ───────────────────────────────────────────────────
        wallet_balance = 0.0
        last_wallet_txn = None
        try:
            WalletTxn = request.env['kuec.wallet.transaction'].sudo()
            txns = WalletTxn.search([
                ('partner_id', '=', partner.id),
                ('state', '=', 'done'),
            ], order='create_date desc')
            wallet_balance = sum(txns.mapped('amount'))
            last_txn = txns[:1] if txns else None
            if last_txn:
                last_wallet_txn = {
                    'type': last_txn.transaction_type,
                    'amount': last_txn.amount,
                    'date': last_txn.date,
                }
        except Exception:
            pass

        # ── Helpdesk tickets ──────────────────────────────────────────────────
        kpi_tickets = 0
        try:
            kpi_tickets = request.env['helpdesk.ticket'].sudo().search_count([
                ('partner_id', 'child_of', [partner.id]),
                ('stage_id.is_close', '=', False),
            ])
        except Exception:
            pass

        # ── Upcoming subscription invoice dates ───────────────────────────────
        upcoming_subs = []
        try:
            subs = SaleOrder.search(base_domain + [
                ('state', '=', 'sale'),
                ('next_invoice_date', '>=', today),
                ('next_invoice_date', '<=', in_30),
            ], order='next_invoice_date asc', limit=5)
            for s in subs:
                upcoming_subs.append({
                    'order_id': s.id,
                    'name': s.wink_source_product_id.name or s.name,
                    'date': s.next_invoice_date,
                    'amount': s.recurring_total or s.amount_total,
                })
        except Exception:
            pass

        # ── Attention items (consolidated) ────────────────────────────────────
        attention_count = kpi_pending_docs + len(quotes_to_approve) + len(overdue_invoices)

        # ── Recent 5 requests ─────────────────────────────────────────────────
        recent_orders = SaleOrder.search(base_domain + [
            ('state', 'in', ['draft', 'sent', 'sale', 'done']),
        ], order='write_date desc', limit=5)

        return request.render('kuec_service_catalogue.wink_customer_dashboard', {
            # KPI Row 1
            'kpi_orders': kpi_orders,
            'kpi_quotes': kpi_quotes,
            'kpi_subscriptions': kpi_subscriptions,
            'kpi_project_based': kpi_project_based,
            'kpi_completed': kpi_completed,
            'kpi_renewals': kpi_renewals,
            # KPI Row 2
            'kpi_dr': kpi_dr,
            'kpi_cr': kpi_cr,
            'kpi_overdue': kpi_overdue,
            'kpi_open_invoices': kpi_open_invoices,
            'next_payment_date': next_payment_date,
            'currency': currency,
            # KPI Row 3
            'kpi_projects': kpi_projects,
            'kpi_tasks': kpi_tasks,
            'kpi_tasks_done': kpi_tasks_done,
            'task_progress_pct': task_progress_pct,
            'kpi_employees': kpi_employees,
            # Lists / panels
            'recent_orders': recent_orders,
            'recent_payments': recent_payments,
            'pending_docs': pending_docs,
            'kpi_pending_docs': kpi_pending_docs,
            'quotes_to_approve': quotes_to_approve,
            'overdue_invoices': overdue_invoices,
            'bundle_entitlements': bundle_entitlements,
            'upcoming_subs': upcoming_subs,
            'attention_count': attention_count,
            'status_breakdown': status_breakdown,
            'status_total': status_total,
            'partner': partner,
            'wallet_balance': wallet_balance,
            'last_wallet_txn': last_wallet_txn,
            'kpi_tickets': kpi_tickets,
            'page_name': 'dashboard',
        })

    @http.route('/my/wallet', type='http', auth='user', website=True)
    def portal_wallet(self, **kw):
        """Customer eWallet page: balance, transaction history, top-up."""
        partner = request.env.user.partner_id.commercial_partner_id
        wallet_balance = partner.sudo().wink_wallet_balance or 0.0
        transactions = request.env['kuec.wallet.transaction'].sudo().search([
            ('partner_id', '=', partner.id),
            ('state', '=', 'done'),
        ], order='date desc, id desc', limit=50)
        return request.render('kuec_service_catalogue.wink_portal_wallet', {
            'wallet_balance': wallet_balance,
            'transactions': transactions,
            'partner': partner,
            'currency': request.env.company.currency_id,
            'topup_success': kw.get('topup_success') == '1',
            'topup_pending': kw.get('topup_pending') == '1',
            'page_name': 'wallet',
        })

    @http.route('/my/wallet/topup', type='http', auth='user', website=True, methods=['POST'])
    def portal_wallet_topup_initiate(self, **post):
        """Store top-up amount in session and redirect to wallet payment page."""
        try:
            amount = round(float(post.get('amount', 0)), 2)
            if amount <= 0:
                raise ValueError()
        except (ValueError, TypeError):
            return request.redirect('/my/wallet?error=invalid_amount')

        partner = request.env.user.partner_id.commercial_partner_id
        currency = request.env.company.currency_id

        request.session['wink_topup_amount'] = amount
        request.session['wink_topup_partner_id'] = partner.id
        request.session['wink_topup_currency_id'] = currency.id
        return request.redirect('/my/wallet/pay')

    @http.route('/my/wallet/pay', type='http', auth='user', website=True)
    def portal_wallet_pay(self, **kw):
        """Dedicated payment page for wallet top-up — owns its own payment.form context."""
        partner = request.env.user.partner_id.commercial_partner_id
        amount = request.session.get('wink_topup_amount')
        session_partner_id = request.session.get('wink_topup_partner_id')
        currency_id = request.session.get('wink_topup_currency_id')

        if not amount or session_partner_id != partner.id:
            return request.redirect('/my/wallet')

        currency = request.env['res.currency'].sudo().browse(currency_id)

        # Build payment form context — mirrors account_payment/controllers/portal.py
        from odoo.addons.payment import utils as payment_utils
        from odoo.addons.payment.controllers.portal import PaymentPortal
        access_token = payment_utils.generate_access_token(partner.id, amount, currency.id)

        providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            request.env.company.id,
            partner.id,
            amount,
            currency_id=currency.id,
        )
        payment_methods_sudo = request.env['payment.method'].sudo()._get_compatible_payment_methods(
            providers_sudo.ids,
            partner.id,
            currency_id=currency.id,
        )
        tokens_sudo = request.env['payment.token'].sudo()._get_available_tokens(
            providers_sudo.ids, partner.id
        )
        show_tokenize_input_mapping = PaymentPortal._compute_show_tokenize_input_mapping(
            providers_sudo
        )

        return request.render('kuec_service_catalogue.wink_wallet_pay_page', {
            'amount': amount,
            'currency': currency,
            'partner_id': partner.id,
            'partner': partner,
            'providers_sudo': providers_sudo,
            'payment_methods_sudo': payment_methods_sudo,
            'tokens_sudo': tokens_sudo,
            'show_tokenize_input_mapping': show_tokenize_input_mapping,
            'default_payment_provider_id': providers_sudo[:1].id if providers_sudo else False,
            'access_token': access_token,
            'transaction_route': '/payment/transaction',
            'landing_route': '/my/wallet/topup/done',
        })

    @http.route('/my/wallet/topup/done', type='http', auth='user', website=True)
    def portal_wallet_topup_done(self, **kw):
        """Landing route after payment — credits wallet if transaction confirmed."""
        from datetime import timedelta
        from odoo import fields as odoo_fields

        partner = request.env.user.partner_id.commercial_partner_id
        amount = request.session.pop('wink_topup_amount', None)
        session_partner_id = request.session.pop('wink_topup_partner_id', None)
        currency_id = request.session.pop('wink_topup_currency_id', None)

        if not amount or session_partner_id != partner.id:
            return request.redirect('/my/wallet')

        # Find the most recent completed payment transaction for this amount/partner
        tx = request.env['payment.transaction'].sudo().search([
            ('partner_id', 'child_of', [partner.id]),
            ('amount', '=', amount),
            ('currency_id', '=', currency_id),
            ('state', '=', 'done'),
            ('create_date', '>=', odoo_fields.Datetime.now() - timedelta(minutes=30)),
        ], order='create_date desc', limit=1)

        if not tx:
            return request.redirect('/my/wallet?topup_pending=1')

        # Guard against double-crediting — use exact memo match (not LIKE) to prevent
        # false positives when tx.reference appears in a longer description.
        memo = f'eWallet Top-Up — {tx.reference}'
        existing = request.env['kuec.wallet.transaction'].sudo().search([
            ('partner_id', '=', partner.id),
            ('description', '=', memo),
            ('transaction_type', '=', 'topup'),
        ], limit=1)
        if not existing:
            # Post the correction JV first so we can link move_id immediately.
            # Wallet balance is credited regardless of JV outcome (money already left
            # the customer's card); GL failures are logged for manual correction.
            correction_move = self._wink_post_topup_correction_jv(
                partner, tx, amount, currency_id, memo
            )
            request.env['kuec.wallet.transaction'].sudo().create({
                'partner_id': partner.id,
                'transaction_type': 'topup',
                'amount': amount,
                'description': memo,
                'currency_id': currency_id,
                'move_id': correction_move.id if correction_move else False,
            })

        return request.redirect('/my/wallet?topup_success=1')

    def _wink_post_topup_correction_jv(self, partner, tx, amount, currency_id, memo):
        """Post a correcting journal entry to reclassify the payment provider AR credit
        to the WEWL wallet liability account, then reconcile the AR lines.

        The payment provider always posts:
            DR  Bank / Gateway Clearing
            CR  Accounts Receivable

        This method posts the correction:
            DR  Accounts Receivable   (offsets the provider's AR credit)
            CR  WEWL Wallet Liability (books the actual wallet obligation)

        Both AR lines are then reconciled so AR nets to zero.

        Net GL result:
            DR  Bank / Gateway Clearing
            CR  WEWL Wallet Liability  ✓

        Args:
            partner: res.partner record of the customer.
            tx: confirmed payment.transaction record.
            amount: top-up amount (float).
            currency_id: currency ID (int).
            memo: journal entry label string.

        Returns:
            account.move: the posted correction move, or None if posting failed.
        """
        import logging as _logging
        _log = _logging.getLogger(__name__)
        try:
            env = request.env

            wallet_journal = env['account.journal'].sudo().search(
                [('is_ewallet_journal', '=', True), ('company_id', '=', env.company.id)], limit=1
            )
            if not wallet_journal or not wallet_journal.default_account_id:
                _log.error(
                    'eWallet top-up correction JV skipped for tx %s: '
                    'eWallet journal or its default account is not configured.',
                    tx.reference,
                )
                return None

            # Find the AR credit line from the payment transaction's journal entry
            ar_line = env['account.move.line'].sudo()
            payment_move = tx.payment_id.move_id if tx.payment_id else False
            if payment_move:
                ar_line = payment_move.line_ids.filtered(
                    lambda l: l.account_id.account_type == 'asset_receivable'
                    and not l.reconciled
                )

            # Fall back to partner's default AR account if payment line not found
            if ar_line:
                ar_account = ar_line[0].account_id
            else:
                ar_account = partner.sudo().property_account_receivable_id

            if not ar_account:
                _log.error(
                    'eWallet top-up correction JV skipped for tx %s: '
                    'could not resolve AR account for partner %s.',
                    tx.reference, partner.name,
                )
                return None

            wewl_account = wallet_journal.default_account_id

            correction_move = env['account.move'].sudo().create({
                'journal_id': wallet_journal.id,
                'ref': memo,
                'line_ids': [
                    Command.create({
                        'account_id': ar_account.id,
                        'partner_id': partner.id,
                        'debit': amount,
                        'credit': 0.0,
                        'name': memo,
                        'currency_id': currency_id,
                    }),
                    Command.create({
                        'account_id': wewl_account.id,
                        'partner_id': partner.id,
                        'debit': 0.0,
                        'credit': amount,
                        'name': memo,
                        'currency_id': currency_id,
                    }),
                ],
            })
            correction_move.action_post()

            # Reconcile the AR credit (from payment provider) with the AR debit
            # (from correction) so AR nets to zero.
            if ar_line:
                correction_ar_line = correction_move.line_ids.filtered(
                    lambda l: l.account_id == ar_account and l.debit > 0
                )
                if correction_ar_line:
                    try:
                        (ar_line[0] + correction_ar_line[0]).reconcile()
                    except Exception as rec_err:
                        _log.warning(
                            'eWallet top-up: AR reconciliation failed for tx %s: %s '
                            '(correction JV %s is still posted — manual reconciliation required).',
                            tx.reference, rec_err, correction_move.name,
                        )

            return correction_move

        except Exception as exc:
            _log.error(
                'eWallet top-up correction JV failed for tx %s: %s',
                tx.reference, exc, exc_info=True,
            )
            return None

    @http.route('/terms-and-conditions', type='http', auth='public', website=True)
    def terms_and_conditions(self, **kwargs):
        """Serve the WINK Terms & Conditions page. Content editable from Settings → Wink."""
        company = request.env.company
        terms_html = company.sudo().wink_terms_html or ''
        return request.render('kuec_service_catalogue.wink_terms_and_conditions', {
            'terms_html': terms_html,
            'company': company,
        })

    # ── V-1: Vendor Portal Ratings ────────────────────────────────────────────

    @http.route(['/my/vendor-ratings', '/my/vendor-ratings/page/<int:page>'],
                type='http', auth='user', website=True)
    def vendor_ratings(self, page=1, **kwargs):
        """Vendor portal page showing all customer ratings received for their delivered services.

        Ratings are linked to tasks via rated_partner_id = vendor's partner.
        Each row shows the service name (task), PO reference, score, feedback, and date.
        Only consumed (submitted) ratings are shown.
        """
        vendor_partner = request.env.user.partner_id.commercial_partner_id

        domain = [
            ('rated_partner_id', 'child_of', vendor_partner.id),
            ('consumed', '=', True),
            ('res_model', '=', 'project.task'),
        ]

        Rating = request.env['rating.rating'].sudo()
        total = Rating.search_count(domain)

        pager = portal_pager(
            url='/my/vendor-ratings',
            total=total,
            page=page,
            step=20,
        )

        ratings = Rating.search(domain, order='write_date desc', limit=20, offset=pager['offset'])

        # Build enriched rows: fetch task + PO ref for each rating
        rating_rows = []
        for r in ratings:
            task = None
            po_name = None
            po_id = None
            try:
                task = request.env['project.task'].sudo().browse(r.res_id)
                if task.exists() and task.wink_purchase_order_id:
                    po_name = task.wink_purchase_order_id.name
                    po_id = task.wink_purchase_order_id.id
            except Exception:
                pass
            rating_rows.append({
                'rating': r,
                'task': task,
                'po_name': po_name,
                'po_id': po_id,
            })

        avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0.0

        return request.render('kuec_service_catalogue.wink_vendor_ratings_page', {
            'rating_rows': rating_rows,
            'avg_rating': avg_rating,
            'total': total,
            'pager': pager,
            'page_name': 'vendor_ratings',
        })

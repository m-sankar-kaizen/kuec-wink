from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager

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

        # U-3: My Bundles Counter (confirmed orders with entitlements)
        if not counters or 'bundle_count' in counters:
            bundle_domain = [
                ('message_partner_ids', 'child_of', [partner.id]),
                ('wink_is_portal_request', '=', True),
                ('state', 'in', ['sale', 'done']),
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
            ('state', 'in', ['sale', 'done']),
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
        total_docs_needed = 0

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

            # Per-entitlement prereqs + task map
            ent_activation_map = {}
            try:
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

            # Per-entitlement docs + employee prereqs
            order_has_docs_needed = False
            for ent in entitlements:
                docs_ok, _missing = order._wink_required_docs_approved_for_product(ent.service_product_id)
                doc_items = []
                if ent.service_product_id:
                    for req in ent.service_product_id.kuec_document_ids.filtered(
                        lambda r: r.requirement == 'required'
                    ):
                        sub = request.env['kuec.document.submission'].sudo().search([
                            ('order_id', '=', order.id),
                            ('requirement_id', '=', req.id),
                        ], limit=1)
                        doc_items.append({
                            'req_id': req.id,
                            'name': req.name,
                            'state': sub.state if sub else 'draft',
                            'notes': sub.coordinator_notes or '' if sub else '',
                        })
                if not docs_ok:
                    order_has_docs_needed = True
                requires_emps = bool(getattr(ent.service_product_id, 'requires_employee_selection', False))
                entitlement_prereqs[ent.id] = {
                    'docs_ok': docs_ok,
                    'doc_items': doc_items,
                    'requires_employees': requires_emps,
                    'employees': modal_employees,
                    'order_id': order.id,
                }

            if order_has_docs_needed:
                total_docs_needed += 1

            bundle_obj = None
            if order.wink_source_product_id and order.wink_source_product_id.wink_bundle_id:
                bundle_obj = order.wink_source_product_id.wink_bundle_id

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
            })

        open_modal = kw.get('open_modal', '')
        doc_uploaded = kw.get('doc_uploaded') == '1'

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
            'kpi_docs_needed': total_docs_needed,
        }
        return request.render('kuec_service_catalogue.portal_my_bundles', values)

    # -------------------------------------------------------------------------
    # Bundle Lifecycle — helper to load + authorize a bundle order
    # -------------------------------------------------------------------------
    def _wink_get_bundle_order(self, order_id):
        """Load the bundle sale order for the current portal user.
        Returns (order, error_redirect). error_redirect is non-None when access denied."""
        partner = request.env.user.partner_id.commercial_partner_id
        order = request.env['sale.order'].sudo().browse(int(order_id))
        if not order.exists():
            return None, request.redirect('/my/bundles')
        # Ownership check
        if order.partner_id.commercial_partner_id.id != partner.id:
            return None, request.redirect('/my/bundles')
        # Must be a bundle order
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
        if order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        bundle = order._wink_bundle_get_policy()
        if bundle and not bundle.allow_self_service_cancel:
            return request.redirect('/my/bundles?error=cancel_not_allowed')

        refund_info = order._wink_bundle_compute_refund()
        return request.render('kuec_service_catalogue.wink_bundle_cancel_page', {
            'order': order,
            'bundle': bundle,
            'refund_info': refund_info,
            'tier': order.wink_bundle_tier_id,
            'page_name': 'my_bundles',
            'error': kw.get('error', ''),
        })

    @http.route(['/my/bundles/<int:order_id>/cancel'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_bundle_cancel_submit(self, order_id, **post):
        """Execute bundle cancellation."""
        order, err = self._wink_get_bundle_order(order_id)
        if err:
            return err
        if order.state not in ('sale', 'done'):
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
        if order.state not in ('sale', 'done'):
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
        if order.state not in ('sale', 'done'):
            return request.redirect('/my/bundles')
        tier_id = post.get('tier_id')
        if not tier_id:
            return request.redirect(f'/my/bundles/{order_id}/upgrade?error=no_tier')
        try:
            result = order._wink_bundle_do_upgrade(int(tier_id))
            charge_amount = result.get('charge_amount', 0.0)
            new_tier = result.get('new_tier')
            return request.render('kuec_service_catalogue.wink_bundle_change_done', {
                'order': order,
                'change_type': 'upgrade',
                'new_tier': new_tier,
                'amount': charge_amount,
                'amount_label': 'Pro-rata charge',
                'currency': order.currency_id,
                'page_name': 'my_bundles',
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
        if order.state not in ('sale', 'done'):
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
        if order.state not in ('sale', 'done'):
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

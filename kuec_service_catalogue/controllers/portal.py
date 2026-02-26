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
        
        return values

    @http.route(['/my/requests', '/my/requests/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_requests(self, page=1, sortby=None, **kw):
        partner = request.env.user.partner_id.commercial_partner_id
        SaleOrder = request.env['sale.order'].sudo()

        domain = [
            ('message_partner_ids', 'child_of', [partner.id]),
            ('wink_is_portal_request', '=', True),
            ('state', 'in', ['draft', 'sent', 'sale', 'done'])
        ]

        searchbar_sortings = {
            'date': {'label': 'Order Date', 'order': 'date_order desc'},
            'name': {'label': 'Reference', 'order': 'name'},
            'stage': {'label': 'Stage', 'order': 'state'},
        }
        if not sortby or sortby not in searchbar_sortings:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        request_count = SaleOrder.search_count(domain)
        pager = portal_pager(
            url="/my/requests",
            url_args={'sortby': sortby},
            total=request_count,
            page=page,
            step=20
        )

        requests = SaleOrder.search(domain, order=order, limit=20, offset=pager['offset'])

        values = {
            'requests': requests,
            'page_name': 'my_requests',
            'pager': pager,
            'default_url': '/my/requests',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'partner': partner,
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

    @http.route(['/my/employee/save'], type='http', auth="user", website=True, methods=['POST'])
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

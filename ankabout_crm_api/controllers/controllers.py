# -*- coding: utf-8 -*-
"""
Ankabut CRM Lead Creation API Controller

This controller exposes a public JSON endpoint `/ankabut/create_lead`
that allows external systems to create CRM leads in Odoo using a Bearer token
for authentication.

Expected POST payload:
{
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+971501234567",
    "company": "Example LLC",
    "message": "Looking for services"
}
"""

from odoo import fields, http
from odoo.http import request, Controller, route


def format_time(time_str):
    """Helper to convert timestamp string to datetime (not used in current code)."""
    return fields.datetime.strptime(time_str, '%m/%d/%Y %I:%M:%S')


class CrmLead(Controller):

    @route('/ankabut/create_lead', type='json', auth='public', methods=["POST"])
    def create_lead(self, **rec):
        """
        Create CRM lead based on external POST data from Ankabut.
        Requires a valid Authorization Bearer token matching the company's `crm_lead_token`.

        :param rec: JSON payload with lead data
        :return: Success/failure response
        """
        auth_header = request.httprequest.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return http.Response(status=401)

        api_token = auth_header.split(' ')[1]
        user_company = request.env['res.company'].sudo().search([
            ('crm_lead_token', '=', api_token)], limit=1)

        if not user_company:
            return http.Response(status=401)

        required_fields = ['name', 'email', 'phone', 'company', 'message']
        if not all(field in rec for field in required_fields):
            return {
                'success': False,
                'message': 'Missing required fields'
            }

        vals = {
            'name': rec['name'],
            'email_from': rec['email'],
            'phone': rec['phone'],
            'partner_name': rec['company'],
            'description': rec['message'],
        }

        lead = request.env['crm.lead'].sudo().create(vals)

        return {
            'success': True,
            'message': 'Created Successfully',
            'lead_id': lead.id
        }

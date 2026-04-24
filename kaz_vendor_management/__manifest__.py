# -*- coding: utf-8 -*-
{
    'name': "Vendor Management",
    'summary': "Streamlined vendor onboarding, tender management, bidding, and evaluation workflows",
    'description': """
Vendor Management Module
========================

This module provides a complete vendor lifecycle and tender management system,
enabling organizations to manage vendor registrations, qualification, bidding,
and tender evaluation efficiently.

Key Features
------------
- Vendor self-registration portal with OTP verification
- Automated vendor onboarding workflow and approval process
- Tender publication through the website portal
- Secure vendor login to view and participate in tenders
- RFQ visibility and bid submission through a structured portal interface
- BAFO management and final tender awarding workflow
- Configurable checklists for evaluation and vendor qualification
- Integrated email notifications for tender status updates
- Activity tracking and reminders for procurement teams
- Full Odoo backend integration with Purchases, Contacts, and Activities

This module enhances transparency, improves vendor engagement, and simplifies
procurement operations for organizations of all sizes.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Purchases',
    'version': '1.0',
    'depends': ['website', 'kaz_contact_approval', 'kaz_approval_sign_base', 'kaz_kuec_report_base'],
    'data': [
        'security/res_groups.xml',
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'data/email_template_tender_awarded_data.xml',
        'data/email_template_registration_success_data.xml',
        'data/email_template_vendor_evaluation_data.xml',
        'data/email_template_tender_active_data.xml',
        'data/email_template_bafo_data.xml',
        'data/email_template_vendor_otp_data.xml',
        'data/mail_activity_type_data.xml',
        'data/ir_sequence_data.xml',
        'data/website_menu_data.xml',
        'reports/awarding_letter_reports.xml',
        # Website
        'views/tender_bid_template.xml',
        'views/no_access_tender_info_view_template.xml',
        'views/register_tender_view_template.xml',
        'views/tender_bid_portal_view.xml',
        'views/vendor_register_successful_template.xml',
        'views/vendor_signup_template.xml',
        'views/no_access_tender_view_template.xml',
        'views/tender_view_template.xml',
        # Backend
        'wizards/award_tender_views.xml',
        'wizards/choose_vendor_views.xml',
        'wizards/kick_off_meeting_views.xml',
        'views/company_size_views.xml',
        'views/iso_certification_views.xml',
        'views/purchase_requisition_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/material_purchase_requisition_views.xml',
        'views/tender_bafo_request_views.xml',
        'views/tender_rfq_views.xml',
        'views/res_partner_views.xml',
        'views/tender_checklist_conf_views.xml',
        'views/evaluation_checklist_conf_views.xml',
        'views/tender_bid_views.xml',
        'views/purchase_order_views.xml',
        'views/vendor_evaluation_conf_views.xml',
        'views/vendor_evaluation_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_bank_views.xml',
        'views/purchase_contract_agreement_views.xml',
        'views/purchase_requisition_views.xml',
        'views/tender_res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaz_vendor_management/static/src/css/tender_kanban.css',
            'kaz_vendor_management/static/src/backend/fields/*',
        ],
        'web.assets_frontend': [
            'kaz_vendor_management/static/src/css/vendor.css',
            'kaz_vendor_management/static/src/frontend/**/*',
        ],
        'web.assets_frontend_lazy': [
            'kaz_vendor_management/static/src/frontend/tender/tender.css',
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

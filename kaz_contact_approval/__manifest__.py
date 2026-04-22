# -*- coding: utf-8 -*-
{
    'name': "Contact Approvals",
    'summary': "Manage multi-level contact approval workflows with pre-approver, qualifier, and admin roles.",
    'description': """
    The Contact Approvals module enables organizations to manage and control the approval process of contacts efficiently.

    Key features include:
    - Multi-level approval workflow with Pre-Approver, Qualifier, and Admin roles.
    - Ability to reject contacts with a structured reason via a wizard.
    - Custom checklist configuration for each contact, including attachment requirements, expiry dates, and sequence ordering.
    - Company-specific attachments and checklist lines, ensuring multi-company support.
    - Full integration with Odoo’s contact management (res.partner) and message tracking (chatter) for audit and notifications.

    This module is ideal for companies that need structured validation, approvals, and compliance for managing their contacts and vendors.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources',
    'version': '1.4',
    'depends': ['kz_requisition_quintuple_approvals', 'purchase_requisition', 'sales_team', 'hr', 'contacts'],
    'data': [
        'security/res_groups.xml',
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'data/mail_activity_type_data.xml',
        'data/reminder_mail_template_data.xml',
        'data/reminder_ir_cron_data.xml',
        'wizards/contact_reject_reason_views.xml',
        'views/res_partner_views.xml',
        'views/attachment_attachment_views.xml',
        'views/partner_checklist_conf_views.xml',
        'views/partner_category_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'kaz_contact_approval/static/src/**/*'
        ]
    },
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

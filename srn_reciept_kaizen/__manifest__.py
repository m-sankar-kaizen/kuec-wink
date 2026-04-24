# -*- coding: utf-8 -*-
{
    'name': 'Service Receipt Updates',
    'summary': 'Enhances SRN (Service Receipt Note) processing with notifications, activity scheduling, and custom views',
    'description': """
This module extends and improves the functionality of the Service Receipt Note (SRN) workflow in Odoo. It introduces enhancements such as:

- Custom SRN form and list views for better usability
- Activity scheduling via mail activities (e.g., reminders for pending receipts)
- Role-based access control for SRN operations through new security groups
- Integration with Kaizen notification base for configurable alerts
- Optional cron job definitions for automated tasks (e.g., overdue follow-up)
- UI refinement by removing the database expiration panel in the Enterprise backend

These enhancements aim to streamline the SRN process, improve visibility of pending actions, and ensure compliance with internal service receipt protocols.
    """,
    'author': 'Kaizen Principles',
    'website': 'https://www.kaizenae.com',
    'version': '1.0',
    'category': 'Purchase',
    'depends': ['skit_srn_receipt', 'kz_notification_base'],
    'data': [
        'data/mail_activity_type_data.xml',
        'security/res_groups.xml',
        'views/service_receipt_views.xml',
    ],
    'license': "OPL-1",
    'installable': True,
    'auto_install': False,
    'application': True,
}

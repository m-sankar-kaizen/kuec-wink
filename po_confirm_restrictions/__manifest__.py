# -*- coding: utf-8 -*-
{
    'name': "Purchase Order Confirm Restrictions",
    'summary': """
        Control Partial Purchase Order Confirmation Based on Security Groups
    """,
    'description': """
        This module enforces a two-level approval workflow for confirming Purchase Orders (POs),
        especially when marked as "Partial PO".

        Key Features:
        - Adds a 'Partial PO' toggle on the Purchase Order form.
        - Requires designated group-based approval for POs marked as partial.
        - Introduces multi-level approval states: Waiting, First, and Second Approval.
        - Tracks financial limits: Total Amount and Remaining Amount.
        - Adds file fields for uploading PO and Goods Received Note (GRN) documents.
        - Sends approval request emails and schedules activities for approvers.
        - Approval buttons are restricted and conditionally shown based on user group and PO state.
        - Enhances usability with customized form views, approval status bar, and hotkey support.

        Use Cases:
        - Enables separation of financial and operational approval layers in procurement.
        - Ensures compliance for partial deliveries or partial invoicing.
        - Supports audit traceability with attachments and communication logs.
    """,

    'author': "Kaizen Principles",
    'maintainer': "Kaizen Principles",
    'website': "https://www.kaizenae.com",

    'category': 'Purchase',
    'version': '0.1',

    'depends': [
        'base',
        'account',
        'purchase',
        'kz_notification_base',
    ],

    'data': [
        'data/mail_activity_type_data.xml',
        'data/po_approval_mail_template_data.xml',
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

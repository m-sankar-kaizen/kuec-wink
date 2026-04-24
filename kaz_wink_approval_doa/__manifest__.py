# -*- coding: utf-8 -*-
{
    'name': "WINK DOA Approval",
    'summary': "Delegation of Authority approval workflow for WINK company",
    'description': """
    WINK DOA Approval

    Implements a single-level Coordinator approval workflow for WINK company on
    Account Move (Vendor Bills, Invoices, etc.).

    - Submit for Approval sends the document to the Coordinator group.
    - Coordinator approves → document is marked as Fully Approved.
    - For Vendor Bills (in_invoice), approval also auto-confirms (posts) the bill.
    - Reject and Return for Correction are available at the coordinator stage.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Hidden',
    'version': '1.0',
    'depends': [
        'kaz_kuec_overall_doa_approval',
        'kaz_kuec_wink_company',
        'kaz_vendor_contact_company_restriction'
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_payment_approval_views.xml',
        'views/account_payment_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

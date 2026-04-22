# -*- coding: utf-8 -*-
{
    'name': 'KUEC Leasing Management (IFRS 16)',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Complete IFRS 16 Lease Management for Lessor and Lessee',
    'description': """
        KUEC Leasing Management Module
        ================================
        Complete lease accounting solution compliant with IFRS 16:
        
        Lessor Features:
        ---------------
        * Operating and Finance lease types
        * Automatic PV calculation with discount rate
        * IFRS 16 compliant journal entries (Initial Recognition, Periodic Invoices)
        * Asset book value tracking
        * Selling profit/loss recognition
        * Payment schedule generation
        * Smart button for initial recognition entry
        * Asset protection (ribbon "Is Leased")
        
        Lessee Features:
        ---------------
        * ROU Asset and Lease Liability recognition
        * Automatic depreciation and interest calculation
        * Vendor bill generation
        * Payment tracking
        * IFRS 16 compliant accounting
        
        Proper cancellation with credit/debit notes for posted entries.
    """,
    'author': 'KUEC',
    'website': 'https://www.kuec.com',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'account_asset',
        'mail',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        
        # Data
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/asset_tag_data.xml',
        
        # Views - Lessor
        'views/lessor/lease_lessor_views.xml',
        'views/lessor/account_asset_views.xml',
        # Views - Lessee
        'views/lessee/lease_lessee_contract_views.xml',
        'views/lessee/account_asset_views.xml',
        'views/lessee/res_config_settings_views.xml',
        'views/lessee/lease_lessee_menu.xml',
        'views/lessor/lease_lessor_menu.xml',

    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}

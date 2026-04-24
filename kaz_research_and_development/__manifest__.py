# -*- coding: utf-8 -*-
{
    'name': "Research and Development",
    'summary': "Manage Research & Development requests and automate Purchase Requests upon approval",
    'description': """
    This module allows you to manage Research & Development (R&D) requests within the company. 
    Users can create R&D requests, assign employees and innovation partners, and track their status. 

    Once an R&D request is approved, a corresponding Purchase Request (PR) will be automatically generated 
    to facilitate the procurement of products or services required for the R&D project. 

    Features:
    - Create and manage R&D requests
    - Assign employees and departments automatically
    - Track request state: Draft → Approvals → Approved
    - Link to company and partners
    - Automatic creation of Purchase Requests upon approval
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Purchases',
    'version': '1.0',
    'depends': ['kaz_vendor_management', 'hr'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/mail_activity_type_data.xml',
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/res_config_settings_views.xml',
        'views/research_development_views.xml',
        'views/material_purchase_requisition_views.xml',
        'views/menus.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

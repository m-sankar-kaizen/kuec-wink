# -*- coding: utf-8 -*-
{
    'name': 'KUEC Service Catalogue',
    'version': '18.0.1.1.3',
    'category': 'Sales',
    'summary': 'Service Catalogue & Business Configurability',
    'description': """
    KUEC Service Catalogue module containing core settings, required documents, and Wink tab scaffolding.
    Epic 1 implementation.
    """,
    'author': 'Kaizen Options',
    'depends': [
        'kuec_portal_foundation',
        'sale_management',
        'sale_subscription',
        'website_sale',
        'project',
        'portal',
        'auth_signup',
        'account',
        'hr',
        'web',
        'loyalty'
    ],
    'data': [
        'security/kuec_service_catalogue_security.xml',
        'security/record_rules.xml',
        'security/ir.model.access.csv',
        'data/kuec_classification_data.xml',
        'data/kuec_eligibility_rule_data.xml',
        'data/kuec_tag_data.xml',
        'data/mail_template_data.xml',
        'data/ir_cron_data.xml',
        'data/kuec_tour_data.xml',
        'data/kuec_payment_terms_data.xml',
        'data/mail_template_request.xml',
        'views/kuec_classification_views.xml',
        'views/product_template_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/kuec_plan_change_wizard_views.xml',
        'views/sale_order_views.xml',
        'views/kuec_bundle_group_views.xml',
        'views/website_templates/kuec_catalogue_templates.xml',
        'views/website_templates/employee_portal_templates.xml',
        'views/website_templates/request_templates.xml',
        'views/kuec_employee_directory_views.xml',
        'views/website_templates/wink_catalogue_page.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'kuec_portal_foundation/static/src/scss/wink_theme.scss',
            'kuec_service_catalogue/static/src/js/wink_catalogue.js',
            'kuec_service_catalogue/static/src/js/wink_tour.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

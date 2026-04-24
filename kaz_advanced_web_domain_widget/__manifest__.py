# -*- coding: utf-8 -*-
{
    "name": "Kaizen-Advanced Web Domain Widget",
    "version": "18.0.1.1.0",
    "summary": "Set all relational fields domain by selecting its records unsing `in, not in` operator.",
    "sequence": 10,
    "author": "Kaizen Principles",
    "license": "OPL-1",
    "description": """

        """,
    "depends": ["web"],
    "data": [
        # 'views/assets.xml',
    ],
    "assets": {
        "web._assets_core": [
            "kaz_advanced_web_domain_widget/static/src/tree_editor/*.js",
            "kaz_advanced_web_domain_widget/static/src/tree_editor/*.xml",
            "kaz_advanced_web_domain_widget/static/src/domain_selector/*.js",
            "kaz_advanced_web_domain_widget/static/src/domain_selector/*.xml",
            "kaz_advanced_web_domain_widget/static/src/domain_selector_dialog/*.js",
            "kaz_advanced_web_domain_widget/static/src/domain_selector_dialog/*.xml",
            "kaz_advanced_web_domain_widget/static/src/domain/*.js",
            "kaz_advanced_web_domain_widget/static/src/domain/*.xml",
            "kaz_advanced_web_domain_widget/static/src/model_field_selector/*.js",
            "kaz_advanced_web_domain_widget/static/src/model_field_selector/*.xml",
            "kaz_advanced_web_domain_widget/static/src/autocomplete/*",
            "kaz_advanced_web_domain_widget/static/src/record_selectors/*.js",
            "kaz_advanced_web_domain_widget/static/src/record_selectors/*.xml",
            "kaz_advanced_web_domain_widget/static/src/name_service.js"
        ],
    },
    "application": True,
    "installable": True,
    "auto_install": False,
}

# -*- coding: utf-8 -*-
{
    "name": "Asset Confirm",
    "version": "1.0",
    "summary": "Server action to auto-validate all draft assets",
    "description": """
        Adds a server action on the asset model to validate all draft assets in bulk. 
        This triggers the computation of depreciation lines and changes the state to validated.
    """,
    "category": "Accounting/Accounting",
    "author": "Kaizen",
    "website": "https://www.kaizenae.com",
    "depends": ["account_asset"],
    "data": [
        "views/account_asset_actions.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "auto_install": False,
    "application": False,
}

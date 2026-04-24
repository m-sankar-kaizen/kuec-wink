# -*- coding: utf-8 -*-
"""
Extension of `res.config.settings` to manage loan approval settings at company level.

Kaizen Principles Applied:
- **Standardization**: Centralizes configuration for accounting loan approvals.
- **Built-in Quality**: Uses system parameters to ensure persistent behavior across restarts.
- **Transparency**: Exposes setting in the UI for users with sufficient rights.
"""
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    """
    Extends Odoo's system configuration settings to introduce a toggle for
    enabling or disabling loan approval requirement from the Accounting department.

    Fields:
        loan_approve (Boolean): Indicates whether accounting department approval is required for loans.

    Methods:
        get_values(): Fetches the system parameter `account.loan_approve` into the config wizard.
        set_values(): Persists the `loan_approve` value into the system parameters.

    Usage:
        Accessible via the settings dashboard under technical settings. This boolean switch
        influences whether additional approval steps are enforced in HR Loan workflows.
    """
    _inherit = 'res.config.settings'

    loan_approve = fields.Boolean(
        string="Approval from Accounting Department",
        default=False,
        config_parameter="account.loan_approve",
        help="Enable this option to require loan approval from an accounting manager before disbursement."
    )

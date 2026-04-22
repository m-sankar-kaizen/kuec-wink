# -*- coding: utf-8 -*-
"""
This module extends the `account.move.line` model to add a link to HR loan records.

It enables financial traceability between accounting entries (such as salary journals)
and corresponding HR loan records, supporting payroll and deduction reporting needs.

Kaizen Principle Applied:
- **Standardized Process Integration**: Links payroll loan deductions to journal entries.
- **Transparency**: Improves audit trail between HR and accounting modules.
"""
from odoo import models, api, fields


class AccountMoveLine(models.Model):
    """
    Inherits the `account.move.line` model to establish a relationship
    with the HR Loan module.

    This allows payroll-generated accounting entries (e.g., salary slip deductions)
    to reference the specific HR loan associated with the move line, ensuring
    better tracking and integration between HR and Accounting.

    Typical use case:
        - When salary rules deduct loan repayments, the resulting move lines
          will store a reference to the loan for audit and reconciliation.
    """
    _inherit = "account.move.line"

    loan_id = fields.Many2one(
        'hr.loan',
        string='Loan Reference',
        help='Reference to the HR loan record related to this accounting entry, '
             'typically used in salary deduction journal lines.'
    )

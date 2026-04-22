# -*- coding: utf-8 -*-
"""
Extends core HR models to support:
- Salary rule reporting sequence
- Employee bank-related fields for export
- Company bank account linkage
- Contract-level allowance separation

Used in payroll and banking integrations (e.g. SIF, GCC/UAE bank files).
"""

from odoo import models, fields


class HrEmployee(models.Model):
    """
    Extends hr.employee to add banking and payroll metadata fields.

    Fields:
        - emp_unique_id: Global employee identifier.
        - emp_routing_no: Banking agent code or routing number.
        - addresline1, addresline2: Used in salary payment reports.
        - swift_address_bic: SWIFT or BIC code for bank integration.
        - ku_number: Custom institutional ID (e.g., for Kuwait University).
    """
    _inherit = 'hr.employee'

    emp_unique_id = fields.Char(
        string='Employee Unique ID',
        required=False,
        help="Unique identifier for the employee used in banking or external integrations."
    )

    emp_routing_no = fields.Char(
        string='Agent ID/Routing No',
        required=False,
        help="Routing number or agency identifier for salary processing."
    )

    addresline1 = fields.Char(
        string='Address Line 1',
        required=False,
        help="First line of employee address. Used in banking reports."
    )

    addresline2 = fields.Char(
        string='Address Line 2',
        required=False,
        help="Second line of employee address. Used in banking reports."
    )

    swift_address_bic = fields.Char(
        string='Swift Address/BIC',
        required=False,
        help="SWIFT or BIC code of the employee's bank branch."
    )

    ku_number = fields.Char(
        string='KU Employee Number',
        required=False,
        help="Institution-specific employee number (e.g. for Kuwait University)."
    )


class HrEmployeePublic(models.Model):
    """
    Mirrors selected non-sensitive fields from hr.employee for public/portal use.

    Useful for report access, read-only data sharing with restricted users.
    """
    _inherit = 'hr.employee.public'

    emp_unique_id = fields.Char(
        string='Employee Unique ID',
        required=False,
        help="Public mirror of unique employee ID from HR."
    )

    emp_routing_no = fields.Char(
        string='Agent ID/Routing No',
        required=False,
        help="Public mirror of routing number for bank export."
    )

    addresline1 = fields.Char(
        string='Address Line 1',
        required=False,
        help="First line of public address used for payroll export."
    )

    addresline2 = fields.Char(
        string='Address Line 2',
        required=False,
        help="Second line of public address used for payroll export."
    )

    swift_address_bic = fields.Char(
        string='Swift Address/BIC',
        required=False,
        help="Bank's SWIFT/BIC code for payroll."
    )

    ku_number = fields.Char(
        string='KU Employee Number',
        required=False,
        help="Institutional ID exposed in public model."
    )


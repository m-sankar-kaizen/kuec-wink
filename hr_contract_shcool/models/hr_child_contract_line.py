# -*- coding: utf-8 -*-
from odoo import models, fields


class HrChildContractLine(models.Model):
    """
    Model: hr.child.contract.line
    Description:
        This model represents a single child-related contract line linked to an HR contract.
        It is used to record detailed information about each child covered under an employee's contract,
        typically for benefits such as educational entitlements, tuition, transportation, and related payments.

    Fields:
        contract_id (Many2one):
            Reference to the parent HR contract ('hr.contract') to which this child record belongs.

        child_name (Char):
            The full name of the child.

        paid_to (Char):
            The party to whom payments are made for this child's benefits.
            Defaults to "Employee".

        created_on (Datetime):
            The date and time when this child contract line record was created.

        school (Char):
            The name of the school the child attends.

        reference (Char):
            Any reference or external identifier related to the child's contract or entitlement.

        birth_day (Date):
            The child's date of birth.

        academic (Char):
            The academic year for which the entitlements or payments apply.

        semester (Integer):
            The academic semester number within the academic year.

        grade (Integer):
            The child's current grade level at school.

        book (Float):
            The amount allocated or paid for books for this child.

        total_paid_before (Float):
            The total amount paid previously for this child's entitlements.

        transportation (Float):
            The transportation allowance or cost associated with this child.

        tuition (Float):
            The tuition fees amount related to this child.

        amount_requested (Float):
            The amount currently requested for payment or reimbursement.

        child_entitlement (Float):
            The total entitlement amount approved for this child.

        amount_paid (Float):
            The amount already paid against the requested entitlements.
    """

    _name = 'hr.child.contract.line'
    _description = 'HR Child Contract Line'

    contract_id = fields.Many2one(
        'hr.contract',
        string="Contract",
        required=True,
        help="Reference to the employee's HR contract to which this child contract line belongs."
    )

    child_name = fields.Char(
        string="Child Name",
        required=True,
        help="Full name of the child covered under this contract."
    )

    paid_to = fields.Char(
        string="Paid to",
        default="Employee",
        help="Indicates the recipient of payments related to this child's entitlements."
    )

    created_on = fields.Datetime(
        string="Created On",
        default=fields.Datetime.now,
        help="Timestamp when this record was created."
    )

    school = fields.Char(
        string="School",
        help="Name of the school the child is attending."
    )

    reference = fields.Char(
        string="Reference",
        help="External reference or identifier related to this child's contract."
    )

    birth_day = fields.Date(
        string="Birth Day",
        help="Child's date of birth."
    )

    academic = fields.Char(
        string="Academic Year",
        help="Academic year to which the entitlements or payments apply."
    )

    semester = fields.Integer(
        string="Semester",
        help="Semester number within the academic year."
    )

    grade = fields.Integer(
        string="Grade",
        help="Current grade or class level of the child."
    )

    book = fields.Float(
        string="Book",
        help="Amount allocated or paid for books."
    )

    total_paid_before = fields.Float(
        string="Total Paid Before",
        help="Total amount paid previously for this child's entitlements."
    )

    transportation = fields.Float(
        string="Transportation",
        help="Transportation allowance or costs for the child."
    )

    tuition = fields.Float(
        string="Tuition",
        help="Tuition fees amount for the child."
    )

    amount_requested = fields.Float(
        string="Amount Requested",
        help="Current amount requested for payment or reimbursement."
    )

    child_entitlement = fields.Float(
        string="Child Entitlement",
        help="Approved total entitlement amount for the child."
    )

    amount_paid = fields.Float(
        string="Amount Paid",
        help="Amount already paid against this child's entitlements."
    )

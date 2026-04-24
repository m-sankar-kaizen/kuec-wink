# -*- coding: utf-8 -*-
from odoo import models, fields


class HrContract(models.Model):
    """
    Model: hr.contract (Inherited)
    Description:
        This model extends the standard HR Contract to include additional fields related to
        child contract lines, assignment details, travel ticketing, family counts, and financial
        information pertaining to contracts involving employee assignments and related benefits.

    Fields:
        child_contract_line_ids (One2many):
            Links multiple child contract lines ('hr.child.contract.line') associated with this HR contract.
            Represents the children covered under the contract for benefits tracking.

        assignment_status (Char):
            Status of the employee's assignment (e.g., Active, Completed, Suspended).

        assignment_category (Char):
            Category or classification of the employee's assignment (e.g., Overseas, Local).

        organization (Char):
            Name of the organization or unit related to this contract/assignment.

        contract_type (Char):
            Type of contract (e.g., Fixed-term, Permanent, Temporary).

        payroll_period (Integer):
            Payroll period number associated with the contract, useful for payroll processing.

        ticket_zone (Char):
            Zone or region classification for ticketing purposes.

        country_code (Char):
            ISO or internal code of the country relevant to the contract or travel.

        ticket_class (Char):
            Class of ticket booked or eligible for (e.g., Economy, Business, First).

        adult_ticket_amount (Float):
            Monetary amount allocated or spent on adult tickets.

        child_ticket_amount (Float):
            Monetary amount allocated or spent on child tickets.

        infant_ticket_amount (Float):
            Monetary amount allocated or spent on infant tickets.
            Uses the contract's currency.

        prev_adult_ticket_amount (Float):
            Previous historical amount spent on adult tickets.

        prev_child_ticket_amount (Float):
            Previous historical amount spent on child tickets.

        prev_infant_ticket_amount (Float):
            Previous historical amount spent on infant tickets.
            Uses the contract's currency.

        employee_count (Integer):
            Number of employees covered under the contract (usually 1, but can vary).

        spouse_count (Integer):
            Number of spouses covered under the contract.

        adult_count (Integer):
            Number of adults covered under the contract.

        child_count (Integer):
            Number of children covered under the contract.

        infant_count (Integer):
            Number of infants covered under the contract.

        total_count (Integer):
            Total count of all covered persons (employees, spouse, children, infants).

        start_date (Date):
            Contract or assignment start date.

        end_date (Date):
            Contract or assignment end date.

        days (Integer):
            Duration of the contract or assignment in days.

        previous_outstanding (Float):
            Amount previously outstanding or owed related to the contract.
            Uses the contract's currency.

        year_payment (Float):
            Total payment amount for the year related to the contract.
            Uses the contract's currency.

        deductions_adjustments (Float):
            Any deductions or adjustments applied to payments.

        total_amount (Float):
            Total amount payable or accounted for in this contract.
            Uses the contract's currency.

        remarks (Text):
            Additional notes or remarks related to the contract.
    """

    _inherit = 'hr.contract'

    child_contract_line_ids = fields.One2many(
        'hr.child.contract.line',
        'contract_id',
        string="Child Contract Lines",
        help="Child records linked to this HR contract for tracking benefits."
    )

    assignment_status = fields.Char(
        string="Assignment Status",
        help="Current status of the employee's assignment."
    )
    assignment_category = fields.Char(
        string="Assignment Category",
        help="Category or classification of the assignment."
    )
    organization = fields.Char(
        string="Organization",
        help="Organization or unit associated with this contract."
    )
    contract_type = fields.Char(
        string="Contract Type",
        help="Type of contract (e.g., Fixed-term, Permanent)."
    )
    payroll_period = fields.Integer(
        string="Payroll Period",
        help="Payroll period number linked to this contract."
    )
    ticket_zone = fields.Char(
        string="Ticket Zone",
        help="Ticketing zone or region classification."
    )
    country_code = fields.Char(
        string="Country Code",
        help="Country code relevant to the contract or travel."
    )
    ticket_class = fields.Char(
        string="Ticket Class",
        help="Class of travel ticket eligible or booked."
    )

    adult_ticket_amount = fields.Float(
        string="Adult Ticket Amount",
        help="Amount allocated or spent on adult travel tickets."
    )
    child_ticket_amount = fields.Float(
        string="Child Ticket Amount",
        help="Amount allocated or spent on child travel tickets."
    )
    infant_ticket_amount = fields.Float(
        string="Infant Ticket Amount",
        help="Amount allocated or spent on infant travel tickets, in contract currency."
    )

    prev_adult_ticket_amount = fields.Float(
        string="Previous Adult Ticket Amount",
        help="Historical amount spent on adult tickets before this contract period."
    )
    prev_child_ticket_amount = fields.Float(
        string="Previous Child Ticket Amount",
        help="Historical amount spent on child tickets before this contract period."
    )
    prev_infant_ticket_amount = fields.Float(
        string="Previous Infant Ticket Amount",
        help="Historical amount spent on infant tickets before this contract period, in contract currency."
    )

    employee_count = fields.Integer(
        string="Employee Count",
        help="Number of employees covered by this contract."
    )
    spouse_count = fields.Integer(
        string="Spouse Count",
        help="Number of spouses covered by this contract."
    )
    adult_count = fields.Integer(
        string="Adult Count",
        help="Number of adults covered by this contract."
    )
    child_count = fields.Integer(
        string="Child Count",
        help="Number of children covered by this contract."
    )
    infant_count = fields.Integer(
        string="Infant Count",
        help="Number of infants covered by this contract."
    )
    total_count = fields.Integer(
        string="Total Count",
        help="Total number of individuals covered (employees, spouse, children, infants)."
    )
    start_date = fields.Date(
        string="Start Date",
        help="Contract or assignment start date."
    )
    end_date = fields.Date(
        string="End Date",
        help="Contract or assignment end date."
    )
    days = fields.Integer(
        string="Days",
        help="Duration of the contract or assignment in days."
    )
    previous_outstanding = fields.Float(
        string="Previous Outstanding",
        help="Outstanding amount carried over from previous periods, in contract currency."
    )
    year_payment = fields.Float(
        string="Year Payment",
        help="Total payment amount for the year, in contract currency."
    )
    deductions_adjustments = fields.Float(
        string="Deductions and Adjustments",
        help="Deductions or adjustments applied to payments."
    )
    total_amount = fields.Float(
        string="Total Amount",
        help="Total amount payable or accounted for in this contract, in contract currency."
    )
    remarks = fields.Text(
        string="Remarks",
        help="Additional notes or remarks related to this contract."
    )

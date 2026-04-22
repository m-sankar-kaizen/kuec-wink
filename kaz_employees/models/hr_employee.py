# -*- coding: utf-8 -*-
"""
This module extends Odoo's `hr.employee` model to support KAZ-specific fields such as
employee code, bank info, blood type, emergency contacts, children info, and
IBAN validation. It also introduces supporting models: blood type, kids details,
emergency contacts, relationships, and bank branches.

Includes:
---------
- Custom constraints on IBAN format
- Sequence generation for employee records
- Scale detection from contracts
- Employee public model extension for portal/internal use
"""

from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    """
    Inherits the `hr.employee` model to include KAZ-specific employee details.

    Fields added:
    -------------
    - emp_code (unique employee code)
    - bank information (name, branch, IBAN)
    - emergency contacts
    - children information
    - personal identifiers (EID, passport, spouse details)
    - dynamic scale assignment from contracts
    """
    _inherit = 'hr.employee'

    # Unique SQL constraint on employee code
    _sql_constraints = [
        ('emp_code_unique', 'unique(emp_code)', 'Employee code must be unique.')
    ]

    emp_code = fields.Char(string='Employee Code')
    unit_id = fields.Many2one('employee.unit', string="Unit")
    section_id = fields.Many2one('employee.section', string="Section")
    hire_date = fields.Date(string='Hire Date')

    kaz_employee_type = fields.Selection(
        string='Employee Type',
        required=True,
        default='local',
        selection=[('local', 'Local'), ('expat', 'Expat')],
        help="Classifies employees as either Local or Expat."
    )

    sequence = fields.Char(string='Sequence', default='New')
    blood_type_id = fields.Many2one('blood.type', string="Blood Type")
    emergency_data_ids = fields.One2many('emergency.data', 'employee_id', string="Emergency Contacts")
    father_name = fields.Char(string='Father Name')
    mother_name = fields.Char(string='Mother Name')
    spouse_name = fields.Char(string='Spouse Name')
    spouse_employee_id = fields.Many2one("hr.employee", string="Spouse Employee")
    emirates = fields.Char(string='Emirates ID')
    emirates_expiration = fields.Date(string='EID Expiration Date')
    passport_expiration = fields.Date(string='Passport Expiration')
    issue_date = fields.Date(string='Passport Issue Date')
    kid_ids = fields.One2many('kids.details', 'parent_id', string="Children")

    bank_name_id = fields.Many2one('res.bank', string='Bank Name')
    bank_branch_id = fields.Many2one('bank.branch', string='Bank Branch')
    iban_num = fields.Char(string='IBAN NO')

    @api.onchange('iban_num')
    def _onchange_iban(self):
        """Prepend 'AE' to IBAN if not already present."""
        for rec in self:
            if rec.iban_num and not rec.iban_num.startswith('AE'):
                rec.iban_num = f"AE{rec.iban_num}"

    @api.constrains('iban_num')
    def _check_iban_format(self):
        """Ensure IBAN format: starts with 'AE' and followed by 21 digits."""
        for rec in self:
            if (
                    not rec.iban_num or
                    not rec.iban_num.startswith('AE') or
                    len(rec.iban_num) != 23 or
                    not rec.iban_num[2:].isdigit()
            ):
                raise ValidationError(
                    "IBAN must start with 'AE' followed by exactly 21 digits.")

    grade_id = fields.Many2one(related='job_id.grade_id')
    scale = fields.Selection(
        compute='get_current_contract',
        selection=[('minimum', 'Minimum'), ('midpoint', 'Midpoint'), ('maximum', 'Maximum')],
        string="Salary Scale",
        store=False,
        help="Derived from the currently active contract."
    )

    def get_current_contract(self):
        """Detect the current active contract and derive the scale."""
        for rec in self:
            Contract = self.env['hr.contract']
            current_contract = Contract.search([
                ('employee_id', '=', rec.id),
                ('state', '=', 'open')
            ], order='date_start desc', limit=1)
            rec.scale = current_contract.scale

    @api.onchange("spouse_employee_id")
    def onchange_spouse_employee_id(self):
        """Auto-populate spouse name from linked employee record."""
        if self.spouse_employee_id:
            self.spouse_name = self.spouse_employee_id.name

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to assign employee sequence code."""
        for vals in vals_list:
            vals['sequence'] = self.env['ir.sequence'].next_by_code('hr.employee')
        return super().create(vals_list)

    def action_open_contract(self):
        """
        inherit action_open_contract
        :return:
        """
        res = super().action_open_contract()
        if not self.contract_ids:
            res['context'].update({
                'default_department_id': self.department_id.id,
                'default_job_id': self.job_id.id
            })
        return res


class HrEmployeePublic(models.Model):
    """
    Public/portal variant of the HR employee model.
    Mirrors private fields as readonly or related versions.
    """
    _inherit = 'hr.employee.public'

    emp_code = fields.Char(string='Employee Code', related='employee_id.emp_code')
    unit_id = fields.Many2one('employee.unit', string="Unit", related="employee_id.unit_id")
    section_id = fields.Many2one('employee.section', related="employee_id.section_id")
    hire_date = fields.Date(string='Hire Date', related="employee_id.hire_date")
    kaz_employee_type = fields.Selection(related="employee_id.kaz_employee_type")
    sequence = fields.Char(string='Sequence', related="employee_id.sequence")
    blood_type_id = fields.Many2one('blood.type', related="employee_id.blood_type_id")
    emergency_data_ids = fields.One2many(related="employee_id.emergency_data_ids")
    father_name = fields.Char(string='Father Name', related="employee_id.father_name")
    mother_name = fields.Char(string='Mother Name', related="employee_id.mother_name")
    spouse_name = fields.Char(string='Spouse Name', related="employee_id.spouse_name")
    emirates = fields.Char(string='Emirates ID', related="employee_id.emirates")
    emirates_expiration = fields.Date(string='EID Expiration Date', related="employee_id.emirates_expiration")
    passport_expiration = fields.Date(string='Passport Expiration', related="employee_id.passport_expiration")
    issue_date = fields.Date(string='Passport Issue Date', related="employee_id.issue_date")
    kid_ids = fields.One2many(related="employee_id.kid_ids")
    bank_name_id = fields.Many2one('res.bank', string='Bank Name', related="employee_id.bank_name_id")
    bank_branch_id = fields.Many2one('bank.branch', string='Bank Branch', related="employee_id.bank_branch_id")
    iban_num = fields.Char(string='IBAN NO', related="employee_id.iban_num")
    grade_id = fields.Many2one(related='employee_id.grade_id')
    scale = fields.Selection(related="employee_id.scale")
    spouse_employee_id = fields.Many2one("hr.employee", related="employee_id.spouse_employee_id")


# ----------------------------------------------------
# Supporting Models
# ----------------------------------------------------

class BloodType(models.Model):
    """Simple list of blood types (A+, B-, etc.)."""
    _name = "blood.type"
    _description = "Blood Types"
    name = fields.Char(string='Name')


class BankBranch(models.Model):
    """Bank branches for employee banking info."""
    _name = 'bank.branch'
    _description = "Bank Branches"
    name = fields.Char(string="Branch Name")


class Relationship(models.Model):
    """Relationship types for emergency contact persons."""
    _name = 'relationship'
    _description = "Relationship Types"
    name = fields.Char(string='Relationship Type')


class KidsDetails(models.Model):
    """
    Records details of employees’ children including birth date
    and auto-calculated age.
    """
    _name = 'kids.details'
    _description = "Kids Details"

    name = fields.Char(string='Child Name')
    age = fields.Date(string='Birth Date')
    age_calc = fields.Integer(string='Age', compute='compute_age_calc')
    parent_id = fields.Many2one('hr.employee', readonly=True, string="Parent Employee")

    @api.depends('age')
    def compute_age_calc(self):
        """Compute child’s age based on birthdate."""
        for rec in self:
            if rec.age and rec.age <= fields.Date.today():
                rec.age_calc = relativedelta(
                    fields.Date.from_string(fields.Date.today()),
                    fields.Date.from_string(rec.age)
                ).years
            else:
                rec.age_calc = 0


class Emergency(models.Model):
    """
    Emergency contact information linked to employees.
    """
    _name = 'emergency.data'
    _description = "Emergency Contact Information"

    name = fields.Char(string='Name')
    email = fields.Char(string='Email')
    number = fields.Char(string='Phone Number')

    type = fields.Selection([
        ('uae', 'UAE'),
        ('home', 'Home Country')
    ], default='uae', string="Location")

    relationship_id = fields.Many2one('relationship', string='Relationship')
    employee_id = fields.Many2one('hr.employee', string="Employee")

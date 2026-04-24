# -*- coding: utf-8 -*-
from odoo import models, fields, api


class HrContract(models.Model):
    """
    Extension of the `hr.contract` model to compute:
    - Total salary by summing up all allowance-related fields.
    - Pension deduction for local employees (UAE nationals) as 5% of relevant salary components.
    - Pension deduction for Omani expatriates as 7.5% of limited salary components (wage + living).

    This model assumes that the following custom fields are available in `hr.contract`:
        - Personal_allowance
        - Premium_allowance
        - living_allowance
        - connectivity_allowance
        - social_uae_allowance
        - acting_allowance_amount
        - kaz_child_allowance

    It also depends on:
        - `employee_id.kaz_employee_type`: custom field categorizing the employee as 'local' or 'expat'
        - `employee_id.country_id`: used to check if employee is Omani
    """

    _inherit = 'hr.contract'

    total_salary = fields.Monetary(
        string='Total Salary',
        currency_field='currency_id',
        compute='_calc_total_salary',
        help="Total salary calculated by summing wage and various allowances."
    )

    pension_deduction = fields.Monetary(
        string="Pension Deduction",
        compute='compute_pension_deduction',
        help="Applicable only to local (UAE national) employees. 5% of total eligible earnings."
    )

    pension_deduction_oman = fields.Monetary(
        string="Pension Deduction Oman",
        compute='compute_pension_deduction_oman',
        help="Applicable to expatriates working in Oman. 7.5% of basic wage + living allowance."
    )

    @api.depends('employee_id')
    def compute_pension_deduction(self):
        """
        Compute the pension deduction for local employees (UAE nationals).
        The deduction is 5% of: wage + Premium Allowance + Living Allowance + Child Allowance.
        """
        for rec in self:
            if rec.employee_id.kaz_employee_type == 'local':
                # Apply 5% pension on eligible components
                rec.pension_deduction = (
                                                rec.wage +
                                                rec.Premium_allowance +
                                                rec.living_allowance +
                                                rec.kaz_child_allowance
                                        ) * 0.05
            else:
                rec.pension_deduction = 0

    @api.depends('employee_id')
    def compute_pension_deduction_oman(self):
        """
        Compute the pension deduction for expatriates working in Oman.
        The deduction is 7.5% of (wage + living allowance) if the employee is an expat and Omani.
        """
        oman_country = self.env.ref('base.om')  # Oman country record
        for rec in self:
            if (
                    rec.employee_id.kaz_employee_type == 'expat' and
                    rec.employee_id.country_id == oman_country
            ):
                rec.pension_deduction_oman = (
                                                     rec.wage + rec.living_allowance
                                             ) * 0.075
            else:
                rec.pension_deduction_oman = 0

    @api.depends(
        'wage',
        'Personal_allowance',
        'Premium_allowance',
        'living_allowance',
        'connectivity_allowance',
        'social_uae_allowance',
        'acting_allowance_amount',
        'kaz_child_allowance'
    )
    def _calc_total_salary(self):
        """
        Compute the total salary by summing:
        wage + all allowances (Personal, Premium, Living, Connectivity, Social UAE, Acting, Child).
        """
        for rec in self:
            rec.total_salary = (
                    rec.wage +
                    rec.Personal_allowance +
                    rec.Premium_allowance +
                    rec.living_allowance +
                    rec.connectivity_allowance +
                    rec.social_uae_allowance +
                    rec.acting_allowance_amount +
                    rec.kaz_child_allowance
            )

# -*- coding: utf-8 -*-
"""
This module extends the `hr.contract` model to add additional allowances and benefits
specific to the KAZ organization's compensation structure. It includes dynamic field
calculations, validations against grade-level limits, and salary scale computations.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    """
    Extension of the core `hr.contract` model to include custom allowances, benefits,
    and validations tied to employee grades.

    Key Features:
    -------------
    - Related fields for dynamic allowance values based on employee grade.
    - Computation of salary scale position (minimum/midpoint/maximum).
    - Validation for social UAE allowance not exceeding grade limits.
    - Dynamic updating of allowances on employee change.
    """

    _inherit = 'hr.contract'

    # Related field to reflect employee type from employee model
    kaz_employee_type = fields.Selection(
        related='employee_id.kaz_employee_type',
        string="Employee Type",
        readonly=True,
    )

    # Allowances from grade, with fallbacks/defaults
    Personal_allowance = fields.Float(
        string='Monthly Personal',
        default=lambda self: self.grade_id.monthly_personal_allowance if self.grade_id else 0.0,
        help="Monthly personal allowance as per grade."
    )

    Premium_allowance = fields.Float(
        string='Monthly Premium-UAE',
        default=lambda self: self.grade_id.monthly_premium_uae_allowance if self.grade_id else 0.0,
        help="Monthly premium allowance for UAE employees as per grade."
    )

    living_allowance = fields.Float(
        string='Monthly Living',
        related="employee_id.grade_id.monthly_living_allowance",
        readonly=True,
        help="Monthly living allowance directly fetched from employee's grade."
    )

    living_allowance_additional = fields.Float(
        string='Additional Living Allowance',
        default=0.0,
        help="Optional additional living allowance."
    )

    social_uae_allowance = fields.Float(
        string="Social UAE Allowance",
        default=0.0,
        help="Allowance applicable for UAE nationals."
    )

    connectivity_allowance = fields.Float(
        string='Monthly Connectivity',
        related='grade_id.monthly_connectivity',
        readonly=True,
        help="Monthly internet/communication allowance from grade."
    )

    relocation_benefit = fields.Float(string='Relocation Benefit')
    repatriation_allowance = fields.Float(string='Repatriation Benefit')
    educational_benefit = fields.Float(string='Educational Allowance')

    annual_air_ticket = fields.Boolean(string='Annual Air Ticket')
    end_of_Service_Gratuity = fields.Boolean(string='End of Service Gratuity')
    retirement_fund = fields.Boolean(string='Retirement Fund')

    # Salary scale classification: minimum/midpoint/maximum
    scale = fields.Selection(
        compute='get_scale_basic',
        selection=[
            ('minimum', 'Minimum'),
            ('midpoint', 'Midpoint'),
            ('maximum', 'Maximum')
        ],
        string="Salary Scale",
        store=True,
        help="Categorization of basic wage based on grade thresholds."
    )

    scale_basic = fields.Float(
        string="Scale Basic",
        help="Customizable wage field that is validated against grade thresholds."
    )

    # Grade is a related field from employee for consistency
    grade_id = fields.Many2one(
        'hr.grade',
        related='employee_id.grade_id',
        string="Grade",
        readonly=True
    )

    # -------------------------------
    # Constraints
    # -------------------------------

    @api.constrains('social_uae_allowance')
    def constrain_social_uae_allowance(self):
        """
        Constraint to ensure that the entered social UAE allowance does not
        exceed the allowance specified for the employee's grade.
        """
        for rec in self:
            if rec.grade_id and rec.social_uae_allowance > rec.grade_id.social_uae_allowance:
                raise ValidationError(
                    _("The entered amount for Social UAE Allowance (%s) exceeds the defined limit (%s).") % (
                        rec.social_uae_allowance, rec.grade_id.social_uae_allowance
                    )
                )

    # -------------------------------
    # Onchange Events
    # -------------------------------

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        """
        On change of employee, update the living allowance value from the employee's grade.
        """
        if self.employee_id and self.employee_id.grade_id:
            self.living_allowance = self.employee_id.grade_id.monthly_living_allowance

    @api.onchange('scale_basic')
    def onchange_scale_basic(self):
        """
        When user manually updates `scale_basic`, validate that the value falls within the
        allowed range [min, max] defined by the employee's grade. Also updates the wage.
        """
        for rec in self:
            grade = rec.grade_id
            if not grade or rec.scale_basic <= 0:
                continue
            scale_values = rec._get_scale_basic(grade)
            min_val = scale_values['min']
            mid_val = scale_values['mid']
            max_val = scale_values['max']

            # Assign wage directly from scale_basic
            rec.wage = rec.scale_basic

            # Validate scale_basic falls in allowed range
            if not (min_val <= rec.scale_basic <= max_val):
                raise ValidationError(
                    _("The value of scale basic must be between {} and {}.").format(min_val, max_val)
                )

    # -------------------------------
    # Helpers
    # -------------------------------

    def _get_scale_basic(self, grade):
        """
        Returns a dictionary of salary thresholds for a given grade.

        Parameters:
        -----------
        grade : recordset
            The hr.grade record.

        Returns:
        --------
        dict : {
            'min': float,
            'mid': float,
            'max': float
        }
        """
        return {
            'min': grade.minimum_basic,
            'mid': grade.midpoint_basic,
            'max': grade.maximum_basic,
        }

    @api.depends('scale_basic')
    def get_scale_basic(self):
        """
        Computes the nearest classification (minimum/midpoint/maximum) for the
        `scale_basic` value in relation to the employee's grade ranges.
        """
        for rec in self:
            if not rec.grade_id or rec.scale_basic <= 0:
                continue

            scale_values = rec._get_scale_basic(rec.grade_id)
            min_val = scale_values['min']
            mid_val = scale_values['mid']
            max_val = scale_values['max']

            # Determine the closest match among min/mid/max
            nearest_key = min(
                scale_values.keys(),
                key=lambda k: abs(rec.scale_basic - scale_values[k])
            )

            if nearest_key == 'min':
                rec.scale = 'minimum'
            elif nearest_key == 'mid':
                rec.scale = 'midpoint'
            elif nearest_key == 'max':
                rec.scale = 'maximum'

# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Duration Settings
    secondment_max_duration_months = fields.Integer(
        string='Maximum Secondment Duration (Months)',
        default=6,
        config_parameter='hr_employee_secondment.max_duration_months',
        help='Maximum duration in months for a single secondment period. Default: 6 months.'
    )
    
    secondment_max_extension_months = fields.Integer(
        string='Maximum Extension Duration (Months)',
        default=6,
        config_parameter='hr_employee_secondment.max_extension_months',
        help='Maximum additional months allowed for one-time extension. Default: 6 months.'
    )
    
    secondment_allow_extensions = fields.Boolean(
        string='Allow Secondment Extensions',
        default=True,
        config_parameter='hr_employee_secondment.allow_extensions',
        help='Enable employees to extend their secondment period one time.'
    )
    
    # Allowance Settings
    secondment_allowance_threshold_months = fields.Integer(
        string='Allowance Eligibility Threshold (Months)',
        default=2,
        config_parameter='hr_employee_secondment.allowance_threshold_months',
        help='Minimum continuous months required to qualify for secondment allowance. Default: 2 months.'
    )
    
    secondment_allowance_percentage = fields.Float(
        string='Secondment Allowance Percentage',
        default=25.0,
        digits=(5, 2),
        config_parameter='hr_employee_secondment.allowance_percentage',
        help='Percentage of seconded position basic salary paid as monthly allowance. Default: 25%.'
    )
    
    secondment_requires_original_duties = fields.Boolean(
        string='Allowance Requires Original Duties',
        default=True,
        config_parameter='hr_employee_secondment.requires_original_duties',
        help='Allowance only applies if employee maintains their original position duties.'
    )
    
    # Grade Eligibility Settings
    secondment_max_grade_difference = fields.Integer(
        string='Maximum Grade Difference',
        default=2,
        config_parameter='hr_employee_secondment.max_grade_difference',
        help='Maximum number of grades an employee can be promoted above their current grade. Default: 2 grades.'
    )
    
    # Notification Settings
    secondment_notification_days_before_end = fields.Integer(
        string='Notification Days Before End',
        default=30,
        config_parameter='hr_employee_secondment.notification_days_before_end',
        help='Number of days before secondment end date to send notification to HR Manager. Default: 30 days.'
    )
    
    secondment_auto_complete_on_end = fields.Boolean(
        string='Auto-Complete on End Date',
        default=False,
        config_parameter='hr_employee_secondment.auto_complete_on_end',
        help='Automatically mark secondment as completed when end date is reached.'
    )

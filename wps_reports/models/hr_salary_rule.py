# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrSalaryRule(models.Model):
    """
    Inherits hr.salary.rule to add report sequence functionality.

    Fields:
        - report_sequence: Used to control the order of appearance in salary structure reports or payslip exports.
    """
    _inherit = 'hr.salary.rule'

    report_sequence = fields.Integer(
        string='Report Sequence',
        required=False,
        help="Controls the sequence in which this salary rule appears in the printed reports or payslip exports."
    )

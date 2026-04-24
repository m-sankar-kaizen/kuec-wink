# -*- coding: utf-8 -*-
from odoo import models, fields


class HrEmployeePublic(models.Model):
    """
    Extension of hr.employee.public to expose probation-related info in public models.

    Related Fields:
    ---------------
    - is_under_probation: Inherits value from the related hr.employee.
    - remaining_days_to_finish_probation: Inherits value from hr.employee.
    """
    _inherit = 'hr.employee.public'

    company_code = fields.Selection(related='employee_id.company_code')

    is_under_probation = fields.Selection(
        related='employee_id.is_under_probation',
        readonly=True
    )
    remaining_days_to_finish_probation = fields.Integer(
        related='employee_id.remaining_days_to_finish_probation',
        readonly=True
    )
    is_extend_probation = fields.Boolean(
        related='employee_id.is_extend_probation',
        readonly=True
    )
    extend_probation_date = fields.Date(
        related='employee_id.extend_probation_date',
        readonly=True
    )
    extend_probation_remarks = fields.Text(
        related='employee_id.extend_probation_remarks',
        readonly=True
    )
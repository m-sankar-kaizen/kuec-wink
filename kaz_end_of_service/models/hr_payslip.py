# -*- coding: utf-8 -*-
from odoo import models, fields


class HrPayslip(models.Model):
    """
    Inherits the 'hr.payslip' model to add a link to the
    'hr.employee.settlements' model.

    This extension allows tracking which end-of-service (EOS)
    settlement generated a particular payslip. It's particularly
    useful when generating final settlements like gratuity,
    leave encashment, or retirement benefits, and ensuring
    traceability between payslips and EOS requests.
    """

    _inherit = 'hr.payslip'

    end_of_service_id = fields.Many2one(
        comodel_name='hr.employee.settlements',
        string='End of Service Settlement',
        readonly=True,
        help="Reference to the End of Service Settlement request "
             "that triggered the generation of this payslip."
    )

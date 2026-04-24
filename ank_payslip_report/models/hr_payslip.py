# -*- coding: utf-8 -*-
"""
This module extends the hr.payslip model to add custom report actions
for printing Ank-style payslip reports.

Author: Kaizen Principles
Website: https://www.kaizenae.com
License: OPL-1
"""
from odoo import models, fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    """Extension of hr.payslip model to include Ank-specific report actions."""

    def action_print_ank_payslip(self):
        """
        Triggers the Ank Customized Payslip Report.

        This method generates the PDF report using the QWeb template
        'ank_customized_payslip_report' for a single payslip.

        :return: report action for Ank customized payslip
        :rtype: dict
        """
        report_name = 'ank_payslip_report.ank_customized_payslip_report'
        return self.env.ref(report_name).report_action(self)

    def action_print_ank_payslip_ank(self):
        """
        Triggers the Ank Customized Payslip Report Variant.

        This is an alternate version of the payslip report using a
        different QWeb template 'ank_customized_payslip_report_ank'.

        :return: report action for variant payslip
        :rtype: dict
        """
        report_name = 'ank_payslip_report.ank_customized_payslip_report_ank'
        return self.env.ref(report_name).report_action(self)

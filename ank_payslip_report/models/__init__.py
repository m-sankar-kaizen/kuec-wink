# -*- coding: utf-8 -*-
"""
Initialization module for ank_bonus.

This module loads the necessary Python files for the custom bonus feature
in the Payroll module. It includes logic to generate bonus Excel reports
from payslip batches.

Modules imported:
-----------------
- hr_payslip: Inherits hr.payslip.run model to implement 'Print Bonus' feature.

Author: Kaizen Principles
Website: https://www.kaizenae.com
License: OPL-1
"""
from . import hr_payslip

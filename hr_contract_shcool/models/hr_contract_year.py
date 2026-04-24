# -*- coding: utf-8 -*-

from odoo import models, fields


class HrChildContractYearLine(models.Model):
    """
    Model: hr.contract.year
    Description:
        This model represents a yearly summary or record related to child contracts under an HR contract.
        It can be used to track or aggregate child contract data on a per-year basis,
        such as entitlements, payments, or other relevant yearly information.

    Fields:
        (To be defined based on requirements, for example:
         - contract_id: Many2one linking to hr.contract
         - year: Integer or Char representing the year
         - total_amount: Float for yearly totals, etc.)
    """

    _name = 'hr.contract.year'
    _description = 'HR Child Contract Year Line'

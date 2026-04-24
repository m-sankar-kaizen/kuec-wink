# -*- coding: utf-8 -*-
from odoo import models, fields


class HrLeaveType(models.Model):
    """
    Extends `hr.leave.type` to add configuration
    flags for requiring additional levels of approval.

    Fields:
        - by_hr_director: If checked, the leave
         request requires HR Director validation.
        - by_ceo: If checked, the leave request requires CEO validation.
    """
    _inherit = 'hr.leave.type'

    by_hr_director = fields.Boolean("By Hr Director",
                                    help="If enabled, leave requests "
                                         "will require HR Director approval.")
    by_ceo = fields.Boolean("By CEO",
                            help="If enabled, leave requests"
                                 " will require CEO-level approval.")

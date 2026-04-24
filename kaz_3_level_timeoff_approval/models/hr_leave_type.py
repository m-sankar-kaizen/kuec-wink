# -*- coding: utf-8 -*-
from odoo import models, fields


class HrLeaveType(models.Model):
    """
    Inherits the hr.leave.type model to add support for a new, more granular
    time-off approval workflow: 'three_level'.

    The default Odoo time-off approval process supports either:
        - No validation
        - Single-level validation (Manager only)
        - Two-level validation (Manager + Officer)

    This customization introduces a 'three_level' validation option, where:
        1. The Employee's Direct Manager approves first
        2. The Time Off Officer validates the request next
        3. The HR Manager gives the final approval

    Use case:
        Organizations with strict HR protocols or hierarchical structures
        where multiple approvals are necessary before a leave is validated.

    This field is used in hr.leave logic to determine the approval path and UI behavior.
    """
    _inherit = 'hr.leave.type'

    # Selection field extended to include 'three_level' approval option.
    leave_validation_type = fields.Selection(
        selection_add=[
            ('three_level', "By Employee's Approver, Time Off Officer and Hr Manager")
        ],
        ondelete={
            # If a leave type using 'three_level' is deleted,
            # fallback to the default validation method
            'three_level': 'set default'
        },
        help=(
            "Defines how time off requests for this type are validated:\n"
            "- 'three_level': Requires approval from three roles: direct manager, time off officer, and HR manager.\n"
            "Use this for leave types that require stricter control or audit trail."
        )
    )

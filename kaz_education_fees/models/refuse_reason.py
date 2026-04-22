# -*- coding: utf-8 -*-
from odoo import models, fields


class RefuseReason(models.Model):
    """
    Extension of the 'refuse.reason' model to link refusal reasons to
    Education Fees records, enabling traceability of refusals in the
    education reimbursement workflow.
    """
    _inherit = 'refuse.reason'
    _description = 'Refuse Reason'

    education_fees_id = fields.Many2one(
        'education.fees',
        string="Education Fees",
        help="Reference to the education fees request that was refused."
    )

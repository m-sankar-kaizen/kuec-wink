# -*- coding: utf-8 -*-
from odoo import models, fields


class HrSequence(models.Model):
    """
    HR Sequence Model

    This model defines a reusable sequence reference used for HR-related documents or entities.
    It can be linked to one or more job positions to manage job-specific sequences
    for items such as applicant references, offer numbers, or employee codes.

    Fields:
        name (Char): A user-defined label indicating the name or starting reference of the sequence.
        jobs_ids (One2many): Reverse relation to all job positions using this sequence.
    """
    _name = 'hr.sequence'
    _description = 'HR Sequence'

    name = fields.Char(
        string="Name",
        required=True,
        help="The name or starting reference for this HR sequence."
    )

    jobs_ids = fields.One2many(
        'hr.job',
        'hr_sequence_id',
        string="Related Job Positions",
        help="Job positions that use this HR sequence"
             " for tracking or referencing purposes."
    )

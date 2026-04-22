# -*- coding: utf-8 -*-
from odoo import models, fields


class HrRecruitmentStage(models.Model):
    """
    Inherits the `hr.recruitment.stage` model to add stage-specific access control
    by associating approval user groups with recruitment stages.

    This customization allows you to define which user group is allowed to
    approve or move an applicant into a particular recruitment stage.

    Field:
        approval_groups_id (Many2one): A reference to the user group (`res.groups`)
        whose members are allowed to approve applicants for this stage.
    """
    _inherit = 'hr.recruitment.stage'

    approval_groups_id = fields.Many2one(
        'res.groups',
        string="Approval Group",
        help="Only users in this group can move applicants into this stage."
    )

    company_id = fields.Many2one('res.company')
    company_code = fields.Selection(related='company_id.company_code')

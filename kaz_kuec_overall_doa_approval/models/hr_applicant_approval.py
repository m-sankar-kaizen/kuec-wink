# -*- coding: utf-8 -*-
from odoo import models, fields, _


class HrApplicantApproval(models.Model):
    _name = 'hr.applicant.approval'
    _description = 'Hr Applicant Approval'
    _inherit = 'approval.reject.mixin'
    _parent_record = 'applicant_id'

    applicant_id = fields.Many2one('hr.applicant', string='Applicant')

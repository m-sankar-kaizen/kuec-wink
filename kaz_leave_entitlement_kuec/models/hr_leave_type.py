# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    company_code = fields.Selection(related='company_id.company_code', string='Company Code')
    leave_validation_type = fields.Selection(
        selection_add=[
            ('escalate_to_x', 'Approver → Time Off Officer → Escalation for Long Leaves')
        ], ondelete={'escalate_to_x': 'cascade'}
    )
    escalate_to_job_position_id = fields.Many2one('hr.job', string='Escalate To')
    approval_requirement_days = fields.Integer(
        string='Approval Requirement Days',
        help='If zero then Approval cycle will be applied in all time off requests.',
    )
    employee_type = fields.Selection(
        selection=[
            ('local', 'Local'),
            ('expat', 'Expat'),
        ],
        string='Employee Type',
        help='If left empty all employees can select this leave type.',
    )
    religion_id = fields.Many2one('hr.religion', string='Religion')
    is_attachment_mandatory = fields.Boolean(string='Attachment Mandatory')
    attachment_warning = fields.Text(string='Attachment Warning')
    requires_advance_notice = fields.Boolean(string='Requires Advance Notice')
    advance_number_of_days = fields.Integer(string='Advance Number of Days')
    allow_leave_extension = fields.Boolean(string='Allow Leave Extension')
    gender = fields.Selection(
        selection=[
            ('male', 'Male'),
            ('female', 'Female'),
        ],
        string='Gender',
        help='Gender of the leave. If left empty all employees can select this leave type.',
    )
    kuec_grade_id = fields.Many2one('kuec.grade', string='Grade',
                                    help='Grade of the leave requester. '
                                         'if left empty all employees can select this leave type.', )
    min_days_for_request = fields.Float(string='Minimum Days For Request',
                                        help="Minimum allowed number of days per single leave.")
    max_days_for_request = fields.Float(string='Maximum Days For Request',
                                        help="Maximum allowed number of days per single leave.")
    is_wfh = fields.Boolean(string='Is Work from Home')

    @api.model
    def default_get(self, default_fields):
        rec = super().default_get(default_fields)
        rec.update({
            'company_id': self.env.company.id
        })
        return rec

    @api.constrains('leave_validation_type', 'company_id')
    def _check_leave_validation_type(self):
        for record in self:
            if record.company_code not in [
                'KUEC'] and record.leave_validation_type == 'escalate_to_x':
                raise ValidationError(_(
                    "The selected leave approval policy is restricted to KUEC and cannot be used for other companies."
                ))

    @api.constrains('max_days_for_request', 'min_days_for_request')
    def _check_max_days_constraints(self):
        for record in self:
            if record.company_code in ['KUEC']:
                if record.min_days_for_request > 0 and 0 < record.max_days_for_request < record.min_days_for_request:
                    raise ValidationError(
                        _("Maximum Days For Request must be greater than or equal to Minimum Days For Request.")
                    )

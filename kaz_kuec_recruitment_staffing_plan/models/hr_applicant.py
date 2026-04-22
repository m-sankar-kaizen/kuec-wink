from odoo import models, fields, api


class HrApplications(models.Model):
    _inherit = 'hr.applicant'

    used_hiring_request_ids = fields.Many2many(
        'hr.recruitment.requests',
        compute='_compute_used_hiring_requests',
    )
    company_code = fields.Selection(related='company_id.company_code')

    @api.depends('approved_hiring_request_id')
    def _compute_used_hiring_requests(self):
        Model = self.env['hr.applicant']
        for rec in self:
            used = Model.search([
                ('approved_hiring_request_id', '!=', False),
                ('id', '!=', rec.id),
            ]).mapped('approved_hiring_request_id').ids
            rec.used_hiring_request_ids = [(6, 0, used)]

    job_position_id = fields.Many2one(
        'hr.job')
    approved_hiring_request_id = fields.Many2one(
        'hr.recruitment.requests',
        domain="[('id', 'not in', used_hiring_request_ids)]")

    def create_employee_from_applicant(self):
        res = super().create_employee_from_applicant()
        if res.get('res_id'):
            employee = self.env['hr.employee'].browse(res['res_id'])
            employee.hire_date = self.date_closed.date()
            employee.approved_hiring_request_id = self.approved_hiring_request_id.id
        return res

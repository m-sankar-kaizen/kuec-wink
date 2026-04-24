from odoo import models, fields, api
from odoo.exceptions import ValidationError

class KRA(models.Model):
    _name = 'kra.kra'
    _description = 'Key Result Area'

    name = fields.Char(required=True)
    description = fields.Text()
    department_id = fields.Many2one('hr.department', string='Department')
    kpi_id = fields.Many2many('kra.kpi', string='KPIs')  # New field to link KPI to a KRA
    job_id = fields.Many2one('hr.job', string='Job Position')
    is_department_wise = fields.Boolean(string='Department Wise', default=False)
    is_jobposition_wise = fields.Boolean(string='Job Position Wise', default=False)

    @api.onchange('is_department_wise')
    def _onchange_is_department_wise(self):
        if self.is_department_wise:
            self.is_jobposition_wise = False

    @api.onchange('is_jobposition_wise')
    def _onchange_is_jobposition_wise(self):
        if self.is_jobposition_wise:
            self.is_department_wise = False

    @api.constrains('is_department_wise', 'is_jobposition_wise', 'department_id', 'job_id', 'kpi_id')
    def _check_exclusive_flags_and_required_fields(self):
        for record in self:
            if not record.is_department_wise and not record.is_jobposition_wise:
                raise ValidationError("Please select at least one KRA type: either 'Department Wise' or 'Job Position Wise'.")
    
            # Ensure mutual exclusivity
            if record.is_department_wise and record.is_jobposition_wise:
                raise ValidationError("Only one of 'Department Wise' or 'Job Position Wise' can be selected.")

            # Ensure department_id is set if department-wise is True
            if record.is_department_wise and not record.department_id:
                raise ValidationError("Please select a Department when 'Department Wise' is enabled.")

            # Ensure job_id is set if job-wise is True
            if record.is_jobposition_wise and not record.job_id:
                raise ValidationError("Please select a Job Position when 'Job Position Wise' is enabled.")
            
            # Ensure at least one KPI is linked
            if not record.kpi_id:
                raise ValidationError("At least one KPI must be linked to the KRA.")


class KPI(models.Model):
    _name = 'kra.kpi'
    _description = 'Key Performance Indicator'

    name = fields.Char(required=True)
    description = fields.Text()
    rating = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent'),('6', 'Outstanding'),],string="Communication")
    

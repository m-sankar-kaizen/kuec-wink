from odoo import models, fields


class HrJob(models.Model):
    """
    Extension of the built-in hr.job model to include Arabic job position,
    job code, and associated HR grade.

    Fields:
        - employee_arabic_job_position (Char): Stores the job title in Arabic.
        - job_code (Char): Optional unique code representing the job.
        - grade_id (Many2one): Link to HR Grade that is in 'confirm' state only.
    """
    _inherit = 'hr.job'

    employee_arabic_job_position = fields.Char(
        string="Employee Arabic Job Position")
    job_code = fields.Char(
        string='Job Code',
        required=False,
    )
    grade_id = fields.Many2one('hr.grade',
                               domain="[('state', '=', 'confirm')]")

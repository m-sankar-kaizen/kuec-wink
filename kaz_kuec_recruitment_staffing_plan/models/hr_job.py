from odoo import models, fields


class HrJob(models.Model):
    _inherit = 'hr.job'

    request_id = fields.Many2one(
        'hr.job.position.request',
        readonly=True)

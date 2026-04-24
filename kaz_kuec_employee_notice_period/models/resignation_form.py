from odoo import models, fields, api
from datetime import timedelta


class ResignationForm(models.Model):
    _inherit = 'register.form'

    last_working_date = fields.Date(store=True,
                                    readonly=False,
                                    compute='_compute_last_working_date')

    @api.depends('name',
                 'name.contract_id',
                 'name.contract_id.notice_period',
                 'notify')
    def _compute_last_working_date(self):
        for record in self:
            if record.name and record.name.contract_id.notice_period:
                notice_period_days = record.name.contract_id.notice_period
                record.last_working_date = record.notify + timedelta(days=notice_period_days)
            else:
                record.last_working_date = False


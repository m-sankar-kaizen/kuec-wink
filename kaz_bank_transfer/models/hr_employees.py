from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    bank_transfer_history_ids = fields.One2many(
        'bank.transfer',
        'employee_id',
        string='Bank Transfer History')

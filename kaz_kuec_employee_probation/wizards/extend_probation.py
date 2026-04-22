from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ExtendProbation(models.Model):
    _name = 'extend.probation'
    _description = 'Extend Probation Wizard'

    employee_id = fields.Many2one('hr.employee',
                                  string='Employee')
    existing_date = fields.Date(string='Existing Probation End Date')
    new_date = fields.Date(string='New Probation End Date',
                           required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        readonly=True,
    )

    def action_confirm(self):
        self.ensure_one()
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if self.new_date and self.existing_date:
            extension_days = (self.new_date - self.existing_date).days
            if extension_days > self.company_id.maximum_probation_extension_period:
                raise ValidationError(
                    f"The extension period exceeds the maximum allowed "
                    f"of {self.company_id.maximum_probation_extension_period} days."
                )
        if not active_id or not active_model:
            return {'type': 'ir.actions.act_window_close'}
        record = self.env[active_model].browse(active_id).exists()
        if not record:
            return {'type': 'ir.actions.act_window_close'}
        record.write({
            'probation_end_date': self.new_date,
            'is_extended': True
        })
        return {'type': 'ir.actions.act_window_close'}

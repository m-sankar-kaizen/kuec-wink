# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ActingDelegationWizard(models.TransientModel):
    _name = 'acting.delegation.wizard'
    _description = 'Acting Delegation Prompt'

    leave_id = fields.Many2one('hr.leave', required=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    date_start = fields.Datetime(required=True)
    date_end = fields.Datetime(required=True)

    delegate_choice = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], required=True, default='no', string='Delegate Permissions?')

    acting_employee_id = fields.Many2one('hr.employee', string='Acting Employee')
    group_ids = fields.Many2many('res.groups', string='Delegated Groups')

    def action_submit(self):
        self.ensure_one()
        leave = self.leave_id
        if self.delegate_choice == 'no':
            leave.message_post(body=_('Employee chose not to delegate system permissions during leave.'))
            return {'type': 'ir.actions.act_window_close'}
        if not self.acting_employee_id:
            raise UserError(_('Please choose an acting employee.'))
        if not self.group_ids:
            raise UserError(_('Please select at least one group to delegate.'))
        # Create delegation record
        validation_type = self.env['ir.config_parameter'].sudo().get_param('hr_acting_delegation.validation_type', default='blocking')
        delegation = self.env['acting.delegation'].create({
            'leave_id': leave.id,
            'employee_id': self.employee_id.id,
            'acting_employee_id': self.acting_employee_id.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'group_ids': [(6, 0, self.group_ids.ids)],
            'validation_type': validation_type,
        })
        leave.message_post(body=_('Employee chose to delegate permissions to %s from %s to %s.') % (self.acting_employee_id.name, self.date_start, self.date_end))
        # Store link
        leave.write({'acting_delegation_id': delegation.id})
        return {'type': 'ir.actions.act_window_close'}

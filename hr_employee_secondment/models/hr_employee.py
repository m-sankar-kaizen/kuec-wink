# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    secondment_count = fields.Integer(
        string='Secondment Count',
        compute='_compute_secondment_count',
        help='Total number of secondments for this employee'
    )
    
    active_secondment_id = fields.Many2one(
        'hr.employee.secondment',
        string='Active Secondment',
        compute='_compute_active_secondment',
        help='Current active secondment if any'
    )
    
    has_active_secondment = fields.Boolean(
        string='Has Active Secondment',
        compute='_compute_active_secondment',
        help='Indicates if employee has an active secondment'
    )

    def _compute_secondment_count(self):
        """Count total secondments for this employee"""
        for employee in self:
            employee.secondment_count = self.env['hr.employee.secondment'].search_count([
                ('employee_id', '=', employee.id)
            ])
    
    def _compute_active_secondment(self):
        """Find active secondment for this employee"""
        for employee in self:
            active = self.env['hr.employee.secondment'].search([
                ('employee_id', '=', employee.id),
                ('state', '=', 'active')
            ], limit=1)
            employee.active_secondment_id = active.id if active else False
            employee.has_active_secondment = bool(active)
    
    def action_view_secondments(self):
        """View all secondments for this employee"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Secondments - %s' % self.name,
            'res_model': 'hr.employee.secondment',
            'domain': [('employee_id', '=', self.id)],
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {'default_employee_id': self.id}
        }

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrTravel(models.Model):
    _name = 'hr.travel'
    _description = 'HR Travel and Errand'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', readonly=True)
    grade_id = fields.Many2one('kuec.grade',
                               related='employee_id.kuec_grade_id',
                               string='Grade', tracking=True)
    travel_level = fields.Char(string='Travel Level', tracking=True)
    date_from = fields.Date(string='Travel From', required=True, tracking=True)
    date_to = fields.Date(string='Travel To', required=True, tracking=True)
    days_count = fields.Integer(string='Days',
                                compute='_compute_days_count',
                                store=True)
    destination = fields.Many2one('res.destination',
                                  string='Destination',
                                  required=True,
                                  tracking=True)
    purpose = fields.Text(string='Purpose', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    expense_ids = fields.Many2many('hr.expense', string='Expenses')
    expense_count = fields.Integer(string='Expenses',
                                   compute='_compute_expense_count', store=False)

    @api.depends('date_from', 'date_to')
    def _compute_days_count(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to >= rec.date_from:
                rec.days_count = (rec.date_to - rec.date_from).days + 1
            else:
                rec.days_count = 0

    @api.depends('expense_ids')
    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = len(rec.expense_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq = self.env['ir.sequence'].next_by_code('hr.travel')
            vals['name'] = seq or _('New')
        return super().create(vals)

    def action_confirm(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise UserError(_('Travel end date cannot be before start date.'))
            rec.state = 'confirmed'
        return True

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == 'cancelled':
                rec.state = 'draft'
        return True

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
        return True

    def action_done(self):
        for rec in self:
            rec.state = 'done'
        return True

    def action_create_expense(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_('You can only create an expense from a confirmed travel.'))
            if not rec.employee_id:
                raise UserError(_('Employee is required to create an expense.'))
            description_text = rec.purpose or rec.destination.name or ''
            expense_vals = {
                'name': _('Travel to %s') % (rec.destination.name or ''),
                'employee_id': rec.employee_id.id,
                'date': rec.date_from,
                'company_id': rec.company_id.id,
                # Odoo 18: use 'description' to store purpose or destination as notes
                'description': description_text,
            }
            # Remove empty description if field unsupported in current db schema
            if not description_text:
                expense_vals.pop('description')
            expense = self.env['hr.expense'].create(expense_vals)
            rec.expense_ids = [(4, expense.id)]
        return True

    def action_view_expense(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Expenses'),
            'res_model': 'hr.expense',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.expense_ids.ids)],
            'target': 'current',
        }

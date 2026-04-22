from odoo import models, fields, api,_
from odoo.exceptions import ValidationError


class Feedback360(models.Model):
    _name = 'hrms.feedback360'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '360 Feedback'

    name = fields.Char(string='Sequence',copy=False, readonly=True, default=lambda self: _('New'))
    performance_feedback_id = fields.Many2one('performance.feedback', string="Performance Feedback")
    evaluation_id = fields.Many2one('hrms.evaluation',string="Self Evaluation of Employee")
    employee_id = fields.Many2one('hr.employee','Employee')
    feedback_type = fields.Selection([
        ('peer', 'Peer'),
        ('subordinate', 'Subordinate'),
        ('manager', 'Manager'),
    ], string="Feedback Type")
    feedback_provider_id = fields.Many2one('hr.employee','Feedback Provider', default=lambda self: self._default_employee())
    rating = fields.Selection([('0', 'Nil'),('1', 'Poor'),('2', 'Average'),('3', 'Good'),('4', 'Very Good'),('5', 'Excellent')],string='Overall Rating')
    comment = fields.Text('Your Comment')
    suggestion = fields.Text('Your Suggestion')
    user_id = fields.Many2one('res.users',default=lambda self: self.env.uid)

    @api.onchange('evaluation_id')
    def _onchange_evaluation(self):
        if self.evaluation_id:
            self.employee_id = self.evaluation_id.employee_id.id

    def _default_employee(self):
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        if employee:
            return employee
        else:
            return False
        
    @api.constrains('feedback_provider_id', 'employee_id')
    def _check_feedback_provider_not_self(self):
        for rec in self:
            if rec.feedback_provider_id == rec.employee_id:
                raise ValidationError(_("Feedback provider and employee cannot be the same."))

        
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hrms.feedback360') or _('New')
        return super().create(vals_list)

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class GoldenVisaRequest(models.Model):
    _name = 'kuec.golden.visa.request'
    _description = "Golden Visa Request Letter"
    _inherit = ['mail.thread',
                'mail.activity.mixin']
    _rec_name = 'sequence'

    def get_default_employee(self):
        emp = self.env['hr.employee'].sudo().search([
            ('user_id', '=', self.env.user.id),
            ('company_id', '=', self.env.company.id)], limit=1)
        return emp.id

    employee_id = fields.Many2one('hr.employee',
                                  string='Employee',
                                  default=get_default_employee)
    date = fields.Date(string='Date',
                       default=fields.Date.today)
    emp_id = fields.Char(related='employee_id.sequence',
                         string='Employee ID')
    duration_service = fields.Float()
    total_monthly_salary = fields.Float()
    good_conduct_certificate = fields.Binary()
    position_id = fields.Many2one(related='employee_id.job_id',
                                  string='Position')
    department_id = fields.Many2one(related='employee_id.department_id',
                                    string='Department')
    hr_signature = fields.Image(
        string="HR Signature & Stamp",
        copy=False, attachment=True, max_width=1024, max_height=1024)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    ],
        default='draft',
        tracking=True,
        required=True)
    sequence = fields.Char(default="Draft",
                           readonly=True)
    justification = fields.Html(string="Justification")

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company.id,
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence') or vals['sequence'] == _('Draft'):
                vals['sequence'] = self.env[
                                       'ir.sequence'].next_by_code(
                    'kuec.golden.visa.request') or _('Draft')
        return super().create(vals_list)

    def action_submit(self):
        self.ensure_one()
        self.write({
            'state': 'submitted'
        })

    def action_reset(self):
        self.ensure_one()
        self.write({
            'state': 'draft'
        })

    def action_print(self):
        self.ensure_one()
        return self.env.ref(
            'kaz_kuec_letters.action_report_kuec_golden_visa_letter_report').report_action(
            self)



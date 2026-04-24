from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class KUECVisaRequest(models.Model):
    _name = 'kuec.visa.request'
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
    date = fields.Date(default=fields.Date.today())
    passport_number = fields.Char(
        related='employee_id.passport_id')
    country_id = fields.Many2one(
        string="Nationality",
        related='employee_id.country_id')
    emirates = fields.Char(
        related='employee_id.emirates')
    visa_type = fields.Selection([
        ('new', 'New'),
        ('renewal', 'Renewal'),
        ('family', 'Family'),
    ],
        default='new',
        tracking=True,
        required=True
    )
    purpose_of_visa = fields.Char()
    employment_duration = fields.Float()
    hr_signature = fields.Image(
        string="Signature",
        copy=False, attachment=True, max_width=1024, max_height=1024)
    company_id = fields.Many2one(
        'res.company',
        readonly=True,
        default=lambda self: self.env.company.id)
    stamp = fields.Binary(related='company_id.stamp')

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence') or vals['sequence'] == _('Draft'):
                vals[
                    'sequence'] = self.env[
                                       'ir.sequence'].next_by_code(
                    'kuec.visa.request') or _('Draft')
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
            'kaz_kuec_letters.action_report_visa_request_letter').report_action(
            self)





from odoo import models, fields, _, api
from odoo.exceptions import ValidationError


class HealthInsurance(models.Model):
    _name = 'kuec.health.insurance'
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
    emp_id = fields.Char(related='employee_id.sequence', string='Employee ID')
    position_id = fields.Many2one(related='employee_id.job_id',
                                  string='Position')
    department_id = fields.Many2one(related='employee_id.department_id',
                                    string='Department')
    email = fields.Char(related='employee_id.work_email', string='Email')
    mobile = fields.Char(related='employee_id.work_phone', string='Mobile')
    insurance_card_number = fields.Char('Insurance Card Number')
    insurance_provider_name = fields.Char('Insurance Provider Name')
    policy_validity_date = fields.Date(string='Policy Validity Date',
                                       default=fields.Date.today)
    coverage_level_local_international = fields.Selection([
        ('local', 'Local'),
        ('international', 'International'),
    ])

    coverage_level_individual_family = fields.Selection([
        ('individual', 'Individual'),
        ('family', 'Family'),
    ])

    all_children_ids = fields.Many2many('kids.details',
                                        compute='compute_all_childrens')

    @api.depends('employee_id',
                 'employee_id.kid_ids',
                 'employee_id.kid_ids.age_calc')
    def compute_all_childrens(self):
        for record in self:
            kids = record.employee_id.kid_ids.filtered(lambda x: x.age_calc <= 18)
            record.all_children_ids = kids.ids

    @api.constrains('children_ids')
    def _check_children_ids(self):
        for record in self:
            for child in record.children_ids:
                if child.age_calc > 18:
                    raise ValidationError(_(
                        "Child %s is older than 18 years and cannot be added."
                    ) % child.name)
            if len(record.children_ids) > 3:
                raise ValidationError(_(
                    "Maximum 3 children are allowed."
                ))

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        for rec in self:
            rec.children_ids = False
            rec.spouse = rec.employee_id.spouse_complete_name

    spouse = fields.Char(string="Spouse Name")

    children_ids = fields.Many2many('kids.details',
                                    domain="[('id', 'in', all_children_ids)]")

    policy_number = fields.Char()

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('sequence') or vals['sequence'] == _('Draft'):
                vals['sequence'] = self.env[
                                       'ir.sequence'].next_by_code(
                    'kuec.health.insurance.letter') or _('Draft')
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
            'kaz_kuec_letters.action_report_kuec_health_insurance_letter_report').report_action(
            self)

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SalaryLetter(models.Model):
    _name = 'kuec.salary.letter'
    _inherit = ['salary.letter',
                'mail.thread',
                'mail.activity.mixin']

    _rec_name = 'sequence'

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
                    'kuec.salary.letter') or _('Draft')
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

    def action_print_salary_letter(self):
        self.ensure_one()
        return self.env.ref(
            'kaz_kuec_letters.action_report_salary_letter_uae_xpat_report').report_action(
            self)

    def action_print_detailed_salary_letter(self):
        self.ensure_one()
        return self.env.ref(
            'kaz_kuec_letters.action_report_salary_detailed_letter_uae_xpat_report').report_action(
            self)

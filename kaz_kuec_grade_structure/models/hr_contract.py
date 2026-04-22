from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    company_code = fields.Selection(related='company_id.company_code')
    kuec_grade_id = fields.Many2one('kuec.grade',
                                    related="employee_id.kuec_grade_id",)
    min_basic_kuec = fields.Float(related='kuec_grade_id.min_basic_kuec',
                                  store=True)
    max_basic_kuec = fields.Float(related='kuec_grade_id.max_basic_kuec',
                                  store=True)

    @api.onchange('scale_basic')
    def onchange_scale_basic(self):
        for rec in self:
            if rec.company_code == 'KUEC' and rec.kuec_grade_id and rec.scale_basic != 0:
                if not (rec.min_basic_kuec <= rec.scale_basic <= rec.max_basic_kuec):
                    raise ValidationError(
                        "Scale basic for KUEC employees should"
                        " be between Min and Max scale of KUEC Employees.")
                else:
                    rec.write({'wage': rec.scale_basic})
                return

            if rec.company_code == 'ANK' and rec.grade_id:
                grade = rec.grade_id
                if not grade or rec.scale_basic <= 0:
                    continue
                scale_values = rec._get_scale_basic(grade)
                min_val = scale_values['min']
                mid_val = scale_values['mid']
                max_val = scale_values['max']

                # Assign wage directly from scale_basic
                rec.wage = rec.scale_basic

                # Validate scale_basic falls in allowed range
                if not (min_val <= rec.scale_basic <= max_val):
                    raise ValidationError(
                        _("The value of scale basic must be between {} and {}.").format(
                            min_val, max_val)
                    )
            if rec.company_code not in ['KUEC', 'ANK']:
                rec.wage = rec.scale_basic

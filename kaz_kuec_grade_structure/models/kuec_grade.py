from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KUECGrade(models.Model):
    _name = 'kuec.grade'
    _description = 'KUEC Grade Structure'

    name = fields.Char(required=True)
    kuec_grade_structure_ids = fields.Many2many(
        'hr.payroll.structure',
        string="Grade Structures"
    )

    def get_default_sequence(self):
        """
        Compute the default grade sequence per company.

        Sequence is incremented based on the highest
        existing grade sequence within the same company.
        """
        company = self.env.company
        last = self.search(
            [('company_id', '=', company.id)],
            order='sequence desc',
            limit=1
        )
        return (last.sequence or 0) + 1 if last else 1

    sequence = fields.Integer(default=get_default_sequence)
    min_basic_kuec = fields.Float(
        string='Minimum Basic')
    mid_basic_kuec = fields.Float(
        string='Medium Basic')
    max_basic_kuec = fields.Float(
        string='Maximum Basic')
    is_education_allowance = fields.Boolean()
    per_child_allowance = fields.Float(
        string="Per Child Allowance",
        help="Maximum allowance amount that can be reimbursed per child."
    )
    reimbursement_limit = fields.Float(
        string="Reimbursement Limit",
        help="Maximum total reimbursement amount allowed "
             "for the employee in one academic year."
    )
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company,
                                 readonly=True)

    ticket_type_id = fields.Many2one(
        'ticket.type',
        string='Ticket Type',
        help="Defines the travel ticket type assigned "
             "to this grade (e.g., Economy, Business)."
    )
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    living_allowance = fields.Monetary(string="Living Allowance", currency_field='currency_id')
    vacation_allowance = fields.Monetary(string="Vacation Allowance", currency_field='currency_id')
    connectivity_allowance = fields.Monetary(string="Connectivity Allowance", currency_field='currency_id')
    personal_allowance = fields.Monetary(string="Personal Allowance", currency_field='currency_id')
    premium_allowance = fields.Monetary(string="Premium Allowance", currency_field='currency_id')
    child_allowance = fields.Monetary(string="Child Allowance", currency_field='currency_id')

    # @api.onchange('scale_basic')
    # def onchange_scale_basic(self):
    #     for rec in self:
    #         if rec.company_id.company_code == 'KUEC':
    #             if not (
    #                     rec.min_basic_kuec <= rec.scale_basic <= rec.max_basic_kuec):
    #                 raise ValidationError(
    #                     "Scale basic for KUEC employees should"
    #                     " be between Min and Max scale of KUEC Employees.")
    #             else:
    #                 rec.write({'wage': rec.scale_basic})
    #             return
    #     return super().onchange_scale_basic()

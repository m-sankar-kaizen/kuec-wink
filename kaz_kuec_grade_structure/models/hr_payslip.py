from odoo import models, fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    kuec_grade_id = fields.Many2one('kuec.grade',
                                    store=True,
                                    related='contract_id.kuec_grade_id')
    kuec_grade_structure_ids = fields.Many2many(
        'hr.payroll.structure', 'payslip_kuec_structure_rel',
        'payslip_id', 'kuec_structure_id',
        string="Grade Structure (KUEC)",
        related='kuec_grade_id.kuec_grade_structure_ids')

    def _return_kuec_domain(self):
        if self.kuec_grade_structure_ids:
            return [('id', 'in', self.kuec_grade_structure_ids.ids)]
        else:
            all_domain = self.env['hr.payroll.structure'].sudo().search([])
            return [('id', 'in', all_domain.ids)]

    struct_id = fields.Many2one('hr.payroll.structure',
                                string='Salary Structure',
                                domain=_return_kuec_domain,
                                compute='_compute_struct_id',
                                readonly=False, store=True)

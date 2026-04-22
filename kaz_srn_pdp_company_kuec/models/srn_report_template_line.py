# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SRNReportTemplateLine(models.Model):
    _name = 'srn.report.template.line'
    _description = 'SRN Report Template Line'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    company_code = fields.Selection(related='company_id.company_code')
    sequence = fields.Integer('Sequence')
    srn_report_template_id = fields.Many2one('srn.report.template', 'SRN Report Template')
    answer_selection_ids = fields.Many2many('answer.selection', string='Answers')

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-increment sequence within the same company, safe for batch creation."""
        sequence_cache = {}

        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id
            # Initialize cache entry if not present
            if company_id not in sequence_cache:
                # Fetch latest sequence for this company
                last_record = self.sudo().search(
                    [('company_id', '=', company_id),
                     ('srn_report_template_id', '=', vals.get('srn_report_template_id'))],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

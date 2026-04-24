# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorEvaluationConf(models.Model):
    _name = 'vendor.evaluation.conf'
    _description = 'Vendor Evaluation Conf'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    evaluation_conf_line_ids = fields.One2many('vendor.evaluation.conf.line', 'evaluation_conf_id')
    total_weight = fields.Integer(string='Total Weight', compute='_compute_total_weight')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
        ],
        default='draft',
        string='State',
        required=True,
        tracking=True,
    )

    def action_activate(self):
        if self.total_weight != 100:
            raise ValidationError(
                _("The total weight must be exactly 100. Please re-distribute the checklist line weights.")
            )
        self.state = 'active'

    def action_reset_to_draft(self):
        self.state = 'draft'

    @api.depends('evaluation_conf_line_ids', 'evaluation_conf_line_ids.weight')
    def _compute_total_weight(self):
        for conf in self:
            conf.total_weight = sum(conf.evaluation_conf_line_ids.mapped('weight'))

    @api.constrains('evaluation_conf_line_ids', 'evaluation_conf_line_ids.weight')
    def _check_total_weight(self):
        for rec in self:
            if rec.total_weight > 100:
                raise ValidationError(
                    _("The total weight of all checklist lines cannot exceed 100%.")
                )

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
                    [('company_id', '=', company_id)],
                    order='sequence desc',
                    limit=1
                )
                last_sequence = last_record.sequence if last_record else 0
                sequence_cache[company_id] = last_sequence

            # Increment cached sequence and assign it
            sequence_cache[company_id] += 1
            vals['sequence'] = sequence_cache[company_id]

        return super().create(vals_list)

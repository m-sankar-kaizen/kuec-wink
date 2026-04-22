# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PurchaseRequisitionType(models.Model):
    _name = 'purchase.requisition.type'
    _description = 'Purchase Requisition Type'
    _check_company_auto = True

    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, required=True)
    sequence = fields.Integer(string='Sequence')
    value_min = fields.Float(string="Minimum Value")
    value_max = fields.Float(string="Maximum Value")

    def _get_default_justification_required(self):
        """Can be inherited to modify the intention if needed."""
        return True

    is_justification_required = fields.Boolean(string="Justification Required",
                                               default=_get_default_justification_required)
    is_tender = fields.Boolean(string="Tender", help="Whether this type is a tender or not")
    min_bids = fields.Integer(string="Minimum Bids")
    max_bids = fields.Integer(string="Maximum Bids")
    requisition_type = fields.Selection(
        [
            ('standard', 'Standard'),
            ('repeated', 'Repeated'),
            ('variation', 'Variation'),
        ],
        string='Requisition Type', default='standard'
    )
    repeat_max_days = fields.Integer(string="Max Days for Repeat", default=60)
    variation_max_percent = fields.Float(string="Max Variation Percentage")
    rq_type_attachment_line_ids = fields.One2many('rq.type.attachment.line', 'requirement_type_id',
                                                  string="Requisition Type Attachment Line")
    allowed_user_ids = fields.Many2many('res.users', string="Allowed Users")

    @api.constrains('requisition_type', 'variation_max_percent', 'repeat_max_days')
    def _check_requisition_type(self):
        for record in self:
            # if record.requisition_type == "variation" and record.variation_max_percent <= 0:
            #     raise ValidationError(_("Max Variation Percentage must be greater than 0"))
            if record.requisition_type == "repeated" and record.repeat_max_days <= 0:
                raise ValidationError(_("Max Days for Repeat must be greater than 0"))

    @api.constrains('value_min', 'value_max')
    def _check_min_max_value(self):
        for record in self:
            if record.value_min <= 0:
                raise ValidationError(_("Minimum Value must be greater than 0"))
            if record.value_max < 0:
                raise ValidationError(_("Maximum Value must be greater than or equal to 0"))
            if 0 < record.value_max < record.value_min:
                raise ValidationError(_("Minimum Value must be less than Maximum value"))

    @api.constrains('min_bids', 'max_bids')
    def _check_min_max_rfqs(self):
        for record in self:
            if record.is_tender:
                if record.min_bids <= 0:
                    raise ValidationError(_("Minimum Bids must be greater than 0"))
                    # Only check max_bids if it is 1 or more
                    if record.max_bids and record.max_bids >= 1 and record.min_bids > record.max_bids:
                        raise ValidationError(
                            _("Minimum Bids must be less than or equal to Maximum Bids")
                        )

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-increment sequence within the same company, safe for batch creation."""
        sequence_cache = {}

        for vals in vals_list:
            company_id = vals.get('company_id') or self.env.company.id

            # Skip if sequence is already provided manually
            if 'sequence' in vals:
                continue

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

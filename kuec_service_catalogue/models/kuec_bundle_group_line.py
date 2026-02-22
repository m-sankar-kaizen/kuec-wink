# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class KuecBundleGroupLine(models.Model):
    _name = 'kuec.bundle.group.line'
    _description = 'WINK Bundle Tier Line'
    _order = 'sequence asc'

    bundle_group_id = fields.Many2one(
        'kuec.bundle.group', 
        required=True, 
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    label = fields.Char(required=True)
    product_tmpl_id = fields.Many2one(
        'product.template',
        required=True,
        domain=[
            ('available_on_wink', '=', True),
            ('commercial_structure', '=', 'bundled')
        ]
    )
    combo_id = fields.Many2one(
        'product.combo',
        required=True
    )

    @api.constrains('sequence', 'bundle_group_id')
    def _check_unique_sequence(self):
        for line in self:
            count = self.search_count([
                ('bundle_group_id', '=', line.bundle_group_id.id),
                ('sequence', '=', line.sequence),
                ('id', '!=', line.id)
            ])
            if count > 0:
                raise ValidationError(
                    "Sequence %s is already used in this bundle group. Each tier must have a unique sequence." % line.sequence
                )

    @api.constrains('combo_id')
    def _check_standalone_in_combo(self):
        for line in self:
            if not line.combo_id:
                continue
            for item in line.combo_id.combo_item_ids:
                if item.product_id.product_tmpl_id.commercial_structure == 'standalone':
                    raise ValidationError(
                        "Bundle '%(combo)s' contains '%(product)s' which is Standalone Only and cannot be included in a bundle." % {
                            'combo': line.combo_id.name,
                            'product': item.product_id.name
                        }
                    )

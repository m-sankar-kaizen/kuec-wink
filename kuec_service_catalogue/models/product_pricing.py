# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductPricing(models.Model):
    _inherit = 'product.pricing'

    kuec_plan_features = fields.Text(
        string='Plan Features (one per line)',
        help='Enter one feature per line. Each line becomes a bullet point in the customer portal.'
    )
    kuec_is_most_popular = fields.Boolean(
        string='Most Popular',
        default=False,
        help='Check on exactly one plan per product to show the "Most Popular" badge in the portal.'
    )

    @api.constrains('kuec_is_most_popular')
    def _check_only_one_most_popular_per_product(self):
        for rec in self:
            if not rec.kuec_is_most_popular:
                continue
            product_field = 'product_template_id' if 'product_template_id' in rec._fields else 'product_tmpl_id'
            product_id = getattr(rec, product_field, None)
            if not product_id:
                continue
            domain = [(product_field, '=', product_id.id), ('kuec_is_most_popular', '=', True)]
            count = self.search_count(domain)
            if count > 1:
                raise ValidationError(
                    'Only one plan can be marked as Most Popular per service.'
                )

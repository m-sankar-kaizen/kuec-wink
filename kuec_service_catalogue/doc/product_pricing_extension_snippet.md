# Optional: Extend product.pricing (Plan Features & Most Popular)

Use this only when your Odoo instance has the `product.pricing` model in the registry (e.g. from the Subscription app). If you get **"Model 'product.pricing' does not exist in registry"**, do **not** add this; the main catalogue works without it (plans just won’t have features list or “Most Popular” badge).

## 1. New addon that depends on the module providing product.pricing

Create a separate addon (e.g. `kuec_service_catalogue_subscription`) with:

**`__manifest__.py`**
```python
{
    'name': 'KUEC Service Catalogue — Subscription Plan Fields',
    'version': '18.0.1.0.0',
    'depends': ['kuec_service_catalogue', 'sale_subscription'],  # or the app that provides product.pricing
    'data': ['views/product_pricing_views.xml'],
    'installable': True,
}
```

**`models/product_pricing.py`**
```python
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
            if self.search_count(domain) > 1:
                raise ValidationError('Only one plan can be marked as Most Popular per service.')
```

**`views/product_pricing_views.xml`**  
Form view for `product.pricing` with fields `kuec_is_most_popular` and `kuec_plan_features` (and standard fields like `recurrence_id`, `price`; use `product_tmpl_id` or `product_template_id` depending on your Odoo version).

## 2. Install only when product.pricing exists

Install this addon only on instances where the Subscription app (or the module that defines `product.pricing`) is installed. Do **not** install it on databases where that model is not in the registry.

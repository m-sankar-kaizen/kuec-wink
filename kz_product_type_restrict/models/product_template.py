# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """
    Inherits the `product.template` model to enforce a constraint on allowed product types.

    This customization ensures that only products of type 'Consumable' (`consu`)
    or 'Service' (`service`) can be created or saved in the system.

    Prevents users from accidentally or intentionally creating products of type
    'Stockable Product' (`product`) or any other unsupported type for the specific
    business use case.

    Use Case:
    - Organizations that do not manage inventory or wish to restrict product types
      to service-based or non-stockable consumables.
    """

    _inherit = 'product.template'

    @api.constrains('type')
    def restrict_type(self):
        """
        Constraint method to validate that the product's `type` is either
        'consu' (Consumable) or 'service'.

        Raises:
            ValidationError: If the type is not in the allowed list.

        Allowed Values:
            - 'consu': Consumable
            - 'service': Service

        Disallowed Values (will raise error):
            - 'product': Stockable Product
            - 'event': Event Product (if enabled in enterprise)
            - 'none': Undefined (rare use case)

        Example Error Message:
            "Can not create a product which type is not service or consumable"
        """
        for rec in self:
            if rec.type not in ['consu', 'service']:
                raise ValidationError(
                    _('Can not create a product which type is not service or consumable')
                )

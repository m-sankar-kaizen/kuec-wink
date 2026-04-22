# -*- coding: utf-8 -*-
from odoo import models, fields, api


class MaterialPurchaseRequisitionLine(models.Model):
    """
    Model: material.purchase.requisition.line

    Represents individual product lines within a material purchase requisition (`material.purchase.requisition`).

    Each line describes a product to be either purchased from a vendor or transferred internally,
    along with relevant details such as quantity, unit of measure, and vendor options.

    Fields:
        - requisition_id: Link to the parent requisition.
        - product_id: The product being requested.
        - description: A textual description of the product (usually auto-filled from product name).
        - qty: Quantity requested.
        - uom: Unit of measure for the product (auto-filled from product).
        - partner_id: One or more vendors suggested for this line.
        - requisition_type: Whether the line should be fulfilled via internal transfer or purchase order.

    Features:
        - Automatically sets product description and unit of measure when a product is selected.
        - Supports multiple vendors per line.
    """
    _name = "material.purchase.requisition.line"
    _description = 'Material Purchase Requisition Lines'

    requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisitions',
        help="The parent material requisition this line belongs to."
    )

    company_id = fields.Many2one(related='requisition_id.company_id', string='Company', store=True)

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        help="Select the product to request in this line."
    )

    description = fields.Char(
        string='Description',
        required=True,
        help="Free-text description of the product. Automatically filled based on selected product."
    )

    qty = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
        help="Quantity of the product being requested."
    )

    uom = fields.Many2one(
        'uom.uom',  # Was `product.uom` in Odoo 11
        string='Unit of Measure',
        required=True,
        help="Unit of measure for the product (auto-fills from product's purchase UoM)."
    )

    partner_id = fields.Many2many(
        'res.partner',
        string='Vendors',
        help="Suggested or approved vendors for this line. Can be one or more."
    )

    requisition_type = fields.Selection(
        selection=[
            ('internal', 'Internal Picking'),
            ('purchase', 'Purchase Order')
        ],
        string='Requisition Action',
        default='purchase',
        required=True,
        help="Specifies whether this line will be fulfilled via internal stock transfer or by issuing a purchase order."
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        """
        Onchange handler for product_id.

        - Automatically sets the description field to the product's display name.
        - Automatically sets the unit of measure field to the product's default UoM.

        This ensures consistency between the selected product and the line details.
        """
        for rec in self:
            if rec.product_id:
                # Fill description from the product's display name
                rec.description = rec.product_id.display_name
                # Set default unit of measure from product's purchase UoM
                rec.uom = rec.product_id.uom_id.id

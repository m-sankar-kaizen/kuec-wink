# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class VendorRequisitionWizard(models.TransientModel):
    """
    Wizard to select vendors for a purchase requisition and generate corresponding purchase orders.

    Fields:
        vendor_ids (Many2many): List of selected vendors (res.partner) for the requisition.
        requisition_id (Many2one): Reference to the related material.purchase.requisition.

    Methods:
        default_get(fields_list):
            Automatically sets the default requisition_id from the active context if available.

        apply_vendors():
            Main logic to:
            - Validate requisition and vendor selection.
            - Create purchase orders for each selected vendor.
            - Create purchase order lines for the requisition lines of type 'purchase'.
            - Update the requisition with new purchase orders and vendors.
            - Change requisition state to 'stock' and approval state to 'completed'.
    """

    _name = "vendor.requisition.wizard"
    _description = "Wizard for Vendor Selection in Requisition"

    vendor_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Vendors",
        required=True,
        help="Select one or more vendors to create purchase orders."
    )

    requisition_id = fields.Many2one(
        comodel_name="material.purchase.requisition",
        string="Requisition",
        required=True,
        help="Reference to the purchase requisition to apply vendor selections."
    )

    @api.model
    def default_get(self, fields_list):
        """
        Override default_get to set the requisition_id field automatically
        from the active_id in context when called from a requisition form or list view.

        Args:
            fields_list (list): List of fields to get defaults for.

        Returns:
            dict: Dictionary of default values for the wizard fields.
        """
        defaults = super(VendorRequisitionWizard, self).default_get(fields_list)
        if self.env.context.get('active_model') == 'material.purchase.requisition' and self.env.context.get('active_id'):
            defaults['requisition_id'] = self.env.context['active_id']
        return defaults

    def apply_vendors(self):
        """
        Apply the selected vendors to the requisition by creating purchase orders.

        Steps:
            - Validate that requisition and vendors are selected.
            - For each vendor, create a purchase order linked to the requisition.
            - For each requisition line of type 'purchase', create corresponding purchase order lines.
            - Update requisition's purchase_ids and purchase_vendor_ids with new entries.
            - Call onchange method to update any dependent fields on requisition.
            - Update requisition state to 'stock' and approvement_state to 'completed'.

        Raises:
            ValidationError: If requisition is missing or no vendors selected.

        Returns:
            True on successful processing.
        """
        self.ensure_one()

        # Validate requisition presence
        requisition = self.requisition_id
        if not requisition:
            raise ValidationError(_("Requisition not found."))

        # Validate vendor selection
        if not self.vendor_ids:
            raise ValidationError(_("You must select at least one vendor."))

        # Track created purchase orders and vendor mapping
        purchase_orders = requisition.purchase_ids.ids or []
        po_dict = {}

        for vendor in self.vendor_ids:
            if vendor not in po_dict:
                # Prepare purchase order values including linked requisition and attachments
                po_vals = {
                    'partner_id': vendor.id,
                    'currency_id': requisition.currency_id.id,
                    'purchase_manual_currency_rate_active': requisition.purchase_manual_currency_rate_active,
                    'purchase_manual_currency_rate': requisition.purchase_manual_currency_rate,
                    'date_order': fields.Date.today(),
                    'company_id': requisition.company_id.id,
                    'scope_of_work_attacchment_ids': requisition.attacchment_ids.ids,
                    'shareholders_attacchment_ids': requisition.shareholders_attacchment_ids.ids,
                    'board_attacchment_ids': requisition.board_attacchment_ids.ids,
                    'custom_requisition_id': requisition.id,
                    'origin': requisition.name,
                }

                # Create purchase order
                purchase_order = self.env['purchase.order'].create(po_vals)
                purchase_orders.append(purchase_order.id)
                po_dict[vendor] = purchase_order

            # Create purchase order lines for requisition lines of type 'purchase'
            for line in requisition.requisition_line_ids.filtered(lambda l: l.requisition_type == 'purchase'):
                po_line_vals = requisition.with_context(partner_id=vendor.id)._prepare_po_line(line, po_dict[vendor])
                self.env['purchase.order.line'].sudo().create(po_line_vals)

        # Update requisition's purchase orders and vendors
        requisition.purchase_ids = [(6, 0, purchase_orders)]
        existing_vendors = requisition.purchase_vendor_ids.ids or []
        requisition.purchase_vendor_ids = [(6, 0, list(set(existing_vendors + self.vendor_ids.ids)))]

        # Trigger onchange methods and update requisition states
        requisition._onchange_purchase_vendor()
        requisition.state = 'stock'
        requisition.approvement_state = 'completed'

        return True

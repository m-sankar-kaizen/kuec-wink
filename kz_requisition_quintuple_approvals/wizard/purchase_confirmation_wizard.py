# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseConfirmationWizard(models.TransientModel):
    """
    Transient model to handle the confirmation process for purchase requisitions and orders.

    This wizard allows the user to either approve or reject a requisition linked to a purchase order.
    In case of approval with modifications, it creates a copy of the existing requisition, marks
    the original as canceled, and links the new requisition to the purchase order for resubmission workflow.

    Attributes:
        requisition_id (Many2one): Reference to the material.purchase.requisition record.
        purchase_id (Many2one): Reference to the purchase.order record.
        mode (Selection): The action mode for the wizard - either 'approve' or 'reject'.
        message (Text): Optional message provided during confirmation.

    Methods:
        confirm():
            Executes the confirmation logic based on the current wizard's requisition and purchase order.
            If both are set, duplicates the requisition, cancels the original, updates linkage fields,
            and triggers recalculation/update on the new requisition for resubmission handling.
    """

    _name = 'purchase.confirmation.wizard'
    _description = 'Purchase Confirmation Wizard'

    requisition_id = fields.Many2one(
        comodel_name='material.purchase.requisition',
        string='Requisition',
        required=False,
        help="Reference to the purchase requisition to be confirmed or rejected.")

    purchase_id = fields.Many2one(
        comodel_name='purchase.order',
        string='Purchase',
        required=False,
        help="Reference to the related purchase order.")

    mode = fields.Selection(
        string='Mode',
        selection=[('reject', 'Reject'),
                   ('approve', 'Approve')],
        required=False,
        help="Action mode to either approve or reject the requisition.")

    message = fields.Text(
        string="Message",
        required=False,
        help="Optional message related to the confirmation or rejection.")

    def confirm(self):
        """
        Confirm the purchase requisition related to the purchase order.

        If both requisition and purchase order are set:
        - Creates a copy of the requisition for resubmission with the prefix 'EB/' in the name.
        - Cancels the original requisition.
        - Sets linkage fields between the original and new requisitions, and the purchase order.
        - Calls 'prepare_compare_quantities' on the purchase order to get quantity comparison data.
        - Calls 'update_after_resubmission' on the new requisition passing the comparison data for further update logic.
        - Updates purchase order and requisition references to maintain the resubmission workflow linkage.

        This method supports workflows where a requisition needs modification or re-approval
        before the purchase order can proceed.
        """
        if self.requisition_id and self.purchase_id:
            new_requisition = self.requisition_id.copy()
            self.requisition_id.cancel()
            new_requisition.name = "EB/" + new_requisition.name
            self.purchase_id.replaced_requisition_id = new_requisition.id
            # self.purchase_id.button_cancel()  # Currently commented out, possibly for manual cancellation
            self.requisition_id.resubmitted_requisition_id = new_requisition.id
            new_requisition.resubmitted_original_requisition_id = self.requisition_id.id

            compare_list = self.purchase_id.prepare_compare_quantities()
            new_requisition.update_after_resunbmission(compare_list)
            new_requisition.purchase_ids = self.requisition_id.purchase_ids.ids or []
            self.purchase_id.custom_requisition_id = new_requisition.id

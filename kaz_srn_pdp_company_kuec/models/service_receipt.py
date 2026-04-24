# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ServiceReceipt(models.Model):
    _inherit = 'service.receipt'

    company_code = fields.Selection(related="company_id.company_code", string="Company Code")

    # def service_button_validate(self):
    #     """
    #     Validate the receipt:
    #         - Ensures required signatures exist
    #         - Handles backorder conditions via pre-hooks
    #         - Sets date_done and transitions state to done
    #
    #     Returns:
    #         True if validation passes or a wizard if backorder is required.
    #     """
    #     if self.company_code not in ['KUEC']:
    #         self.check_signature()
    #
    #     self.date_done = fields.Datetime.today()
    #     for line in self.service_receipt_line_ids:
    #         if line.quantity_done == 0.0:
    #             line.quantity_done = line.product_uom_qty
    #     if not self.env.context.get('button_validate_service_ids'):
    #         self = self.with_context(button_validate_service_ids=self.ids)
    #     res = self._pre_service_action_done_hook()
    #     if res is not True:
    #         return res
    #     pickings_not_to_backorder = self.filtered(lambda p: p.create_backorder == 'never')
    #     if self.env.context.get('picking_ids_not_to_backorder'):
    #         pickings_not_to_backorder |= self.browse(
    #             self.env.context['picking_ids_not_to_backorder']).filtered(
    #             lambda p: p.create_backorder != 'always'
    #         )
    #     pickings_to_backorder = self - pickings_not_to_backorder
    #     pickings_not_to_backorder.with_context(cancel_backorder=True).service_action_done()
    #     pickings_to_backorder.with_context(cancel_backorder=False).service_action_done()
    #     return True


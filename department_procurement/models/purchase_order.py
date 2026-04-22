from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super().button_confirm()
        lines = self.order_line
        for line in lines:
            if line.related_department_procurement_plan_items_id:
                plan_line = line.related_department_procurement_plan_items_id
                difference = line.product_qty - plan_line.approved_planned_quantity
                if difference > 0:
                    deviation_status = 'over'
                elif difference < 0:
                    deviation_status = "under"
                else:
                    deviation_status = "on_target"
                plan_line.write({
                    'actual_purchased_qty': line.product_qty,
                    'actual_purchase_price': line.price_unit,
                    'qty_deviation': plan_line.approved_planned_quantity - line.product_qty,
                    'cost_deviation': plan_line.planned_cost - line.price_unit,
                    'execution_rate': (line.product_qty / plan_line.approved_planned_quantity)*100,
                    'deviation_status': deviation_status,
                })
        return res


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    related_department_procurement_plan_items_id = fields.Many2one(
        'annual.department.procurement.plan.items', string="Master Plan Ref")

    master_plan_status = fields.Selection(
        related='related_department_procurement_plan_items_id.master_plan_status')

    department_procurement_plan_items_status = fields.Selection(
        related='related_department_procurement_plan_items_id.status')

    @api.onchange('related_department_procurement_plan_items_id')
    def onchange_related_department_procurement_plan_items_id(self):
        self.ensure_one()
        self.product_id = self.related_department_procurement_plan_items_id.product_id.id

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        lines = self.invoice_line_ids
        for line in lines:
            if line.related_department_procurement_plan_items_id:
                plan_line = line.related_department_procurement_plan_items_id
                difference = line.quantity - plan_line.planned_quantity
                if difference > 0:
                    deviation_status = 'over'
                elif difference < 0:
                    deviation_status = "under"
                else:
                    deviation_status = "on_target"
                plan_line.write({
                    'actual_bill_qty': line.quantity,
                    'actual_bill_price': line.price_unit,
                    'qty_deviation': plan_line.planned_quantity - line.quantity,
                    'cost_deviation': plan_line.planned_cost - line.price_unit,
                    'execution_rate': (line.quantity / plan_line.planned_quantity) * 100,
                    'deviation_status': deviation_status,
                })
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    related_department_procurement_plan_items_id = fields.Many2one(
        'annual.department.procurement.plan.items', string="Master Plan Ref")

    @api.onchange('related_department_procurement_plan_items_id')
    def onchange_related_department_procurement_plan_items_id(self):
        self.ensure_one()
        self.product_id = self.related_department_procurement_plan_items_id.product_id.id

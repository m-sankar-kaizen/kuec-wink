from odoo import models, fields, api


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    warning_field = fields.Html(compute='_compute_warning_field',
                                string="Warning")
    company_code = fields.Selection(related='company_id.company_code',
                                    store=True,
                                    string="Company Code")

    @api.depends('requisition_line_ids',
                 'requisition_line_ids.related_department_procurement_plan_items_id')
    def _compute_warning_field(self):
        for rec in self:
            total = 0
            master_total = 0
            qty = 0
            master_qty = 0
            rec.warning_field = ''
            for line in rec.requisition_line_ids:
                if line.related_department_procurement_plan_items_id:
                    master_total += line.related_department_procurement_plan_items_id.sub_total
                    master_qty += line.related_department_procurement_plan_items_id.planned_quantity
                    qty += line.qty
                    total += line.subtotal
                    if total > master_total or qty > master_qty:
                        rec.warning_field = "<div class='alert alert-warning'>Warning: The total amount/ quantity of this purchase requisition exceeds the total amount/ quantity allocated in the master procurement plan.</div>"

    def action_approve_kuec_pr(self):
        res = super().action_approve_kuec_pr()
        if self.approvement_state == 'approved':
            lines = self.requisition_line_ids
            for line in lines:
                if line.related_department_procurement_plan_items_id:
                    plan_line = line.related_department_procurement_plan_items_id
                    difference = line.qty - plan_line.approved_planned_quantity
                    if difference > 0:
                        deviation_status = 'over'
                    elif difference < 0:
                        deviation_status = "under"
                    else:
                        deviation_status = "on_target"
                    plan_line.write({
                        'actual_requisition_qty': line.qty,
                        'actual_requisition_price': line.price_unit,
                        'qty_deviation': plan_line.approved_planned_quantity - line.qty,
                        'cost_deviation': plan_line.planned_cost - line.price_unit,
                        'execution_rate': (line.qty / plan_line.approved_planned_quantity) * 100 if plan_line.approved_planned_quantity > 0 else 0,
                        'deviation_status': deviation_status,
                    })
        return res

    def button_approve(self):
        res = super().button_approve()
        if self.approvement_state == 'approved':
            lines = self.requisition_line_ids
            for line in lines:
                if line.related_department_procurement_plan_items_id:
                    plan_line = line.related_department_procurement_plan_items_id
                    difference = line.qty - plan_line.approved_planned_quantity
                    if difference > 0:
                        deviation_status = 'over'
                    elif difference < 0:
                        deviation_status = "under"
                    else:
                        deviation_status = "on_target"
                    plan_line.write({
                        'actual_requisition_qty': line.qty,
                        'actual_requisition_price': line.price_unit,
                        'qty_deviation': plan_line.approved_planned_quantity - line.qty,
                        'cost_deviation': plan_line.planned_cost - line.price_unit,
                        'execution_rate': (line.qty / plan_line.approved_planned_quantity) * 100,
                        'deviation_status': deviation_status,
                    })
        return res


class MaterialPurchaseRequisitionLine(models.Model):
    _inherit = 'material.purchase.requisition.line'

    company_code = fields.Selection(related='company_id.company_code',
                                    store=True,
                                    string="Company Code")

    in_master_plan = fields.Selection(selection=[('yes', 'Yes'), ('no', 'No')], string="In Master Plan?")

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

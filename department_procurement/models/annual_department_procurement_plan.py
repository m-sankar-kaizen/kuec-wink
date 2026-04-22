# -*- coding: utf-8 -*-
from odoo import models, fields, api
from markupsafe import Markup
from odoo.exceptions import ValidationError


class AnnualDepartmentProcurementPlan(models.Model):
    """
    Annual Department Procurement Model
    """
    _name = 'annual.department.procurement.plan'
    _description = 'Annual Department Procurement Plan'
    _inherit = "mail.thread", "mail.activity.mixin"
    _check_company_auto = True
    _order = 'id desc'

    @api.model
    def _default_employee_id(self):
        """
        Get default Employee
        :return:
        """
        return self.env.user.employee_id

    @api.model
    def _default_department_id(self):
        """
        Get default Department
        :return:
        """
        return self.env.user.employee_id.department_id

    name = fields.Char(required=True)
    employee_id = fields.Many2one('hr.employee',
                                  string="Department Manager",
                                  default=_default_employee_id,
                                  check_company=True,
                                  tracking=True)
    department_id = fields.Many2one('hr.department',
                                    tracking=True,
                                    default=_default_department_id)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        self.department_id = self.employee_id.department_id.id

    date_start = fields.Date(tracking=True,
                             related="master_plan_id.date_start",
                             string="Start Date")
    date = fields.Date(tracking=True,
                       related="master_plan_id.date",
                       string="End Date")
    company_id = fields.Many2one('res.company',
                                 readonly=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  related="company_id.currency_id")
    active = fields.Boolean(default=True)

    planned_item_ids = fields.One2many(
        'annual.department.procurement.plan.items',
        'plan_id')
    notes = fields.Html()
    master_plan_id = fields.Many2one(
        'procurement.master.plan')
    master_plan_status = fields.Selection(
        related='master_plan_id.status')

    status = fields.Selection([
        ('draft', "Draft"),
        ('submitted', "Submitted"),
        ('rejected', "Rejected"),
    ], default="draft",
        copy=False,
        required=True,
        tracking=True)
    total = fields.Monetary(compute='compute_total')

    used_price_percent = fields.Html(compute='compute_used_price_percent')

    @api.depends('planned_item_ids.planned_quantity',
                 'planned_item_ids.planned_cost',
                 'planned_item_ids.actual_requisition_qty',
                 'planned_item_ids.actual_purchased_qty',
                 'planned_item_ids.actual_bill_qty',
                 'planned_item_ids.actual_requisition_price',
                 'planned_item_ids.actual_purchase_price',
                 'planned_item_ids.actual_bill_price')
    def compute_used_price_percent(self):
        """
        Compute how much % of planned quantity and cost is used.
        Show soft alerts with color codes depending on thresholds.
        """
        for rec in self:
            total_planned_qty = sum(line.planned_quantity for line in rec.planned_item_ids) or 0
            total_actual_qty = sum(
                line.actual_requisition_qty + line.actual_purchased_qty + line.actual_bill_qty
                for line in rec.planned_item_ids
            )

            total_planned_cost = sum(line.planned_cost for line in rec.planned_item_ids) or 0
            total_actual_cost = sum(
                line.actual_requisition_price + line.actual_purchase_price + line.actual_bill_price
                for line in rec.planned_item_ids
            )

            qty_percent = (total_actual_qty / total_planned_qty * 100) if total_planned_qty else 0
            cost_percent = (total_actual_cost / total_planned_cost * 100) if total_planned_cost else 0

            # Determine alert level (soft warnings)
            def colorize(percent):
                if percent >= 100:
                    return "danger"   # Red
                elif percent >= 75:
                    return "warning"  # Orange
                elif percent >= 50:
                    return "info"     # Blue
                else:
                    return "success"  # Green

            qty_color = colorize(qty_percent)
            cost_color = colorize(cost_percent)

            rec.used_price_percent = Markup(f"""
                <div>
                    <span class="badge bg-{qty_color}">
                        Notice: {qty_percent:.1f}% of the planned quantity has been utilized. Please review before proceeding.
                    </span> 
                    <span class="badge bg-{cost_color}" style="margin-left: 8px;">
                        Notice: {cost_percent:.1f}% of the planned cost has been utilized. Please review before proceeding.
                    </span>
                </div>
            """)

    @api.depends('planned_item_ids.sub_total')
    def compute_total(self):
        """
        Function to compute total
        :return:
        """
        for rec in self:
            rec.total = sum(rec.planned_item_ids.mapped('sub_total')) or 0.0

    def action_request(self):
        """
        Submit a plan
        :return:
        """
        self.ensure_one()
        employee_user = self.employee_id.user_id or self.department_id.manager_id.user_id
        if employee_user:
            self.env['mail.activity'].sudo().create({
                'summary': 'Please fill the Annual Procurement Plan.',
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'res_model_id': self.env['ir.model']._get_id('annual.department.procurement.plan'),
                'res_id': self.id,
                'user_id': employee_user.id
            })

    def action_confirm_request(self):
        """
        Confirm a plan
        :return:
        """
        self.ensure_one()
        activities = self.env['mail.activity'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id)
        ])
        for activity in activities:
            activity.action_done()

        self.env['mail.activity'].sudo().create({
            'summary': f'Annual Procurement Plan filled by {self.env.user.name}.',
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'res_model_id': self.env['ir.model']._get_id(
                'annual.department.procurement.plan'),
            'res_id': self.id,
            'user_id': self.master_plan_id.create_uid.id
        })

        self.write({
            'status': 'requested'
        })

    def action_submit(self):
        """
        Submit a plan
        :return:
        """
        self.ensure_one()
        if self.master_plan_id.status != 'open':
            raise ValidationError("Cannot submit plan because"
                             " the master plan is not open.")
        for rec in self.planned_item_ids:
            rec.master_plan_id = self.master_plan_id.id
        activities = self.env['mail.activity'].sudo().search([
            ('res_model', '=', self._name),
            ('res_id', '=', self.id),
            ('activity_type_id', '=',
             self.env.ref('mail.mail_activity_data_todo').id)
        ])
        for activity in activities:
            activity.action_done()
        self.write({
            'status': 'submitted'
        })

    def reset_to_draft(self):
        """Reset to draft a plan"""
        self.ensure_one()
        self.write({
            'status': 'draft'
        })

    def action_reject(self):
        """Reset to draft a plan"""
        self.ensure_one()
        self.write({
            'status': 'rejected'
        })

    is_exceed_limit = fields.Boolean(compute='compute_is_exceed_limit')

    @api.depends('planned_item_ids.planned_quantity',
                 'planned_item_ids.planned_cost',
                 'planned_item_ids.actual_requisition_qty',
                 'planned_item_ids.actual_purchased_qty',
                 'planned_item_ids.actual_bill_qty',
                 'planned_item_ids.actual_requisition_price',
                 'planned_item_ids.actual_purchase_price',
                 'planned_item_ids.actual_bill_price')
    def compute_is_exceed_limit(self):
        """
            Compute whether the actual quantities (requisition, purchased, billed)
            exceed the planned quantity for any planned item line.

            This sets `is_exceed_limit` to True if any line in `planned_item_ids`
            exceeds the planned quantity, otherwise False.
            """
        for rec in self:
            rec.is_exceed_limit = any(
                line.planned_quantity < max(
                    line.actual_requisition_qty,
                    line.actual_purchased_qty,
                    line.actual_bill_qty,
                )
                for line in rec.planned_item_ids
            ) or any(
                line.planned_cost < max(
                    line.actual_requisition_price,
                    line.actual_purchase_price,
                    line.actual_bill_price,
                )
                for line in rec.planned_item_ids
            )


class AnnualDepartmentProcurementPlanItems(models.Model):
    """
    Plan items
    """
    _name = 'annual.department.procurement.plan.items'
    _description = 'Annual Department Procurement Plan Items'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Inherit create for annual
         department procurement plan items
        :param vals_list:
        :return:
        """
        for values in vals_list:
            if values.get('plan_id'):
                plan = self.env[
                    'annual.department.procurement.plan'].browse(
                    values['plan_id'])
                department = plan.department_id
                department.last_sequence += 1
                plans_in_department = department.last_sequence
                department_short_code = department.short_code
                year_suffix = fields.Date.today().strftime("%y")
                values["name"] = f"{department_short_code}/" \
                             f"{year_suffix}/" \
                             f"{str(plans_in_department).zfill(6)}"
        return super().create(vals_list)

    name = fields.Char(string="Reference",
                       readonly=True,
                       copy=False,
                       default="New")
    department_id = fields.Many2one("hr.department",
                                    store=True,
                                    related='plan_id.department_id')
    employee_id = fields.Many2one("hr.employee",
                                  store=True,
                                  related='plan_id.employee_id')
    product_id = fields.Many2one('product.product')
    description = fields.Char()
    budget_reference_id = fields.Many2one('budget.line')
    planned_quantity = fields.Float(default=1.0,
                                    help="Quantity of the planned item",
                                    required=True)
    approved_planned_quantity = fields.Float(default=0.0,
                                             help="Quantity of the planned item which is approved",)

    planned_cost = fields.Monetary(default=1.0,
                                   help="Cost of the planned item",
                                   required=True)
    approved_planned_cost = fields.Monetary(default=0.0,
                                            help="Cost of the planned item which is approved",)
    currency_id = fields.Many2one('res.currency',
                                  related='plan_id.currency_id')
    planned_purchase_quarter = fields.Selection([('q1', 'Q1'),
                                                 ('q2', 'Q2'),
                                                 ('q3', 'Q3'),
                                                 ('q4', 'Q4')],
                                                required=True)
    company_id = fields.Many2one('res.company',
                                 related='plan_id.company_id')
    uom_id = fields.Many2one(
        'uom.uom',
        string='UOM',
        required=True)

    @api.onchange('product_id')
    def onchange_product(self):
        self.uom_id = self.product_id.uom_po_id
        self.planned_cost = self.product_id.standard_price

    sub_total = fields.Monetary(compute='compute_subtotal',
                                store=True)

    sub_total_actual = fields.Monetary(compute='compute_subtotal_actual',
                                       help="Actual Purchase Price * Approved Planned Quantity",
                                       store=True)

    sub_total_approved = fields.Monetary(compute='compute_subtotal_approved',
                                         store=True)

    @api.depends('approved_planned_quantity', 'approved_planned_cost')
    def compute_subtotal_approved(self):
        for rec in self:
            rec.sub_total_approved = rec.approved_planned_quantity * rec.approved_planned_cost

    date_start = fields.Date(tracking=True,
                             string="Start Date",
                             related='plan_id.date_start')
    date = fields.Date(tracking=True,
                       string="End Date",
                       related='plan_id.date')
    status = fields.Selection(related='plan_id.status',
                              store=True)
    category_id = fields.Many2one('product.category',
                                  related="product_id.categ_id")

    @api.depends('planned_quantity', 'planned_cost')
    def compute_subtotal(self):
        """
        Computation of Subtotal
        :return:
        """
        for rec in self:
            rec.sub_total = rec.planned_quantity * rec.planned_cost

    @api.depends('actual_purchase_price', 'approved_planned_quantity')
    def compute_subtotal_actual(self):
        """
        Computation of Actual Subtotal
        :return:
        """
        for rec in self:
            rec.sub_total_actual = rec.actual_purchase_price * rec.approved_planned_quantity

    plan_id = fields.Many2one('annual.department.procurement.plan')
    master_plan_id = fields.Many2one(
        'procurement.master.plan')
    master_plan_status = fields.Selection(
        related='master_plan_id.status',
    )

    # Actual Fields

    actual_requisition_qty = fields.Float(readonly=True)
    actual_purchased_qty = fields.Float(readonly=True)
    actual_bill_qty = fields.Float(readonly=True)

    actual_requisition_price = fields.Monetary(readonly=True)
    actual_purchase_price = fields.Monetary(readonly=True)
    actual_bill_price = fields.Monetary(readonly=True)

    qty_deviation = fields.Float(readonly=True)
    cost_deviation = fields.Monetary(readonly=True)
    execution_rate = fields.Float(readonly=True)

    deviation_status = fields.Selection([
        ('on_target', 'On Target'),
        ('under', 'Under'),
        ('over', 'Over')],
        readonly=True)

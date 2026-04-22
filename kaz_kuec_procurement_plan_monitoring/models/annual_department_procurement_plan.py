from odoo import models, fields, api
from datetime import datetime, time


class AnnualDepartmentProcurementPlan(models.Model):
    _inherit = 'annual.department.procurement.plan'

    @api.model
    def get_planned_vs_actual(self, department_id, company_id):
        """
        Compute planned vs actual data for a department.
        This method is meant to be called via RPC from OWL.
        """
        department_procurement_plans = self.search([('department_id', '=', department_id),
                                                    ('company_id', '=', company_id),
                                                    ('company_id', '=', company_id),
                                                    ])
        planned_items = department_procurement_plans.planned_item_ids

        approved_total_approved_planned_qty = sum(planned_items.mapped('approved_planned_quantity'))
        total_approved_actual_qty = sum(planned_items.mapped('actual_purchased_qty'))

        total_planned_purchase_price = sum(planned_items.mapped('planned_cost'))
        total_actual_purchase_price = sum(planned_items.mapped('actual_purchase_price'))

        if not department_procurement_plans.exists():
            return {
                "approved_total_approved_planned_qty": 0,
                "total_approved_actual_qty": 0,
                "total_planned_purchase_price": 0,
                "total_actual_purchase_price": 0
            }

        # Example logic (replace with your real computation)

        qty_percentage = (
            (total_approved_actual_qty / approved_total_approved_planned_qty) * 100
            if approved_total_approved_planned_qty else 0.0
        )

        price_percentage = (
            (total_actual_purchase_price / total_planned_purchase_price) * 100
            if total_planned_purchase_price else 0.0
        )

        return {
            "planned_qty": approved_total_approved_planned_qty,
            "actual_qty": total_approved_actual_qty,
            "difference_qty": approved_total_approved_planned_qty - total_approved_actual_qty,
            "qty_percentage": qty_percentage,

            "planned_price": total_planned_purchase_price,
            "actual_price": total_actual_purchase_price,
            "difference_price": total_planned_purchase_price - total_actual_purchase_price,
            "price_percentage": price_percentage,
        }

    @api.model
    def load_data(self, filters):
        procurement_domain = [("company_id", "=", filters.get("company_id"))]
        purchase_domain = [("company_id", "=", filters.get("company_id"))]
        annual_dpt_plan_domain = [("company_id", "=", filters.get("company_id"))]
        tender_domain = [("company_id", "=", filters.get("company_id")),
                         ('state', 'in', ['active', 'under_review'])]

        if filters.get("startDate"):
            procurement_domain.append((
                "create_date", ">=",
                fields.Datetime.to_datetime(filters["startDate"])
            ))
            purchase_domain.append((
                "create_date", ">=",
                fields.Datetime.to_datetime(filters["startDate"])
            ))
            annual_dpt_plan_domain.append((
                "create_date", ">=",
                fields.Datetime.to_datetime(filters["startDate"])
            ))
            tender_domain.append((
                "create_date", ">=",
                fields.Datetime.to_datetime(filters["startDate"])
            ))

        if filters.get("endDate"):
            procurement_domain.append((
                "create_date", "<=",
                fields.Datetime.to_datetime(filters["endDate"])
            ))
            purchase_domain.append((
                "create_date", "<=",
                fields.Datetime.to_datetime(filters["endDate"])
            ))
            annual_dpt_plan_domain.append((
                "create_date", "<=",
                fields.Datetime.to_datetime(filters["endDate"])
            ))
            tender_domain.append((
                "create_date", "<=",
                fields.Datetime.to_datetime(filters["endDate"])
            ))

        if filters.get("requisition_type"):
            procurement_domain.append(
                ("requisition_type_id", "in", filters["requisition_type"]))

        if filters.get("vendor"):
            procurement_domain.append(("vendor_id", "in", filters["vendor"]))
            purchase_domain.append(("partner_id", "in", filters["vendor"]))
            tender_domain.append(("partner_ids", "in", filters["vendor"]))

        if filters.get("product"):
            procurement_domain.append(("requisition_line_ids.product_id", "in", filters["product"]))
            purchase_domain.append(("order_line.product_id", "in", filters["product"]))
            annual_dpt_plan_domain.append((
                "planned_item_ids.product_id", "in", filters["product"]
            ))
            tender_domain.append((
                "tender_rfq_line_ids.product_id", "in", filters["product"]
            ))

        if filters.get("departments"):
            procurement_domain.append(("department_ids", "in", filters["departments"]))
            annual_dpt_plan_domain.append(("department_id", "in", filters["departments"]))

        total_requisition = self.env["material.purchase.requisition"].search(procurement_domain)

        total_days = 0
        count = 0
        prs = total_requisition.filtered(lambda x: x.purchase_id)

        for pr in prs:
            po = pr.purchase_id

            pr_date = pr.create_date
            po_date = po.date_order or po.create_date

            if pr_date and po_date:
                diff_days = (po_date - pr_date).days
                total_days += diff_days
                count += 1

        average_days = total_days / count if count else 0

        master_plan_requisition = total_requisition.filtered(
            lambda r: any(r.requisition_line_ids.mapped('in_master_plan')))
        non_master_plan_requisition = total_requisition.filtered(
            lambda r: not any(r.requisition_line_ids.mapped('in_master_plan')))

        procurement_plan = self.env['annual.department.procurement.plan'].search(
            annual_dpt_plan_domain
        )
        warning_triggered = procurement_plan.filtered(
            lambda p: p.is_exceed_limit)
        not_approved_requisitions = total_requisition.filtered(
            lambda r: r.kuec_approval_state != 'approved'
        )
        tenders = self.env['tender.rfq'].search(tender_domain)

        po_domain = purchase_domain + [("state", "in", ["purchase", "done"])]

        po = self.env["purchase.order"].read_group(
            domain=po_domain,
            fields=["date_order"],
            groupby=["date_order:month"])

        grouped_month = self.env["purchase.order"].read_group(
            domain=po_domain,
            fields=["date_order"],
            groupby=["date_order:month"],
            orderby="date_order_count desc",
            limit=1,
        )

        top_month = grouped_month[0].get(
            "date_order:month") if grouped_month else None
        top_month_count = grouped_month[0].get("date_order_count",
                                               0) if grouped_month else 0

        grouped_quarter = self.env["purchase.order"].read_group(
            po_domain,
            ["date_order"],
            ["date_order:quarter"],
            orderby="date_order_count desc",
            limit=1,
        )

        top_quarter = grouped_quarter[0].get(
            "date_order:quarter") if grouped_quarter else None
        top_quarter_count = grouped_quarter[0].get("date_order_count",
                                                   0) if grouped_quarter else 0

        grouped_year = self.env["purchase.order"].read_group(
            po_domain,
            ["date_order"],
            ["date_order:year"],
            orderby="date_order_count desc",
            limit=1,
        )

        top_year = grouped_year[0].get(
            "date_order:year") if grouped_year else None
        top_year_count = grouped_year[0].get("date_order_count",
                                             0) if grouped_year else 0

        po_domain = purchase_domain + [
            ("state", "in", ["purchase", "done"]),
        ]

        grouped_vendors = self.env["purchase.order"].read_group(
            domain=po_domain,
            fields=[
                "partner_id",
                "amount_total:sum",
            ],
            groupby=["partner_id"],
            orderby="amount_total:sum desc",
            limit=10,
        )

        print('po_domain', po_domain)

        top_10_vendors = [
            {
                "vendor_id": rec["partner_id"][0],
                "vendor_name": rec["partner_id"][1],
                "total_spent": rec.get("amount_total", 0.0),
                "po_count": rec.get("partner_id_count", 0),
            }
            for rec in grouped_vendors
            if rec.get("partner_id")
        ]

        grouped_types = self.env["material.purchase.requisition"].read_group(
            domain=procurement_domain,  # add date / department filters here
            fields=[
                "requisition_type_id",
                "total_amount:sum",
            ],
            groupby=["requisition_type_id"],
            orderby="total_amount:sum desc",
            limit=10,
        )
        top_10_request_types = [
            {
                "requisition_type_id": rec["requisition_type_id"][0],
                "request_type_name": rec["requisition_type_id"][1],
                "total_spend": rec.get("total_amount", 0.0),
                "request_count": rec.get("requisition_type_id_count", 0),
            }
            for rec in grouped_types
            if rec.get("requisition_type_id")
        ]

        all_pr = self.env["material.purchase.requisition"].search(
            procurement_domain)
        department_data = {}

        print('all_pr', all_pr)

        for req in all_pr:
            print(req)
            for dep in req.department_id:
                if dep.id not in department_data:
                    department_data[dep.id] = {
                        "department_id": dep.id,
                        "department_name": dep.name,
                        "total_spend": 0.0,
                        "request_count": 0,
                    }
                department_data[dep.id]["total_spend"] += req.total_amount
                department_data[dep.id]["request_count"] += 1

        # Sort by total_spend descending and take top 10
        top_departments = sorted(department_data.values(),
                                 key=lambda x: x["total_spend"], reverse=True)[
                          :10]

        print('top_10_vendors', top_10_vendors)

        x = {
            "total_pr_created": self.env["material.purchase.requisition"].search_count(
                procurement_domain),
            "total_pr_approved": self.env["material.purchase.requisition"].search_count(
                procurement_domain + [("kuec_approval_state", "=", "approved")]
            ),
            "total_quotations": self.env["purchase.order"].search_count(
                purchase_domain + [("state", "in", ['rfq', 'sent', 'to approve'])]
            ),
            "total_po": self.env["purchase.order"].search_count(
                purchase_domain + [("state", "in", ["purchase", "done"])]
            ),
            'per_total_pr_confirmed': (len(master_plan_requisition) / len(total_requisition)) * 100 if total_requisition else 0.0,
            'warning_triggered': len(warning_triggered),
            'not_approved_requisitions': len(not_approved_requisitions),
            'tenders': len(tenders),
            'average_days': average_days,
            'total_pr_rfq_po': {
                'total_pr': self.env["material.purchase.requisition"].search_count(
                    procurement_domain),
                'total_rfq': self.env["purchase.order"].search_count(
                    purchase_domain + [("state", "in", ['rfq', 'sent', 'to approve'])]
                    ),
                'total_po': self.env["purchase.order"].search_count(
                    purchase_domain + [("state", "in", ["purchase", "done"])]
                    ),
            },
            'non_master_plan_requisition': len(non_master_plan_requisition),
            'top_procurement_period': {
                'month': {
                    'label': top_month,
                    'count': top_month_count,
                },
                'quarter': {
                    'label': top_quarter,
                    'count': top_quarter_count,
                },
                'year': {
                    'label': top_year,
                    'count': top_year_count,
                }
            },
            'top_10_vendors': top_10_vendors,
            'top_10_request_types': top_10_request_types,
            'top_departments': top_departments,
        }
        return x




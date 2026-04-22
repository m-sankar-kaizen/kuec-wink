from odoo import models, api, fields
from datetime import timedelta, datetime


class IncompletePoReport(models.AbstractModel):
    _name = "report.kaz_po_close_out.incomplete_po_report"
    _description = "Incomplete Purchase Orders Report"

    def _get_report_values(self, docids, data=None):
        """
        This method provides the context and dataset for the QWeb template.

        :param docids: Active record IDs (usually not used here since we report across all POs)
        :param data: Optional dict passed from the action
        :return: dict context for QWeb rendering
        """
        months_limit = int(
            self.env["ir.config_parameter"].sudo().get_param(
                "kaz_po_close_out.po_incomplete_months_limit"
            )
        )
        cutoff_date = fields.Datetime.now() - timedelta(days=months_limit * 30)

        complete_states = ["done", "purchase", "cancel"]
        purchase_orders = self.env["purchase.order"].search([
            ("state", "not in", complete_states),
            ("create_date", "<", cutoff_date),
        ], order="create_date asc")

        records = []
        for po in purchase_orders:
            last_activity = po.message_ids[:1].date if po.message_ids else po.write_date

            records.append({
                "po_number": po.name or "",
                "creation_date": po.create_date.strftime("%Y-%m-%d %H:%M:%S"),
                "status": po.state,
                "department": po.department_id.name if po.department_id else "",
                "total_value": po.amount_total,
                "currency": po.currency_id.symbol,
                "last_activity": last_activity.strftime("%Y-%m-%d %H:%M:%S"),
            })
        return {
            "doc_ids": docids,
            "doc_model": "purchase.order",
            "docs": records,
            "months_limit": months_limit,
            "report_title": f"Incomplete Purchase Orders older than {months_limit} months",
        }


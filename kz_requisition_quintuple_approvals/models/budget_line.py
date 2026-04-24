# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


# enterprise/account_budget/models/budget_line.py

class BudgetLine(models.Model):
    """
    Extension of the budget.line model to support additional computed fields:
    - reserved_amount: Indicates funds reserved for draft/sent purchases not yet completed.
    - committed_amount: Indicates funds committed in purchases that are confirmed or completed but not invoiced.

    The calculations are based on linked requisition lines within the specified budget dates
    and matched against the budget's general accounts.
    """
    _inherit = "budget.line"

    reserved_amount = fields.Monetary(
        string="Reserved Amount",
        compute="_compute_reserved_amount",
        help="Total amount reserved for purchases in 'draft' or 'sent' states."
    )

    committed_amount = fields.Monetary(
        string="Committed Amount",
        compute="_compute_committed_amount",
        help="Total committed amount for purchases confirmed or completed, but not invoiced."
    )
    committed_percentage = fields.Float(
        compute='_compute_committed_amount',
        string='Committed (%)')

    def _compute_reserved_amount(self):
        """
        Computes the reserved amount for the budget line using SQL query.
        Reserved = requisitions not in 'draft', 'rejected', or 'cancel'
        with related purchases in 'draft' or 'sent' state.
        """
        for line in self:
            if not (line.general_budget_id and line.company_id and line.date_from and line.date_to):
                line.reserved_amount = 0.0
                continue

            account_ids = tuple(line.general_budget_id.account_ids.ids)
            if not account_ids:
                line.reserved_amount = 0.0
                continue

            if len(account_ids) == 1:
                account_ids += (0,)

            query = """
                   SELECT COALESCE(SUM(mprl.amount_incurrency), 0.0) AS total_reserved
                   FROM material_purchase_requisition_line AS mprl
                   JOIN material_purchase_requisition AS mpr
                       ON mpr.id = mprl.requisition_id
                   WHERE mpr.approvement_state NOT IN ('draft', 'rejected', 'cancel')
                     AND mpr.company_id = %s
                     AND mprl.account_id IN %s
                     AND mpr.request_date BETWEEN %s AND %s
                     AND EXISTS (
                         SELECT 1
                         FROM purchase_order AS po
                         JOIN material_purchase_requisition_purchase_order_rel AS rel
                           ON rel.purchase_order_id = po.id
                          AND rel.material_purchase_requisition_id = mpr.id
                         WHERE po.state IN ('draft', 'sent')
                     )
               """

            self.env.cr.execute(query, (
                line.company_id.id,
                account_ids,
                line.date_from,
                line.date_to,
            ))
            result = self.env.cr.fetchone()
            total_reserved = result[0] if result else 0.0

            line.reserved_amount = total_reserved

    def _compute_committed_amount(self):
        """
        Computes the committed amount for the budget line using SQL query.
        Committed = requisitions in 'completed' state
        with related purchases in 'purchase' or 'done' state but not yet invoiced.
        """
        for line in self:
            if not (line.general_budget_id and line.company_id and line.date_from and line.date_to):
                line.committed_amount = 0.0
                line.committed_percentage = 0.0
                continue

            account_ids = tuple(line.general_budget_id.account_ids.ids)
            if not account_ids:
                line.committed_amount = 0.0
                line.committed_percentage = 0.0
                continue

            # Handle single-element tuples for SQL safety
            if len(account_ids) == 1:
                account_ids += (0,)

            query = """
                    SELECT COALESCE(SUM(mprl.amount_incurrency), 0.0) AS total_committed
                    FROM material_purchase_requisition_line AS mprl
                    JOIN material_purchase_requisition AS mpr
                        ON mpr.id = mprl.requisition_id
                    WHERE mpr.approvement_state = 'completed'
                      AND mpr.company_id = %s
                      AND mprl.account_id IN %s
                      AND mpr.request_date BETWEEN %s AND %s
                      AND EXISTS (
                          SELECT 1
                          FROM purchase_order AS po
                          JOIN material_purchase_requisition_purchase_order_rel AS rel
                            ON rel.purchase_order_id = po.id
                           AND rel.material_purchase_requisition_id = mpr.id
                          WHERE po.state IN ('purchase', 'done')
                            AND NOT EXISTS (
                                SELECT 1
                                FROM account_move AS inv
                                JOIN account_move_line AS aml
                                  ON aml.move_id = inv.id
                                WHERE inv.state = 'posted'
                                  AND aml.purchase_line_id IN (
                                      SELECT pol.id
                                      FROM purchase_order_line AS pol
                                      WHERE pol.order_id = po.id
                                  )
                            )
                      )
                """

            self.env.cr.execute(query, (
                line.company_id.id,
                account_ids,
                line.date_from,
                line.date_to,
            ))
            result = self.env.cr.fetchone()
            total_committed = result[0] if result else 0.0
            committed_percentage = total_committed / line.budget_amount if line.budget_amount else 0.0

            line.committed_amount = total_committed
            line.committed_percentage = committed_percentage if not line.expense else -committed_percentage

    @api.depends('budget_analytic_id.name', 'general_budget_id.name')
    def _compute_display_name(self):
        """
        Custom display name for budget lines. Combines budget name and general budget name.
        """
        for record in self:
            parts = [record.budget_analytic_id.name]
            if record.general_budget_id:
                parts.append(record.general_budget_id.name)
            record.display_name = " / ".join(filter(None, parts))

    def select_line(self):
        """
        Assigns the general account from a selected budget line to each line of the given requisition.
        Ensures only one line is selected and applies the first account of general_budget_id.
        """
        selected = self.env['budget.line'].sudo().browse(self._context.get('active_ids', False))
        if len(selected) > 1:
            raise ValidationError(_("You must select one line"))

        requisition = self.env['material.purchase.requisition'].sudo().browse(
            self.env.context.get('requisition', False))
        selected = selected[0]

        if selected and selected.general_budget_id and selected.general_budget_id.account_ids and requisition:
            account = selected.general_budget_id.account_ids[0]
            for line in requisition.requisition_line_ids:
                line.account_id = account.id

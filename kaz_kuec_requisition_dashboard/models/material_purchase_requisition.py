from odoo import models, api, fields


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    @api.model
    def retrieve_dashboard(self):
        """
        Returns values to populate the custom dashboard.
        All counts are RECORD COUNTS (not activity counts),
        so they match the list view opened on click.
        """
        self.check_access('read')

        today = fields.Date.today()
        company = self.env.company
        companies = self.env.companies
        uid = self.env.uid

        # -------------------------------------------------
        # Activity-based PR counts (MATCH JS DOMAINS)
        # -------------------------------------------------

        activity_today = self.search_count([
            ('activity_ids.date_deadline', '=', today),
        ])

        activity_due = self.search_count([
            ('activity_ids.date_deadline', '<', today),
        ])

        activity_upcoming = self.search_count([
            ('activity_ids.date_deadline', '>', today),
        ])

        # -------------------------------------------------
        # Requisition status counts
        # -------------------------------------------------

        waiting_approval = self.search_count([
            ('kuec_approval_state', 'not in',
             ['draft', 'approved', 'rejected', 'cancel']),
        ])

        waiting_for_po = self.search_count([
            ('purchase_ids', '=', False),
            ('kuec_approval_state', '=', 'approved'),
        ])

        prs_converted_po = self.search_count([
            ('purchase_ids', '!=', False),
            ('kuec_approval_state', '=', 'approved'),
        ])

        open_prs = self.search_count([
            ('kuec_approval_state', 'not in',
             ['approved', 'rejected', 'cancel']),
        ])

        # -------------------------------------------------
        # Result
        # -------------------------------------------------

        return {
            'open_prs': open_prs,
            'waiting_approval': waiting_approval,
            'waiting_for_po': waiting_for_po,
            'prs_converted_po': prs_converted_po,
            'activity_today': activity_today,
            'activity_due': activity_due,
            'activity_upcoming': activity_upcoming,
            'company_currency_symbol': company.currency_id.symbol,
        }



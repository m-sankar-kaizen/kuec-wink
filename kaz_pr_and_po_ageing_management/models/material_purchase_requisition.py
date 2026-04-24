# -*- coding: utf-8 -*-

from datetime import timedelta, date

from odoo import models, fields, api, _


class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    expiry_warning_message = fields.Text(string="Expiry Warning Message")
    raise_expiry_warning = fields.Boolean(default=False, string="Raise Expiry Warning")

    def get_fiscal_year_end(self):
        company = self.company_id
        last_day = company.draft_pr_pa_notify_day
        last_month = int(company.draft_pr_pa_notify_month)
        today = fields.Date.today()
        fiscal_year_end = date(today.year, last_month, last_day)
        return fiscal_year_end

    def submit_to_approve(self):
        if self.raise_expiry_warning:
            self.raise_expiry_warning = False
            self.expiry_warning_message = ""
        return super().submit_to_approve()

    @api.onchange('request_date')
    def _onchange_request_date(self):
        if not self.raise_expiry_warning:
            return
        fiscal_year_end = self.get_fiscal_year_end()
        # If request_date is AFTER fiscal year end → assume user carried it over
        if self.request_date > fiscal_year_end:
            self.raise_expiry_warning = False
            self.expiry_warning_message = ""

    def _get_purchase_requisition_reminder_companies(self):
        return self.env['res.company'].search([])

    @api.model
    def cron_purchase_requisition_reminder(self):
        """Notify responsible users X days before fiscal year-end
                and auto-cancel PR on fiscal year-end day."""

        companies = self._get_purchase_requisition_reminder_companies()
        today = fields.Date.today()

        for company in companies:
            last_day = company.draft_pr_pa_notify_day
            last_month = int(company.draft_pr_pa_notify_month)
            notify_days = company.draft_pr_pa_notify_days or 0

            fiscal_year_end = date(today.year, last_month, last_day)

            draft_prs = self.search([
                ('state', '=', 'draft'),
                ('company_id', '=', company.id),
                ('request_date', '<=', fiscal_year_end),
            ])

            # ---- CASE 1: Auto-cancel on fiscal year-end ----
            if today == fiscal_year_end:
                body = _(
                    "This Purchase Requisition was automatically cancelled due to fiscal year-end.")
                for pr in draft_prs:
                    pr.write({
                        'state': 'cancel',
                        'expiry_warning_message': body,
                        'raise_expiry_warning': True,
                    })
                    pr.message_post(body=body)
                continue

            # ---- CASE 2: Notification from X days before fiscal year-end ----
            notify_date = fiscal_year_end - timedelta(days=notify_days)

            if today >= notify_date:
                note = _(
                    "This Purchase Requisition is still in Draft state. "
                    "Please take action: either Cancel it, or update it and Submit for Approval. "
                    "Otherwise, it will be auto-cancelled on %s."
                ) % fiscal_year_end.strftime('%d-%B-%Y')
                for pr in draft_prs:
                    responsible_user = pr.employee_id.user_id or pr.create_uid
                    pr.expiry_warning_message = note
                    pr.raise_expiry_warning = True
                    pr.activity_schedule(
                        activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                        user_id=responsible_user.id,
                        summary=_("Draft PR Approaching Fiscal Year-End"),
                        note=note
                    )

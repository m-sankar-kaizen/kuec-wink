# -*- coding: utf-8 -*-
from datetime import date

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ExtendAgreement(models.Model):
    _name = 'extend.agreement'
    _description = 'Extend Agreement'

    purchase_requisition_id = fields.Many2one('purchase.requisition', string="Purchase Requisition")
    new_date_end = fields.Date(string="New Date End", required=True)
    request_user_id = fields.Many2one('res.users', string="Request User",
                                      default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company', string="Company",
                                 default=lambda self: self.env.company)
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        string="State",
        default='draft'
    )

    def action_notify(self):
        """Notify all users in the Purchase Agreement Manager group"""
        admin_group = self.env.ref('kaz_purchase_agreement.group_purchase_agreement_manager_kuec', raise_if_not_found=False)
        if not admin_group:
            return

        users_to_notify = admin_group.users
        if not users_to_notify:
            return

        note = _("A new agreement extension request has been created by %s for agreement %s, requesting new end date %s.") % (
            self.request_user_id.name,
            self.purchase_requisition_id.name or 'N/A',
            self.new_date_end.strftime('%d-%B-%Y')
        )

        for user in users_to_notify:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                user_id=user.id,
                summary=_("New Agreement Extension Request"),
                note=note
            )

    @api.constrains('new_date_end', 'purchase_requisition_id')
    def _check_new_date_end(self):
        for record in self:
            if record.purchase_requisition_id and record.new_date_end:
                if record.new_date_end <= record.purchase_requisition_id.date_end:
                    raise ValidationError(_(
                        "The new end date must be later than the current agreement end date (%s)."
                    ) % record.purchase_requisition_id.date_end)

    def get_fiscal_year_end(self):
        company = self.company_id
        last_day = company.draft_pr_pa_notify_day
        last_month = int(company.draft_pr_pa_notify_month)
        today = fields.Date.today()
        fiscal_year_end = date(today.year, last_month, last_day)
        return fiscal_year_end

    def action_approve(self):
        """Approve the extension request"""
        for record in self:
            record.state = 'approved'
            if record.purchase_requisition_id and record.new_date_end:
                fiscal_year_end = self.get_fiscal_year_end()
                old_end_date = record.purchase_requisition_id.date_end
                write_vals = {
                    'tracking_state': 'extended',
                    'date_end': record.new_date_end,
                }
                if record.new_date_end > fiscal_year_end:
                    write_vals['raise_expiry_warning'] = False
                record.purchase_requisition_id.write(write_vals)

                # Post a message on the PR
                record.purchase_requisition_id.message_post(
                    body=_("The agreement end date has been extended from %s to %s.") % (
                        old_end_date.strftime('%d-%B-%Y') if old_end_date else 'N/A',
                        record.new_date_end.strftime('%d-%B-%Y')
                    )
                )

    def action_reject(self):
        """Reject the extension request"""
        for record in self:
            record.state = 'rejected'

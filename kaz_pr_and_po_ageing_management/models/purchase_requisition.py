# -*- coding: utf-8 -*-
from datetime import timedelta, date

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    expiry_warning_message = fields.Text(string="Expiry Warning Message")
    raise_expiry_warning = fields.Boolean(default=False, string="Raise Expiry Warning")
    tracking_state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('expiring_soon', 'Expiring Soon'),
            ('extended', 'Extended'),
            ('done', 'Done'),
            ('expired', 'Expired'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        string="Tracking State",
        copy=False,
    )
    extend_agreement_ids = fields.One2many('extend.agreement', 'purchase_requisition_id',
                                           string="Extend Requests")

    def action_extend_agreement(self):
        self.ensure_one()
        if self.extend_agreement_ids.filtered(lambda r: r.state == 'draft'):
            raise UserError(_("There is already an extension request in draft"))
        return {
            'type': 'ir.actions.act_window',
            'name': _("Extend Request"),
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'extend.agreement',
            'views': [(False, 'form')],
            'context': {
                'default_purchase_requisition_id': self.id
            }
        }

    def action_draft(self):
        res = super().action_draft()
        self.tracking_state = 'draft'
        return res

    def action_confirm(self):
        res = super().action_confirm()
        self.tracking_state = 'active'
        return res

    def action_cancel(self):
        res = super().action_cancel()
        self.tracking_state = 'cancelled'
        return res

    def action_done(self):
        res = super().action_done()
        self.tracking_state = 'done'
        return res

    def _get_purchase_agreement_reminder_companies(self):
        return self.env['res.company'].search([])

    @api.model
    def cron_purchase_agreement_reminder(self):
        """Notify responsible users X days before fiscal year-end
        and auto-cancel agreements on fiscal year-end day."""
        companies = self._get_purchase_agreement_reminder_companies()
        today = fields.Date.today()

        for company in companies:
            last_day = company.draft_pr_pa_notify_day
            last_month = int(company.draft_pr_pa_notify_month)
            notify_days = company.draft_pr_pa_notify_days or 0

            fiscal_year_end = date(today.year, last_month, last_day)

            agreements = self.search([
                ('state', 'in', ['draft', 'confirmed']),
                ('company_id', '=', company.id),
                ('date_end', '<=', fiscal_year_end),
            ])

            # ---- CASE 1: Auto-cancel on fiscal year-end ----
            if today == fiscal_year_end:
                body = _(
                    "This Purchase Agreement was automatically cancelled due to fiscal year-end."
                )
                for agreement in agreements:
                    state = 'cancel' if agreement.state == 'draft' else 'done'
                    tracking_state = 'expired' if agreement.state == 'draft' else 'done'
                    agreement.write({
                        'state': state,
                        'expiry_warning_message': body,
                        'raise_expiry_warning': True,
                        'tracking_state': tracking_state,
                    })
                    agreement.message_post(body=body)
                continue

            # ---- CASE 2: Notification from X days before fiscal year-end ----
            notify_date = fiscal_year_end - timedelta(days=notify_days)

            if today >= notify_date:
                for agreement in agreements:
                    responsible_user = agreement.user_id or agreement.create_uid

                    if agreement.state == 'draft':
                        note = _(
                            "This Purchase Agreement is still in Draft state. "
                            "Please review and extend the agreement if needed, or submit it for confirmation. "
                            "Otherwise, it will be auto-cancelled on %s."
                        ) % fiscal_year_end.strftime('%d-%B-%Y')
                    elif agreement.state == 'confirmed':
                        note = _(
                            "This Purchase Agreement is in Confirmed state. "
                            "You can extend the agreement if needed before fiscal year-end (%s)."
                        ) % fiscal_year_end.strftime('%d-%B-%Y')
                    else:
                        continue  # skip other states
                    agreement.write({
                        'expiry_warning_message': note,
                        'raise_expiry_warning': True,
                        'tracking_state': 'expiring_soon',
                    })
                    agreement.activity_schedule(
                        activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                        user_id=responsible_user.id,
                        summary=_("Purchase Agreement Approaching Fiscal Year-End"),
                        note=note
                    )

# -*- coding: utf-8 -*-
from odoo import models, fields, _, Command, api
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    company_code = fields.Selection(related="company_id.company_code", string="Company Code")
    srn_report_line_ids = fields.One2many('srn.report.line', 'purchase_id',
                                          string="SRN Report Lines")
    can_show_srn_tab = fields.Boolean('Can Show SRN Tab', default=False,
                                      compute='_compute_can_show_srn_tab', store=True)
    srn_scope_of_work = fields.Html('SRN Scope of Work')
    total_paid_amount = fields.Monetary(
        string="Total Paid Amount",
        currency_field='currency_id',
        compute='_compute_total_paid_amount',
        store=True
    )

    @api.depends('invoice_ids.payment_state', 'invoice_ids.amount_paid')
    def _compute_total_paid_amount(self):
        for order in self:
            # Filter only posted invoices (state='posted')
            posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            payment_ids = posted_invoices.mapped('matched_payment_ids').filtered(lambda rec: rec.state == 'paid')
            order.total_paid_amount = sum(payment_ids.mapped('amount'))

    def action_notify_finance(self):
        self.ensure_one()

        # Get finance users from group: account.group_account_invoice
        finance_users = self._get_finance_users()
        # Message that will appear in the activity
        note_message = _(
            "Service PO %s has been completed. Please proceed with the finance processing."
        ) % (self.name)

        # Create a To-Do activity for each finance user
        for user in finance_users:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=user.id,
                summary=_("Process Completed Service PO"),
                note=note_message,
            )

        # Optional: Log it in the chatter
        self.message_post(body=_("Notification sent to Finance team for further processing."))

        return True

    def _get_finance_users(self):
        finance_group = self.env.ref('account.group_account_invoice', raise_if_not_found=False)
        if not finance_group:
            raise UserError(_("Finance group not found: account.group_account_invoice"))

        finance_users = finance_group.users.filtered(
            lambda u: u.company_id.company_code in ['KUEC']
        )
        if not finance_users:
            raise UserError(_("No users found in the 'Account Invoice' group."))

        return finance_users

    @api.depends('service_receipt_ids', 'service_receipt_ids.state')
    def _compute_can_show_srn_tab(self):
        for purchase in self:
            can_show_srn_tab = False
            if purchase.service_receipt_ids:
                can_show_srn_tab = not purchase.service_receipt_ids.filtered(
                    lambda r: r.state not in ['done', 'cancel'])
            purchase.can_show_srn_tab = can_show_srn_tab

    def action_generate_srn_report_lines(self):
        self.ensure_one()
        if self.srn_report_line_ids:
            raise UserError(_('SRN Report Lines already has been created.'))
        default_template = self.company_id.srn_report_template_id
        if not default_template:
            raise UserError(
                _("SRN Report Template not found. Please configure it in the settings."))

            # Sort template lines by sequence ascending
        sorted_lines = default_template.srn_report_template_line_ids.sorted(lambda l: l.sequence)
        self.srn_report_line_ids = [Command.clear()] + [
            Command.create({
                'sequence': idx + 1,
                'name': line.name,
                'srn_report_template_line_id': line.id,
            }) for idx, line in enumerate(sorted_lines)
        ]

    def service_completion_report(self):
        self.ensure_one()

        if not self.service_receipt_ids:
            raise UserError(
                _("Nothing to print. There are no SRN records for this Purchase Order."))

        if self.service_receipt_ids.filtered(lambda r: r.state not in ['done', 'cancel']):
            raise UserError(_("Please process all SRNs before generating the completion report."))

        if not self.srn_report_line_ids:
            raise UserError(
                _("SRN Report Lines are not created. Please generate them and complete the required details first.")
            )

        for line in self.srn_report_line_ids:
            if not line.answer_selection_id:
                raise UserError(
                    _("Please complete all questions under the SRN Report Lines before proceeding."))

        return self.env.ref(
            'kaz_srn_pdp_company_kuec.service_completion_receipt_report_action'
        ).report_action(self, config=False)

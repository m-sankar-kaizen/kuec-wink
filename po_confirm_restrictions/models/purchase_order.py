# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PurchaseOrder(models.Model):

    """
    Extends the standard `purchase.order` model to implement a multi-stage approval workflow,
    track partial invoicing, and attach purchase documentation such as the PO file and GRN.

    Enhancements:
    -------------
    • Multi-level Approval Workflow:
        - Tracks approval state using `approval_state` (waiting_approval, first_approval, second_approval).
        - Notifies users via `mail.activity` and email based on group-based permissions.

    • Additional Financial Fields:
        - `total_amount`: Total approved amount for the purchase order.
        - `remaining_amount`: Remaining balance to be invoiced or delivered.
        - `partial_po`: Boolean indicating whether the PO has been partially invoiced or fulfilled.

    • Attachment Fields:
        - `purchase_order_attach`: Upload for the original PO document.
        - `goods_received_note`: Upload for the Goods Received Note (GRN).

    • Activity & Notification Automation:
        - Automatically schedules activities (`related_activity_id`) for relevant groups based on approval state.
        - Sends HTML-styled email notifications with direct PO view links.

    • Invoicing Integration:
        - Extends `_prepare_invoice()` to propagate PO-related values (attachments, totals) to the vendor bill.

    Use Case:
    ---------
    Suitable for organizations with formal procurement approval chains, document validation requirements,
    or partial delivery and billing practices. Enhances auditability and accountability throughout
    the purchasing lifecycle.
    """

    _inherit = 'purchase.order'
    _description = "Purchase Order"

    total_amount = fields.Monetary(currency_field='currency_id')
    remaining_amount = fields.Monetary(currency_field='currency_id')
    partial_po = fields.Boolean(default=False)

    purchase_order_attach = fields.Binary()
    goods_received_note = fields.Binary()
    related_activity_id = fields.Many2one('mail.activity')

    approval_state = fields.Selection([('waiting_approval', 'Waiting Approval'),
                                       ('first_approval', 'First Approval'),
                                       ('second_approval', 'Second Approval')],
                                      copy=False, default='waiting_approval',
                                      tracking=True)

    def _prepare_invoice(self):
        """
        Prepares the dictionary of values required to create a vendor bill (invoice) for the purchase order.

        Returns:
            dict: A dictionary of field values to be passed to `account.move` during invoice creation.
        """
        self.ensure_one()
        move_type = self._context.get('default_move_type', 'in_invoice')

        partner_invoice = self.env['res.partner'].sudo().browse(self.partner_id.address_get(['invoice'])['invoice'])
        partner_bank_id = self.partner_id.commercial_partner_id.bank_ids.filtered_domain(
            ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)])[:1]

        invoice_vals = {
            'ref': self.partner_ref or '',
            'move_type': move_type,
            'narration': self.notes,
            'currency_id': self.currency_id.id,
            'partner_id': partner_invoice.id,
            'fiscal_position_id': (
                    self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(partner_invoice)).id,
            'payment_reference': self.partner_ref or '',
            'partner_bank_id': partner_bank_id.id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_line_ids': [],
            'company_id': self.company_id.id,
            'partial_po': self.partial_po,
            'total_amount': self.total_amount,
            'remaining_amount': self.remaining_amount,
            'purchase_order_attach': self.purchase_order_attach,
            'goods_received_note': self.goods_received_note,

        }
        return invoice_vals

    def button_draft(self):
        """
                Resets the purchase order to draft and updates the `approval_state` to 'waiting_approval'.

                Returns:
                    recordset: The result of the super call to `button_draft()`.
                """
        self.write({'approval_state': 'waiting_approval'})
        return super().button_draft()

    def button_confirm(self):
        """
                Overrides the standard `button_confirm` method to implement multi-level PO approval logic.

                Approval Flow:
                - If the user belongs to the second-level group: Marks as second approval and confirms.
                - If in first-level group and PO is waiting: Marks as first approval and sends notifications.
                - If ineligible but PO is still in approval: Triggers next-level notifications.

                Returns:
                    dict | bool | recordset: Notification action dict or standard confirm result.
                """
        receiptns = self._get_recipients_ids()
        first_level_receipents = receiptns[0]
        second_level_receipents = receiptns[1]
        for po in self:
            if not po:
                return False
            if self.env.user.id in second_level_receipents:
                po.approval_state = 'second_approval'
                body = _('Second approval by %s . Approved at %s .',
                         self.env.user.name,
                         fields.Datetime.now())
                self.message_post(body=body,
                                  message_type='notification')
                return super().button_confirm()
            elif po.approval_state == 'waiting_approval' and self.env.user.id in first_level_receipents:
                po.approval_state = 'first_approval'
                body = _('First approval by %s . Approved at %s .',
                         self.env.user.name, fields.Datetime.now())
                self.message_post(body=body,
                                  message_type='notification')
                po.send_notification(second_level_receipents)
                self.create_confirmation_email(self)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': _("Approve request email has been sent"),
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
            elif po.approval_state == 'first_approval' and self.env.user.id not in second_level_receipents:
                po.send_notification(second_level_receipents)
                self.create_confirmation_email(self)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': _("Approve request email has been sent"),
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
            else:
                po.send_notification(first_level_receipents)
                self.create_confirmation_email(self)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'success',
                        'message': _("Approve request email has been sent"),
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }
    
    def send_notification(self, users_list):
        """
                Schedules a `mail.activity` of type 'QFQ Approval Required' for each user in `users_list`.

                Args:
                    users_list (list): List of user IDs to assign the approval activity.
                """
        for user_id in users_list:
            self.activity_schedule('po_confirm_restrictions.mail_po_notify', user_id=user_id,
                               note=f'RFQ  {self.name} Needs Approval ')

    def create_confirmation_email(self, po):
        """
                Sends HTML-styled approval request emails to relevant users based on PO approval state.

                Args:
                    po (recordset): The purchase order for which the email is being generated.

                Returns:
                    bool: True if emails were successfully created and sent.
                """
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Get alert recipients
        recipient_emails = self._get_recipients()
        confiremd_by = self.env.user.name
        # Convert project details to HTML
        body_html = self.convert_to_html(base_url, po, confiremd_by)
        email_temp = self.env.ref('po_confirm_restrictions.email_template_approval_notify').sudo()
        # Create and send email
        for email in recipient_emails:
            if email:
                mail = self.env['mail.mail'].sudo().create({
                    'subject': f'Order {po.name} Approval Request',
                    'body_html': body_html,
                    'email_to': email,
                    'email_from': po.company_id.srn_notification_email,

                })
                mail.sudo().send()
        return True

    @staticmethod
    def convert_to_html(base_url, po, confirmed_by):
        """
        Constructs the frontend URL to view the current purchase order in Odoo's web client.

        Returns:
            str: A string URL to the PO form view.
        """
        # Define CSS styles for consistent styling
        styles = """
            <style>
                .email-body {
                    font-family: Arial, sans-serif;
                    color: #333;
                }
                .email-content {
                    font-size: 16px;
                    color: #666;
                    margin-bottom: 10px;
                }
                .email-header {
                    font-size: 14px;
                }
                .email-link {
                    font-size: 12px;
                    color: #901790;
                    display: inline-block;
                    padding: 8px 12px;
                    text-decoration: none;
                    font-weight: 400;
                    background-color: #f2f2f2;
                    border-radius: 4px;
                    margin-top: 10px;
                }
                .email-link:hover {
                    background-color: #e2e2e2;
                }
                .email-button {
                    padding: 10px 20px;
                    font-size: 14px;
                    color: white;
                    background-color: #901790;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                }
                .email-button:hover {
                    background-color: #701170;
                }
            </style>
        """

        # Create HTML body with appropriate styling
        html_body = f"""
            {styles}
            <div class="email-body">
                <p class="email-header">Dear Ms./ Mrs./</p>
                <p class="email-content">Kindly be informed that:</p>
                <p class="email-content"><strong>Purchase Order:</strong> {po.name} </p>
                <p class="email-content">  requires your approval<strong>{confirmed_by}</strong>.</p>
                <a class="email-link" href="{base_url}/web#id={po.id}&model=purchase.order">
                    <button class="email-button">View Purchase Order</button>
                </a>
                 <p class="email-content">  Best Regards <strong></strong>.</p>
            </div>
        """

        return html_body

    def get_document_url(self):
        """
            Constructs the frontend URL to view the current purchase order in Odoo's web client.

            Returns:
                str: A string URL to the PO form view.
            """
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + "/web#id={po.id}&model=purchase.order"
        return url

    def _get_recipients(self):
        """
        Determines the email addresses of users who should be notified for approval based on
        the current `approval_state`.

        Returns:
            set: A set of user email strings.
        """
        first_group_xml_id = (
                'po_confirm_restrictions.group_first_level_po_confirmation_approval')
        second_group_xml_id = (
            'po_confirm_restrictions.group_second_level_po_confirmation_approval')
        first_recipient_group = self.env.ref(first_group_xml_id)
        second_recipient_group = self.env.ref(second_group_xml_id)
        recipient_group = first_recipient_group + second_recipient_group
        recipients = {user.partner_id.email for user in recipient_group.users if user}
        if self.approval_state == 'waiting_approval':
            return  {user.partner_id.email for user in first_recipient_group.users}
        if self.approval_state == 'first_approval':
            return  {user.partner_id.email for user in second_recipient_group.users}
        return {}

    def _get_recipients_ids(self):
        """
        Retrieves the user IDs of first-level and second-level approvers for activity scheduling.

        Returns:
            tuple: A tuple of two lists:
                - First-level user IDs
                - Second-level user IDs
        """
        first_group_xml_id = (
                'po_confirm_restrictions.group_first_level_po_confirmation_approval')
        second_group_xml_id = (
            'po_confirm_restrictions.group_second_level_po_confirmation_approval')

        first_recipient_group = self.env.ref(first_group_xml_id)
        second_recipient_group = self.env.ref(second_group_xml_id)

        recipients = [user.id for user in first_recipient_group.users if user], [user.id for user in second_recipient_group.users if user]
        return recipients

    @api.model
    def create_activity(self):
        """
            Creates a `mail.activity` for all applicable approval users related to this purchase order.

            Returns:
                recordset: The last created `mail.activity` record.
            """
        # Example data
        activity = None
        model_name = 'purchase.order'
        record_id = self.id
        po_object = self.env['purchase.order'].sudo().browse([record_id])
        summary = f'Follow-up {po_object.name} Confirmation'
        note = 'Kindly Mark Activity as Done Or Approve PO Validation.'
        user_ids = self._get_recipients_ids()
        activity_type = self.env.ref("mail.mail_activity_data_todo", False)
        if not activity_type:
            raise ValueError("Activity Type not found: {}".format(activity_type))
        # Create the activity
        for user_id in user_ids:
            activity = self.env['mail.activity'].sudo().create({
                'res_model_id': self.env['ir.model']._get_id(model_name),
                'res_id': record_id,
                'activity_type_id': activity_type.id,
                'summary': summary,
                'note': note,
                'user_id': user_id,
            })
            self.related_activity_id = activity
        return activity

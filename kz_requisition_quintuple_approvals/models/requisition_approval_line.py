# -*- coding: utf-8 -*-
from odoo import models, fields, api


class RequisitionApprovalLine(models.Model):
    """
    Model to represent each step in a requisition approval flow.

    This model tracks approval/rejection actions on a requisition,
    the users involved in each stage, and automates follow-up notifications
    based on a configurable period (requisition_days_reminder).
    """

    _name = 'requisition.approval.line'
    _description = 'Requisition Approval Line'

    line_date = fields.Datetime(
        string='Date',
        default=fields.Datetime.now(),
        help="Timestamp of when this line entry was created."
    )

    description = fields.Text(
        string='Description',
        help="Optional description or note for this approval line."
    )

    requester = fields.Many2one(
        'res.users',
        string='Requester',
        help="User who requested the approval for this line."
    )

    state = fields.Selection([
        ('request', 'Approval Request'),
        ('approval', 'Approved'),
        ('rejection', 'Rejection'),
    ], string='Type', help="Current state of the approval line.")

    approver_id = fields.Many2one(
        'res.users',
        string='Approved by',
        help="User who approved this line."
    )

    rejecter_id = fields.Many2one(
        'res.users',
        string='Rejected by',
        help="User who rejected this line."
    )

    send_to = fields.Many2many(
        comodel_name='res.users',
        string='Sent to',
        help="Users to whom the approval request was sent."
    )

    requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisition',
        ondelete='cascade',
        help="The requisition associated with this approval line."
    )

    approved = fields.Boolean(
        string='Approved?',
        help="Flag indicating whether this line has been approved."
    )

    rejected = fields.Boolean(
        string='Rejected?',
        help="Flag indicating whether this line has been rejected."
    )

    last_notification = fields.Datetime(
        string='Last Notification',
        default=fields.Datetime.now(),
        help="Datetime of the last notification sent for this approval line."
    )

    @api.model
    def _send_notification(self):
        """
        Scheduled method to send email and activity notifications
        to users who haven't responded to a requisition approval request.

        It uses the company-level configuration 'requisition_days_reminder'
        to determine if a reminder should be sent.
        """
        notification_period = self.env.company.requisition_days_reminder
        lines_with_no_decision = self.env['requisition.approval.line'].sudo().search([
            ('approved', '=', False),
            ('rejected', '=', False),
            ('state', '=', 'request')
        ])

        for line in lines_with_no_decision:
            # Check if notification period has passed
            if (fields.Datetime.now() - line.last_notification).days >= notification_period:
                line.notify_group(line.send_to)
                line.last_notification = fields.Datetime.now()

    def notify_group(self, users):
        """
        Notify a group of users by scheduling an activity and sending an email reminder.

        :param users: recordset of `res.users` to notify.
        """
        if users:
            for user in users:
                self.action_send_reminder_approval_email(user, "New Requisition needs approval")

                # Schedule a system activity for the user to act upon the requisition
                self.requisition_id.activity_schedule(
                    'kz_requisition_quintuple_approvals.mail_requisition_approval',
                    user_id=user.id,
                    note=f'Requisition {self.requisition_id.name} Needs Approval'
                )

    def action_send_reminder_approval_email(self, user, message):
        """
        Sends a styled HTML email to a specific user as a reminder to approve a requisition.

        :param user: `res.users` record to whom the email will be sent
        :param message: message body to include in the email content
        """
        for requisition in self.requisition_id:
            if user.email:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                requisition_url = (
                    f"{base_url}/web#id={requisition.id}&model=material.purchase.requisition&view_type=form"
                )

                subject = f"Requisition: {requisition.name}"
                body_html = f"""
                    <p>Dear Mr {user.name},</p>
                    <p>{message}</p>
                    <p>Please click the button below to view the requisition:</p>
                    <p>
                        <a href="{requisition_url}" style="
                            background-color: #4CAF50;
                            color: white;
                            padding: 10px 20px;
                            text-align: center;
                            text-decoration: none;
                            display: inline-block;
                            font-size: 16px;
                            border-radius: 5px;">
                            View Requisition
                        </a>
                    </p>
                    <p>Best regards,<br/>{requisition.env.user.name}</p>
                """

                mail_values = {
                    'subject': subject,
                    'email_from': requisition.company_id.srn_notification_email,
                    'body_html': body_html,
                    'email_to': user.email,
                    'author_id': self.env.user.partner_id.id,
                }

                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.sudo().send()

                # Post internal message to requisition chatter for audit trail
                requisition.message_post(
                    body=f"Reminder email sent to {user.name} with requisition link."
                )

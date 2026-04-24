# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ServiceReceipt(models.Model):
    _inherit = 'service.receipt'

    show_end_user_button = fields.Boolean(
        string='',
        required=False, compute='_compute_show_button')

    last_sign = fields.Selection(
        string='Last_sign',
        selection=[('1', '1'),
                   ('2', '2'), ('3', '3')],
        required=False, )
    first_sign_sent = fields.Boolean(
        string='First_sign_sent',
        required=False, copy=False)

    second_sign_sent = fields.Boolean(
        string='Second_sign_sent',
        required=False, copy=False)
    third_sign_sent = fields.Boolean(
        string='third_sign_sent',
        required=False, copy=False)

    ens_users_ids = fields.Many2many(
        comodel_name='res.users',
        string='End Users', copy=False)

    def _compute_show_button(self):
        for rec in self:
            if rec.create_uid.id == rec.env.user.id:
                rec.show_end_user_button = True
            else:
                rec.show_end_user_button = False

    def notify_end_users(self):
        if not self.ens_users_ids:
            raise ValidationError(_("Select End Users"))
        message = f"Service Receipt {self.name} require signature"

        self.notify_users(self.ens_users_ids, message)
        self.first_sign_sent = True

    @api.onchange('end_user_signature')
    def change_end_user_signature(self):
        if self.end_user_signature:
            if self.env.user.id not in self.ens_users_ids.ids:
                raise UserError(_("You are not allowed to sign this SRN"))
            self.end_user_id = self.env.user.id

    @api.onchange('procurement_department_signature')
    def change_procurement_department_user_id(self):
        if self.procurement_department_signature:
            if not self.env.user.has_group('srn_reciept_kaizen.service_receipt_procurement'):
                raise UserError(_("You are not allowed to sign this SRN"))
            self.procurement_department_user_id = self.env.user.id

    @api.onchange('department_head_signature')
    def change_department_head_user_id(self):
        if self.department_head_signature:
            if not self.env.user.has_group('srn_reciept_kaizen.service_receipt_dep_manager'):
                raise UserError(_("You are not allowed to sign this SRN"))
            self.department_head_user_id = self.env.user.id

    def write(self, vals):
        users = []
        srn_admin_group = self.env.ref('skit_srn_receipt.srn_admin')
        users += srn_admin_group.users.ids
        if vals.get('end_user_signature'):
            if vals.get('end_user_signature') == '' and self.end_user_signature:
                users.append(self.end_user_id.id)
                if not self.env.user.id in users:
                    raise UserError(_("only user who signed and SRN admin can remove signature "))
        if vals.get('procurement_department_signature'):
            if vals.get(
                    'procurement_department_signature') == '' and self.procurement_department_signature:
                users.append(self.procurement_department_user_id.id)
                if not self.env.user.id in users:
                    raise UserError(_("only user who signed and SRN admin can remove signature "))
        if vals.get('department_head_signature'):
            if vals.get('department_head_signature') == '' and self.department_head_signature:
                users.append(self.department_head_user_id.id)
                if not self.env.user.id in users:
                    raise UserError(_("only user who signed and SRN admin can remove signature "))
        res = super().write(vals)
        return res

    def notify_procurement(self):
        if self.end_user_signature:
            self.second_sign_sent = True

            approve_group = self.env.ref('srn_reciept_kaizen.service_receipt_procurement')
            users = approve_group.users
            message = f"Service Receipt {self.name} require signature"
            self.notify_users(users, message)

    def notify_dep_head(self):
        if self.procurement_department_signature:
            self.third_sign_sent = True
            approve_group = self.env.ref('srn_reciept_kaizen.service_receipt_dep_manager')
            users = approve_group.users
            message = f"Service Receipt {self.name} require signature"
            self.notify_users(users, message)

    def notify_users(self, users, message):
        service = self
        if service:
            service = service[0]
        for user in users:
            message = f"Service Receipt {self.name} requires signature"
            service.action_signature_email(user, message)
            # self.action_signature_email(user, message)
            service.activity_schedule('srn_reciept_kaizen.mail_service_sign', user_id=user.id,
                                      note=message)

    def action_signature_email(self, user, message):
        for rec in self:
            if user.email:
                # Get the base URL for generating the requisition link
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                requisition_url = f"{base_url}/web#id={rec.id}&model=service.receipt&view_type=form"

                # Email subject and body with user's name and a button for the requisition link
                subject = f"Service Receipt: {rec.name} signature"
                body_html = f"""
                       <p>Dear Mr {user.name},</p>
                       <p>{message}</p>
                       <p>Please click the button below to view the service receipt:</p>
                       <p>
                           <a href="{requisition_url}" style="background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; text-decoration: none; display: inline-block; font-size: 16px; border-radius: 5px;">
                               View Service receipt
                           </a>
                       </p>
                       <p>Best regards \n {rec.env.user.name}</p>
                   """

                # Prepare email values
                mail_values = {
                    'subject': subject,
                    'email_from': self.company_id.srn_notification_email,
                    'body_html': body_html,
                    'email_to': user.email,  # Email of the passed user object
                    'author_id': self.env.user.partner_id.id,  # Current user as sender
                }

                # Send the email
                mail = self.env['mail.mail'].sudo().create(mail_values)
                mail.sudo().send()

    def clear_signature(self):
        users = []
        srn_admin_group = self.env.ref('skit_srn_receipt.srn_admin')
        users += srn_admin_group.users.ids
        field_name = self.env.context.get('field_name')
        if field_name:
            if field_name == 'end_user_signature':
                users.append(self.end_user_id.id)
                if not self.env.user.id in users:
                    raise UserError(_("only user who signed and SRN admin can remove signature "))
            if field_name == 'procurement_department_signature':
                users.append(self.procurement_department_user_id.id)
                if not self.env.user.id in users:
                    raise UserError(_("only user who signed and SRN admin can remove signature "))

            if field_name == 'department_head_signature':
                users.append(self.department_head_user_id.id)
                if not self.env.user.id in users:
                    raise UserError(_("only user who signed and SRN admin can remove signature "))

            setattr(self, field_name, False)

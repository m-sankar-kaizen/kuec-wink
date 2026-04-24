# -*- coding: utf-8 -*-
import logging

from datetime import timedelta

from odoo import models, fields, _, Command, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_portal = fields.Boolean(string='Is Portal')
    company_size_id = fields.Many2one('company.size', string='Company Size')
    other_partner_category = fields.Char(
        string='Other Category',
        help="Other partner category, only visible the view if the portal user fills it"
    )
    offered_product_ids = fields.Many2many('product.template', string='Offered Product')
    other_offered_product = fields.Char(
        string='Other Offered Product',
        help="Other offered product, only visible the view if the portal user fills it"
    )
    other_partner_certificates = fields.Char(
        string='Other Certificates',
        help="Other offered product, only visible the view if the portal user fills it"
    )
    years_of_experience = fields.Selection(
        [
            ('lt_2', 'Less than 2 Years'),
            ('2_to_5', '2-5 Years'),
            ('6_to_10', '6-10 Years'),
            ('10_plus', '10+ Years'),
        ],
        string='Years of Experience',
        help="Years of experience, Used for Vendor registration"
    )
    has_worked_for_govt = fields.Boolean(string='Has Worked For Govt',
                                         help="Has Worked For Govt or Large Enterprise?")
    worked_company_ids = fields.One2many('worked.company', 'partner_id', string='Worked Company')
    delivery_capacity = fields.Selection(
        [
            ('local', 'Local Only'),
            ('regional', 'Regional Only (GCC or MENA)'),
            ('international', 'International'),
        ],
        string='Delivery Capacity',
        help="Delivery capacity, Used for Vendor registration"
    )
    iso_certification_ids = fields.Many2many('iso.certification', string='ISO Certifications')
    icv_score = fields.Float(string="ICV Certificate Score %", help="ICV %, Used for Vendor registration",
                             default=1.0)
    # Contact Person Details
    contact_name = fields.Char("Contact Name")
    contact_function = fields.Char("Contact Job Position")
    contact_phone = fields.Char("Contact Phone")
    contact_email = fields.Char("Contact Email")
    vendor_evaluation_ids = fields.One2many('vendor.evaluation', 'partner_id',
                                            string='Vendor Evaluations')
    vendor_score = fields.Float(string='Vendor Score', compute='_compute_vendor_evaluation',
                                store=True)
    evaluated_date = fields.Datetime(string='Evaluated Date', compute='_compute_vendor_evaluation',
                                     store=True)
    evaluation_rating = fields.Selection(
        selection=[
            ('0', '0%'),
            ('1', '20%'),
            ('2', '40%'),
            ('3', '60%'),
            ('4', '80%'),
            ('5', '100%'),
        ],
        default='0',
        store=True,
        string='Evaluation Rating',
        compute='_compute_vendor_evaluation'
    )
    vendor_evaluation_conf_id = fields.Many2one(
        'vendor.evaluation.conf',
        string='Vendor Evaluation',
        check_company=True
    )
    generate_evaluation = fields.Boolean(string='Need Evaluation', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'vendor_evaluation_conf_id' in fields_list:
            evaluation = self.env['vendor.evaluation.conf'].search([
                ('company_id', '=', self.env.company.id),
                ('state', '=', 'active'),
            ], order='sequence asc', limit=1)
            if evaluation:
                res['vendor_evaluation_conf_id'] = evaluation.id
        return res

    @api.constrains('icv_score')
    def _check_icv_score(self):
        for rec in self:
            if rec.icv_score < 0 or rec.icv_score > 100:
                raise ValidationError(_("ICV % must be between 0 and 100."))

    def _get_vendor_evaluation_company_ids(self):
        return self.env['res.company'].sudo().search([])

    @api.model
    def cron_vendor_evaluation_reminder(self):

        today = fields.Date.today()
        _logger.info("Starting Vendor Evaluation Reminder Cron for date: %s", today)

        company_ids = self._get_vendor_evaluation_company_ids()
        Template = self.env.ref('kaz_vendor_management.mail_template_vendor_evaluation_reminder')

        for company in company_ids:
            reminder_days = company.vendor_evaluation_reminder_days or 0
            expired_date = today - timedelta(days=reminder_days)
            _logger.info("Checking company %s (ID: %s) with reminder_days=%s, expired_date=%s",
                         company.name, company.id, reminder_days, expired_date)

            vendors = self.env['res.partner'].search([
                ('is_vendor', '=', True),
                ('company_id', '=', company.id),
                '|',
                ('evaluated_date', '=', False),
                ('evaluated_date', '<=', expired_date),
            ])
            if not vendors:
                continue

            # Mark them for evaluation
            vendors.write({'generate_evaluation': True})

            # Send email to purchase managers
            managers = self.env['res.users'].search([
                ('groups_id', 'in', self.env.ref('purchase.group_purchase_manager').id),
                ('company_ids', 'in', company.id),
            ])

            for manager in managers:
                Template.with_user(self.env.uid).sudo().with_context(
                    {'notification_vendors': vendors.read(['name', 'evaluated_date'])}
                ).send_mail(
                    company.id,
                    force_send=True,
                    email_values={'email_to': manager.partner_id.email},
                )

        _logger.info("Vendor Evaluation Reminder Cron finished")

    def action_generate_evaluation(self):
        self.ensure_one()
        self.env['vendor.evaluation'].create({
            'partner_id': self.id,
        })
        self.generate_evaluation = False
        return self.action_vendor_open_evaluation()

    def action_vendor_open_evaluation(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Vendor Evaluation"),
            'view_mode': 'list,form',
            'res_model': 'vendor.evaluation',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('id', 'in', self.vendor_evaluation_ids.ids)],
            'order': 'create_date desc',
        }

    @api.depends('vendor_evaluation_ids.state', 'vendor_evaluation_ids.total_score')
    def _compute_vendor_evaluation(self):
        for record in self:
            # Get last created evaluation
            last_eval = record.vendor_evaluation_ids.sorted('create_date', reverse=True)[:1]

            if last_eval and last_eval.state == 'evaluated':
                record.vendor_score = last_eval.total_score
                record.evaluated_date = last_eval.write_date
                record.evaluation_rating = last_eval.rating
            else:
                record.vendor_score = 0.0
                record.evaluated_date = record.evaluated_date or False
                record.evaluation_rating = '0'

    def action_pre_approve(self):
        super().action_pre_approve()
        if self.is_portal:
            self.grant_portal_access()

    def grant_portal_access(self):
        """Grant portal access to this partner with proper Command usage."""
        self.ensure_one()

        group_portal = self.env.ref('base.group_portal')
        user_types_category = self.env.ref('base.module_category_user_type')

        # Find all User Type groups (Internal, Portal, Public)
        user_type_groups = self.env['res.groups'].sudo().search([
            ('category_id', '=', user_types_category.id)
        ])

        # Get or create user
        user_sudo = self.user_ids.sudo()[:1]
        created_now = False
        if not user_sudo:
            company = self.company_id or self.env.company
            user_sudo = self.with_company(company.id).env['res.users'].sudo().create({
                'name': self.name,
                'login': self.email,
                'partner_id': self.id,
                'company_ids': [Command.set([company.id])],
                'company_id': company.id,
            })
            created_now = True

        user_sudo.write({
            'groups_id': [
                *(Command.unlink(gid) for gid in user_type_groups.ids),
                Command.link(group_portal.id),
            ],
            'active': True,
        })

        # prepare invitation/signup
        user_sudo.partner_id.signup_prepare()

        if created_now:
            user_sudo.with_context(active_test=True).partner_id.sudo().message_post(
                body=_("Portal access has been granted to this partner.")
            )
            user_sudo.with_context(create_user=1).action_reset_password()

    def action_revoke_access(self):
        """Remove the user of the partner from the portal group.
        If the user was only in the portal group, we archive it.
        """
        self.ensure_one()
        if not self.is_portal:
            raise UserError(
                _('The partner "%s" has no portal access or is internal.', self.partner_id.name))

        group_portal = self.env.ref('base.group_portal')
        group_public = self.env.ref('base.group_public')
        # Remove the sign up token, so it can not be used
        self.sudo().signup_type = None

        user_sudo = self.user_ids.sudo()[:1]

        # remove the user from the portal group
        if user_sudo and user_sudo._is_portal():
            user_sudo.write(
                {'groups_id': [Command.unlink(group_portal.id), Command.link(group_public.id)],
                 'active': False})

    def _create_activity_and_send_registration_success_mail(self):
        self = self.sudo()
        self.ensure_one()

        # Get all users in the group
        approver_group = self.env.ref("kaz_contact_approval.group_contact_pre_approver")
        _logger.info(f"Position 1 - 1")
        if not approver_group:
            self.sudo().message_post(body="⚠️ Contact approval group not found.")
            return
        _logger.info(f"Position 1 - 2")
        users = approver_group.sudo().users
        if not users:
            self.message_post(body="⚠️ No users found in the contact approval group.")
            return

        _logger.info(f"Position 1 - 3")

        # Get the activity type
        activity_type = self.env.ref("kaz_contact_approval.mail_activity_type_contact_approval")
        if not activity_type:
            self.message_post(body="⚠️ Contact approval activity type not found.")
            return

        _logger.info(f"Position 1 - 4")

        # Create activity for each user
        for user in users:
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=user.id,
                summary="Review and approve contact details",
                note="Please review and approve this contact registration request."
            )

        _logger.info(f"Position 1 - 5")

        self._send_registration_success_mail()

    def _send_registration_success_mail(self):
        self = self.sudo()
        self.ensure_one()

        _logger.info(f"Position 2 - 1")

        template = self.env.ref(
            "kaz_vendor_management.mail_template_registration_success",
            raise_if_not_found=False
        )

        _logger.info(f"Position 2 - 2")
        if template:
            template.sudo().send_mail(self.id, force_send=True)
        else:
            # Log a message in chatter
            self.message_post(
                body=(
                    "⚠️ Registration Email Not Sent\n"
                    "The mail template Vendor Registration Success "
                    "could not be found."
                )
            )

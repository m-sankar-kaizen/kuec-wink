# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, api

_logger = logging.getLogger(__name__)


class PartnerAttachmentLine(models.Model):
    _name = 'partner.attachment.line'
    _inherit = 'attachment.line.mixin'
    _description = 'Partner Attachment Line'
    _check_company_auto = True

    partner_id = fields.Many2one('res.partner')
    expiry_date = fields.Date('Expiry Date')
    attachment_link = fields.Char('Attachment Link')
    ir_attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    is_expired = fields.Boolean('Expired', compute='_compute_is_expired')

    def _compute_is_expired(self):
        today = fields.Date.today()
        for record in self:
            record.is_expired = bool(record.expiry_date and record.expiry_date < today)

    def _get_target_company_ids(self):
        """
        Helper function to return the list of company IDs to process.
        Modify logic here to fetch from config settings or specific hardcoded IDs.
        """
        # Example 3 (Default): Return all active companies
        return self.env['res.company'].sudo().search([]).ids

    @api.model
    def action_attachment_expiry_reminder(self):
        """Cron to notify users about attachments that are about to expire"""
        _logger.info("Started Cron for partner attachment expiry reminder")
        # 1. Call the helper function
        company_ids = self._get_target_company_ids()

        if not company_ids:
            _logger.info("No companies found or configured for attachment expiry processing.")
            return

        # 2. Update SQL to filter by these Company IDs
        # We use 'AND pal.company_id IN %s'
        query = """SELECT 
                        rp.id AS partner_id,
                        rp.name AS partner_name,
                        rp.is_vendor,
                        rp.is_customer,
                        pal.company_id,
                        c.name AS company_name,
                        ARRAY_AGG(pal.id) AS attachment_line_ids,
                        ARRAY_AGG(pal.expiry_date) AS expiry_dates
                    FROM partner_attachment_line pal
                    JOIN res_partner rp ON rp.id = pal.partner_id
                    JOIN res_company c ON c.id = pal.company_id
                    WHERE rp.state = 'approved'
                      AND pal.company_id IN %s
                      AND pal.expiry_date_required = TRUE
                      AND pal.expiry_date IS NOT NULL
                      AND pal.expiry_date <= CURRENT_DATE + (c.attachment_expiry_reminder || ' days')::interval
                      AND pal.expiry_date >= CURRENT_DATE
                    GROUP BY rp.id, rp.name, rp.is_vendor, rp.is_customer, pal.company_id, c.name
                """

        # 3. Pass the tuple of IDs as a parameter to execute
        # Note: We wrap tuple(company_ids) inside another tuple for the params argument
        self.env.cr.execute(query, (tuple(company_ids),))
        lines = self.env.cr.dictfetchall()
        if not lines:
            _logger.info("No attachments expiring today.")
            return
        template = self.env.ref('kaz_contact_approval.expired_document_email_template')

        for line in lines:
            partner = self.env['res.partner'].browse(line['partner_id'])
            is_vendor = line['is_vendor']
            is_customer = line['is_customer']
            cc_users = self.env['res.users']

            if is_vendor:
                cc_users |= self.env.ref('purchase.group_purchase_manager').users
            if is_customer:
                cc_users |= self.env.ref('sales_team.group_sale_manager').users

            email_cc = ','.join(cc_users.mapped('email'))

            attachments = self.env['partner.attachment.line'].search_read(
                domain=[('id', 'in', line['attachment_line_ids'])],
                fields=['name', 'expiry_date'],
            )
            template.with_context(attachments=attachments).send_mail(
                partner.id,
                force_send=True,
                email_values={'email_cc': email_cc}
            )
            attachment_names = ', '.join([att['name'] for att in attachments])
            partner.message_post(
                body=(
                    f"The following document(s) are about to expire: {attachment_names}. "
                    f"An email notification has been sent to the partner and related users."
                ),
                subject="Attachment Expiry Notification",
                message_type='notification',
            )

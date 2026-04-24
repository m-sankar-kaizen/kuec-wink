from odoo import models, tools
import logging

_logger = logging.getLogger(__name__)

class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _send(self, auto_commit=False, raise_exception=False, smtp_session=None,
              alias_domain_id=False, mail_server=False, post_send_callback=None):

        for mail in self:
            if not mail.email_from:
                fallback_email = False

                # 1️⃣ Try to take from mail server username
                if mail.mail_server_id and mail.mail_server_id.smtp_user:
                    fallback_email = mail.mail_server_id.smtp_user

                # 2️⃣ Otherwise use hardcoded fallback
                if not fallback_email:
                    fallback_email = self.env.user.partner_id.email or mail.record_company_id.default_from_email or self.env.company.default_from_email

                _logger.info(
                    "Email From missing for mail ID %s. Using fallback: %s",
                    mail.id, fallback_email
                )

                mail.email_from = fallback_email
        # Call original method
        return super()._send(
            auto_commit=auto_commit,
            raise_exception=raise_exception,
            smtp_session=smtp_session,
            alias_domain_id=alias_domain_id,
            mail_server=mail_server,
            post_send_callback=post_send_callback
        )
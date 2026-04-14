# -*- coding: utf-8 -*-
# ISSUE-001: Post-init hook for empty-string normalization (ORM only; no raw SQL).
# ISSUE-009: Odoo 18 calls post_init_hook(env); use savepoint + batching; never close cr.
# WINK-RATE: Override helpdesk rating template with 5-face design (bypasses noupdate flag).

BATCH_SIZE = 2000

# WINK 5-face body for helpdesk rating email.
# Stored as a string and written directly so noupdate on the helpdesk template is bypassed.
_HELPDESK_RATING_BODY = """<div>
    <t t-set="access_token" t-value="object._rating_get_access_token()"/>
    <t t-set="partner" t-value="object._rating_get_partner()"/>
    <t t-set="base_url" t-value="object.get_base_url()"/>
    <table border="0" cellpadding="0" cellspacing="0" width="590" style="width:100%;max-width:590px;margin:0 auto;font-family:Arial,sans-serif;">
    <tbody>
        <tr><td valign="top" style="font-size:13px;padding-bottom:16px;">
            <t t-if="partner.name">Hello <t t-out="partner.name or ''">Customer</t>,<br/><br/></t>
            <t t-else="">Hello,<br/><br/></t>
            Thank you for contacting us. We would love to hear your feedback on how we handled your ticket
            <strong t-out="object.name or ''">ticket name</strong>.
        </td></tr>
        <tr><td style="text-align:center;padding:24px 0 8px 0;">
            <p style="font-size:15px;font-weight:bold;margin:0 0 6px 0;">Rate your experience</p>
            <p style="font-size:12px;color:#888;margin:0 0 20px 0;">Click on the face that best reflects your experience</p>
            <table border="0" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                    <td style="padding:0 10px;text-align:center;vertical-align:top;">
                        <a t-attf-href="/rate/{{ access_token }}/1" style="text-decoration:none;display:block;">
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_face_1.svg" width="65" height="65" alt="Very Bad" style="display:block;margin:0 auto 6px auto;"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <div style="font-size:11px;color:#555;margin-top:4px;">Very Bad</div>
                        </a>
                    </td>
                    <td style="padding:0 10px;text-align:center;vertical-align:top;">
                        <a t-attf-href="/rate/{{ access_token }}/2" style="text-decoration:none;display:block;">
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_face_2.svg" width="65" height="65" alt="Poor" style="display:block;margin:0 auto 6px auto;"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <div style="font-size:11px;color:#555;margin-top:4px;">Poor</div>
                        </a>
                    </td>
                    <td style="padding:0 10px;text-align:center;vertical-align:top;">
                        <a t-attf-href="/rate/{{ access_token }}/3" style="text-decoration:none;display:block;">
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_face_3.svg" width="65" height="65" alt="Medium" style="display:block;margin:0 auto 6px auto;"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <div style="font-size:11px;color:#555;margin-top:4px;">Medium</div>
                        </a>
                    </td>
                    <td style="padding:0 10px;text-align:center;vertical-align:top;">
                        <a t-attf-href="/rate/{{ access_token }}/4" style="text-decoration:none;display:block;">
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_face_4.svg" width="65" height="65" alt="Good" style="display:block;margin:0 auto 6px auto;"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_off.svg" width="14" height="14" alt="-"/>
                            <div style="font-size:11px;color:#555;margin-top:4px;">Good</div>
                        </a>
                    </td>
                    <td style="padding:0 10px;text-align:center;vertical-align:top;">
                        <a t-attf-href="/rate/{{ access_token }}/5" style="text-decoration:none;display:block;">
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_face_5.svg" width="65" height="65" alt="Excellent" style="display:block;margin:0 auto 6px auto;"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <img t-attf-src="{{ base_url }}/kuec_service_catalogue/static/src/img/wink_star_on.svg" width="14" height="14" alt="*"/>
                            <div style="font-size:11px;color:#555;margin-top:4px;">Excellent</div>
                        </a>
                    </td>
                </tr>
            </table>
        </td></tr>
        <tr><td valign="top" style="font-size:13px;padding-top:20px;color:#444;">
            We appreciate your feedback. It helps us improve continuously.<br/>
            <span style="font-size:11px;color:#aaa;">This survey was sent because your support ticket has been resolved.</span>
        </td></tr>
        <tr><td style="padding-top:16px;font-size:13px;">Best regards,<br/><strong><t t-out="object.company_id.name or ''">KUEC</t></strong></td></tr>
    </tbody>
    </table>
</div>"""


def post_init_hook(env):
    """
    Workflow:
        1. Normalize empty strings to NULL for passport_number and emirates_id on
           kuec.employee.directory. Idempotent; batched to avoid long locks.
        2. Override helpdesk rating email template with WINK 5-face design.
           Written directly via ORM to bypass the noupdate flag on the helpdesk record.
    """
    # ISSUE-001: Employee directory empty-string normalization
    with env.cr.savepoint():
        Model = env['kuec.employee.directory'].sudo()
        for field in ('passport_number', 'emirates_id'):
            while True:
                records = Model.search([(field, '=', '')], limit=BATCH_SIZE)
                if not records:
                    break
                records.write({field: False})

    # WINK-RATE: Force-update helpdesk rating template with 5-face design.
    # Uses env.ref() + direct write() to bypass ir.model.data noupdate=True on the
    # helpdesk module's template record.
    with env.cr.savepoint():
        try:
            tmpl = env.ref('helpdesk.rating_ticket_request_email_template', raise_if_not_found=False)
            if tmpl:
                tmpl.sudo().write({'body_html': _HELPDESK_RATING_BODY})
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'WINK-RATE: Could not update helpdesk rating template — helpdesk may not be installed.',
                exc_info=True,
            )

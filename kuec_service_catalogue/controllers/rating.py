# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.tools.misc import get_lang
from odoo.addons.rating.controllers.main import Rating


class WinkRating(Rating):
    """Override Odoo's rating controller to accept 1–5 scale instead of 1/3/5."""

    @http.route('/rate/<string:token>/<int:rate>', type='http', auth='public', website=True)
    def action_open_rating(self, token, rate, **kwargs):
        """Accept rating values 1–5 and render WINK 5-face landing page."""
        if rate not in (1, 2, 3, 4, 5):
            return request.not_found()

        rating, record_sudo = self._get_rating_and_record(token)

        if not request.env.user._is_public() and \
                request.env.user.partner_id.commercial_partner_id != rating.partner_id.commercial_partner_id:
            return request.render('rating.rating_external_page_invalid_partner', {
                'model_name': request.env['ir.model']._get(rating.res_model).display_name,
                'name': record_sudo.display_name,
                'web_base_url': rating.get_base_url(),
            })

        lang = rating.partner_id.lang or get_lang(request.env).code
        rate_names = {
            1: request.env._('Very Bad'),
            2: request.env._('Poor'),
            3: request.env._('Medium'),
            4: request.env._('Good'),
            5: request.env._('Excellent'),
        }
        return request.env['ir.ui.view'].with_context(lang=lang)._render_template(
            'kuec_service_catalogue.wink_rating_page_submit', {
                'rating': rating,
                'token': token,
                'rate_names': rate_names,
                'rate': rate,
            }
        )

    @http.route(['/rate/<string:token>/submit_feedback'], type='http', auth='public', methods=['post', 'get'], website=True)
    def action_submit_rating(self, token, rate=0, **kwargs):
        """Accept 1–5 rating values on submit."""
        rating, record_sudo = self._get_rating_and_record(token)
        if request.httprequest.method == 'POST':
            rate = int(rate)
            if rate not in (1, 2, 3, 4, 5):
                return request.not_found()
            record_sudo.rating_apply(
                rate,
                rating=rating,
                feedback=kwargs.get('feedback'),
                subtype_xmlid=None,
            )
            # I-6: Low-score escalation — post warning to task chatter for coordinator
            if rate <= 2:
                try:
                    feedback_text = kwargs.get('feedback', '').strip() or 'None provided'
                    record_sudo.message_post(
                        body=(
                            "⚠️ Low rating (%d/5) received for service <b>%s</b>.<br/>"
                            "Customer feedback: %s"
                        ) % (rate, record_sudo.name, feedback_text),
                        message_type='comment',
                        subtype_xmlid='mail.mt_note',
                    )
                except Exception:
                    pass

        lang = rating.partner_id.lang or get_lang(request.env).code
        return request.env['ir.ui.view'].with_context(lang=lang)._render_template(
            'rating.rating_external_page_view', {
                'web_base_url': rating.get_base_url(),
                'rating': rating,
            }
        )

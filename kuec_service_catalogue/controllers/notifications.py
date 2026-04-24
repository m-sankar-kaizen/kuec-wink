# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.http import request
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

_NOTIF_LIMIT = 30
_TYPE_ICON = {
    'email': 'fa-envelope',
    'comment': 'fa-comment',
    'notification': 'fa-bell',
}


class WinkPortalNotifications(http.Controller):
    """JSON endpoints powering the WINK portal notification bell.

    Workflow:
        1. /my/notifications/count  — fast unread badge count (polled every 30 s)
        2. /my/notifications/list   — full notification list for the dropdown panel
        3. /my/notifications/read   — mark one, many, or all notifications as read
    """

    def _get_portal_partner(self):
        """Return the commercial partner for the current portal user."""
        return request.env.user.partner_id.commercial_partner_id

    def _get_record_ids(self, partner):
        """Find all WINK sale order IDs and linked task IDs for a partner.

        Returns:
            tuple: (order_ids list, task_ids list)
        """
        order_ids = request.env['sale.order'].sudo().search([
            ('partner_id', 'child_of', partner.id),
            ('wink_is_portal_request', '=', True),
        ]).ids

        task_ids = []
        if order_ids:
            task_ids = request.env['project.task'].sudo().search([
                ('sale_order_id', 'in', order_ids),
            ]).ids

        return order_ids, task_ids

    def _build_record_domain(self, order_ids, task_ids):
        """Build the OR domain to filter by sale.order and/or project.task records."""
        if order_ids and task_ids:
            return [
                '|',
                '&', ('model', '=', 'sale.order'), ('res_id', 'in', order_ids),
                '&', ('model', '=', 'project.task'), ('res_id', 'in', task_ids),
            ]
        if order_ids:
            return [('model', '=', 'sale.order'), ('res_id', 'in', order_ids)]
        return [('model', '=', 'project.task'), ('res_id', 'in', task_ids)]

    def _build_activity_domain(self, order_ids, task_ids):
        """Build the OR domain for mail.activity (uses res_model, not model)."""
        if order_ids and task_ids:
            return [
                '|',
                '&', ('res_model', '=', 'sale.order'), ('res_id', 'in', order_ids),
                '&', ('res_model', '=', 'project.task'), ('res_id', 'in', task_ids),
            ]
        if order_ids:
            return [('res_model', '=', 'sale.order'), ('res_id', 'in', order_ids)]
        return [('res_model', '=', 'project.task'), ('res_id', 'in', task_ids)]

    def _get_notification_domain(self, partner):
        """Build the mail.message search domain for this partner's portal records.

        Returns:
            tuple: (order_ids list, domain list) — domain is empty list if nothing found.
        """
        order_ids, task_ids = self._get_record_ids(partner)

        if not order_ids and not task_ids:
            return [], []

        record_filter = self._build_record_domain(order_ids, task_ids)
        base = [
            ('message_type', 'in', ['comment', 'email', 'notification']),
            ('author_id', '!=', partner.id),
        ]

        return order_ids, record_filter + base

    def _get_pending_activities(self, order_ids, task_ids):
        """Return pending mail.activity records on the partner's WINK records."""
        if not order_ids and not task_ids:
            return request.env['mail.activity'].sudo().browse()
        domain = self._build_activity_domain(order_ids, task_ids)
        return request.env['mail.activity'].sudo().search(
            domain, limit=10, order='date_deadline asc'
        )

    def _get_read_message_ids(self, partner):
        """Return the set of message IDs already marked read by this partner."""
        reads = request.env['kuec.portal.notification'].sudo().search([
            ('partner_id', '=', partner.id),
            ('is_read', '=', True),
        ])
        return set(reads.mapped('message_id').ids)

    @http.route('/my/notifications/count', type='json', auth='user', website=True)
    def notification_count(self):
        """Return the count of unread notifications for the current portal user."""
        if request.env.user._is_public():
            return {'count': 0}
        try:
            partner = self._get_portal_partner()
            order_ids, task_ids = self._get_record_ids(partner)
            if not order_ids and not task_ids:
                return {'count': 0}

            # Unread chatter messages
            _, domain = self._get_notification_domain(partner)
            read_ids = self._get_read_message_ids(partner)
            messages = request.env['mail.message'].sudo().search(
                domain, order='date desc', limit=_NOTIF_LIMIT
            )
            unread_msgs = sum(1 for m in messages if m.id not in read_ids)

            # Pending activities
            activities = self._get_pending_activities(order_ids, task_ids)
            total = unread_msgs + len(activities)
            return {'count': total}
        except Exception:
            _logger.exception('notification_count failed')
            return {'count': 0}

    @http.route('/my/notifications/list', type='json', auth='user', website=True)
    def notification_list(self):
        """Return the list of recent notifications for the dropdown panel.

        Workflow:
            1. Fetch pending activities and prepend them (always shown as unread).
            2. Fetch recent chatter messages, skip those marked read.
        """
        if request.env.user._is_public():
            return {'notifications': []}
        try:
            partner = self._get_portal_partner()
            order_ids, task_ids = self._get_record_ids(partner)
            if not order_ids and not task_ids:
                return {'notifications': []}

            result = []

            # ── Pending activities (shown first, always unread) ──
            activities = self._get_pending_activities(order_ids, task_ids)
            for act in activities:
                link = self._resolve_activity_link(act, order_ids)
                note_text = html2plaintext(act.note or '').strip() if act.note else ''
                body = act.summary or note_text or act.activity_type_id.name or 'Pending action'
                if len(body) > 100:
                    body = body[:97] + '...'
                result.append({
                    'id': 'act_%s' % act.id,
                    'author': act.user_id.name or 'System',
                    'body': body,
                    'date': act.date_deadline.strftime('%d %b') if act.date_deadline else '',
                    'link': link,
                    'icon': 'fa-tasks',
                    'is_read': False,
                    'record_name': act.res_name or '',
                })

            # ── Chatter messages ──
            _, domain = self._get_notification_domain(partner)
            if domain:
                read_ids = self._get_read_message_ids(partner)
                messages = request.env['mail.message'].sudo().search(
                    domain, order='date desc', limit=_NOTIF_LIMIT
                )
                for msg in messages:
                    link = self._resolve_notification_link(msg, order_ids)
                    body_text = html2plaintext(msg.body or '').strip()
                    if len(body_text) > 100:
                        body_text = body_text[:97] + '...'
                    result.append({
                        'id': msg.id,
                        'author': msg.author_id.name or 'System',
                        'body': body_text,
                        'date': msg.date.strftime('%d %b, %H:%M') if msg.date else '',
                        'link': link,
                        'icon': _TYPE_ICON.get(msg.message_type, 'fa-bell'),
                        'is_read': msg.id in read_ids,
                        'record_name': msg.record_name or '',
                    })

            return {'notifications': result}
        except Exception:
            _logger.exception('notification_list failed')
            return {'notifications': []}

    def _resolve_notification_link(self, msg, order_ids):
        """Resolve the portal URL for a notification message, anchored to the chatter."""
        if msg.model == 'sale.order' and msg.res_id in order_ids:
            return '/my/requests/%s#wink-portal-chatter' % msg.res_id
        if msg.model == 'project.task':
            task = request.env['project.task'].sudo().browse(msg.res_id)
            if task.exists():
                return '/my/tasks/%s#task_chat' % task.id
        return '/my/requests'

    def _resolve_activity_link(self, act, order_ids):
        """Resolve the portal URL for a pending activity, anchored to the chatter."""
        if act.res_model == 'sale.order' and act.res_id in order_ids:
            return '/my/requests/%s#wink-portal-chatter' % act.res_id
        if act.res_model == 'project.task':
            task = request.env['project.task'].sudo().browse(act.res_id)
            if task.exists():
                return '/my/tasks/%s#task_chat' % task.id
        return '/my/requests'

    @http.route('/my/notifications/read', type='json', auth='user', website=True, methods=['POST'])
    def notification_mark_read(self, message_ids=None, mark_all=False):
        """Mark one, multiple, or all notifications as read.

        Activity IDs (prefixed 'act_') are ignored — activities clear when completed.

        Args:
            message_ids: list of mail.message IDs (integers only) to mark read.
            mark_all: if True, fetch and mark all message notifications read.

        Returns:
            dict: {'ok': bool}
        """
        if request.env.user._is_public():
            return {'ok': False}
        try:
            partner = self._get_portal_partner()
            Tracker = request.env['kuec.portal.notification'].sudo()

            if mark_all:
                _, domain = self._get_notification_domain(partner)
                if domain:
                    msgs = request.env['mail.message'].sudo().search(
                        domain, limit=_NOTIF_LIMIT
                    )
                    message_ids = msgs.ids
            else:
                # Filter to integers only — discard activity string IDs
                message_ids = [mid for mid in (message_ids or []) if isinstance(mid, int)]

            if not message_ids:
                return {'ok': True}

            existing = Tracker.search([
                ('partner_id', '=', partner.id),
                ('message_id', 'in', message_ids),
            ])
            existing.write({'is_read': True})
            marked_ids = set(existing.mapped('message_id').ids)
            new_ids = [mid for mid in message_ids if mid not in marked_ids]
            if new_ids:
                Tracker.create([
                    {'partner_id': partner.id, 'message_id': mid, 'is_read': True}
                    for mid in new_ids
                ])
            return {'ok': True}
        except Exception:
            _logger.exception('notification_mark_read failed')
            return {'ok': False}

# -*- coding: utf-8 -*-
from odoo import models, fields


class KuecPortalNotification(models.Model):
    """Lightweight read-state tracker for WINK portal notifications.

    One record per (partner, message) pair. Created and marked read
    when the portal user dismisses or clicks a notification.
    """
    _name = 'kuec.portal.notification'
    _description = 'WINK Portal Notification Read Tracker'
    _order = 'create_date desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Portal User',
        required=True,
        ondelete='cascade',
        index=True,
        help='The portal partner this read-state belongs to.',
    )
    message_id = fields.Many2one(
        'mail.message',
        string='Message',
        required=True,
        ondelete='cascade',
        index=True,
        help='The chatter message this notification references.',
    )
    is_read = fields.Boolean(
        string='Read',
        default=False,
        index=True,
        help='True once the portal user has dismissed or clicked the notification.',
    )

    _sql_constraints = [
        ('unique_partner_message', 'UNIQUE(partner_id, message_id)',
         'A notification tracker already exists for this partner and message.'),
    ]

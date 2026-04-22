# -*- coding: utf-8 -*-
import calendar

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

MONTH_SELECTION = [
    ('1', 'January'),
    ('2', 'February'),
    ('3', 'March'),
    ('4', 'April'),
    ('5', 'May'),
    ('6', 'June'),
    ('7', 'July'),
    ('8', 'August'),
    ('9', 'September'),
    ('10', 'October'),
    ('11', 'November'),
    ('12', 'December'),
]


class ResCompany(models.Model):
    _inherit = 'res.company'

    draft_pr_pa_notify_days = fields.Integer(
        string="Days Before Fiscal Year-End to Notify Draft PRs",
        default=30,
        help="Number of days in advance of fiscal year-end to notify responsible users about Draft PRs and PAs."
    )
    draft_pr_pa_notify_day = fields.Integer(
        string="Notification Day",
        default=1,
        required=True,
        help="Day of the month to notify users about draft PRs/PAs."
    )
    draft_pr_pa_notify_month = fields.Selection(
        MONTH_SELECTION,
        string="Notification Month",
        default='12',
        required=True,
        help="Month to notify users about draft PRs/PAs."
    )

    @api.constrains('draft_pr_pa_notify_day', 'draft_pr_pa_notify_month')
    def _check_notify_date(self):
        """Ensure day is valid for the selected month"""
        for rec in self:
            day = rec.draft_pr_pa_notify_day
            month = int(rec.draft_pr_pa_notify_month)
            year = fields.datetime.now().year  # temporary year for validation
            max_day = calendar.monthrange(year, month)[1]
            if day < 1 or day > max_day:
                raise ValidationError(
                    _("Invalid notification day %s for month %s.") % (day,
                                                                      rec.draft_pr_pa_notify_month)
                )

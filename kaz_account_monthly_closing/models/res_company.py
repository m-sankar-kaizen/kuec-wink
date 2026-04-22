# -*- coding: utf-8 -*-
import logging
import calendar
from datetime import date, timedelta
from odoo import models, api, fields, _

_LOGGER = logging.getLogger("=== KAZ - Account Closing Period ===")


class ResCompany(models.Model):
    _inherit = 'res.company'

    # BR-1: Subledger lock day (Invoices/Bills/Payments)
    br_sale_lock_day = fields.Integer(
        string="Lock Sales Day",
        default=15,
        help="Day of the month when sales are locked "
             "Invoices, Customer Payments)."
    )

    br_purchase_lock_day = fields.Integer(
        string="Lock Purchase Day",
        default=15,
        help="Day of the month when purchases are locked "
             "(Bills, Vendor Payments)."
    )

    # BR-2: GL lock day (General Journal)
    br_gl_lock_day = fields.Integer(
        string="GL Lock Day",
        default=20,
        help="Day of the month when the general ledger is locked."
    )

    # BR-1/BR-2: Choose current month or previous month locking
    br_lock_mode = fields.Selection(
        [
            ('previous', "Lock Previous Month"),
        ],
        default='previous',
        string="Lock Mode",
        help="Determines whether locking is applied on the previous month "
             "or the current month."
    )

    br_gl_lock_date = fields.Date(
        string='Full Ledger Lock Date',
        tracking=True,
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    user_br_gl_lock_date = fields.Date(compute='_compute_user_br_gl_lock_date')

    @api.depends('br_gl_lock_date')
    @api.depends_context('uid', 'ignore_exceptions')
    def _compute_user_br_gl_lock_date(self):
        ignore_exceptions = bool(self.env.context.get('ignore_exceptions', False))
        for company in self:
            company.user_br_gl_lock_date = company._get_user_lock_date('br_gl_lock_date', ignore_exceptions)

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _prev_month(self, ref_date):
        """Return last day of previous month (correct logic)."""
        first_day_current_month = ref_date.replace(day=1)
        last_day_prev_month = first_day_current_month - timedelta(days=1)
        return last_day_prev_month

    def _current_month_last_day(self, ref_date):
        """Return last day of current month."""
        y, m = ref_date.year, ref_date.month
        last_day = calendar.monthrange(y, m)[1]
        return date(y, m, last_day)

    @api.model
    def cron_update_period_locks(self):
        """
            Runs daily.
            - On configured Sub-ledger lock day → lock previous/current month sub-ledgers
            - On configured GL lock day → lock previous/current month full GL
        """
        today = date.today()
        company_ids = self.search([('company_code', '=', 'KUEC')])

        for company in company_ids:
            if company.br_lock_mode == "previous":
                lock_month_last_day = company._prev_month(today)
            else:
                lock_month_last_day = company._current_month_last_day(today)
            current_month_last_day = company._current_month_last_day(today)
            previous_month_last_day = company._prev_month(today)

            # -------------------------------------
            # BR-1: SUB-LEDGER LOCK
            # -------------------------------------

            if company.br_sale_lock_day:
                company.message_post(
                    body=_("Sales locked until %s.") % previous_month_last_day
                )
                company.sale_lock_date = previous_month_last_day - timedelta(days=company.br_sale_lock_day)

            if company.br_purchase_lock_day:
                company.message_post(
                    body=_("Purchases locked until %s.") % previous_month_last_day
                )
                company.purchase_lock_date = previous_month_last_day - timedelta(days=company.br_purchase_lock_day)

            # -------------------------------------
            # BR-2: FULL GL LOCK
            # -------------------------------------
            if company.br_gl_lock_day:
                company.message_post(
                    body=_("General Ledger locked until %s.") % previous_month_last_day
                )
                company.br_gl_lock_date = previous_month_last_day - timedelta(days=company.br_gl_lock_day)

        return True

    def _get_violated_lock_dates(self, accounting_date, has_tax, journal):
        """
            Get all the lock dates affecting the current accounting_date.
            :param accounting_date: The accounting date
            :param has_tax: If any taxes are involved in the lines of the invoice
            :param journal: The affected journal
            :return: a list of tuples containing the lock dates ordered chronologically.
        """
        company_id = self.env.company
        if (
                not company_id.fiscalyear_lock_date
                and company_id.br_gl_lock_date
                and accounting_date <= company_id.br_gl_lock_date
                and journal.id == company_id.account_tax_periodicity_journal_id.id
        ):
            return None

        locks = super()._get_lock_date_violations(accounting_date, has_tax, journal)

        field = 'br_gl_lock_date'
        violated_date = self._get_violated_soft_lock_date(field, accounting_date)
        if violated_date:
            # Insert before hard lock (or append if hard lock not present)
            locks = self.insert_before_hard_lock(locks, (violated_date, field))

        return locks

    @staticmethod
    def insert_before_hard_lock(lock_dates, custom_tuple):
        """
        Insert custom_tuple before the tuple whose second value is 'hard_lock_date'.
        If 'hard_lock_date' is not found, append the custom_tuple at the end.

        :param lock_dates: List of tuples [(date, field_name), ...]
        :param custom_tuple: Tuple like (date, 'custom_field')
        :return: Modified lock_dates list
        """
        # Find index of 'hard_lock_date'
        index = next(
                (i for i, (_, field) in enumerate(lock_dates) if field == 'hard_lock_date'),
            None
        )

        # Insert or append
        if index is not None:
            lock_dates.insert(index, custom_tuple)
        else:
            lock_dates.append(custom_tuple)

        return lock_dates

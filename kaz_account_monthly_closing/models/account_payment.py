# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # used to display a message when the invoice's accounting date is prior of the tax lock date
    br_tax_lock_date_message = fields.Char(compute='_compute_br_tax_lock_date_message')

    @api.depends('date')
    def _compute_br_tax_lock_date_message(self):
        for payment in self:
            payment_date = payment.date or fields.Date.context_today(payment)
            payment.br_tax_lock_date_message = payment._get_lock_date_message(payment_date, False)

    def _get_lock_date_message(self, payment_date, has_tax):
        """
            Get a message describing the latest lock date affecting the specified date.
            :param payment_date: The date to be checked
            :param has_tax: If any taxes are involved in the lines of the invoice
            :return: a message describing the latest lock date affecting this move and the date it will be
                        accounted on if posted, or False if no lock dates affect this move.
        """
        self.ensure_one()
        company_id = self.env.company
        if company_id.br_gl_lock_date and self.journal_id.id != company_id.account_tax_periodicity_journal_id.id:
            lock_dates = self.company_id._get_violated_lock_dates(payment_date, has_tax, self.journal_id)
            if lock_dates:
                # accounting_date = self._get_accounting_date(payment_date, has_tax, lock_dates=lock_dates)
                # tax_lock_date_message = _(
                #     "The date is being set prior to: %(lock_date_info)s. "
                #     "The Journal Entry will be accounted on %(accounting_date)s upon posting.",
                #     lock_date_info=self.env['res.company']._format_lock_dates(lock_dates),
                #     accounting_date=format_date(self.env, accounting_date))
                tax_lock_date_message = _(
                    "The date is being set prior to: %(lock_date_info)s. ",
                    lock_date_info=self.env['res.company']._format_lock_dates(lock_dates))
                return tax_lock_date_message
        return False

from odoo import models, fields

from odoo.addons.account.models.company import SOFT_LOCK_DATE_FIELDS, LOCK_DATE_FIELDS


class AccountChangeLockDate(models.TransientModel):
    _inherit = 'account.change.lock.date'

    br_gl_lock_date = fields.Date(
        string='Full Ledger Lock Date',
        default=lambda self: self.env.company.br_gl_lock_date,
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    br_gl_lock_date_for_me = fields.Date(
        string='Full Ledger Lock For Me',
        compute='_compute_lock_date_exceptions',
    )
    br_gl_lock_date_for_everyone = fields.Date(
        string='Full Ledger Lock For Everyone',
        compute='_compute_lock_date_exceptions',
    )
    min_br_gl_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )
    min_br_gl_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )

    def action_revoke_min_br_gl_lock_date_exception_for_me(self):
        return self._action_revoke_min_exception('min_br_gl_lock_date_exception_for_me_id')

    def action_revoke_min_br_gl_lock_date_exception_for_everyone(self):
        return self._action_revoke_min_exception('min_br_gl_lock_date_exception_for_everyone_id')

# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


DAYS_PER_MONTH = 30
DAYS_PER_YEAR = DAYS_PER_MONTH * 12


class ValidateAccountMove(models.TransientModel):
    """
    Wizard model used for validating and posting `account.move` entries in bulk.

    This model extends Odoo's `validate.account.move` wizard to support conditional
    immediate posting of future-dated entries using the `force_post` flag.
    """
    _inherit = "validate.account.move"

    force_post = fields.Boolean(
        string="Force",
        help="Entries with a future date are usually set to auto-post later. "
             "Enable this to override and post them immediately."
    )

    def validate_move(self):
        """
        Post selected draft account moves or moves from a selected journal.
        If `force_post` is True, future-dated moves will be forcibly posted.
        """
        # Determine domain based on context model
        if self._context.get('active_model') == 'account.move':
            domain = [('id', 'in', self._context.get('active_ids', [])), ('state', '=', 'draft')]
        elif self._context.get('active_model') == 'account.journal':
            domain = [('journal_id', '=', self._context.get('active_id')), ('state', '=', 'draft')]
        else:
            raise UserError(_("Missing 'active_model' in context."))

        # Fetch eligible draft moves with lines
        moves = self.env['account.move'].search(domain).filtered('line_ids')
        if not moves:
            raise UserError(_('There are no journal items in the draft state to post.'))

        # Prevent future auto-posting behavior if force_post is checked
        if self.force_post:
            moves.auto_post = 'no'

        # Use context to skip asset checks when calling _post from the validation wizard
        moves.with_context(called_from_validation=True)._post(not self.force_post)

        return {'type': 'ir.actions.act_window_close'}

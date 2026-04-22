# -*- coding: utf-8 -*-
"""
Extension of the `account.move` model to automatically store the date when
a journal entry is posted.

This customization adds a `posted_date` field to record the date on which the
journal entry is posted. The value is updated automatically when the state
of the journal entry transitions to `posted` via the `write()` method.
"""

import datetime

from odoo import models, fields, api


class AccountMove(models.Model):
    """
    Inherits the standard Odoo `account.move` model.

    Enhancements:
    -------------
    - Adds a `posted_date` field to store the date when a journal entry is posted.
    - Overrides the `write()` method to automatically populate the `posted_date`
      when the state changes to `'posted'`.

    Fields:
    -------
    posted_date : fields.Date
        A date field that stores the date when the journal entry was marked as posted.
    """
    _inherit = 'account.move'

    posted_date = fields.Date(
        string="Posted Date",
        help="The date when the journal entry was posted to the ledger. "
             "Automatically set when state becomes 'posted'.",
        readonly=True,
        copy=False,
    )

    def write(self, vals):
        """
        Overrides the standard `write` method to automatically assign today's
        date to the `posted_date` field when the journal entry is posted.

        Parameters:
        -----------
        vals : dict
            A dictionary containing the field values being written to the record.

        Returns:
        --------
        bool
            The result of the superclass `write()` method.
        """
        # Check if the record is transitioning to the 'posted' state
        state = vals.get('state')
        if state == 'posted':
            # Assign today's date to 'posted_date' field
            vals['posted_date'] = datetime.date.today()

        return super().write(vals)

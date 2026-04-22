from . import models
from . import wizard

from odoo.addons.account.models.company import SOFT_LOCK_DATE_FIELDS, LOCK_DATE_FIELDS

# Add br_gl_lock_date custom field
SOFT_LOCK_DATE_FIELDS.append('br_gl_lock_date')


# Update the hard lock list as well
LOCK_DATE_FIELDS.append('br_gl_lock_date')

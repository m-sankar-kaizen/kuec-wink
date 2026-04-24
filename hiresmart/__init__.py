import logging

# [Start] Class & filter function for suppressing noisy Odoo log about binary fields stored in attachments ############################
class SuppressBinaryLogFilter(logging.Filter):
    def filter(self, record):
        return not (record.name == 'odoo.osv.expression' and 'Binary field' in record.getMessage())

# For applying filter to specific logger ################
logging.getLogger('odoo.osv.expression').addFilter(SuppressBinaryLogFilter())
# [End] Class & filter function for suppressing noisy Odoo log about binary fields stored in attachments ############################


from . import models
from . import wizard
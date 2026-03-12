# -*- coding: utf-8 -*-
# ISSUE-009: Expose post_init_hook so Odoo can find it via getattr(module, 'post_init_hook').

from . import models
from . import services
from . import wizard
from . import controllers
from ._post_init_hook import post_init_hook

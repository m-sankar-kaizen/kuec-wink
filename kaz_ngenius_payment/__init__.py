# -*- coding: utf-8 -*-
import base64
import logging
import os

from . import controllers
from . import models

from odoo.addons.payment import setup_provider, reset_payment_provider

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Run after fresh install to register the provider and set module_id + icon."""
    setup_provider(env, 'ngenius')

    module = env['ir.module.module'].sudo().search(
        [('name', '=', 'kaz_ngenius_payment')], limit=1
    )
    provider = env['payment.provider'].sudo().search(
        [('code', '=', 'ngenius')], limit=1
    )
    if not provider or not module:
        return

    vals = {'module_id': module.id}
    icon_path = os.path.join(os.path.dirname(__file__), 'static', 'description', 'icon.png')
    if os.path.exists(icon_path):
        with open(icon_path, 'rb') as f:
            vals['image_128'] = base64.b64encode(f.read()).decode()

    provider.write(vals)


def uninstall_hook(env):
    reset_payment_provider(env, 'ngenius')

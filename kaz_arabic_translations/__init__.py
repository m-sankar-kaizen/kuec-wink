# -*- coding: utf-8 -*-
from . import models

from odoo import Command


def _post_install_arabic_language(env):
    ar_lang = env['res.lang'].with_context(active_test=False).search(
        [('code', '=', 'ar_001')])
    env["base.language.install"].create({
        'overwrite': True,
        'lang_ids': [Command.set(ar_lang.ids)]
    }).lang_install()

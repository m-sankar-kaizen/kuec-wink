# -*- coding: utf-8 -*-
from odoo import Command


def install_es_ar_lang(env):
    lang_code = "es_AR"
    lang_id = env['res.lang'].with_context(active_test=False).search(
        [('code', '=', lang_code)]).id
    installer = env['base.language.install'].create({'lang_ids': [Command.link(lang_id)]})
    installer.lang_install()

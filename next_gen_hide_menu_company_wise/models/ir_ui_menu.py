# -*- coding: utf-8 -*-

from odoo import api, models
import copy
from odoo.http import request
import re


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def load_menus(self, debug):
        res = super(IrUiMenu, self).load_menus(debug)
        menu_copy = copy.deepcopy(res)
        ids_to_remove = self._company_dependent_menus(res)
        for menu_id in ids_to_remove:
            menu_copy.pop(menu_id, None)
            self._remove_menu_from_parent(menu_copy, menu_id)
        return menu_copy

    def _company_dependent_menus(self, menus):
        cids_cookie = request.httprequest.cookies.get('cids', '')
        if not cids_cookie:
            cids_cookie = str(self.env.company.id)
        if not cids_cookie:
            return set()
        try:
            company_ids = [int(x) for x in re.split(r',\s*', cids_cookie) if x.isdigit()]
        except ValueError:
            return set()
        company_records = self.env['res.company'].sudo().browse(company_ids)
        if not company_records:
            return set()

        black_list_menus = set(company_records[0].menu_ids.ids)
        for company in company_records[1:]:
            black_list_menus.intersection_update(company.menu_ids.ids)

        return black_list_menus

    def _remove_menu_from_parent(self, menus, menu_id):
        for parent_menu in menus.values():
            if 'children' in parent_menu:
                parent_menu['children'] = [child_id for child_id in parent_menu['children'] if child_id != menu_id]

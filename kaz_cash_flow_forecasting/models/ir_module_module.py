# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, modules, tools, _
from odoo.addons.base.models.ir_module import assert_log_admin_access
_logger = logging.getLogger(__name__)
class IrModuleModule(models.Model):
    """Minor helper to register the optional kaz_budget_forecasting package if present."""
    _inherit = "ir.module.module"
    @assert_log_admin_access
    @api.model
    def action_update_list_for_budget_forecasting(self):
        """Ensure the 'kaz_budget_forecasting' module is known to Odoo (without installing it).
        Note: This does not install or change state; it only registers metadata if missing.
        """
        mod_name = 'kaz_budget_forecasting'
        mod = self.env['ir.module.module'].sudo().search(
            [('name', '=', mod_name)],
            limit=1)
        res = [0, 0]
        terp = self.sudo().get_module_info(mod_name)
        values = self.sudo().get_values_from_terp(terp)
        skip = False
        if not mod:
            mod_path = modules.get_module_path(mod_name)
            if not mod_path or not terp:
                skip = True
                pass
            else:
                state = "uninstalled" if terp.get('installable', True) else "uninstallable"
                mod = self.sudo().create(dict(name=mod_name, state=state, **values))
                res[1] += 1
        if not skip:
            _logger.info("===========2=============")
            mod._update_dependencies(terp.get('depends', []), terp.get('auto_install'))
            _logger.info("===========3=============")
            mod._update_exclusions(terp.get('excludes', []))
            _logger.info("===========4=============")
            mod._update_category(terp.get('category', 'Uncategorized'))
            _logger.info("===========5=============")
            _logger.info("===========Final=============")
        return res
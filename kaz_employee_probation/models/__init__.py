# -*- coding: utf-8 -*-
"""
This is the __init__.py file for the custom HR module extension.

It ensures that the specified submodules are loaded when the module is initialized by Odoo.

Modules imported:
-----------------
- res_company: Contains extensions to the res.company model.
- hr_employee: Contains custom logic or field extensions to the hr.employee model.
"""
from . import res_company
from . import hr_employee
from . import hr_employee_public
from . import res_config_settings

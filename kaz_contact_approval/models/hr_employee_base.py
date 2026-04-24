# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class HrEmployeeBase(models.AbstractModel):
    _inherit = 'hr.employee.base'

    def _create_work_contacts(self):
        if any(employee.work_contact_id for employee in self):
            raise UserError(_('Some employee already have a work contact'))
        work_contacts = self.env['res.partner'].create([{
            'email': employee.work_email,
            'mobile': employee.mobile_phone,
            'name': employee.name,
            'image_1920': employee.image_1920,
            'company_id': employee.company_id.id,
            'state': 'approved' if employee.company_id.company_code in ['KUEC'] else 'draft',
        } for employee in self])
        for employee, work_contact in zip(self, work_contacts):
            employee.work_contact_id = work_contact

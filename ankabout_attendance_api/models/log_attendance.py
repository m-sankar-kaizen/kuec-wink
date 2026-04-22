# -*- coding: utf-8 -*-
from odoo import models, fields, api


class LogAttendance(models.Model):
    """
    A model for storing raw attendance logs (punches) from external systems.

    This model is useful for maintaining a log of biometric or third-party
    punch records, which can then be processed or matched with Odoo's
    standard attendance workflow.

    Fields:
        punch_id (Char): A unique identifier for the punch (usually from device/API).
        employee_id (Many2one): The employee who punched in/out.
        punch_type (Selection): Either 'Check In' or 'Check Out'.
        punch_time (Datetime): The datetime of the punch.
        company_id (Many2one): Company related to the employee.
    """
    _name = 'log.attendance'
    _description = 'Employee Attendance'
    _rec_name = 'punch_id'

    punch_id = fields.Char(string='Punch ID', required=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee', required=True)
    emp_code = fields.Char(string='Employee Code', related='employee_id.emp_code')
    device_location = fields.Char(string='Device Location')
    department_id = fields.Many2one(string='Department', related='employee_id.department_id', store=True)
    punch_time = fields.Datetime(string='Punch Time', default=fields.Datetime.now)
    punch_type = fields.Selection(string='Punch Type', selection=[('0', 'Check In'), ('1', 'Check Out')])
    is_biometric = fields.Boolean(string='Biometric', readonly=True, copy=False, default=False)
    company_id = fields.Many2one(related='employee_id.company_id', string='Company', store=True)

    @api.model
    def check_in_employee(self, employee_id, punch_date):
        """
        Simulates a check-in for the given employee at the specified time.
        NOTE: The field 'check_in' does not exist in this model unless extended later.

        :param employee_id: ID of the employee checking in.
        :param punch_date: Datetime object of check-in time.
        :return: Attendance record created.
        """
        attendance = self.create({
            'employee_id': employee_id,
            'check_in': punch_date  # This assumes the model has this field.
        })
        return attendance

    @api.model
    def check_out_employee(self, employee_id, punch_date):
        """
        Simulates a check-out for the given employee. It finds the latest open check-in
        and sets its check-out, or creates a new one if none exists.

        :param employee_id: ID of the employee checking out.
        :param punch_date: Datetime object of check-out time.
        :return: Updated or new attendance record.
        """
        attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False)
        ], limit=1)

        if attendance:
            attendance.check_out = punch_date
        else:
            attendance = self.create({
                'employee_id': employee_id,
                'check_out': punch_date
                # This assumes the model has this field.
            })
        return attendance

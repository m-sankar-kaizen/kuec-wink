# -*- coding: utf-8 -*-

"""
HR Attendance API Controller
============================

This module provides a custom JSON API endpoint to log employee check-in
and check-out data from external biometric or attendance devices.

The endpoint:
    - Validates a token-based Authorization header.
    - Matches employees by unique employee code.
    - Prevents duplicate punch entries.
    - Creates attendance (`hr.attendance`) and log (`log.attendance`) records.

Designed for use with external systems like Ankabut HR devices.
"""
import logging
import pytz

from dateutil import parser

from odoo import SUPERUSER_ID
from odoo.http import Controller, request, route, Response


def format_time(time_str):
    """
    Convert ISO 8601 time string with timezone info into a naive UTC datetime.

    Args:
        time_str (str): Timestamp string in ISO format (e.g., 2024-05-01T08:00:00+04:00)

    Returns:
        datetime: Naive UTC datetime object
    """
    dt_with_tz = parser.parse(time_str)
    dt_utc = dt_with_tz.astimezone(pytz.utc)
    return dt_utc.replace(tzinfo=None)


class HrAttendanceApi(Controller):
    """
    HR Attendance REST Controller

    This controller exposes a JSON endpoint at `/ankabut/create_hr_attendance`
    to log employee attendance from external systems.
    """

    @route('/ankabut/create_hr_attendance', type='json', auth='public', methods=["POST"])
    def create_hr_attendance(self, **punch_data):
        """
        Handle incoming JSON punch data and record attendance entries.

        Expected JSON structure:
        {
            "punch_data": [
                {
                    "id": "unique_device_id",
                    "emp_code": "employee_code",
                    "punch_type": "0" or "1",
                    "punch_time": "ISO 8601 timestamp"
                },
                ...
            ]
        }

        Returns:
            list: A list of dictionaries for each punch record indicating success or failure.
        """
        auth_header = request.httprequest.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return Response(status=401)

        api_token = auth_header.split(' ')[1]
        user = request.env['res.company'].sudo().search([('attendance_token', '=', api_token)], limit=1)

        if not user:
            return Response(status=401)

        required_fields = ['id', 'emp_code', 'punch_type', 'punch_time', 'device_location']
        responses = []

        for rec in punch_data.get('punch_data', []):
            try:
                if not all(field in rec for field in required_fields):
                    responses.append({
                        'success': False,
                        'message': 'Missing required fields for attendance'
                    })
                    continue

                employee = request.env['hr.employee'].sudo().search(
                    domain=[('emp_code', '=', rec['emp_code']), ('company_id', '=', user.id)],
                    limit=1
                )

                if not employee:
                    responses.append({
                        'success': False,
                        'message': f'Employee not found for attendance with id {rec["id"]}',
                    })
                    continue

                existing_log = request.env['log.attendance'].sudo().search([('punch_id', '=', rec['id'])], limit=1)

                if existing_log:
                    responses.append({
                        'success': False,
                        'message': f'This punch already exists with id {rec["id"]}',
                    })
                    continue

                last_log = request.env['log.attendance'].sudo().search(
                    domain=[('employee_id', '=', employee.id), ('punch_type', '=', rec['punch_type'])],
                    order='punch_time desc',
                    limit=1
                )

                punch_time = format_time(rec['punch_time'])

                if last_log and abs((punch_time - last_log.punch_time).total_seconds()) < 60:
                    responses.append({
                        'success': False,
                        'message': f'Duplicate punch within 60s skipped for id {rec["id"]}',
                    })
                    continue

                attendance_model = request.env['hr.attendance'].sudo()
                open_attendance = attendance_model.search(
                    domain=[('employee_id', '=', employee.id), ('check_out', '=', False)],
                    limit=1
                )
                punch_time = format_time(rec['punch_time'])

                if rec["punch_type"] == '0':  # check-in
                    if not open_attendance:
                        attendance_model.create({
                            'employee_id': employee.id,
                            'check_in': punch_time,
                        })

                elif rec["punch_type"] == '1':  # check-out
                    if open_attendance:
                        if punch_time < open_attendance.check_in:
                            responses.append({
                                'success': False,
                                'message': 'Check-out time must be after check-in.',
                            })
                            continue
                        open_attendance.write({'check_out': punch_time})

                log_vals = {
                    "punch_id": rec['id'],
                    "employee_id": employee.id,
                    "punch_type": rec['punch_type'],
                    "punch_time": punch_time,
                    "is_biometric": True,
                    "company_id": user.id,
                    "device_location": rec['device_location'],
                }
                log_record = request.env['log.attendance'].with_user(SUPERUSER_ID).sudo().create(log_vals)

                responses.append({
                    'success': True,
                    'message': 'Created successfully',
                    'log_id': log_record.id,
                    'punch_id': log_record.punch_id
                })

            except Exception as e:
                logging.error("Punch processing error: %s", str(e))
                responses.append({
                    'success': False,
                    'message': f"Server error processing punch with id {rec.get('id')}",
                })

        return responses

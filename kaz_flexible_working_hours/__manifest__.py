# -*- coding: utf-8 -*-
{
    'name': "Employee Flexible Working Hours",
    'summary': """
        Manage flexible working hours for employees with buffer check-in time,
        planned vs actual attendance tracking, and detailed lateness reports.
    """,
    'description': """
        This module enhances the standard HR Attendance functionality by introducing support 
        for flexible working hours. It allows HR managers to define a buffer check-in window 
        (e.g., employees can arrive up to X hours late without being marked as late), and 
        automatically computes each employee’s planned check-in and check-out times based 
        on their working schedule (resource calendar).

        Key Features:
        - Define flexible check-in buffer time on employee work schedules.
        - Compute and store the planned check-in and check-out times for each attendance.
        - Display planned vs actual attendance in a dedicated menu.
        - Automatically calculate late-in hours beyond the allowed flexible buffer.
        - Admin-specific group for viewing and managing planned attendance records.

        Use Cases:
        - Universities and organizations with flexible timing policies.
        - HR departments needing visibility into punctuality while respecting flexible shifts.
        - Real-time tracking of late arrivals for compliance and analytics.

        This tool empowers HR teams to maintain a healthy balance between flexible work policies 
        and accountability, all within the Odoo environment.
    """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Human Resources/Employees',
    'version': '1.0',
    'depends': ['hr_attendance', 'resource'],
    'data': [
        'security/ir.model.access.csv',
        'views/resource_calendar_views.xml',
        'views/hr_attendance_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

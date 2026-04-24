# -*- coding: utf-8 -*-

{
    'name': 'Material Purchase Requisition',
    'summary': 'Create and manage employee-driven material purchase or stock requisitions with multi-level approvals',
    'description': """
Material Purchase and Stock Requisition Management
==================================================

This module empowers employees to request products or materials through a streamlined requisition workflow. Requests can be fulfilled either through:
1. **Internal Picking** (warehouse dispatch), or
2. **Purchase Orders** (RFQ to vendors).

Key Features:
-------------
- Employee submission of material requisitions.
- One requisition can contain multiple items.
- Dual approval workflow:
    - Department Manager Approval
    - Purchase Manager Approval
- Automatic email notifications to approvers.
- Internal picking creation when item is available in warehouse.
- Automatic Purchase Order generation when stock is insufficient or requisition is marked for procurement.
- Line-level action selection: 'Internal Picking' or 'Purchase Order'.
- Links stock pickings and purchase orders to requisitions for traceability.
- Seamless integration with HR, Stock, and Purchase modules.

Use Cases:
----------
- Factory, construction, and warehouse environments.
- Office procurement and inventory restocking.
- Real estate and infrastructure project sites.
- Inter-departmental inventory control.

Kaizen Principles Applied:
--------------------------
- Modular and maintainable design
- Granular security control and approval rules
- Integration-focused extensibility
- Optimized user interface with contextual information
- Reduces duplication, delays, and miscommunication

Technical Details:
------------------
- Inherits:
    - `hr.department.form.view`
    - `hr.employee.form.view`
    - `stock.picking.form.view`
- Adds:
    - Custom QWeb report: `purchase_requisition`
    - Requisition line-specific actions
    - Multi-company access rules
    - Advanced search, group-by, and filters

For full demonstration or customization requests, please contact us.

    """,
    'author': "Kaizen Principles",
    'website': "https://www.kaizenae.com",
    'category': 'Inventory/Inventory',
    'version': '1.4',
    'depends': [
        'stock',
        'hr',
        'purchase',
    ],
    'data': [
        'security/security.xml',
        'security/multi_company_security.xml',
        'security/ir.model.access.csv',
        'data/purchase_requisition_sequence_data.xml',
        'data/employee_purchase_approval_template_data.xml',
        'data/confirm_template_material_purchase_data.xml',
        'report/purchase_requisition_report.xml',
        'views/material_purchase_requisition_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_department_views.xml',
        'views/stock_picking_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
    'auto_install': False,
}

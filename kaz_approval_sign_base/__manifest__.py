# -*- coding: utf-8 -*-
{
    'name': "Approvals Base",
    'summary': "Reusable sequential approval & rejection workflow framework",
    'description': """
    Base Approval Workflow Framework
    --------------------------------

    This module provides a reusable mixin (`approval.reject.mixin`) that enables any 
    Odoo model to implement a structured, multi-step approval or rejection workflow.

    Key features:
    - Sequential approval steps with ordering via sequence
    - Approval, Reject, and Return for Correction (RFC) request types
    - Digital signature capture using Sign app integration
    - Automatic generation of signature and reason based on user and request type
    - Configurable link to the parent document via `_parent_record`
    - Support for triggering dynamic methods on the parent record via `next_action`
    - Full compute/inverse logic for signature and reason fields
    - Company-aware fields with automatic defaults
    - Designed as a foundational module for building advanced approval systems

    This module does not provide UI on its own.  
    Other modules can inherit the mixin to add approval workflows to their models.
        """,
    'author': "Kaizen",
    'website': "https://www.kaizenae.com",
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['sign'],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}

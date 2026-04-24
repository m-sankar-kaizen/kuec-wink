# -*- coding: utf-8 -*-
from odoo import models


class EducationFeesChild(models.Model):
    """
        Temporary model used for cleanup or data migration purposes.

        This model is not meant to be exposed to users or used in production logic.
        It's typically used to:
        - Store intermediate or legacy data temporarily
        - Facilitate cleanup scripts
        - Assist with module upgrades or schema transformations

        After the migration or cleanup process is completed, this model should be removed.
        """

    _name = 'education.fees.child'
    _description = 'Temporary model for cleanup'

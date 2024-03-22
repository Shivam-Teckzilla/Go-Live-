from odoo import models, api
from datetime import datetime

class InheritHREmployee(models.Model):
    _inherit = 'hr.employee'

    
    def report_print(self):
        report = self.env.ref('vendor_reporting.action_empolyee_report').report_action(self)
        return report

    
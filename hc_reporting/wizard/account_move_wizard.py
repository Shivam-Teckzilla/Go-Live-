from odoo import models, fields, api

class CustomerDetailsWizard(models.TransientModel):
    _name = 'customer.details.wizard'
    
    filename = fields.Char(string='Filename')

    def yes_report(self):
        report = self.env.ref('hc_reporting.action_voucher_report').report_action(self)
        return report


from odoo import api, fields, models

class CustomerDetailsWizard(models.TransientModel):
	_name = 'customer.details.wizard'

	demurrage_day = fields.Float("Demurrage Days")
	applicant_id = fields.Many2one('stock.picking', string="Applicant")

	def submit_details(self):
		if self.applicant_id and self.demurrage_day:
			self.applicant_id.write({'demurrage_day': self.demurrage_day})
		return {'type': 'ir.actions.act_window_close'}

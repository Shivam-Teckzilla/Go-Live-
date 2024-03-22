from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import xlwt
from io import  BytesIO
import io
import base64
from datetime import datetime
import xlrd.xldate
from num2words import num2words


class InheritHREmployee(models.Model):
	_inherit = 'hr.employee'

	son_of = fields.Char("SO")
	
	def report_print(self):
		report = self.env.ref('hc_reporting.action_empolyee_report').report_action(self)
		return report
	
   
class AccountMove(models.Model):
	_inherit = 'account.move'

	amount_word = fields.Char(string ="Amount in Word", compute="_compute_amount_word")

	def _compute_amount_word(self):
		for order in self:
			amount_in_words = num2words(order.amount_total, to='currency', lang='en')
			order.amount_word = amount_in_words


	def custom_bill_pdf_print(self):
		report = self.env.ref('hc_reporting.action_tax_report').report_action(self)
		return report
		
	def action_open_wizard(self):
		wizard = self.env['customer.details.wizard']
   
		return {
		'name': ('Voucher Report'),
		'type': 'ir.actions.act_window',  
		'res_model': 'customer.details.wizard',    
		'view_mode': 'form',  
		'res_id': wizard.id,  
		'target': 'new'
		}
	
	def action_post(self):
		moves_with_payments = self.filtered('payment_id')
		other_moves = self - moves_with_payments

		if self.move_type == 'in_invoice':
			action =self.action_open_wizard()
			if moves_with_payments:
				moves_with_payments.payment_id.action_post()

			if other_moves:
				other_moves._post(soft=False)

			return action
		
		

		if moves_with_payments:
			moves_with_payments.payment_id.action_post()

		if other_moves:
			other_moves._post(soft=False)

		return False
	
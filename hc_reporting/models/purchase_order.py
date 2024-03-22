from odoo import api, fields, models, _
from num2words import num2words

class PurchaseOrder(models.Model):
	_inherit = "purchase.order"

	amount_word = fields.Char(string ="Amount in Word", compute="_compute_amount_word")
	
	def _compute_amount_word(self):
		for order in self:
			amount_in_words = num2words(order.amount_total, to='currency', lang='en')
			order.amount_word = amount_in_words


	def purchase_tax_invoice_pdf_print(self):
		report = self.env.ref('hc_reporting.action_purchase_tax_invoice_report').report_action(self)
		return report
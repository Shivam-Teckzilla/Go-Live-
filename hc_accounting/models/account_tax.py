from odoo import api, fields, models ,_
from num2words import num2words
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_amount, format_date, formatLang, groupby


class AccountTax(models.Model):
	_inherit = 'account.tax'
	
	is_tds = fields.Boolean("Is TDS")


class ResPartner(models.Model):
	_inherit = 'res.partner'

	tds_ids = fields.Many2one("account.tax", string="TDS", domain="[('is_tds', '=', True)]")


	
class AccountMove(models.Model):
	_inherit = 'account.move'


	quality_check_id = fields.Many2one('quality.check', string="Quality Check", copy=False)
	quality_alert_id = fields.Many2one('quality.alert', string="Quality Alert", copy=False)

	net_payable = fields.Float(
		string='Net Payable', compute='_compute_net_payable',)
	tax_id = fields.Many2one('account.tax')
	check_amount_in_words = fields.Char(compute='_amt_in_words', string='Amount in Words')

	@api.depends('amount_total')
	def _amt_in_words(self):
		for rec in self:
			rec.check_amount_in_words = num2words(str(rec.amount_total), lang='en_IN').replace(',', '').replace('and',
																												'').replace(
				'point', 'and paise').replace('thous', 'thousand')

	def write(self, vals):
		credit = 0
		if vals.get('tax_id'):
			tax = self.env['account.tax'].search([('id', '=', vals['tax_id'])])
			amt = self.amount_total
			acc = tax.invoice_repartition_line_ids.filtered(lambda x: x.account_id.id)
			credit = abs(amt * tax.amount / 100)
			self.invoice_line_ids = [
				(0, 0, {'move_id': self.id, 'name': tax.name, 'account_id': acc.account_id.id, 'quantity': 1,
						'price_unit': credit})]
		res = super().write(vals)
		return res

	@api.model
	def create(self, vals):
		res = super(AccountMove, self).create(vals)
		if res.tax_id:
			# tax = self.env['account.tax'].search([('id', '=', vals['tax_id'])])
			amt = res.amount_total
			acc = res.tax_id.invoice_repartition_line_ids.filtered(lambda x: x.account_id.id)
			credit = abs(amt * res.tax_id.amount / 100)
			res.invoice_line_ids = [
				(0, 0, {'move_id': self.id, 'name': res.tax_id.name, 'account_id': acc.account_id.id, 'quantity': 1,
						'price_unit': credit})]
		return res

	def _compute_net_payable(self):
		for move in self:
			move.net_payable = move.amount_total - sum(self.line_ids.mapped('matched_debit_ids').mapped('amount'))

	
	def action_post(self):
		for move in self:
			if move.partner_id and move.partner_id.tds_ids:
				move.invoice_line_ids.write({'tax_ids': [(4, move.partner_id.tds_ids.id, None)]})
		result = super(AccountMove, self).action_post()
		return result


class PurchaseOrderInherit(models.Model):
	_inherit = 'purchase.order'

	def action_create_invoice(self):
		"""Create the invoice associated to the PO.
        """
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

		# 1) Prepare invoice vals and clean-up the section lines
		invoice_vals_list = []
		sequence = 10
		for order in self:
			if order.invoice_status != 'to invoice':
				continue

			order = order.with_company(order.company_id)
			pending_section = None
			# Invoice values.
			invoice_vals = order._prepare_invoice()
			# Invoice line values (keep only necessary sections).
			for line in order.order_line:
				if line.display_type == 'line_section':
					pending_section = line
					continue
				if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
					if pending_section:
						line_vals = pending_section._prepare_account_move_line()
						line_vals.update({'sequence': sequence})
						invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
						sequence += 1
						pending_section = None
					line_vals = line._prepare_account_move_line()
					line_vals.update({'sequence': sequence})
					invoice_vals['invoice_line_ids'].append((0, 0, line_vals))
					sequence += 1

			invoice_vals_list.append(invoice_vals)



		if not invoice_vals_list:
			raise UserError(
				_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

		# 2) group by (company_id, partner_id, currency_id) for batch creation
		new_invoice_vals_list = []
		for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (
		x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
			origins = set()
			payment_refs = set()
			refs = set()
			ref_invoice_vals = None
			for invoice_vals in invoices:
				if not ref_invoice_vals:
					ref_invoice_vals = invoice_vals
				else:
					ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
				origins.add(invoice_vals['invoice_origin'])
				payment_refs.add(invoice_vals['payment_reference'])
				refs.add(invoice_vals['ref'])
			ref_invoice_vals.update({
				'ref': ', '.join(refs)[:2000],
				'invoice_origin': ', '.join(origins),
				'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
			})
			new_invoice_vals_list.append(ref_invoice_vals)
		invoice_vals_list = new_invoice_vals_list

		# 3) Create invoices.
		moves = self.env['account.move']
		AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
		for vals in invoice_vals_list:
			moves |= AccountMove.with_company(vals['company_id']).create(vals)

		# 4) Some moves might actually be refunds: convert them if the total amount is negative
		# We do this after the moves have been created since we need taxes, etc. to know if the total
		# is actually negative or not
		moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_move_type()

		# 5) Deduct total amount of debit notes containing "starch" or "moisture" from PO subtotal
		total_debit_note_amount = 0.0
		for debit_note in self.debit_notes_ids.filtered(
				lambda dn: dn.ref and ('starch' in dn.ref.lower() or 'moisture' in dn.ref.lower() or 'foreign' in dn.ref.lower() or 'difference' in dn.ref.lower())):
			print("Reference",debit_note.ref)
			total_debit_note_amount += debit_note.amount_total


		# 6) Divide remaining amount by quantity and set as price_unit
		# for invoice_vals, order in zip(invoice_vals_list, self):
		# 	# order.net_payable = order.amount_total - total_debit_note_amount
		#
		# 	if 'invoice_line_ids' in invoice_vals and invoice_vals['invoice_line_ids']:
		# 		invoice = moves.filtered(lambda m: m.company_id == order.company_id)
		#
		# 		invoice.net_payable = invoice.amount_total - total_debit_note_amount
		#
		# 		# Deduct total_debit_note_amount from the product of price_unit * quantity
		# 		for i, line_vals in enumerate(invoice_vals['invoice_line_ids']):
		# 			price_unit = line_vals[2].get('price_unit', 0.0)
		# 			quantity = line_vals[2].get('quantity', 1.0)
		# 			new_price_unit = max(price_unit - total_debit_note_amount / max(1, quantity), 0.0)
		# 			invoice.invoice_line_ids[i].write({'price_unit': new_price_unit})
		#
		# 		print('Net payable',invoice.net_payable)
		#
		# return self.action_view_invoice(moves)
		for invoice_vals, order in zip(invoice_vals_list, self):
			if 'invoice_line_ids' in invoice_vals and invoice_vals['invoice_line_ids']:
				invoice = moves.filtered(lambda m: m.company_id == order.company_id)


				# Deduct total_debit_note_amount from the product of price_unit * quantity
				for i, line_vals in enumerate(invoice_vals['invoice_line_ids']):
					price_unit = line_vals[2].get('price_unit', 0.0)
					product_id = line_vals[2].get('product_id', False)

					purchase_order_line = order.order_line[0]

					# Get the corresponding stock move for the product in the current line
					stock_move = order.picking_ids.mapped('move_ids_without_package').filtered(
						lambda move: move.product_id == purchase_order_line.product_id and
									 move.quantity == purchase_order_line.qty_received)


					if stock_move:
						# Update quantity based on dispatch qty inside stock_move
						quantity = stock_move.product_uom_qty
						invoice.invoice_line_ids[i].write({'quantity': quantity})
						# invoice.net_payable = invoice.amount_total - total_debit_note_amount
						new_price_unit = max(price_unit - total_debit_note_amount / max(1, quantity), 0.0)
						invoice.invoice_line_ids[i].write({'quantity': quantity, 'price_unit': new_price_unit})

					else:
						price_unit = line_vals[2].get('price_unit', 0.0)
						quantity = line_vals[2].get('quantity', 1.0)
						new_price_unit = max(price_unit - total_debit_note_amount / max(1, quantity), 0.0)
						invoice.invoice_line_ids[i].write({'price_unit': new_price_unit})

		return self.action_view_invoice(moves)
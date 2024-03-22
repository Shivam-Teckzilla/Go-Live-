from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import xlwt
from io import  BytesIO
import io
import base64
from datetime import datetime
import xlrd.xldate


class TbsSale(models.Model):
	_name = 'tbs.sale'
	_description = 'TBS SALE'
	_rec_name = 'settlement_ref'

	@api.model
	def create(self, vals):
		if vals.get('settlement_ref', _('New')) == _('New'):
			if vals.get('tbs_type') == 'sale':
				vals['settlement_ref'] = self.env['ir.sequence'].next_by_code('tbs.sale') or _('New')
			
			if vals.get('tbs_type') == 'purchase':
				vals['settlement_ref'] = self.env['ir.sequence'].next_by_code('tbs.purchase') or _('New')

		result = super(TbsSale, self).create(vals)
		return result

	
	settlement_ref = fields.Char(string='Settlement Ref', copy=False,
						   readonly=True, index=True, default=lambda self: _('New'))
	
	partner_id = fields.Many2one('res.partner', string='Customer',required=True)
	transporter_id = fields.Many2one('res.partner', string='Transporter',required=True)
	transpoter_rate = fields.Many2one("transport.rates", string = "Rates")
	action_id = fields.Many2one("account.move", string = "Action")
	
	grn_start = fields.Date("GRN Start Date")
	grn_end = fields.Date("GRN End Date")
	state = fields.Selection([
		('draft', 'Draft'),
		('approval_pending', 'Wait For Approval'),
		('approved', 'Approved'),
	
		('cancel', 'Cancelled'),], 
		string='State', tracking=True, default='draft')
	settlement_ids = fields.One2many("tbs.sale.settlement.lines", "set_id", "Settlement Lines")
	approval_request = fields.Many2one ("approval.request", string = "Approval")
	fetch_button_hide = fields.Boolean("Fetch Button Hide", default = False)
	tbs_type = fields.Selection([
		('sale', 'Sale'),
		('purchase', 'Purchase'),
	], string='TBS Type',)
	sub_total = fields.Float("Total", compute='_compute_sub_total', store=True)

	@api.depends('settlement_ids.freight_amount')
	def _compute_sub_total(self):
		for sale in self:
			sub_total = sum(line.freight_amount for line in sale.settlement_ids)
			sale.sub_total = sub_total

	def action_approved(self):
		for rec in self:
			rec.state = 'approved'
			
			


	def action_fetch_data(self):
		
		if not self.partner_id or not self.grn_start or not self.grn_end:
			return
		
		account_moves = self.env['account.move'].search([
				('partner_id', '=', self.partner_id.id),
				('date', '>=', self.grn_start),
				('date', '<=', self.grn_end),
				('tbs_sale_id', '=', False)
			])

		transport_rates = self.env['transport.rates'].search([
				('transporter', '=', self.transporter_id.id),
				('location_rates_ids.effective_date', '<=', self.grn_end),
				('location_rates_ids.effective_date', '>=', self.grn_start),
			],limit=1)
		
		if self.tbs_type == 'purchase':
			print("^^^^^^^^^^^^^^^^^^^^^^")
			if transport_rates.rate_for == 'transporter':
					print("@@@@@@@@@@@@@@@@")
					for rate in transport_rates:
						for location_rate in rate.location_rates_ids:
							for move in account_moves:
								if location_rate.locations.id == move.sale_order_id.location_rate_id.id:
									if location_rate.rates_id.state == 'approved':
										# if move.action_id.picking_ids.state == 'done':
											
											settlement_lines = []
											location = move.sale_order_id.location_rate_id.name
											settlement_lines.append((0, 0, {
												'grn_no': ', '.join(move.sale_order_id.picking_ids.mapped('name')) if move.sale_order_id.picking_ids else '',
												'grn_date': move.sale_order_id.picking_ids.scheduled_date,
												'po_no': move.sale_order_id.name,
												'po_date': move.sale_order_id.date_order,
												'trailer_no': move.action_id.truck_type.truck_type.name if move.action_id.truck_type.truck_type.name else move.action_id.truck_types.name,
												'truck_no': move.action_id.truck_no if move.action_id.truck_no else move.action_id.truck_number,
												'dispatch_qty': move.sale_order_id.order_line.product_uom_qty,
												'received_qty': move.sale_order_id.order_line.qty_delivered,
												'grn_weight': move.action_id.net_weight,
												'demurrage_day': move.action_id.picking_ids.demurrage_day,
												'freight_rate': ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
												'freight_amount': (move.action_id.picking_ids.move_ids_without_package.product_uom_qty) * ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
											}))
											move.sale_order_id.write({
											'tab_purchase': self.settlement_ref,
											'purchase_total_freight_rate': (move.action_id.picking_ids.move_ids_without_package.product_uom_qty) * ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
												})
											move.write({
											'tab_purchase': self.settlement_ref,
											'purchase_total_freight_rate': (move.action_id.picking_ids.move_ids_without_package.product_uom_qty) * ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
											'purchase_freight_rate' : (location_rate.demurrage_charge)+(location_rate.deport_charge)	})
											self.write({'fetch_button_hide': True})
											self.write({'settlement_ids': settlement_lines})
											break 
										# else:
										# 	raise ValidationError(f" Delivery No: {move.action_id.picking_ids.name}, is pending")
									else:
										raise ValidationError("Approved rate not found")
	
							else:
								continue  
							break 
						else:
							continue
						break 
					else:
						raise ValidationError("TBS rates not found")
		
		transport_rates_customer = self.env['transport.rates'].search([
				('customer_id', '=', self.partner_id.id),
				('location_rates_ids.effective_date', '<=', self.grn_end),
				('location_rates_ids.effective_date', '>=', self.grn_start),
			],limit=1)
		
		if self.tbs_type == 'sale':
			
			if transport_rates_customer.rate_for == 'customer':
					print("$$$$$$$$$$$$$$$$$$$$$")
				
					for rate in transport_rates_customer:
						for location_rate in rate.location_rates_ids:
							for move in account_moves:
								if location_rate.locations.id == move.sale_order_id.location_rate_id.id:
									if location_rate.rates_id.state == 'approved':
										if move.action_id.picking_ids.state == 'done':
											settlement_lines = []
											location = move.sale_order_id.location_rate_id.name
											settlement_lines.append((0, 0, {
												'grn_no': ', '.join(move.sale_order_id.picking_ids.mapped('name')) if move.sale_order_id.picking_ids else '',
												'grn_date': move.sale_order_id.picking_ids.scheduled_date,
												'po_no': move.sale_order_id.name,
												'po_date': move.sale_order_id.date_order,
												'trailer_no': move.action_id.truck_type.truck_type.name if move.action_id.truck_type.truck_type.name else move.action_id.truck_types.name,
												'truck_no': move.action_id.truck_no if move.action_id.truck_no else move.action_id.truck_number,
												'dispatch_qty': move.sale_order_id.order_line.product_uom_qty,
												'received_qty': move.sale_order_id.order_line.qty_delivered,
												'grn_weight': move.action_id.net_weight,
												'demurrage_day': move.action_id.picking_ids.demurrage_day,
												'freight_rate': ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
												'freight_amount': (move.action_id.picking_ids.move_ids_without_package.product_uom_qty) * ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
											}))
											move.sale_order_id.write({
											'tab_sale': self.settlement_ref,
											'total_freight_rate': (move.action_id.picking_ids.move_ids_without_package.product_uom_qty) * ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
												})
											move.write({
											'tab_sale': self.settlement_ref,
											'total_freight_rate': (move.action_id.picking_ids.move_ids_without_package.product_uom_qty) * ((location_rate.demurrage_charge)*(move.action_id.picking_ids.demurrage_day)+location_rate.deport_charge),
												})
											self.write({'fetch_button_hide': True})
											self.write({'settlement_ids': settlement_lines})
											break  
										else:
											raise ValidationError(f" Delivery No: {move.action_id.picking_ids.name}, is pending")
									else:
										raise ValidationError("Approved rate not found")
	
							else:
								continue  
							break 
						else:
							continue
						break 
					else:
						raise ValidationError("TBS rates not found")

			
			
		
	def action_view_account_move(self):
		return {
			'name': ('Account Move'),
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'account.move',
			'domain': [('tbs_sale_id', '=', self.id), ('move_type', '=', 'in_refund')],
			'context': {'default_tbs_sale_id': self.id, 'default_move_type' : 'in_refund' }
		}
	
	def action_view_account_move_tbs_bill(self):
		return {
			'name': ('Account Move'),
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'account.move',
			'domain': [('tbs_sale_id', '=', self.id), ('move_type', '=', 'in_invoice')],
			'context': {'default_tbs_sale_id': self.id, 'default_move_type' : 'in_invoice'}
		}
	
	def action_view_approval(self):
		return {
			'name': ('Approval Request'),
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'approval.request',
			'domain': [('res_id', '=', self.id), ('res_model', '=', self.env.context.get('active_model'))],
		}

	def send_for_approval(self):
		approval_cat_id = self.env.ref('hc_transport.approval_category_tbs_sale_approval')
	
		for rec in self:
			rec.state = 'approval_pending'
			approval_request = self.env['approval.request'].create({
				'request_owner_id': self.env.user.id,
				'category_id': approval_cat_id.id,
				'name': rec.settlement_ref,
				'res_id' : rec.id,
				'res_model' : self.env.context.get('active_model'),
				# 'partner_id': rec.partner_id.id,
				'sale_tbs_id' : self.id
			})

			
	def cancel_request(self):
		for rec in self:
			rec.state = 'cancel'

	def action_resend_draft(self):
		for rec in self:
			rec.state = 'draft'

	def action_approve(self):
		for rec in self:
			rec.state = 'approved'
			

	def report_xls_print(self):
		filename = 'transportor.xls'
		filename = f'{self.settlement_ref}.xls'
		workbook = xlwt.Workbook()
		stylePC = xlwt.XFStyle()
		alignment = xlwt.Alignment()
		alignment.horz = xlwt.Alignment.HORZ_CENTER
		fontP = xlwt.Font()
		fontP.bold = True
		fontP.height = 200
		stylePC.font = fontP
		stylePC.num_format_str = '@'
		stylePC.alignment = alignment
		style_title = xlwt.easyxf("font:height 200;pattern: pattern solid, pattern_fore_colour gray25; font: name Liberation Sans, bold on,color black; align: horiz center")
		style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center")
		style = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black;")
		worksheet = workbook.add_sheet('Sheet 1')
		margin_style = xlwt.easyxf("font: name Liberation Sans,color red;")
		title = "Transportor For : " + self.partner_id.name

		move_records = self.env['tbs.sale'].search([])

		
		worksheet.write_merge(1,1, 1, 11, title , style=style_title)
		worksheet.write(3, 1, 'Sr No.', style_title)
		worksheet.write(3, 2, 'Depot/Location', style_title)
		worksheet.write(3, 3, 'Truck No.', style_title)
		worksheet.write(3, 4, 'Gr No.', style_title)
		worksheet.write(3, 5, 'Date', style_title)
		worksheet.write(3, 6, 'Dispatch QTY.(BL)', style_title)
		worksheet.write(3, 7, 'Received QTY.(BL)', style_title)
		worksheet.write(3, 8, 'Shortage(BL)', style_title)
		worksheet.write(3, 9, '% of Shortage', style_title)
		worksheet.write(3, 10, 'Bill Amount', style_title)
		worksheet.write(3, 11, 'Freight Amount', style_title)
		


		row_index = 4
		clos = 0

		
		for settlement_line in self.settlement_ids:
			worksheet.write(row_index, 1, 1, style)
			worksheet.write(row_index, 2, self.action_id.location_rate_id.name, style)
			worksheet.write(row_index, 3, settlement_line.truck_no, style)
			worksheet.write(row_index, 4, settlement_line.grn_no, style)
			worksheet.write(row_index, 5, str(settlement_line.grn_date), style)
			worksheet.write(row_index, 6, settlement_line.dispatch_qty, style)
			worksheet.write(row_index, 7, settlement_line.received_qty, style)
			# worksheet.write(row_index, 8, settlement_line.received_qty, style)
			# worksheet.write(row_index, 9, settlement_line.received_qty, style)
			worksheet.write(row_index, 10, settlement_line.freight_rate, style)
			worksheet.write(row_index, 11, settlement_line.freight_amount, style)
			row_index += 1

					

		fp = io.BytesIO()
		workbook.save(fp)
		export_id = self.env['purchase.report.excel'].create({'excel_file': base64.b64encode(fp.getvalue()), 'file_name': filename})

		res = {
				'view_mode': 'form',
				'res_id': export_id.id,
				'res_model': 'purchase.report.excel',
				'view_type': 'form',
				'type': 'ir.actions.act_window',
				'target':'new'
				}
		return res




class purchase_report_excel(models.TransientModel):
	_name = "purchase.report.excel"
	_description="Purchase Report Excel"

	excel_file = fields.Binary('Transportor Report')
	file_name = fields.Char('Excel File', size=64)



class TbsSaleSettlementLines(models.Model):
	_name = 'tbs.sale.settlement.lines'
	_description = 'settlement lines'

	set_id = fields.Many2one("tbs.sale", string = "Settlement Line")
	grn_no = fields.Char("GRN No")
	grn_date = fields.Date("GRN Date")
	po_no = fields.Char("SO No")
	po_date = fields.Date("SO Date")
	truck_no =fields.Char("Truck No")
	trailer_no =fields.Char("Truck Type")
	grn_weight = fields.Integer('GRN Weight')
	freight_rate = fields.Float("Freight Rate")
	freight_amount = fields.Float("Freight Amount")
	dispatch_qty =fields.Integer("Dispatch QTY")
	received_qty =fields.Integer("Received QTY")
	demurrage_day = fields.Float("Demurrage Days")


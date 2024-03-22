from odoo import api, fields, models, exceptions
from odoo.exceptions import ValidationError
from datetime import timedelta

class CustomeTransportRates(models.Model):
	_name = 'transport.rates'
	_description = 'Transporter Rates'
	_rec_name = 'custom_name'
	

	transporter_tolerance = fields.Float("Transporter Tolerance")
	transporter = fields.Many2one('res.partner', string='Transporter', copy=False,)
	approval_request = fields.Many2one ("approval.request", string = "Approval")
	state = fields.Selection([
		('draft', 'Draft'),
		('approval_pending', 'Approval Pendding'),
		('rejected', 'Rejected'),
		('approved', 'Approved'),
		('cancel', 'Cancelled'),], 
		string='State', tracking=True, default='draft')
	
	location_rates_ids = fields.One2many("location.rate", "rates_id", "Location Rates")
	rate_for = fields.Selection([
		('customer', 'Customer'),
		('transporter', 'Transporter'),
	], string='Rate For',default='transporter', required=True)
	customer_id = fields.Many2one('res.partner', string='Customer',)
	custom_name = fields.Char("Custom Name", compute='_compute_custom_name', store=True)

	@api.depends('transporter', 'customer_id')
	def _compute_custom_name(self):
		for record in self:
			if record.rate_for == 'transporter':
				record.custom_name = record.transporter.name
			elif record.rate_for == 'customer':
				record.custom_name = record.customer_id.name
			else:
				record.custom_name = ''

	# Override _name_get method to use custom_name
	def name_get(self):
		result = []
		for record in self:
			result.append((record.id, record.custom_name))
		return result

	@api.onchange('rate_for')
	def onchange_rate_for(self):
		if self.rate_for == 'customer':
			self.transporter = False  
		elif self.rate_for == 'transporter':
			self.customer_id = False

	@api.constrains('transporter','customer_id')
	def _check_unique_transporter(self):
		if self.rate_for == 'transporter':
			for record in self:
				existing_record = self.env['transport.rates'].search([
					('transporter', '=', record.transporter.id),
					('id', '!=', record.id),
				])
				if existing_record:
					raise exceptions.ValidationError("Rate for the selected tranporter already exists")
					
		if self.rate_for == 'customer':
			for record in self:
				existing_record = self.env['transport.rates'].search([
					('transporter', '=', record.customer_id.id),
					('id', '!=', record.id),
				])
				if existing_record:
					raise exceptions.ValidationError("Rate for the selected customer already exists")
					

	def action_view_approval(self):
		return {
			'name': ('Approval Request'),
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'approval.request',
			'domain': [('res_id', '=', self.id), ('res_model', '=', self.env.context.get('active_model'))],

		}

	def action_send_for_approval(self):
		approval_cat_id = self.env.ref('hc_transport.approval_category_transporter_rates_approval')
	
		for rec in self:
			rec.state = 'approval_pending'
			rec.location_rates_ids.states = 'approval_pending'
			approval_request = self.env['approval.request'].create({
				'request_owner_id': self.env.user.id,
				'category_id': approval_cat_id.id,
				'name': rec.custom_name,
				'res_id' : rec.id,
				'transport_rates_id' : rec.id,
				'res_model' : self.env.context.get('active_model'),

			})


	def action_resend_draft(self):
		for rec in self:
			rec.state = 'draft'
			rec.location_rates_ids.states = 'draft'

	def cancel_request(self):
		for rec in self:
			rec.state = 'cancel'
			rec.location_rates_ids.states = 'cancel'

	def action_approve(self):
		for rec in self:
			rec.state = 'approved'
			rec.location_rates_ids.write({'states': 'approved'})
			

class CustomeLocationRate(models.Model):
	_name = 'location.rate'
	_rec_name ="locations"

	rates_id = fields.Many2one("transport.rates", string = "rates")
	effective_date = fields.Date("Submission Date")
	locations = fields.Many2one('transporter.location',string ="Depot")
	deport_charge = fields.Float("Depot Charges")
	contract_start = fields.Date("Contract Start")
	contract_end = fields.Date("Contract End")
	demurrage_day = fields.Float("Demurrage Days")
	demurrage_charge = fields.Float("Demurrage Charges/Day")
	rate_total = fields.Float("Rate",compute= "_compute_rate_total")
	states = fields.Selection([
		('draft', 'Draft'),
		('approval_pending', 'Approval Pendding'),
		('approved', 'Approved'),
		('cancel', 'Cancelled'),], 
		string='Status', tracking=True, readonly= True, default='draft')
	partner_id = fields.Many2one(related='rates_id.transporter', store=True, string="Partner")

	
	@api.depends('demurrage_charge', 'deport_charge')
	def _compute_rate_total(self):
		for record in self:
			rate_total = (record.deport_charge + record.demurrage_charge)
			record.rate_total = rate_total
	
	@api.constrains('effective_date', 'locations', 'rates_id.transporter')
	def _check_unique_submission_date_location(self):
		for record in self:
			existing_record = self.env['location.rate'].search([
				('effective_date', '=', record.effective_date),
				('locations', '=', record.locations.id),
				('rates_id.transporter', '=', record.rates_id.transporter.id),
				('id', '!=', record.id),
			])
			if existing_record:
				if existing_record[0].locations.id == record.locations.id and existing_record[0].effective_date == record.effective_date:
					raise exceptions.ValidationError(f"Rate for Depot {record.locations.name} dated {record.effective_date} already exists")
	
	
	@api.constrains('contract_start', 'contract_end')
	def check_contract_dates(self):
		for record in self:
			if record.contract_start >= record.contract_end:
				raise ValidationError("Contract End date should be greater than Contract Start date")
			min_date = record.contract_start + timedelta(days=30)
			if record.contract_end <= min_date:
				raise ValidationError("Contract Period Should Not Be Less Than A Month")

class TrailerType(models.Model):
	_name = 'trailer.type'
	_description = 'Trailer Type'
	_rec_name = 'name'

	name = fields.Char(string='Name')

class TransporterLocation(models.Model):
	_name = 'transporter.location'
	_description = 'Transporter Location'
	_rec_name = 'name'

	name = fields.Char(string='Depot')
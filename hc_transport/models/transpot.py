from odoo import api, fields, models, _

class CustomeTransportToken(models.Model):
	_name = 'transport.token'
	_description = 'Transport Token'
	_rec_name = "name2"

	name = fields.Char(string='Transporter Name')
	name2 = fields.Many2one("res.partner",string='Transporter Name' )
	transfer_date = fields.Datetime(string='Registration Time', default=fields.Datetime.now())
	
	transporter_name = fields.Char(string='Transporter')
	chasis_number=fields.Char("Chassis Number")
	truck_no = fields.Char(string='Truck No')
	state = fields.Selection([
		('draft', 'Document'),
		('approval_pending', 'Approval Pending'),
		('rejected', 'Rejected'),
		('approved', 'Approved'),
		('cancel', 'Cancel'),], 
		string='State', tracking=True, default='draft')
	
	gst_number = fields.Char("GSTIN",)
	
	cin_number = fields.Char("CIN No")
	date = fields.Date(string='Date',)
	approval_request = fields.Many2one('approval.request', string='Approval Request')
	product_id = fields.Many2one('product.template', string='Product Name', copy=False, required=True)
	
	transporter_add = fields.Char("Transporter Address")
	transporter_street = fields.Char("Street")
	transporter_street2 = fields.Char("Street2")
	transporter_city = fields.Char("City")
	transporter_state = fields.Many2one(
		"res.country.state", string='State',
		 readonly=False, store=True,)
	transporter_country = fields.Many2one(
		'res.country', string='Country',
		readonly=False, store=True, compute="_compute_transporter_country")
	transporter_phone = fields.Char("Phone")
	transporter_pin = fields.Char("Pincode")
	email =fields.Char("Email")
	website = fields.Char("Website")
	no_truck =fields.Float("Number of Truck",compute='_compute_no_truck', readonly = True )
	truck_details_ids = fields.One2many("truck.details", 'details_ids', string = "Truck Details")
	
	fiscal_position = fields.Many2one(
		'account.fiscal.position',
		string='Fiscal Position',
	)
	l10n_in_gst_treatment = fields.Selection([
			('regular', 'Registered Business - Regular'),
			('composition', 'Registered Business - Composition'),
			('unregistered', 'Unregistered Business'),
			('consumer', 'Consumer'),
			('overseas', 'Overseas'),
			('special_economic_zone', 'Special Economic Zone'),
			('deemed_export', 'Deemed Export'),
			('uin_holders', 'UIN Holders'),
		], string="GST Treatment")

	l10n_in_pan = fields.Char(
		string="PAN"
	)

	bank = fields.Char("Bank")
	bank_name =fields.Char("Bank Name")
	branch_name = fields.Char("Branch Name")
	ifsc_code = fields.Char("IFSC Code")
	account_number = fields.Float("Account Number")
	account_name = fields.Char("Account Holder Name")
	currency_id = fields.Many2one('res.currency', readonly=True,
		string="Currency") 
	property_account_payable_id = fields.Many2one('account.account',
		string="Account Payable",
		)
	property_account_receivable_id = fields.Many2one('account.account', 
		string="Account Receivable",
		)
	payment_terms = fields.Many2one('account.payment.term',
		string='Customer Payment Terms',)
	related_field =fields.Many2one("sale.order", string = "related")
	approval_id = fields.Many2one ("approval.request", string = "Approval")



	@api.onchange('name2')
	def onchange_name2(self):
		if self.name2:
			self.transporter_street = self.name2.street
			self.transporter_street2 = self.name2.street2
			self.transporter_city = self.name2.city
			self.transporter_state = self.name2.state_id
			self.transporter_country = self.name2.country_id
			self.transporter_phone = self.name2.phone
			self.transporter_pin = self.name2.zip
			self.email = self.name2.email
			self.website = self.name2.website  
			self.gst_number = self.name2.vat  
	

	def action_view_approval(self):
		return {
			'name': _('Approval Request'),
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'approval.request',
			'domain': [('res_id', '=', self.id), ('res_model', '=', self.env.context.get('active_model'))],
		}
	

	@api.depends('transporter_state')
	def _compute_transporter_country(self):
		for record in self:
			if record.transporter_state:
				record.transporter_country = record.transporter_state.country_id.id
			else:
				record.transporter_country = False
	

	def action_confirm(self):
		for rec in self:

			approval_cat_id = self.env.ref('hc_transport.approval_category_registration_transfer')
			approval_request = self.env['approval.request'].create({
				'request_owner_id': self.env.user.id,
				'category_id': approval_cat_id.id,
				'name' : self.name2.name,
				'res_id' : rec.id,
				'res_model' : self.env.context.get('active_model'),

			})
			rec.write({'state': 'approval_pending', 'approval_request': approval_request.id})


	def action_rejeceted(self):
		for rec in self:
			rec.state = 'rejected'

	def action_approved(self):
	
		for rec in self:
			rec.state = 'approved'
		

	def cancel_request(self):
		for rec in self:
			rec.state = 'cancel'


	@api.depends('truck_details_ids')
	def _compute_no_truck(self):
		for record in self:
			record.no_truck = len(record.truck_details_ids)

class CustomeTruckDetails(models.Model):
	_name = 'truck.details'
	_description = 'Truck Details'
	_rec_name = 'truck_type'

	details_ids = fields.Many2one("transport.token", string= "Details")
	truck_type = fields.Many2one("trailer.type", string = "Truck Type")
	chassis_number = fields.Char("Chassis Number")
	truck_no = fields.Char("Truck Number")
	regi_number = fields.Integer("Engine Number")
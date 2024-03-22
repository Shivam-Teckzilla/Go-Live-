from odoo import api, fields, models, _

	
class ResPartner(models.Model):
	_inherit = "res.partner"
	
	partner_type = fields.Selection([
		('transporter', 'Transporter'),], 
		string='Partner Type')
	approval_request = fields.Many2one ("approval.request", string = "Approval")
	approval_count = fields.Integer(compute="_compute_approval_count", string='Approval', copy=False, default=0, store=True)
	sent_for_approval = fields.Boolean("Sent", default = False)
	truck_details_ids = fields.One2many("truck.details", 'details_ids', string = "Truck Details")
	no_truck =fields.Integer("Number of Truck", compute = '_compute_no_truck')
	product_id = fields.Many2one('product.template',
				domain=[('type', '!=', 'service')], 
				string='Product', required=True)
	product_category_ids = fields.Many2many('product.category', string='Product Category')
	transporter_type = fields.Selection([('harp_chemical', 'Harp Chemical'), ('customer', 'Customer')])

	def create(self, values):
		partner = super(ResPartner, self).create(values)
		partner_type = False
		if self._context.get('active_model') == 'res.users':
			partner_type = values[0].get('partner_type',False)
		elif self._context.get('active_model') == 'res.partner':
			partner_type = values.get('partner_type',False)
		if partner_type == 'transporter':
			partner.write({'active': False})
			
			approval_cat_id = self.env.ref('hc_transport.approval_category_registration_transfer')
			approval_request = self.env['approval.request'].create({
				'request_owner_id': self.env.user.id,
				'category_id': approval_cat_id.id,
				'name': partner.name,
				'res_id' : partner.id,
				'action_ids' : partner.id,
				'res_model' : self.env.context.get('active_model')
			})
			partner.write({'sent_for_approval': True})

		if partner_type != 'transporter':
			partner.write({'active': False})
			approval_cat_id = self.env.ref('hc_transport.approval_category_customer_approval')
			approval_request = self.env['approval.request'].create({
				'request_owner_id': self.env.user.id,
				'category_id': approval_cat_id.id,
				'name': partner.name,
				'res_id' : partner.id,
				'action_ids' : partner.id,
				'res_model' : self.env.context.get('active_model'),
			})
			partner.write({ 'sent_for_approval': True})

		return partner
	
	

	@api.depends('truck_details_ids')
	def _compute_no_truck(self):
		for record in self:
			record.no_truck = len(record.truck_details_ids)

	@api.depends('approval_request')
	def _compute_approval_count(self):
		for record in self:
			approvals = self.env['approval.request'].sudo().search([('partner_id', '=', record.id)])
			if approvals:
				record.approval_count = len(approvals)


	def action_view_approval(self):
		return {
			'name': _('Approval Request'),
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'approval.request',
			'domain': [('res_id', '=', self.id), ('res_model', '=', self.env.context.get('active_model'))],

		}
	
	def action_approve(self):
		self.write({'active': True})


	
	
class CustomeTruckDetails(models.Model):
	_name = 'truck.details'
	_description = 'Truck Details'
	_rec_name = 'truck_type'

	details_ids = fields.Many2one("res.partner", string= "Details")
	truck_type = fields.Many2one("trailer.type", string = "Truck Type", required=True)
	chassis_number = fields.Char("Chassis Number", required=True)
	truck_no = fields.Char("Truck Number", required=True)
	regi_number = fields.Char("Engine Number", required=True)
	attachment_ids = fields.Many2many('ir.attachment', string="Attachments", help="Attachments related to the truck details")



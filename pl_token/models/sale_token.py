# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError
from num2words import num2words
from lxml import etree, html


class CustomeSaleToken(models.Model):
    _name = 'sale.token'
    _description = 'Sale Token'
    _order = "issued_time desc, name"

    @api.model
    def create(self, vals):
        res = super(CustomeSaleToken, self).create(vals)
        # sequence_code = "sale.token." + str(res.sale_token_type_id.code)
        sequence_code = res.sale_token_type_id.sequence_id.code
        res.name = self.env['ir.sequence'].next_by_code(sequence_code)
        if not res.name:
            raise ValidationError(" Please create sequence for Token Type")
        return res

    name = fields.Char(string='Sale Token No', copy=False,
                       readonly=True, index=True, default=lambda self: _('New'))

    sale_token_type_id = fields.Many2one('token.type', string='Token Type', required=True,
                                         domain="[('for_token_type', '=', 'sale')]")
    token_date = fields.Datetime(string='Token Date', readonly=True, default=fields.Datetime.now())
    driver_name = fields.Char(string='Driver Name')
    driver_license = fields.Char(string='Driver License')
    driver_mobile = fields.Char(string='Driver Mobile')
    transporter_name = fields.Char(string='Transporter Name')
    truck_no = fields.Char(string='Truck No', related="truck_type.truck_no", store=True)

    transporter_name = fields.Char(string='Transporter Name')
    # truck_name = fields.Many2one("trailer.type", string = 'Truck')
    # truck_no = fields.Char(string='Truck No', related="truck_type.truck_no")
    trailer_type_id = fields.Many2one('trailer.type', string='Truck Type')
    order_id = fields.Many2one('sale.order', string='SO Ref')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issue', 'Issued'),
        ('weight_in', 'Waiting Weighment In'),
        ('loading', 'Loading'),
        ('weight_out', 'Waiting Weighment Out'),
        ('done', 'Done'),
        ('reject', 'Rejected'),
        ('cancel', 'Cancel')], string='State', tracking=True, default='draft')
    issued_time = fields.Datetime(string='Token Issued Time', default=fields.Datetime.now())
    gentry_in_time = fields.Datetime(string='Gate Entry In Time', default=fields.Datetime.now())
    gross_weight = fields.Float(string='Gross Weight', digits='Product Unit of Measure')
    net_weight = fields.Float(string='Net Weight', compute="_compute_net_weight", digits='Product Unit of Measure')
    tare_weight = fields.Float(string='Tare Weight', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', compute='_compute_uom_val')

    # order_id = fields.Many2one('sale.order', string='SO Ref',compute = "_compute_order_id", readonly = False, store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issue', 'Issued'),
        ('weight_in', 'Waiting Weighment In'),
        ('loading', 'Loading'),
        ('weight_out', 'Waiting Weighment Out'),
        ('done', 'Done'),
        ('reject', 'Rejected'),
        ('cancel', 'Cancel')], string='State', tracking=True, default='draft')
    issued_time = fields.Datetime(string='Token Issued Time', default=fields.Datetime.now())
    gentry_in_time = fields.Datetime(string='Gate Entry In Time', default=fields.Datetime.now())
    gross_weight = fields.Float(string='Gross Weight', digits='Product Unit of Measure')
    net_weight = fields.Float(string='Net Weight', compute="_compute_net_weight", digits='Product Unit of Measure')
    tare_weight = fields.Float(string='Tare Weight', digits='Product Unit of Measure')

    weight_in_user_id = fields.Many2one('res.users', string='Weighment In By')
    min_tare_weight = fields.Float(string='Min Tare Weigh Allowed', digits='Product Unit of Measure')
    so_reject_reason_id = fields.Many2one('reject.name', string='Reject Reason', readonly=True)
    po_ref = fields.Char(string='Po Ref')
    temp_id = fields.Many2one('product.template', string='Item')
    temp_name = fields.Char("Name")

    based_on = fields.Selection([
        ('conf_po', 'PO Configuration'),
        ('conf_so', 'SO Configuration')], string='Based On', related='temp_id.based_on')
    transporter = fields.Boolean("Transporter Type", related='temp_id.transporter')

    partner_id = fields.Many2one('res.partner', string='Customer')
    # product_id = fields.Many2one('product.product', string='Item')
    sale_order = fields.Many2one('sale.order', string='Sale Order')
    sale_order_id = fields.Many2one('purchase.order', string='Sale Order')
    sale_order_info = fields.Text(string='Sale Order Info', readonly=True)
    weightment_in_datetime = fields.Datetime(string='Weighment in Datetime', )
    weightment_out_datetime = fields.Datetime(string='Weighment out Datetime', )
    weight_in_user_out = fields.Many2one('res.users', string='Weighment Out By')

    trasfer_status = fields.Selection([
        ('harp_chemical', ' By Harp Chemical'),
        ('customer', 'By Customer'),
    ], string='Transporter Type')

    transfer_status_visible = fields.Boolean(related='sale_token_type_id.product_category.transporter')
    categ_id = fields.Many2one(related='sale_token_type_id.product_category')

    gr_no = fields.Integer("GR No")
    gr_date = fields.Date("GR Date")
    excise_no = fields.Integer("Excise No")
    excise_date = fields.Date("Excise Date")
    permit_no = fields.Integer("Permit No")
    permit_date = fields.Date("Permit Date")
    bt_no = fields.Integer("Bl")
    # truck_details_ids = fields.Many2many("truck.details", string="Truck Details", compute='_compute_truck_details', readonly=True)
    account_move_id = fields.Many2one('account.move', string='Account Move', readonly=True, copy=False)

    invoice_ids = fields.One2many('account.move', 'action_id', string='Invoices')
    invoice_count = fields.Integer(compute="_compute_invoice_count", string='Invoice Count', copy=False, default=0,
                                   store=True)

    temp_product = fields.Many2one("product.product", compute="_compute_temp_id", string="product")

    picking_ids = fields.One2many('stock.picking', 'action_ids', string='Receipt')
    picking_count = fields.Integer(compute="_compute_picking_count", string='Receipt', copy=False, default=0,
                                   store=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)
    transfer_name = fields.Many2one("res.partner", string="Transporter Name", )
    transfer_name_ids = fields.Many2many("res.partner", string="Transporter Name", compute='compute_transfer_name',
                                         store=True)
    truck_type = fields.Many2one("truck.details", string="Truck Type")
    truck_type_ids = fields.Many2many("truck.details", string="Truck Type")
    truck_types = fields.Many2one("trailer.type", string="Truck Type")
    truck_number = fields.Char(string='Truck No')
    pt_id = fields.Many2one('purchase.token')

    def _compute_uom_val(self):
        for uom in self:
            uom.uom_id = self.env['uom.uom'].search([('name', '=', 'Ton')]).id

    @api.depends('trasfer_status', 'temp_id', 'temp_id.categ_id')
    def compute_transfer_name(self):
        for rec in self:
            if rec.temp_id and rec.trasfer_status:
                partner = self.env['res.partner'].search([('transporter_type', '=', rec.trasfer_status)]).filtered(
                    lambda x: rec.temp_id.categ_id.id in x.product_category_ids.ids)
                rec.transfer_name_ids = False
                # rec.transfer_name = False
                rec.transfer_name_ids = partner.ids

    @api.onchange('transfer_name')
    def compute_truck(self):
        for rec in self:
            if rec.transfer_name:
                rec.truck_type = False
                tructk_detail = self.env['truck.details'].search([('details_ids', '=', rec.transfer_name.id)])
                return {'domain': {'truck_type': [('id', 'in', tructk_detail.ids)]}}

    def get_token_data(self):
        return {

            "TicketNo": self.name,
            "VehicleNo": self.truck_no,
            "Date": None,
            "Time": None,
            "EmptyWeight": self.tare_weight,
            "LoadWeight": self.gross_weight,
            "EmptyWeightDate": self.weightment_in_datetime,
            "EmptyWeightTime": self.weightment_in_datetime,
            "LoadWeightDate": self.weightment_out_datetime,
            "LoadWeightTime": None,
            "NetWeight": self.net_weight,
            "Pending": True,
            "Closed": False,
        }

    def update_token_data(self, kw):
        if kw.get('TicketNo'):
            self.name = kw.get('TicketNo')
        if kw.get('VehicleNo'):
            self.truck_no = kw.get('VehicleNo')
        if kw.get('EmptyWeight'):
            self.tare_weight = kw.get('EmptyWeight')
        if kw.get('LoadWeight'):
            self.gross_weight = kw.get('LoadWeight')
        if kw.get('EmptyWeightDate'):
            self.weightment_in_datetime = kw.get('EmptyWeightDate')
        if kw.get('EmptyWeightTime'):
            self.weightment_in_datetime = kw.get('EmptyWeightTime')
        if kw.get('LoadWeightTime'):
            self.weightment_out_datetime = kw.get('LoadWeightTime')
        if kw.get('NetWeight'):
            self.net_weight = kw.get('NetWeight')
        return True

    @api.depends('gross_weight', 'tare_weight')
    def _compute_net_weight(self):
        for record in self:
            record.net_weight = record.gross_weight - record.tare_weight

    @api.depends('temp_id')
    def _compute_temp_id(self):
        for record in self:
            if record.temp_id:
                record.temp_product = record.temp_id.product_variant_id.id
            else:
                record.temp_product = False

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for record in self:
            record.invoice_count = len(record.invoice_ids)

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = len(record.picking_ids)

    def action_view_stock(self):
        return {
            'name': _('Delivery'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': ['|', ('action_ids', 'in', self.ids), ('id', 'in', self.order_id.picking_ids.ids)],
            'context': {
                'create': False,
            },
        }

    def action_view_invoice(self):
        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('action_id', 'in', self.ids)],
            'context': {
                'create': False,
            },
        }

    @api.constrains('driver_mobile')
    def check_driver_mobile(self):
        for record in self:
            if record.driver_mobile and len(record.driver_mobile) != 10:
                raise ValidationError('Mobile number must be 10 digits.')

    @api.onchange('temp_id')
    def _onchange_temp_id(self):
        if self.temp_id:
            self.temp_name = self.temp_id.name
        else:
            self.temp_name = False

    # @api.onchange('po_ref')
    # def onchange_po_ref(self):
    #     if self.po_ref:
    #         sale_order = self.env['sale.order'].search([('po_ref', '=', self.po_ref)], limit=1)
    #         if sale_order:
    #             order_product_ids = sale_order.order_line.mapped('product_id').ids
    #             partner_id = sale_order.partner_id
    #             order_id = False
    #             order_name = self.env['sale.order'].search([
    #                 ('partner_id', '=', partner_id.id),
    #                 ('order_line.product_id', 'in', order_product_ids)
    #             ], limit=1)
    #             if order_name:
    #                 order_id = order_name.ensure_one().name if order_name else False

    #             result_data = {
    #                 'po_ref': self.po_ref,
    #                 'name': order_id,
    #                 'sale_order_id': sale_order,
    #                 'partner_id': partner_id,
    #                 'product_ids': [(6, 0, order_product_ids)] if order_product_ids else False,
    #             }

    #             print("############",result_data)
    #             self.sale_order_info = [result_data]
    #             self.partner_id = result_data['partner_id']
    #             self.product_id = result_data['product_ids'][0] if result_data['product_ids'] else False
    # self.check = result_data['name']

    # print("Before write - order_id:", self.order_id)

    # self.sudo().write({'order_id': result_data['name']})  # Store the 'name' attribute
    # print("After write - order_id:", self.order_id)

    # @api.onchange('po_ref')
    # def onchange_po_ref(self):
    #     if self.po_ref:
    #         sale_order = self.env['sale.order'].search([('po_ref', '=', self.po_ref)], limit=1)
    #         if sale_order:
    #             self.partner_id = sale_order.partner_id.id

    # @api.depends('po_ref')
    # def _compute_order_id(self):
    #     for record in self:
    #         if record.po_ref:
    #             sale_order = self.env['sale.order'].search([('po_ref', '=', record.po_ref)], limit=1)
    #             if sale_order:
    #                 record.order_id = sale_order.id
    #             else:
    #                 record.order_id = False
    #         else:
    #             record.order_id = False

    @api.depends('po_ref', 'partner_id', 'temp_id')
    def _compute_order_id(self):
        for record in self:
            if record.po_ref and record.partner_id and record.temp_id:
                sale_order = self.env['sale.order'].search([
                    ('po_ref', '=', record.po_ref),
                    ('partner_id', '=', record.partner_id.id),
                    ('order_line.product_template_id', '=', record.temp_id.id)
                ], limit=1)

                if sale_order:
                    record.order_id = sale_order.id
                else:
                    record.order_id = False
                    raise ValidationError("No matching Sale Order found for the specified conditions.")
            else:
                record.order_id = False

    def action_issue(self):
        for rec in self:
            if rec.pt_id:
                pt = rec.pt_id
                rec.write({
                    'temp_id': pt.source_so_id.order_line[0].product_template_id.id,
                    'order_id': pt.source_so_id.id,
                    'partner_id': pt.source_so_id.partner_id.id,
                    'gr_no': pt.gr_no,
                    'gr_date': pt.gr_date,
                    'excise_no': pt.excise_no,
                    'excise_date': pt.excise_date,
                    'permit_no': pt.permit_no,
                    'permit_date': pt.permit_date,
                    'bt_no': pt.bt_no,
                })
            if not rec.order_id:
                raise ValidationError("Order ID(SO Ref) is required before issuing.")
            rec.state = 'issue'

    def action_weight_in(self):
        for rec in self:
            if not rec.pt_id:
                rec.weightment_in_datetime = fields.Datetime.now()
                rec.weight_in_user_id = self.env.user.id
            rec.state = 'weight_in'

    # def create_invoice_delivery(self):
    # 	for rec in self:

    # 		invoice = self.env['account.move'].create({
    # 		'move_type': 'out_invoice',
    # 		'invoice_date': fields.Date.today(),
    # 		'partner_id': self.partner_id.id,
    # 		'sale_order_id' : self.order_id.id,
    # 		'action_id':self.id,

    # 		'invoice_line_ids':[(0, 0,{
    # 				'product_id' : self.temp_product.id,
    # 				'price_unit': 1,
    # 				'quantity': 1,
    # 				'tax_ids':None,

    # 		})], })

    # 	stock_location = self.env.ref('stock.stock_location_stock')
    # 	customer_location = self.env.ref('stock.stock_location_customers')

    # 	receipt = self.env['stock.picking'].create({

    # 		'date_deadline': fields.Date.today(),
    # 		'partner_id': self.partner_id.id,
    # 		'sale_order_id' : self.order_id.id,
    # 		'location_dest_id':1,
    # 		'location_id':1,
    # 		'move_type' : 'direct',
    # 		'state' : 'draft',
    # 		'action_ids' :self.id,
    # 		'picking_type_id' :self.env.ref('stock.picking_type_out').id,

    # 		'move_ids_without_package':[(0, 0,{
    # 				'product_id' : self.temp_product.id,
    # 				'product_uom_qty': self.order_id.order_line.product_uom_qty,
    # 				# 'quantity': 1,
    # 				'product_uom': self.temp_product.uom_id.id,
    # 				'name': 'Your Description',
    # 				'reference': 'Your Reference',
    # 				'state': 'draft',
    # 				'location_dest_id':customer_location.id,
    # 				'location_id':stock_location.id,

    # 		})],
    # 		  })
    # 	return (invoice, receipt )

    # def _create_sale_tbs_record(self):
    # 	sale_tbs_obj = self.env['tbs.sale']
    # 	for sale_record in self:
    # 		sale_tbs_obj.create({
    # 			'tbs_type': 'purchase',
    # 			'partner_id': sale_record.account_move_id.partner_id.id,
    # 			'grn_start': sale_record.account_move_id.invoice_date,
    # 			'grn_end': sale_record.account_move_id.invoice_date,
    # 			'action_id': sale_record.account_move_id.id,
    # 		})

    # def _create_invoices(self):
    # 	res = super(CustomeSaleToken, self)._create_invoices()
    # 	self._create_sale_tbs_record()
    # 	return res
    def _populate_rate(self, rec):
        customer_rate = self.env['transport.rates'].search(
            [('rate_for', '=', 'customer'), ('customer_id', '=', rec.partner_id.id)])
        location_rate = customer_rate.location_rates_ids.filtered(
            lambda
                x: x.locations.id == rec.order_id.location_rate_id.id and x.states == 'approved' and x.effective_date <= rec.token_date.date())
        return location_rate[0].rate_total

    def action_weight_out(self):
        for rec in self:
            rec.weightment_out_datetime = fields.Datetime.now()
            rec.weight_in_user_out = self.env.user.id
            rec.state = 'weight_out'
            rec.order_id.with_context(create_delivery=True).action_confirm()
            rec.order_id.picking_ids.write({'action_ids': rec.id, 'sale_order_id': rec.order_id.id})
            rec.order_id._create_invoices()
            # rec.order_id.invoice_ids.write({'action_id' :rec.id, 'sale_order_id': rec.order_id.id, 'post_action': True },)

            for invoice in rec.order_id.invoice_ids:
                product = self.env['product.product'].search(
                    [('detailed_type', '=', 'service'), ('_is_freight', '=', True)], limit=1)
                # rate_from_customer = self._populate_rate(rec)
                invoice.write({
                    'invoice_line_ids': [(0, 0, {'product_id': product.id, 'quantity': 1})],
                    'action_id': rec.id,
                    'sale_order_id': rec.order_id.id,
                    'location_rate_id': rec.order_id.location_rate_id.id,
                    'invoice_date': fields.Date.today()})
                if rec.trasfer_status == 'harp_chemical':
                    # sale_tbs_obj = self.env['tbs.sale']
                    sale_tbs_obj = self.env['tbs.sale'].create({
                        'tbs_type': 'purchase',
                        'partner_id': rec.partner_id.id,
                        'transporter_id': rec.transfer_name.id,
                        'grn_start': fields.Date.today(),
                        'grn_end': fields.Date.today(),
                        'action_id': rec.account_move_id.id,
                    })
                    sale_tbs_obj.action_fetch_data()
                invoice.action_post()

    def action_load(self):
        for rec in self:
            if rec.tare_weight <= 0 and not rec.pt_id:
                raise ValidationError('Tare Weight is Mandatory')
            else:
                rec.state = 'loading'

    def cancel_request(self):
        for rec in self:
            rec.state = 'cancel'

    def action_done(self):
        for rec in self:
            rec.state = 'done'


class AccountMove(models.Model):
    _inherit = "account.move"

    action_id = fields.Many2one("sale.token", string='ID')
    purchase_token_id = fields.Many2one("purchase.token", string='ID')
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    amount_word = fields.Char(string="Amount in Word", compute="_compute_amount_word")
    location_rate_id = fields.Many2one("transporter.location", string="Depot", )

    def _compute_amount_word(self):
        for order in self:
            amount_in_words = num2words(order.amount_total + order.purchase_freight_rate, to='currency', lang='en')

            order.amount_word = amount_in_words


class StockPicking(models.Model):
    _inherit = "stock.picking"

    action_ids = fields.Many2one("sale.token", string='ID')
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")

# -*- coding: utf-8 -*-
from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime
import pytz


class CustomPurchaseToken(models.Model):
    _name = 'purchase.token'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Token"
    _order = "issued_time desc, name"

    @api.model
    def create(self, vals):
        res = super(CustomPurchaseToken, self).create(vals)
        # sequence_code = "purchase.token." + str(res.sale_token_type_id.code)
        sequence_code = res.token_type_id.sequence_id.code
        res.name_sale = self.env['ir.sequence'].next_by_code(sequence_code)
        if not res.name_sale:
            raise ValidationError(" Please create sequence for Token Type")
        return res

    name = fields.Char(string='Inward Token No', copy=False, index=True, readonly=True, default=lambda self: _('New'))
    token_type_id = fields.Many2one('token.type', string='Token Type', required=True,
                                    domain="[('for_token_type', '=', 'purchase')]")
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True,
                              copy=False)
    reject_reason_id = fields.Many2one('reject.name', string='Reject Reason', copy=False)
    sale_order_id = fields.Many2one('sale.order', string='SO Ref', copy=False)
    trailer = fields.Char(string='Truck No', copy=False)
    driver_name = fields.Char(string='Driver Name')
    driver_license = fields.Char(string='Driver License')
    driver_mobile = fields.Char(string='Driver Mobile')
    partner_id = fields.Many2one('res.partner', string='Vendor', copy=False, required=True)

    name_id = fields.Many2one("purchase.order", string="PO Ref", ondelete='cascade')
    po_line_ids = fields.Many2many('purchase.order.line')
    sale_token_id = fields.Many2one('sale.token', compute='_on_change_source_id', store=True)
    order = fields.Char(string="PO Ref")
    token_id = fields.Many2one("stock.picking", string="Stock Picking")
    # order_ids = fields.One2many("purchase.order", "token_id", string="Purchase Orders", ondelete='cascade')

    state_ids = fields.Char("State", readonly=True, related="partner_id.state_id.name")
    city = fields.Char("City", readonly=True, related="partner_id.city")
    gst_number = fields.Char("GSTIN", readonly=True, related="partner_id.vat")

    product_id = fields.Many2one('product.product', string='Raw Material', copy=False)
    price_unit = fields.Float(compute='_compute_price', store=True,string='Price Per Unit')
    product_ids = fields.Many2many('product.product', string='Raw Material IDS', copy=False, compute='compute_product',
                                   store=True)
    # challan_qty = fields.Float(string='Challan Qty(MT)', digits='Product Unit of Measure', copy=False)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True, copy=False)
    # order_ids = fields.Many2many('purchase.order', 'po_token_po_rela', 'token_id', 'order_id', string='PO Ref', copy=False,  required=True, domain="[('order_line.product_id', '=', product_id),('order_line.partner_id', '=', partner_id),('order_line.state', '=', 'done'),]")

    remarks = fields.Text(string='Remarks', copy=False)
    history = fields.Text(string='History', readonly=True, copy=False)
    gate_sno = fields.Char(string='gate_sno', copy=False)
    trailer_type_id = fields.Many2one('trailer.type', string='Truck Type', force_save='1')
    issued_time = fields.Datetime(string='Token Issued Time', default=fields.Datetime.now())
    gentry_in_time = fields.Datetime(string='Gate Entry In Time', default=fields.Datetime.now())
    gentry_in_user_id = fields.Many2one('res.users', string='Gate Entry In By')
    weight_in = fields.Float(string='Gross Weigh', digits='Product Unit of Measure')
    weight = fields.Float(string='Net Weigh', digits='Product Unit of Measure')
    allow_weight_out = fields.Boolean(string='Allow Weighment Out')
    weight_out = fields.Float(string='Tare Weigh', digits='Product Unit of Measure')
    min_tare_weight = fields.Float(string='Min Tare Weigh Allowed', digits='Product Unit of Measure')
    weight_in_user_id = fields.Many2one('res.users', string='Weighment In By')
    weight_in_user_out = fields.Many2one('res.users', string='Weighment Out By')
    weightment_in_datetime = fields.Datetime(string='Weighment in Datetime', )
    weightment_out_datetime = fields.Datetime(string='Weighment out Datetime', )
    gross_weight = fields.Float(string='Gross Weight', )
    net_weight = fields.Float(string='Net Weight', compute="_compute_net_weight", digits='Product Unit of Measure')
    tare_weight = fields.Float(string='Tare Weight', )
    different_weight = fields.Float(string='Different Weight', compute="_compute_different_weight")
    button_debit_hide = fields.Boolean("Debit Hide")
    is_dropship = fields.Boolean()
    source_so_id = fields.Many2one('sale.order', compute='compute_order_value', store=True)

    @api.depends('product_id','name_id')
    def _compute_price(self):
        for rec in self:
            if rec.product_id and rec.name_id:
                po_line = rec.name_id.order_line.filtered(lambda x: x.product_id.id == rec.product_id.id)
                rec.price_unit = po_line.price_unit
            else:
                rec.price_unit = 0

    @api.depends('is_dropship', 'name_id')
    def compute_order_value(self):
        for rec in self:
            rec.source_so_id = False
            if rec.name_id and rec.is_dropship:
                so = self.env['sale.order'].search([('name', '=', rec.name_id.origin.split(", ")[-1])])
                rec.source_so_id = so[-1].id

    def _populate_data_in_sale_token(self, rec):
        data = {
            'sale_token_type_id': rec.token_type_id.id,
            'driver_name': rec.driver_name,
            'driver_license': rec.driver_license,
            'driver_mobile': rec.driver_mobile,
            'issued_time': rec.issued_time,
            'gentry_in_time': rec.gentry_in_time,
            'pt_id': rec.id
            # 'physically_checked_by': rec.physically_checked_by,
            # 'uploading_supervisor': rec.uploading_supervisor,
            # 'sample_token': rec.sample_token,
            # 'sample_taken_by': rec.sample_taken_by,
        }
        return data

    @api.depends('source_so_id')
    def _on_change_source_id(self):
        for rec in self:
            if rec.source_so_id:
                sale_token = self.env['sale.token'].search(
                    [('order_id', '=', rec.source_so_id.id), ('state', '=', 'draft')])
                if len(sale_token) > 1:
                    raise ValidationError(
                        f'There are more than one sale token in draft for this {rec.source_so_id.name} SO')
                else:
                    if not rec.sale_token_id:
                        token = self.env['sale.token'].create(self._populate_data_in_sale_token(rec))
                        rec.sale_token_id = token.id

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issue', 'Issued'),
        ('weight_in', 'Waiting Weighment In'),
        ('unloading', 'Unloading'),
        ('weight_out', 'Waiting Weighment Out'),
        ('done', 'Done'),
        ('reject', 'Rejected'),
        ('cancel', 'Cancel')], string='State', tracking=True, default='draft')
    party_bill_no = fields.Char(string='Vendor Bill No')
    party_bill_date = fields.Date(string='Vendor Bill Date')
    party_bill_quantity = fields.Char(string='Vendor Bill Quantity')
    # gr_number = fields.Char(string='GR Number')
    # gr_date = fields.Date(string='GR Date')
    order_id = fields.Many2one('purchase.order.line')
    validity_date = fields.Date(string='Validity Date')
    physically_checked_by = fields.Many2one('res.users', string='Physically Checked By')
    uploading_supervisor = fields.Many2one('res.users', string='Unloading Supervisor')
    sample_token = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')], string='Sample Taken', default='yes')
    sample_taken_by = fields.Many2one('res.users', string='Sample Taken By')
    on_hold_id = fields.Many2one('reason.reason', string='On Hold Reason')
    resume_reason_id = fields.Many2one('reason.reason', string='Resume Reason')

    hold_status = fields.Selection([
        ('onhold', 'On Hold'),
        ('released', 'Released')], string='Hold status', default='onhold')
    show_ribbon = fields.Boolean(string='Show Ribbon')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company.id)

    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    resume_reason_button = fields.Boolean(string='Reason Button Hide', default=False)
    on_hold_button = fields.Boolean(string='hold Button Hide', default=False)
    uom_id = fields.Many2one('uom.uom', compute='_compute_uom_val')
    gr_no = fields.Integer("GR No")
    gr_date = fields.Date("GR Date")
    excise_no = fields.Integer("Excise No")
    excise_date = fields.Date("Excise Date")
    permit_no = fields.Integer("Permit No")
    permit_date = fields.Date("Permit Date")
    bt_no = fields.Integer("Bl")

    # part_bill_uom_id = fields.Many2one('uom.uom')
    # part_bill_uom_ids = fields.Many2many('uom.uom', compute='_compute_party_bill', store=True)

    # @api.depends('name_id', 'product_id')
    # def _compute_party_bill(self):
    #     for rec in self:
    #         rec.part_bill_uom_ids = False
    #         line_uom = rec.name_id.order_line.filtered(lambda x: x.product_id.id == rec.product_id.id)
    #         if line_uom.product_uom.name == 'KG':
    #             rec.part_bill_uom_ids = [(4, u.id) for u in self.env['uom.uom'].search([('name', '=', ['QTL', 'KG'])])]
    #         if line_uom.product_uom.name == 'QTL' or line_uom.product_uom.name == 'MT':
    #             rec.part_bill_uom_ids = [(4, u.id) for u in
    #                                      self.env['uom.uom'].search([('name', '=', ['MT', 'QTL', 'KG'])])]

    def action_view_receipt(self):
        return {
            'name': _('Receipt'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'stock.picking',
            'domain': [('token_id', '=', self.id)],
            'context': {
                'create': False,
            },
        }

    @api.depends('name_id')
    def compute_product(self):
        for rec in self:
            if rec.name_id:
                val = rec.name_id.order_line.mapped('product_id')
                rec.product_ids = val

    def _compute_uom_val(self):
        for uom in self:
            uom.uom_id = self.env['uom.uom'].search([('name', '=', 'Ton')]).id

    def create_invoice_debit_note(self, product_uom_qty, quantity):
        for rec in self:
            invoice = self.env['account.move'].create({
                'move_type': 'in_refund',
                'invoice_date': fields.Date.today(),
                'partner_id': self.partner_id.id,
                'purchase_token_id': self.id,

                'invoice_line_ids': [(0, 0, {
                    'product_id': self.name_id.order_line.product_id.id,
                    'price_unit': self.name_id.order_line.filtered(
                        lambda x: x.product_id.id == rec.product_id.id).price_unit,
                    'quantity': float(product_uom_qty) - float(quantity),
                    'tax_ids': self.name_id.order_line.taxes_id,

                })], })
        invoice.action_post()
        rec.update({'button_debit_hide': False})
        rec.name_id.write({'debit_notes_ids': [(4, invoice.id, None)]})

    @api.depends('gross_weight', 'tare_weight')
    def _compute_net_weight(self):
        for record in self:
            record.net_weight = record.gross_weight - record.tare_weight

    @api.depends('party_bill_quantity', 'net_weight')
    def _compute_different_weight(self):
        for record in self:
            record.different_weight = float(record.party_bill_quantity) - float(record.net_weight)

    @api.onchange('different_weight')
    def _onchange_different_weight(self):
        for record in self:
            if record.different_weight > 0:
                record.update({'button_debit_hide': True})
            else:
                record.update({'button_debit_hide': False})

    def get_token_data(self):
        return {

            "TicketNo": self.name,
            "VehicleNo": self.trailer,
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
            self.trailer = kw.get('VehicleNo')
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

    @api.constrains('gr_date', 'party_bill_date')
    def _check_gr_date_not_less_than_bill_date(self):
        for record in self:
            if record.gr_date and record.party_bill_date and record.gr_date < record.party_bill_date:
                raise ValidationError("GR Date should not be less than Party Bill Date.")

    @api.constrains('party_bill_no')
    def _check_duplicate_party_bill_no(self):
        for record in self:
            if record.party_bill_no:
                duplicate_records = self.search([('party_bill_no', '=', record.party_bill_no),('partner_id.id','=',record.partner_id.id),('id', '!=', record.id)])
                if duplicate_records:
                    raise ValidationError("Party Bill No must be unique. Duplicate found in record with ID(s): %s" % (
                        duplicate_records.ids))

    @api.constrains('product_id', 'partner_id')
    def _check_partner_required(self):
        for order in self:
            if not order.partner_id and order.product_id:
                raise ValidationError("Please select a partner when a product is chosen.")

    def view_details(self):
        return {
            "name": _("View Details"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "purchase.token",
            "res_id": self.id,
            "view_id": self.env.ref("pl_token.custom_purchase_token_form_view").id,
            "target": "new",
        }

    @api.model
    def create(self, vals):
        sequence_code = "purchase.token." + str(
            self.env['token.type'].search([('id', '=', vals.get('token_type_id'))]).code)
        vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or _('New')
        return super(CustomPurchaseToken, self).create(vals)

    @api.constrains('driver_mobile')
    def check_driver_mobile(self):
        for record in self:
            if record.driver_mobile and len(record.driver_mobile) != 10:
                raise ValidationError('Mobile number must be 10 digits.')

    def action_issue(self):
        for rec in self:
            if not rec.name_id:
                raise ValidationError("Po Ref Required")
            else:
                if rec.sale_token_id:
                    rec.sale_token_id.action_issue()
                rec.state = 'issue'

    def action_weight_in(self):
        for rec in self:
            rec.weightment_in_datetime = fields.Datetime.now()
            rec.weight_in_user_id = self.env.user.id
            rec.state = 'weight_in'
            if rec.sale_token_id:
                rec.sale_token_id.action_weight_in()

    def action_weight_out(self):
        for rec in self:
            rec.weightment_out_datetime = fields.Datetime.now()
            rec.weight_in_user_out = self.env.user.id
            if rec.sale_token_id:
                rec.sale_token_id.action_weight_out()
            rec.state = 'weight_out'

    def send_uploading(self):
        for rec in self:
            if rec.gross_weight <= 0:
                raise ValidationError('Gross Weight is Mandatory')
            else:
                if rec.sale_token_id:
                    rec.sale_token_id.action_load()
                rec.state = 'unloading'

    # New code

    def action_done(self):
        for rec in self:
            if rec.tare_weight <= 0:
                raise ValidationError('Tare Weight is Mandatory')
            else:
                rec.name_id.with_context(no_picking=True)._create_picking()
                receipt_line = rec.name_id.picking_ids.filtered(lambda x: x.state not in ('done','cancel')).move_ids_without_package.filtered(
                    lambda x: x.product_id.id == rec.product_id.id)

                rec.name_id.picking_ids.party_bill_number = rec.party_bill_no
                rec.name_id.picking_ids.token_id = rec.id
                # rec.token_id = rec.id
                # Update the quantity to self.net_weight
                receipt_line.product_uom_qty = rec.party_bill_quantity
                receipt_line.quantity = rec.net_weight

                if rec.sale_token_id:
                    rec.sale_token_id.tare_weight = rec.tare_weight
                    rec.sale_token_id.gross_weight = rec.gross_weight
                    rec.sale_token_id.weight_in_user_id = rec.weight_in_user_id
                    rec.sale_token_id.weightment_in_datetime = rec.weightment_in_datetime
                    rec.sale_token_id.action_done()
                rec.state = 'done'

    # def action_done(self):
    #     for rec in self:
    #         if rec.tare_weight <= 0:
    #             raise ValidationError('Tare Weight is Mandatory')
    #         else:
    #             rec.name_id.with_context(no_picking=True)._create_picking()
    #             receipt_line = rec.name_id.picking_ids.move_ids_without_package.filtered(
    #                 lambda x: x.product_id.id == rec.product_id.id)
    #             rec.name_id.picking_ids.party_bill_number = rec.party_bill_no
    #             rec.name_id.picking_ids.token_id = rec.id
    #             receipt_line.product_uom_qty = rec.party_bill_quantity
    #             # val = rec.uom_id._compute_quantity(rec.net_weight, receipt_line.product_uom)
    #             receipt_line.quantity = rec.party_bill_quantity
    #             # rec.create_invoice_debit_note(receipt_line.product_uom_qty, receipt_line.quantity)
    #             if rec.sale_token_id:
    #                 rec.sale_token_id.tare_weight = rec.tare_weight
    #                 rec.sale_token_id.gross_weight = rec.gross_weight
    #                 rec.sale_token_id.weight_in_user_id = rec.weight_in_user_id
    #                 rec.sale_token_id.weightment_in_datetime = rec.weightment_in_datetime
    #                 rec.sale_token_id.action_done()
    #             rec.state = 'done'

    # commented previous code
    # receipt = self.env['stock.picking'].search([('token_id', '=', rec.id)])
    # receipt_line = receipt.move_ids_without_package.filtered(lambda x: x.product_id.id == rec.product_id.id)
    # val = rec.uom_id._compute_quantity(rec.net_weight, receipt_line.product_uom)
    # receipt_line.quantity = val
    # rec.create_invoice_debit_note()
    # rec.state = 'done'

    def cancel_request(self):
        for rec in self:
            rec.state = 'cancel'

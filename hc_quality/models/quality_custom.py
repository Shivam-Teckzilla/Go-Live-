from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class QcParameters(models.Model):
    _name = 'qc.parameters'
    _description = 'Quality Control Parameters'

    name = fields.Char(string="Name")
    qc_parameter = fields.Selection([('starch', 'Starch'),
                                     ('moisture', 'Moisture'),
                                     ('fm', 'Foreign Matter'), ], string="Qc Parameter", required=True)
    min_value = fields.Float(string="Min Value")
    max_value = fields.Float(string="Max Value")
    standard_value = fields.Float(string="Standard Value")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    product_category_ids = fields.Many2many('product.category', string="Product Category")
    min_max_type = fields.Selection([('no_specific_min', 'Not Specific Min'), ('no_specific_max', 'Not Specific Max')])

    # _sql_constraints = [
    #     ('col_value_unique', 'unique (qc_parameter, standard_value)', 'The combination Qc/Value type already exists!'),
    # ]
    # use api constraint ...add product category m2m


class QualityCheckInherit(models.Model):
    _inherit = 'quality.check'

    starch = fields.Float(string="Starch", copy=False)
    moisture = fields.Float(string="Moisture", copy=False)
    fm = fields.Float(string="Foreign Matter", copy=False)
    qc_parameters_id = fields.Many2one('qc.parameters', string="Qc Parameters")
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True, copy=False)
    quality_state = fields.Selection([
        ('none', 'To do'),
        ('sent_to_approve', 'Sent To Approve'),
        ('is_approved','Approved'),
        ('partially_pass', 'Partially Pass'),
        ('pass', 'Pass'),
        ('fail', 'Failed')], string='Status', tracking=True,
        default='none', copy=False)
    approval_request_id = fields.Many2one('approval.request', string="Approval Request", copy=False)
    is_approved = fields.Boolean(string="Is Approved", copy=False)

    # is_debit_note = fields.Boolean(string="Is Debit Note", compute="get_is_debit_note")
    #
    # def get_is_debit_note(self):
    #     account_move_search = self.env['account.move'].search([('quality_check_id', '=', self.id),('move_type','=','in_refund')])
    #     if account_move_search:
    #         self.is_debit_note = True
    #     else:
    #         self.is_debit_note = False


    def sent_to_approve(self):
        for rec in self:
            approval_cat_id = self.env.ref('hc_quality.approval_category_quality_approval')
            approval_request = self.env['approval.request'].sudo().search([('res_model','=','quality.check'),('res_id','=',rec.id)])
            if not approval_request:
                approval_request = self.env['approval.request'].sudo().create({
                    'request_owner_id': self.env.user.id,
                    'category_id': approval_cat_id.id,
                    'name': self.name,
                    'res_id': rec.id,
                    'quality_approval': rec.id,
                    'res_model': 'quality.check',

                })
            approval_request.action_confirm()
            rec.write({'quality_state': 'sent_to_approve', 'approval_request_id': approval_request.id})

    def set_to_draft(self):
        self.is_approved = False
        self.write({'quality_state': 'none'})

    def action_approve(self):
        self.is_approved = True
        self.write({'quality_state': 'is_approved'})

    def open_records_list_view(self):

        action = {
            'name': 'Approval',
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'tree',
            'domain': [('id', '=', self.approval_request_id.ids)],
        }
        return action



    def do_partially_pass(self):
        self.write({'quality_state': 'partially_pass'})


    def create_debit_note(self):
        self.ensure_one()
        search_starch = self.env['qc.parameters'].search([('product_category_ids', 'in', self.product_id.categ_id.id), ('qc_parameter', '=', 'starch')])

        search_moisture = self.env['qc.parameters'].search([('product_category_ids', 'in', self.product_id.categ_id.id), ('qc_parameter', '=', 'moisture')])

        search_fm = self.env['qc.parameters'].search([('product_category_ids', 'in', self.product_id.categ_id.id), ('qc_parameter', '=', 'fm')])

        if not search_starch and not search_moisture and not search_fm:
            raise ValidationError(_('Qc Configuration not satisfied'))

        # Create a Debit Note for difference
        search_po = self.env['purchase.order'].search([('name', '=', self.picking_id.origin)])
        search_dispatch_quantity = self.picking_id.move_ids_without_package.filtered(
            lambda line: line.product_id == self.product_id).product_uom_qty
        search_grn_quantity = self.picking_id.move_ids_without_package.filtered(
            lambda line: line.product_id == self.product_id).quantity
        sum_difference = search_dispatch_quantity - search_grn_quantity
        new_unit_price = search_po.order_line.filtered(lambda line: line.product_id == self.product_id).price_unit
        if sum_difference != 0:
            debit_note = self.env['account.move'].create({
                'partner_id': self.partner_id.id,
                'move_type': 'in_refund',
                'ref': f"Debit Note for Quantity Difference {self.picking_id.name} and quality check {self.name}",
                'invoice_date': datetime.now(),
                'quality_check_id': self.id,
                'invoice_line_ids': [(0, 0, {
                    'product_id': self.product_id.id,
                    'name': self.product_id.name,
                    'quantity': sum_difference,
                    'price_unit': new_unit_price,
                    'tax_ids': False
                })],
            })
            debit_note.action_post()
            search_po.write({'debit_notes_ids': [(4, debit_note.id)]})


        # Fail condition

        if (search_starch and search_starch.max_value < self.starch or
                self.starch < search_starch.min_value and self.starch < search_starch.standard_value):
            log_message = f"Failed because Starch is not in range"
            self.message_post(body=log_message, author_id=self.env.user.partner_id.id, message_type="comment")
            self.do_fail()
        elif (search_moisture and search_moisture.max_value < self.moisture or
              self.moisture < search_moisture.min_value and self.moisture < search_moisture.standard_value):
            log_message = f"Failed because Moisture is not in range."
            self.message_post(body=log_message, author_id=self.env.user.partner_id.id, message_type="comment")
            self.do_fail()
        elif (search_fm and search_fm.max_value < self.fm or
              self.fm < search_fm.min_value and self.fm < search_fm.standard_value):
            log_message = f"Failed because FM is not in range"
            self.message_post(body=log_message, author_id=self.env.user.partner_id.id, message_type="comment")
            self.do_fail()
        else:


            sum_difference = 0
            # price_difference_starch, price_difference_moisture, price_difference_fm = 0, 0, 0
            #STARCH CUT Formula
            # If Starch Value < Standard AND Moisture Value <= Standard AND FM Value <= Standard
            # 	Starch Cut Value = Basic Rate/Standard x (Standard-Starch Value) x Net Weight
            po_search = self.env['purchase.order'].search([('name', '=', self.picking_id.origin)])

            # if self.starch <= search_starch.standard_value and self.starch >= search_starch.min_value:
            # if self.starch <= search_starch.standard_value and self.moisture <= search_moisture.standard_value and self.fm <= search_fm.standard_value:
            if self.starch < search_starch.standard_value:
                price_unit_list = po_search.order_line.mapped('price_unit')
                price_unit_list = [float(price) for price in price_unit_list]
                price_difference_starch = sum(price_unit_list)/search_starch.standard_value * (search_starch.standard_value - self.starch) * search_grn_quantity
                print('price_difference_starch', price_difference_starch)
            else:
                 price_difference_starch = 0
            # else:
                # price_difference_starch = 0


            # Moisture Parameter
            # MOISTURE CUT Formula
            # If Moisture Value > Standard
            # 	Moisture Cut Value = Basic Rate x (Moisture Value – Standard)/100 x Net Weight
            # Endif

            if self.moisture > search_moisture.standard_value and self.moisture <= search_moisture.max_value:
                price_unit_list_moisture = po_search.order_line.mapped('price_unit')
                price_unit_list_moisture = [float(price) for price in price_unit_list_moisture]
                price_difference_moisture = sum(price_unit_list_moisture) * (self.moisture - search_moisture.standard_value) / 100 * search_grn_quantity
                print('price_difference_moisture', price_difference_moisture)
            else:
                price_difference_moisture = 0

            # Foreignn Matter
            # FM CUT Formula
            # If FM Value > Standard
            # 	FM Cut Value = Basic Rate x (FM Value – Standard)/100 * Net Weight
            # Endif

            if self.fm > search_fm.standard_value and self.fm <= search_fm.max_value:
                price_unit_list_fm = po_search.order_line.mapped('price_unit')
                price_unit_list_fm = [float(price) for price in price_unit_list_fm]
                price_difference_fm = sum(price_unit_list_fm) * (self.fm - search_fm.standard_value) / 100 * search_grn_quantity
                print('price_difference_fm', price_difference_fm)
            else:
                price_difference_fm = 0

            # Calculate the sum of absolute differences

            # sum_difference = abs(price_difference_starch) + abs(price_difference_moisture) + abs(price_difference_fm)

            # if sum_difference > 0:
            if price_difference_starch != 0 or price_difference_moisture != 0 or price_difference_fm != 0:

                search_po = self.env['purchase.order'].search([('name', '=', self.picking_id.origin)])
                # search_grn_quantity = self.picking_id.tot_req_quant

                # Debit Note for starch
                if search_po:
                    if price_difference_starch > (price_difference_moisture + price_difference_fm):
                        # po_price_subtotal = search_po.order_line.filtered(lambda line: line.product_id == self.product_id).price_subtotal
                        # new_unit_price = price_difference_starch
                        new_unit_price = price_difference_starch / max(1, search_grn_quantity)

                        print('new_unit_price', price_difference_starch)

                        # Add validation on PO quantity total debit note qty should not be greater than PO quantity
                        # Create a debit note
                        debit_note = self.env['account.move'].create({
                            'partner_id': self.partner_id.id,
                            'move_type': 'in_refund',
                            'ref':f"Debit Note for Starch {self.name}",
                            'invoice_date': datetime.now(),
                            'quality_check_id': self.id,
                            'invoice_line_ids': [(0, 0, {
                                'product_id': self.product_id.id,
                                'name': self.product_id.name + " : (For Starch Cut Value)",
                                'quantity': search_grn_quantity,
                                'price_unit': new_unit_price,
                                'tax_ids': False
                            })],
                        })
                        debit_note.action_post()
                        search_po.write({'debit_notes_ids': [(4, debit_note.id)]})
                    else:
                        log_message = f"Failed because Starch is not Satisfying the condition because starch is greater than {price_difference_moisture} '+' {price_difference_fm}"
                        self.message_post(body=log_message, author_id=self.env.user.partner_id.id,
                                          message_type="comment")
                    if price_difference_starch < (price_difference_moisture + price_difference_fm):
                        # new_unit_price = price_difference_moisture
                        new_unit_price = price_difference_moisture / max(1, search_grn_quantity)
                        print('new_unit_price', price_difference_moisture)
                        debit_note = self.env['account.move'].create({
                            'partner_id': self.partner_id.id,
                            'move_type': 'in_refund',
                            'ref':f"Debit Note for Moisture {self.name}",
                            'invoice_date': datetime.now(),
                            'quality_check_id': self.id,
                            'invoice_line_ids': [(0, 0, {
                                'product_id': self.product_id.id,
                                'name': self.product_id.name + " : (For Moisture Cut Value)",
                                'quantity': search_grn_quantity,
                                'price_unit': new_unit_price,
                                'tax_ids': False
                            })],
                        })
                        debit_note.action_post()
                        search_po.write({'debit_notes_ids': [(4, debit_note.id)]})
                    else:
                        log_message = f"Failed because Moisture is not Satisfying the condition"
                        self.message_post(body=log_message, author_id=self.env.user.partner_id.id,
                                          message_type="comment")

                    if price_difference_starch < (price_difference_moisture + price_difference_fm):
                        # new_unit_price = price_difference_fm
                        new_unit_price = price_difference_fm / max(1, search_grn_quantity)
                        print('new_unit_price', price_difference_fm)
                        debit_note = self.env['account.move'].create({
                            'partner_id': self.partner_id.id,
                            'move_type': 'in_refund',
                            'ref':f"Debit Note for Foreign matter {self.name}",
                            'invoice_date': datetime.now(),
                            'quality_check_id': self.id,
                            'invoice_line_ids': [(0, 0, {
                                'product_id': self.product_id.id,
                                'name': self.product_id.name + " : (For FM Cut Value)",
                                'quantity': search_grn_quantity,
                                'price_unit': new_unit_price,
                                'tax_ids': False
                            })],
                        })
                        debit_note.action_post()
                        search_po.write({'debit_notes_ids': [(4, debit_note.id)]})
                    else:
                        log_message = f"Failed because Foreign matter is not Satisfying the condition"
                        self.message_post(body=log_message, author_id=self.env.user.partner_id.id,
                                          message_type="comment")
                    self.do_partially_pass()
                else:
                    raise ValidationError(_('Purchase Order not found'))
            else:
                self.do_pass()

    def open_refunds(self):
        account_move_search = self.env['account.move'].search([('quality_check_id', '=', self.id),('move_type','=','in_refund')])
        return {
            'name': ('Debit Notes'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', account_move_search.ids)]
        }


class QualityAlertInherit(models.Model):
    _inherit = 'quality.alert'

    # Debit note on Fail
    check_id_state = fields.Selection(related='check_id.quality_state')
    percentage_field = fields.Float(string="Settlement Percentage", default=0)

    starch = fields.Float(string="Starch", copy=False)
    moisture = fields.Float(string="Moisture", copy=False)
    fm = fields.Float(string="Foreign Matter", copy=False)
    status = fields.Selection(selection=[('new',"New"),('done',"Settled"),('rejected',"Rejected")],default='new')

    def debit_note_create_fail(self):
        self.picking_id = self.check_id.picking_id.id
        if not self.starch or not self.moisture or not self.fm:
            raise ValidationError(_('Please fill all QC parameters !!'))
        self.ensure_one()
        search_starch = self.env['qc.parameters'].search(
            [('product_category_ids', 'in', self.check_id.product_id.categ_id.id), ('qc_parameter', '=', 'starch')])

        search_moisture = self.env['qc.parameters'].search(
            [('product_category_ids', 'in', self.check_id.product_id.categ_id.id), ('qc_parameter', '=', 'moisture')])

        search_fm = self.env['qc.parameters'].search(
            [('product_category_ids', 'in', self.check_id.product_id.categ_id.id), ('qc_parameter', '=', 'fm')])

        if not search_starch and not search_moisture and not search_fm:
            raise ValidationError(_('Qc Configuration not satisfied'))

        po_search = self.env['purchase.order'].search([('name', '=', self.picking_id.origin)])
        search_po = self.env['purchase.order'].search([('name', '=', self.picking_id.origin)])
        search_dispatch_quantity = self.picking_id.move_ids_without_package.filtered(
            lambda line: line.product_id == self.check_id.product_id).product_uom_qty
        search_grn_quantity = self.picking_id.move_ids_without_package.filtered(
            lambda line: line.product_id == self.check_id.product_id).quantity
        sum_difference = search_dispatch_quantity - search_grn_quantity
        new_unit_price = search_po.order_line.filtered(lambda line: line.product_id == self.check_id.product_id).price_unit

        starch_standard_value = search_starch.standard_value
        moisture_standard_value = search_moisture.standard_value
        fm_standard_value = search_fm.standard_value
        price_difference_fm = 0
        price_difference_starch = 0
        price_difference_moisture = 0

        # if self.starch != self.check_id.starch:
        if self.starch < starch_standard_value and self.moisture <= moisture_standard_value and self.fm <= fm_standard_value:
            price_unit_list = po_search.order_line.mapped('price_unit')
            price_unit_list = [float(price) for price in price_unit_list]
            price_difference_starch = sum(price_unit_list) / starch_standard_value * (
                        starch_standard_value - self.starch) * search_grn_quantity
            print('price_difference_starch', price_difference_starch)

        # Moisture Parameter
        # MOISTURE CUT Formula
        # If Moisture Value > Standard
        # 	Moisture Cut Value = Basic Rate x (Moisture Value – Standard)/100 x Net Weight
        # Endif

        # if self.moisture != self.check_id.moisture:
        if self.moisture > moisture_standard_value and self.moisture <= search_moisture.max_value:
            price_unit_list_moisture = po_search.order_line.mapped('price_unit')
            price_unit_list_moisture = [float(price) for price in price_unit_list_moisture]
            price_difference_moisture = sum(price_unit_list_moisture) * (
                        self.moisture - moisture_standard_value) / 100 * search_grn_quantity
            print('price_difference_moisture', price_difference_moisture)


        # Foreignn Matter
        # FM CUT Formula
        # If FM Value > Standard
        # 	FM Cut Value = Basic Rate x (FM Value – Standard)/100 * Net Weight
        # Endif

        # if self.fm != self.check_id.fm:
        if self.fm > fm_standard_value and self.fm <= search_fm.max_value:
            price_unit_list_fm = po_search.order_line.mapped('price_unit')
            price_unit_list_fm = [float(price) for price in price_unit_list_fm]
            price_difference_fm = sum(price_unit_list_fm) * (
                        self.fm - fm_standard_value) / 100 * search_grn_quantity
            print('price_difference_fm', price_difference_fm)


        # Calculate the sum of absolute differences

        # sum_difference = abs(price_difference_starch) + abs(price_difference_moisture) + abs(price_difference_fm)

        # if sum_difference > 0:
        if price_difference_starch != 0 or price_difference_moisture != 0 or price_difference_fm != 0:

            search_po = self.env['purchase.order'].search([('name', '=', self.picking_id.origin)])
            # search_grn_quantity = self.picking_id.tot_req_quant

            # Debit Note for starch
            if search_po:
                if price_difference_starch:
                    # po_price_subtotal = search_po.order_line.filtered(lambda line: line.product_id == self.product_id).price_subtotal
                    # new_unit_price = price_difference_starch
                    new_unit_price = price_difference_starch / max(1, search_grn_quantity)

                    print('new_unit_price', price_difference_starch)

                    # Add validation on PO quantity total debit note qty should not be greater than PO quantity
                    # Create a debit note
                    debit_note = self.env['account.move'].create({
                        'partner_id': self.check_id.partner_id.id,
                        'move_type': 'in_refund',
                        'ref': f"Debit Note for Starch {self.name}",
                        'invoice_date': datetime.now(),
                        'quality_alert_id': self.id,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.product_id.id,
                            'name': self.check_id.product_id.name + " : (For Starch Cut Value)",
                            'quantity': search_grn_quantity,
                            'price_unit': new_unit_price,
                            'tax_ids': False
                        })],
                    })
                    debit_note.action_post()
                    search_po.write({'debit_notes_ids': [(4, debit_note.id)]})
                else:
                    log_message = f"Failed because Starch must be smaller than Standard value and greater than Minimum value or Satisfying the condition"
                    self.message_post(body=log_message, author_id=self.env.user.partner_id.id,
                                      message_type="comment")
                if price_difference_moisture:
                    # new_unit_price = price_difference_moisture
                    new_unit_price = price_difference_moisture / max(1, search_grn_quantity)
                    print('new_unit_price', price_difference_moisture)
                    debit_note = self.env['account.move'].create({
                        'partner_id': self.check_id.partner_id.id,
                        'move_type': 'in_refund',
                        'ref': f"Debit Note for Moisture {self.name}",
                        'invoice_date': datetime.now(),
                        'quality_alert_id': self.id,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.product_id.id,
                            'name': self.check_id.product_id.name + " : (For Moisture Cut Value)",
                            'quantity': search_grn_quantity,
                            'price_unit': new_unit_price,
                            'tax_ids': False
                        })],
                    })
                    debit_note.action_post()
                    search_po.write({'debit_notes_ids': [(4, debit_note.id)]})
                else:
                    log_message = f"Failed because Moisture must be greater than Standard value and smaller than Max value"
                    self.message_post(body=log_message, author_id=self.env.user.partner_id.id,
                                      message_type="comment")

                if price_difference_fm:
                    # new_unit_price = price_difference_fm
                    new_unit_price = price_difference_fm / max(1, search_grn_quantity)
                    print('new_unit_price', price_difference_fm)
                    debit_note = self.env['account.move'].create({
                        'partner_id': self.check_id.partner_id.id,
                        'move_type': 'in_refund',
                        'ref': f"Debit Note for Foreign matter {self.name}",
                        'invoice_date': datetime.now(),
                        'quality_alert_id': self.id,
                        'invoice_line_ids': [(0, 0, {
                            'product_id': self.check_id.product_id.id,
                            'name': self.check_id.product_id.name + " : (For FM Cut Value)",
                            'quantity': search_grn_quantity,
                            'price_unit': new_unit_price,
                            'tax_ids': False
                        })],
                    })
                    debit_note.action_post()
                    search_po.write({'debit_notes_ids': [(4, debit_note.id)]})
                else:
                    log_message = f"Failed because Foreign matter must be greater than Standard value and smaller than Max value"
                    self.message_post(body=log_message, author_id=self.env.user.partner_id.id,
                                      message_type="comment")

        settled_stage = self.env['quality.alert.stage'].sudo().search([('done', '=', True)], limit=1)
        if settled_stage:
            self.stage_id = settled_stage.id
            self.status = 'done'
        else:
            raise ValidationError(_('Stage for settlement not found in QA stage master !!'))

    # def debit_note_create_fail(self):
    #     if not self.percentage_field:
    #         raise ValidationError(_('Please enter a percentage'))
    #
    #     search_po = self.env['purchase.order'].search([('name', '=', self.check_id.picking_id.origin)])
    #     search_po_line = search_po.order_line.filtered(lambda line: line.product_id == self.product_id)
    #
    #     if not search_po_line:
    #         raise ValidationError(_('Product not found in the purchase order'))
    #
    #     search_po_quantity = search_po_line.product_uom_qty
    #     original_unit_price = search_po_line.price_unit
    #     percentage_to_subtract = self.percentage_field
    #
    #     # Calculate the new unit price as a percentage of the original unit price
    #     new_unit_price = original_unit_price * (1 - percentage_to_subtract / 100)
    #     new_unit_price = original_unit_price - new_unit_price
    #
    #     # Create debit note
    #     debit_note = self.env['account.move'].create({
    #         'partner_id': self.partner_id.id,
    #         'move_type': 'in_refund',
    #         'ref': f"Settlement Debit Note for {self.name}",
    #         'invoice_date': datetime.now(),
    #         'quality_alert_id': self.id,
    #         'invoice_line_ids': [(0, 0, {
    #             'product_id': self.product_id.id,
    #             'name': self.product_id.name,
    #             'quantity': search_po_quantity,
    #             'price_unit': new_unit_price,
    #             'tax_ids': False
    #         })],
    #     })
    #
    #     return {
    #         'name': ('Debit Notes'),
    #         'view_mode': 'form',
    #         'res_model': 'account.move',
    #         'res_id': debit_note.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'current',
    #     }


    def rejected_debit_note(self):
        search_po = self.env['purchase.order'].search([('name', '=', self.check_id.picking_id.origin)])
        search_dispatch_quantity = self.check_id.picking_id.move_ids_without_package.filtered(
            lambda line: line.product_id == self.product_id).product_uom_qty
        search_received_quantity = self.check_id.picking_id.move_ids_without_package.filtered(
            lambda line: line.product_id == self.product_id).quantity

        # Assuming 'Difference' is part of the reference of debit notes created in check_id
        debit_note_difference = self.env['account.move'].search([
            ('quality_check_id', '=', self.check_id.id),
            ('ref', 'ilike', 'Difference'),
        ])

        if debit_note_difference:
            search_grn_quantity = search_dispatch_quantity - sum(debit_note_difference.mapped('invoice_line_ids.quantity'))
        else:
            search_grn_quantity = search_received_quantity
        search_po_price = search_po.order_line.filtered(
            lambda line: line.product_id == self.product_id).price_unit
        new_unit_price = search_po_price

        # Create debit note
        debit_note = self.env['account.move'].create({
            'partner_id': self.partner_id.id,
            'move_type': 'in_refund',
            'invoice_date': datetime.now(),
            'quality_alert_id': self.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'name': self.product_id.name,
                'quantity': search_grn_quantity,
                'price_unit': new_unit_price,
                'tax_ids': False,
            })],
        })
        rejected_stage = self.env['quality.alert.stage'].sudo().search([('is_rejected','=',True)],limit=1)
        if rejected_stage:
            self.stage_id = rejected_stage.id
            self.status = 'rejected'
        else:
            raise ValidationError(_('Stage for rejection not found in QA stage master !!'))
        return {
            'name': ('Debit Notes'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': debit_note.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }


    def open_refunds(self):
        account_move_search = self.env['account.move'].search([('quality_alert_id', '=', self.id),('move_type','=','in_refund')])
        return {
            'name': ('Debit Notes'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', account_move_search.ids)]
        }

class QualityAlertStages(models.Model):
    _inherit ='quality.alert.stage'

    is_rejected = fields.Boolean("Rejected")
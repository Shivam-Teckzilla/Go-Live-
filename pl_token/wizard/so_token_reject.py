# -*- coding: utf-8 -*-
from odoo import api, models, fields


class SaleRejectReason(models.TransientModel):
    _name = 'so.reject.reason'
    _description = 'Reject Reason'

    so_reject_reason_id = fields.Many2one('reject.name', string='Reject Reason', required=True)
    record_id = fields.Many2one('sale.token')

    def so_token_reject_reason(self):
        refuse_id = self.env['sale.token'].browse(self._context.get('active_id'))
        refuse_id.write({'so_reject_reason_id': self.so_reject_reason_id})
        refuse_id.write({'state': 'reject'})
        return {'type': 'ir.actions.act_window_close'}


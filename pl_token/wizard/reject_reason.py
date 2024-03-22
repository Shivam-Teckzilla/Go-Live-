# -*- coding: utf-8 -*-
from odoo import api, models, fields


class RejectReason(models.TransientModel):
    _name = 'reject.reason'
    _description = 'Reject Reason'

    reject_reason_id = fields.Many2one('reject.name', string='Reject Reason', required=True)
    record_id = fields.Many2one('purchase.token')

    def reject_reason_of_token(self):
        refuse_id = self.env['purchase.token'].browse(self._context.get('active_id'))
        refuse_id.write({'reject_reason_id': self.reject_reason_id})
        refuse_id.write({'state': 'reject'})
        return {'type': 'ir.actions.act_window_close'}


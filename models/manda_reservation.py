import random
import string
from odoo import models, fields, api

class MandaReservation(models.Model):
    _name = 'manda.reservation'
    _description = 'Réservation Chambre MandaBar'
    _rec_name = 'reference'
    _order = 'checkin_date desc'

    reference = fields.Char(string='Référence', readonly=True, default='MANDA-NEW')
    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    partner_email = fields.Char(related='partner_id.email', string='Email client')
    partner_phone = fields.Char(related='partner_id.phone', string='Téléphone')
    room_id = fields.Many2one('manda.room', string='Chambre', required=True)
    room_number = fields.Integer(related='room_id.number', string='Numéro chambre')
    lock_id = fields.Many2one(related='room_id.lock_id', string='Serrure', store=True)
    checkin_date = fields.Datetime(string='Date arrivée', required=True)
    checkout_date = fields.Datetime(string='Date départ', required=True)
    duration_nights = fields.Integer(string='Nuits', compute='_compute_duration', store=True)
    amount_total = fields.Float(string='Montant total (€)', compute='_compute_amount', store=True)
    payment_state = fields.Selection([('pending', 'En attente'), ('paid', 'Payé'), ('refunded', 'Remboursé')], string='État paiement', default='pending')
    bank_account = fields.Char(string='Compte bancaire', compute='_compute_bank_account')
    pin_code = fields.Char(string='Code PIN', readonly=True)
    pin_sent = fields.Boolean(string='PIN envoyé', default=False)
    unifi_user_id = fields.Char(string='ID Utilisateur UniFi', readonly=True, help='ID de l\'utilisateur temporaire créé dans UniFi Access.')
    state = fields.Selection([('draft', 'Brouillon'), ('confirmed', 'Confirmée'), ('checked_in', 'En cours'), ('checked_out', 'Terminée'), ('cancelled', 'Annulée')], string='État', default='draft')
    notes = fields.Text(string='Notes')

    @api.depends('checkin_date', 'checkout_date')
    def _compute_duration(self):
        for rec in self:
            if rec.checkin_date and rec.checkout_date:
                rec.duration_nights = (rec.checkout_date - rec.checkin_date).days
            else:
                rec.duration_nights = 0

    @api.depends('duration_nights', 'room_id.price_per_night')
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = rec.duration_nights * (rec.room_id.price_per_night or 0)

    def _compute_bank_account(self):
        settings = self.env['manda.settings'].sudo().get_settings()
        for rec in self:
            rec.bank_account = settings.bank_account if settings else ''

    def _generate_pin(self):
        return ''.join(random.choices(string.digits, k=6))

    def action_confirm(self):
        for rec in self:
            if not rec.pin_code:
                rec.pin_code = rec._generate_pin()
            rec.state = 'confirmed'
            rec.reference = self.env['ir.sequence'].next_by_code('manda.reservation') or 'MANDA-001'
            rec.action_send_pin_email()

    def action_checkin(self):
        for rec in self:
            rec.state = 'checked_in'
            rec.room_id.state = 'occupied'
            if rec.lock_id:
                unifi_user_id = rec.lock_id.create_unifi_access(
                    pin=rec.pin_code, start_time=rec.checkin_date,
                    end_time=rec.checkout_date,
                    label=f"{rec.reference} - {rec.partner_id.name}",
                    reservation=rec
                )
                if unifi_user_id:
                    rec.unifi_user_id = str(unifi_user_id)

    def action_checkout(self):
        for rec in self:
            rec.state = 'checked_out'
            rec.room_id.state = 'available'
            if rec.lock_id and rec.unifi_user_id:
                rec.lock_id.revoke_unifi_access(unifi_user_id=rec.unifi_user_id)
                rec.unifi_user_id = False

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            if rec.lock_id and rec.unifi_user_id:
                rec.lock_id.revoke_unifi_access(unifi_user_id=rec.unifi_user_id)
                rec.unifi_user_id = False
            rec.room_id.state = 'available'

    def action_send_pin_email(self):
        template = self.env.ref('airbnb_manda.email_template_pin_code', raise_if_not_found=False)
        if template:
            for rec in self:
                template.send_mail(rec.id, force_send=True)
                rec.pin_sent = True

    def _get_thread_with_access(self, thread_id, **kwargs):
        return self.browse(thread_id) if self.browse(thread_id).exists() else self.env['manda.reservation']

import random
import string
import logging
from datetime import timedelta
from odoo import models, fields, api, exceptions

_logger = logging.getLogger(__name__)

class MandaReservation(models.Model):
    _name = 'manda.reservation'
    _description = 'Reservation Chambre Airbnb_Manda'
    _rec_name = 'reference'
    _order = 'checkin_date desc'

    reference = fields.Char(string='Reference', readonly=True, default='Airbnb_Manda-new')
    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    partner_email = fields.Char(related='partner_id.email', string='Email client')
    partner_phone = fields.Char(related='partner_id.phone', string='Telephone')
    room_id = fields.Many2one('manda.room', string='Chambre', required=True)
    room_number = fields.Integer(related='room_id.number', string='Numero chambre')
    lock_id = fields.Many2one(related='room_id.lock_id', string='Serrure', store=True)

    checkin_date = fields.Datetime(string='Date arrivee', required=True)
    checkout_date = fields.Datetime(string='Date depart', required=True)
    duration_nights = fields.Integer(string='Nuits', compute='_compute_duration', store=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirme'),
        ('checked_in', 'En cours'),
        ('checked_out', 'Termine'),
        ('cancelled', 'Annule'),
    ], string='Statut', default='draft')

    channel = fields.Selection([
        ('direct', 'Direct'),
        ('airbnb', 'Airbnb'),
        ('booking', 'Booking.com'),
        ('other', 'Autre'),
    ], string='Canal', default='direct')

    amount_total = fields.Float(string='Montant total (EUR)', compute='_compute_amount', store=True)
    amount_paid = fields.Float(string='Montant paye (EUR)', default=0.0)
    amount_due = fields.Float(string='Reste a payer (EUR)', compute='_compute_amount_due', store=True)

    pin_code = fields.Char(string='Code PIN', readonly=True)
    pin_sent = fields.Boolean(string='PIN envoye', default=False)
    unifi_user_id = fields.Char(string='ID User UniFi', readonly=True)

    beds24_booking_id = fields.Char(string='ID Reservation Beds24', readonly=True)
    beds24_sync_date = fields.Datetime(string='Derniere synchro Beds24', readonly=True)

    invoice_id = fields.Many2one('account.move', string='Facture', readonly=True)
    invoice_state = fields.Selection(related='invoice_id.state', string='Etat facture')

    notes = fields.Text(string='Notes')

    @api.depends('checkin_date', 'checkout_date')
    def _compute_duration(self):
        for rec in self:
            if rec.checkin_date and rec.checkout_date:
                delta = rec.checkout_date - rec.checkin_date
                rec.duration_nights = max(1, delta.days)
            else:
                rec.duration_nights = 0

    @api.depends('duration_nights', 'room_id.price_per_night')
    def _compute_amount(self):
        for rec in self:
            rec.amount_total = rec.duration_nights * (rec.room_id.price_per_night or 0)

    @api.depends('amount_total', 'amount_paid')
    def _compute_amount_due(self):
        for rec in self:
            rec.amount_due = rec.amount_total - rec.amount_paid

    def _generate_pin(self):
        settings = self.env['manda.settings'].get_settings()
        length = settings.pin_length or 4
        return ''.join(random.choices(string.digits, k=length))

    @api.model
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        for vals in vals_list:
            if vals.get('reference', 'Airbnb_Manda-new') == 'Airbnb_Manda-new':
                vals['reference'] = self.env['ir.sequence'].next_by_code('manda.reservation') or 'Airbnb_Manda-001'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if not rec.pin_code:
                rec.pin_code = rec._generate_pin()
            rec.state = 'confirmed'
            settings = self.env['manda.settings'].get_settings()
            if settings.auto_send_pin:
                rec.action_send_pin_email()
            if settings.auto_invoice:
                rec.action_create_invoice()

    def action_checkin(self):
        for rec in self:
            # 1. Revoquer acces menagere si tache en cours pour cette chambre
            housekeeping_tasks = self.env['manda.housekeeping'].search([
                ('room_id', '=', rec.room_id.id),
                ('state', 'in', ['todo', 'in_progress']),
            ])
            for task in housekeeping_tasks:
                if task.housekeeper_unifi_id and rec.lock_id:
                    try:
                        rec.lock_id.delete_unifi_user(task.housekeeper_unifi_id)
                        _logger.info(f"Acces menagere revoques avant check-in: {task.housekeeper_unifi_id}")
                    except Exception as e:
                        _logger.error(f"Erreur revocation menagere: {e}")
                task.write({
                    'housekeeper_unifi_id': False,
                    'housekeeper_pin': False,
                    'state': 'done',
                    'done_date': fields.Datetime.now(),
                })

            # 2. Activer acces client
            rec.state = 'checked_in'
            rec.room_id.state = 'occupied'
            if rec.lock_id:
                user_id = rec.lock_id.create_unifi_user(
                    first_name=rec.partner_id.name.split()[0] if rec.partner_id.name else 'Guest',
                    last_name=' '.join(rec.partner_id.name.split()[1:]) if rec.partner_id.name else '',
                    email=rec.partner_email or '',
                    pin_code=rec.pin_code,
                    start_time=rec.checkin_date,
                    end_time=rec.checkout_date,
                )
                if user_id:
                    rec.unifi_user_id = str(user_id)
                    _logger.info(f"Acces client active: {user_id}")

    def action_checkout(self):
        for rec in self:
            # 1. Changer statut et chambre
            rec.state = 'checked_out'
            rec.room_id.state = 'cleaning'

            # 2. Revoquer acces client UniFi
            if rec.lock_id and rec.unifi_user_id:
                try:
                    rec.lock_id.delete_unifi_user(rec.unifi_user_id)
                    _logger.info(f"Acces client revoques au checkout: {rec.unifi_user_id}")
                except Exception as e:
                    _logger.error(f"Erreur revocation client: {e}")
                rec.unifi_user_id = False

            # 3. Creer tache menage ET demarrer automatiquement
            task = rec._create_and_start_housekeeping_task()
            if task:
                _logger.info(f"Tache menage creee et demarree: {task.name}")

    def _create_and_start_housekeeping_task(self):
        """Creer tache menage et envoyer PIN automatiquement a la menagere"""
        # Chercher la menagere assignee a cette chambre ou par defaut
        assigned_user = self.room_id.default_housekeeper_id or self._get_default_housekeeper()

        task = self.env['manda.housekeeping'].create({
            'name': f"Nettoyage {self.room_id.name} - apres depart",
            'room_id': self.room_id.id,
            'reservation_id': self.id,
            'task_type': 'checkout',
            'scheduled_date': fields.Datetime.now(),
            'assigned_to': assigned_user.id if assigned_user else False,
        })

        # Demarrer automatiquement si menagere assignee
        if assigned_user:
            task.action_start()
            _logger.info(f"PIN menagere envoye automatiquement a {assigned_user.email}")

        return task

    def _get_default_housekeeper(self):
        """Chercher la menagere par defaut (groupe menage)"""
        group = self.env.ref('airbnb_manda.group_manda_housekeeper', raise_if_not_found=False)
        if group and group.users:
            return group.users[0]
        return False

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancelled'
            rec.room_id.state = 'available'
            if rec.lock_id and rec.unifi_user_id:
                try:
                    rec.lock_id.delete_unifi_user(rec.unifi_user_id)
                except Exception as e:
                    _logger.error(f"Erreur revocation annulation: {e}")
                rec.unifi_user_id = False

    @api.model
    def action_auto_checkout(self):
        """Cron: checkout automatique des reservations dont la date est depassee"""
        from datetime import datetime
        now = datetime.now()
        expired = self.search([
            ('state', '=', 'checked_in'),
            ('checkout_date', '<', now),
        ])
        for rec in expired:
            _logger.info(f"Auto checkout: {rec.reference} - {rec.room_id.name}")
            rec.action_checkout()


    def action_send_pin_email(self):
        for rec in self:
            body = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:#2c3e50;padding:30px;text-align:center;">
<h1 style="color:white;margin:0;">Airbnb_Manda</h1>
<p style="color:#bdc3c7;">Bienvenue chez nous !</p>
</div>
<div style="padding:30px;background:#f9f9f9;">
<p style="font-size:18px;">Bonjour <strong>{rec.partner_id.name}</strong>,</p>
<p>Votre reservation est confirmee. Voici vos informations d acces :</p>
<div style="background:white;border:2px solid #2c3e50;border-radius:10px;padding:20px;text-align:center;margin:20px 0;">
<p style="color:#7f8c8d;">Numero de chambre</p>
<p style="font-size:48px;font-weight:bold;color:#2c3e50;">{rec.room_number}</p>
</div>
<div style="background:#3498db;border-radius:10px;padding:25px;text-align:center;margin:20px 0;">
<p style="color:white;">Votre code PIN</p>
<p style="font-size:56px;font-weight:bold;color:white;letter-spacing:15px;">{rec.pin_code}</p>
</div>
<table style="width:100%;border-collapse:collapse;margin:20px 0;">
<tr style="background:#ecf0f1;"><td style="padding:12px;font-weight:bold;">Arrivee</td><td style="padding:12px;">{rec.checkin_date + timedelta(hours=1)}</td></tr>
<tr><td style="padding:12px;font-weight:bold;">Depart</td><td style="padding:12px;">{rec.checkout_date + timedelta(hours=1)}</td></tr>
<tr style="background:#ecf0f1;"><td style="padding:12px;font-weight:bold;">Duree</td><td style="padding:12px;">{rec.duration_nights} nuit(s)</td></tr>
<tr><td style="padding:12px;font-weight:bold;">Montant</td><td style="padding:12px;">{rec.amount_total} EUR</td></tr>
</table>
<p style="color:#7f8c8d;font-size:13px;">Place aux Foires 18, 6900 Marche-en-Famenne</p>
<p style="color:#7f8c8d;font-size:13px;">En cas de souci, contactez-nous : <a href="mailto:raphael@leffetboeuf.be">raphael@leffetboeuf.be</a></p>
</div>
</div>"""
            rec.env['mail.mail'].create({
                'subject': f'Votre code acces Airbnb_Manda - Chambre {rec.room_number} - {rec.reference}',
                'email_to': rec.partner_email,
                'body_html': body,
            }).send()
            rec.pin_sent = True

    def action_create_invoice(self):
        for rec in self:
            if rec.invoice_id:
                continue
            invoice = rec.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': rec.partner_id.id,
                'invoice_origin': rec.reference,
                'invoice_line_ids': [(0, 0, {
                    'name': f'Sejour {rec.room_id.name} - {rec.duration_nights} nuit(s)',
                    'quantity': rec.duration_nights,
                    'price_unit': rec.room_id.price_per_night,
                })],
            })
            rec.invoice_id = invoice.id

    def _create_housekeeping_task(self, task_type):
        task_name = f"Nettoyage {self.room_id.name}" if task_type == 'checkout' else f"Preparation {self.room_id.name}"
        date = self.checkout_date if task_type == 'checkout' else self.checkin_date
        self.env['manda.housekeeping'].create({
            'name': task_name,
            'room_id': self.room_id.id,
            'reservation_id': self.id,
            'task_type': task_type,
            'scheduled_date': date,
        })
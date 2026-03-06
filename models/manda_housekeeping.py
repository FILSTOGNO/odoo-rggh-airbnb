import random
import string
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class MandaHousekeeping(models.Model):
    _name = 'manda.housekeeping'
    _description = 'Tache Menage Airbnb_Manda'
    _rec_name = 'name'
    _order = 'scheduled_date'

    name = fields.Char(string='Tache', required=True)
    room_id = fields.Many2one('manda.room', string='Chambre', required=True)
    lock_id = fields.Many2one(related='room_id.lock_id', string='Serrure', store=True)
    reservation_id = fields.Many2one('manda.reservation', string='Reservation')
    task_type = fields.Selection([
        ('checkout', 'Nettoyage apres depart'),
        ('checkin_prep', 'Preparation avant arrivee'),
        ('periodic', 'Nettoyage periodique'),
    ], string='Type', default='checkout')
    state = fields.Selection([
        ('todo', 'A faire'),
        ('in_progress', 'En cours'),
        ('done', 'Termine'),
    ], string='Etat', default='todo')
    scheduled_date = fields.Datetime(string='Date prevue')
    done_date = fields.Datetime(string='Date realisation')
    assigned_to = fields.Many2one('res.users', string='Assigne a')
    assigned_email = fields.Char(related='assigned_to.email', string='Email menagere', readonly=True)
    notes = fields.Text(string='Notes')
    color = fields.Integer(compute='_compute_color')

    housekeeper_pin = fields.Char(string='PIN Menagere', readonly=True)
    housekeeper_unifi_id = fields.Char(string='ID UniFi Menagere', readonly=True)
    pin_sent = fields.Boolean(string='PIN envoye', default=False)

    @api.depends('state', 'task_type')
    def _compute_color(self):
        colors = {'todo': 1, 'in_progress': 3, 'done': 10}
        for rec in self:
            rec.color = colors.get(rec.state, 0)

    def _generate_pin(self):
        return ''.join(random.choices(string.digits, k=4))

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'
            if not rec.housekeeper_pin:
                rec.housekeeper_pin = rec._generate_pin()
            if rec.lock_id and rec.assigned_to:
                from datetime import datetime, timedelta
                start_time = datetime.now()
                end_time = start_time + timedelta(hours=4)
                user = rec.assigned_to
                first_name = user.name.split()[0] if user.name else 'Menagere'
                last_name = ' '.join(user.name.split()[1:]) if user.name else ''
                email = user.email or f'menagere_{rec.id}@mandabar.be'
                try:
                    unifi_id = rec.lock_id.create_unifi_user(
                        first_name=first_name,
                        last_name=last_name,
                        email=email,
                        pin_code=rec.housekeeper_pin,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    if unifi_id:
                        rec.housekeeper_unifi_id = str(unifi_id)
                except Exception as e:
                    _logger.error(f"Erreur acces UniFi menagere: {e}")
            if rec.assigned_email and not rec.pin_sent:
                rec._send_pin_to_housekeeper()

    def _send_pin_to_housekeeper(self):
        for rec in self:
            if not rec.assigned_email:
                return
            body = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:#2c3e50;padding:30px;text-align:center;">
<h1 style="color:white;margin:0;">MandaBar</h1>
<p style="color:#bdc3c7;">Tache de menage assignee</p>
</div>
<div style="padding:30px;background:#f9f9f9;">
<p>Bonjour <strong>{rec.assigned_to.name}</strong>,</p>
<p>Une tache de nettoyage vous a ete assignee.</p>
<div style="background:white;border:2px solid #2c3e50;border-radius:10px;padding:20px;text-align:center;margin:20px 0;">
<p style="color:#7f8c8d;margin:0;">Chambre</p>
<p style="font-size:36px;font-weight:bold;color:#2c3e50;margin:10px 0;">{rec.room_id.name}</p>
</div>
<div style="background:#27ae60;border-radius:10px;padding:25px;text-align:center;margin:20px 0;">
<p style="color:white;margin:0;">Votre code PIN</p>
<p style="font-size:56px;font-weight:bold;color:white;letter-spacing:15px;margin:10px 0;">{rec.housekeeper_pin}</p>
<p style="color:#a9dfbf;font-size:12px;margin:0;">Valide 4 heures</p>
</div>
</div>
</div>"""
            self.env['mail.mail'].create({
                'subject': f'Menage - {rec.room_id.name} - PIN: {rec.housekeeper_pin}',
                'email_to': rec.assigned_email,
                'body_html': body,
            }).send()
            rec.pin_sent = True

    def action_done(self):
        for rec in self:
            rec.state = 'done'
            rec.done_date = fields.Datetime.now()
            if rec.lock_id and rec.housekeeper_unifi_id:
                try:
                    rec.lock_id.delete_unifi_user(rec.housekeeper_unifi_id)
                    rec.housekeeper_unifi_id = False
                    rec.housekeeper_pin = False
                except Exception as e:
                    _logger.error(f"Erreur revocation acces menagere: {e}")
            if rec.room_id:
                rec.room_id.state = 'available'

    def action_resend_pin(self):
        for rec in self:
            if not rec.housekeeper_pin:
                rec.housekeeper_pin = rec._generate_pin()
            rec.pin_sent = False
            rec._send_pin_to_housekeeper()
from odoo import models, fields, api

class MandaRoom(models.Model):
    _name = 'manda.room'
    _description = 'Chambre Airbnb_Manda'
    _rec_name = 'name'
    _order = 'number'

    name = fields.Char(string='Nom de la chambre', required=True)
    number = fields.Integer(string='Numéro', required=True)
    description = fields.Text(string='Description')
    capacity = fields.Integer(string='Capacité (personnes)', default=2)
    price_per_night = fields.Float(string='Prix par nuit (€)')
    state = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Occupée'),
        ('cleaning', 'En nettoyage'),
        ('maintenance', 'Maintenance'),
    ], string='État', default='available')
    lock_id = fields.Many2one('manda.lock', string='Serrure UniFi')
    beds24_room_id = fields.Char(string='ID Chambre Beds24')
    default_housekeeper_id = fields.Many2one('res.users', string='Menagere par defaut')
    reservation_ids = fields.One2many('manda.reservation', 'room_id', string='Réservations')
    reservation_count = fields.Integer(compute='_compute_counts')
    color = fields.Integer(string='Couleur', default=0)

    @api.depends('reservation_ids')
    def _compute_counts(self):
        for rec in self:
            rec.reservation_count = len(rec.reservation_ids)

    def action_view_reservations(self):
        return {
            'type': 'ir.actions.act_window',
            'name': f'Réservations - {self.name}',
            'res_model': 'manda.reservation',
            'view_mode': 'list,form,calendar',
            'domain': [('room_id', '=', self.id)],
            'context': {'default_room_id': self.id},
        }
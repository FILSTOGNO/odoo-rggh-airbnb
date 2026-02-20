from odoo import models, fields

class MandaRoom(models.Model):
    _name = 'manda.room'
    _description = 'Chambre Airbnb MandaBar'
    _rec_name = 'name'

    name = fields.Char(string='Nom de la chambre', required=True)
    number = fields.Integer(string='Numéro de chambre', required=True)
    description = fields.Text(string='Description')
    price_per_night = fields.Float(string='Prix par nuit (€)')
    active = fields.Boolean(string='Active', default=True)
    lock_id = fields.Many2one('manda.lock', string='Serrure assignée')
    reservation_ids = fields.One2many('manda.reservation', 'room_id', string='Réservations')
    reservation_count = fields.Integer(string='Nombre de réservations', compute='_compute_reservation_count')
    state = fields.Selection([
        ('available', 'Disponible'),
        ('occupied', 'Occupée'),
        ('maintenance', 'Maintenance'),
    ], string='État', default='available')

    def _compute_reservation_count(self):
        for room in self:
            room.reservation_count = len(room.reservation_ids)

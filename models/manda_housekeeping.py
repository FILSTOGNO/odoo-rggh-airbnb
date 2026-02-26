from odoo import models, fields, api

class MandaHousekeeping(models.Model):
    _name = 'manda.housekeeping'
    _description = 'Tâche Ménage MandaBar'
    _rec_name = 'name'
    _order = 'scheduled_date'

    name = fields.Char(string='Tâche', required=True)
    room_id = fields.Many2one('manda.room', string='Chambre', required=True)
    reservation_id = fields.Many2one('manda.reservation', string='Réservation')
    task_type = fields.Selection([
        ('checkout', 'Nettoyage après départ'),
        ('checkin_prep', 'Préparation avant arrivée'),
        ('periodic', 'Nettoyage périodique'),
    ], string='Type', default='checkout')
    state = fields.Selection([
        ('todo', 'À faire'),
        ('in_progress', 'En cours'),
        ('done', 'Terminé'),
    ], string='État', default='todo')
    scheduled_date = fields.Datetime(string='Date prévue')
    done_date = fields.Datetime(string='Date réalisation')
    assigned_to = fields.Many2one('res.users', string='Assigné à')
    notes = fields.Text(string='Notes')
    color = fields.Integer(compute='_compute_color')

    @api.depends('state', 'task_type')
    def _compute_color(self):
        colors = {'todo': 1, 'in_progress': 3, 'done': 10}
        for rec in self:
            rec.color = colors.get(rec.state, 0)

    def action_start(self):
        self.state = 'in_progress'

    def action_done(self):
        self.state = 'done'
        self.done_date = fields.Datetime.now()
        if self.room_id:
            self.room_id.state = 'available'

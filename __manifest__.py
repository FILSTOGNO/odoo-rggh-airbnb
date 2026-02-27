{
    'name': 'Airbnb Manda - Gestion des Accès',
    'version': '19.0.2.0.0',
    'category': 'Property Management',
    'summary': 'Gestion réservations Airbnb avec serrures UniFi Access',
    'description': '''
        Module de gestion des réservations MandaBar:
        - Synchronisation Beds24 (Airbnb/Booking/Direct)
        - Gestion des accès UniFi (codes PIN)
        - Planning par chambre
        - Facturation automatique
        - Tâches ménage automatiques
    ''',
    'author': 'Angelbert',
    'depends': ['base', 'mail', 'account', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_pin.xml',
        'views/manda_settings_views.xml',
        'views/manda_room_views.xml',
        'views/manda_lock_views.xml',
        'views/manda_reservation_views.xml',
        'views/manda_housekeeping_views.xml',
        'views/manda_beds24_views.xml',
        'views/manda_menu.xml',
        'data/manda_cron.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': True,
}

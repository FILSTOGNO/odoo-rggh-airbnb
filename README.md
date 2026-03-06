# 🔐 airbnb_manda — Module Odoo Gestion Accès UniFi

> Module Odoo 19 développé pendant mon stage de fin d'études chez MandaBar (Liège, Belgique).  
> Gestion automatique des accès IoT via l'API UniFi Access Hub, intégré avec le système de réservation hôtelière.

---

## 🎯 Fonctionnalités

- **PIN automatique** — génération d'un code PIN unique à chaque confirmation de réservation
- **Accès client** — création automatique de l'accès UniFi au check-in, révocation au check-out
- **Workflow ménage** — tâche de ménage créée automatiquement après chaque départ avec PIN temporaire pour la ménagère
- **Emails HTML** — notifications automatiques client + ménagère avec code PIN et informations de séjour
- **Cron auto-checkout** — vérification toutes les 15 minutes des réservations expirées
- **Intégration native** — utilise les modèles réels du module `hotel_management_system` (hotel.booking, hotel.booking.line, product.product)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Odoo 19 (VPS OVH)                │
│                                                     │
│   hotel.booking ──► hotel.booking.line              │
│        │                   │                        │
│        │            product.product (chambre)       │
│        │                   │                        │
│        └──► manda.housekeeping ◄──► manda.lock      │
│                                         │           │
└─────────────────────────────────────────┼───────────┘
                                          │ API HTTPS
                                          ▼
┌─────────────────────────────────────────────────────┐
│              Raspberry Pi (Proxy)                   │
│              Tunnel SSH → VPS                       │
└─────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────┐
│           UniFi Access Hub                          │
│     Serrures connectées (codes PIN)                 │
└─────────────────────────────────────────────────────┘
```

---

## 🔄 Flux automatique complet

```
Réservation confirmée
        │
        ▼
🔑 Génération PIN client → 📧 Email client (HTML)
        │
        ▼
Check-in
        │
        ▼
✅ Création accès UniFi client (PIN + dates validité)
🚫 Révocation accès ménagères actives
        │
        ▼
Check-out
        │
        ▼
🚫 Révocation accès client UniFi
🧹 Création tâche ménage automatique
🔑 Génération PIN ménagère (4h) → 📧 Email ménagère
        │
        ▼
Ménage terminé
        │
        ▼
🚫 Révocation accès ménagère
✅ Chambre disponible
```

---

## 🛠️ Stack technique

| Technologie | Usage |
|---|---|
| **Python 3** | Développement du module Odoo |
| **Odoo 19** | Framework ERP / base de données métier |
| **PostgreSQL** | Base de données |
| **API UniFi Access** | Gestion des serrures connectées (HTTPS/REST) |
| **Raspberry Pi** | Proxy local entre VPS et hub UniFi |
| **Tunnel SSH** | Communication sécurisée VPS ↔ Raspberry Pi |
| **Ubuntu (VPS OVH)** | Serveur de production |

---

## 📁 Structure du module

```
airbnb_manda/
├── __manifest__.py              # Déclaration du module Odoo
├── __init__.py
├── models/
|   ├── __init__.py
│   ├── manda_lock.py            # Serrures UniFi + API calls
│   ├── manda_settings.py        # Configuration singleton
│   ├── manda_housekeeping.py    # Tâches ménage + PIN temporaire
│   ├── manda_beds24.py .py    # Extension hotel.booking + product.product
|   ├── manda_lock.py 
|   ├── manda_reservation.py
|   ├── manda_room.py 
|   ├── manda_settings.py 
|   ├── unifi_config.py
|   └──__pycache__ 
├── views/
│   ├── manda_beds24_views.xml    # Extension vues beds24
│   ├── manda_housekeeping_views.xml   # Kanban / List / Form ménage
│   ├── manda_lock_views.xml           # Gestion serrures
│   ├── manda_settings_views.xml       # Configuration
│   ├── manda_menu.xml                 # Menus MandaBar
│   ├── manda_reservation_views.xml
│   └── manda_room_views.xml
├── data/
│   ├── mail_template_pin.xml 
│   └── manda_cron.xml           # Cron auto-checkout 15min
├── security/
│   └── ir.model.access.csv      # Droits d'accès
└── controllers/
│   ├── __init__.py
    └── main.py                  # Webhook endpoint
     
```

---

## ⚙️ Installation

```bash
# 1. Copier le module dans le dossier addons Odoo
cp -r airbnb_manda/ /path/to/odoo/addons/

# 2. Mettre à jour la liste des modules
odoo-bin -c odoo.conf -u airbnb_manda --stop-after-init

# 3. Activer le module dans Odoo
# Apps → Rechercher "airbnb_manda" → Installer
```

### Configuration post-installation

1. **airbnb_manda → Configuration → Parametre**
   - Renseigner l'IP du hub UniFi
   - Ajouter le token API UniFi
   - Configurer l'Access Policy ID

2. **airbnb_manda → Configuration → Serrure UniFi**
   - ANom de la porte
   - Renseigner ID Porte UniFi

---

## 🔑 API UniFi Access

Le module communique avec l'API REST du hub UniFi Access :

```
POST /api/v1/developer/users     → Créer un utilisateur + PIN
PUT  /api/v1/developer/users/:id → Assigner politique d'accès
DEL  /api/v1/developer/users/:id → Révoquer l'accès
```

La communication passe par un **proxy Raspberry Pi** via tunnel SSH pour contourner les restrictions réseau locales.

---

## 👨‍💻 Auteur

**Angelbert FANKEP**  
Bachelor Informatique Industrielle — Institut de technologie de Liège (2026)  
Développeur systèmes industriels & IoT

- 🌐 [fankepa.com](https://fankepa.com)
- 📧 fankepa@gmail.com
- 💼 [GitHub](https://github.com/FILSTOGNO)

---

## 📄 Licence

Projet développé dans le cadre d'un stage de fin d'études.  
© 2026 Angelbert FANKEP — Tous droits réservés.
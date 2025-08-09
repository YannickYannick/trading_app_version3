# 🕺 Bachata App - Application de Gestion de Cours et Événements de Danse

Une application Django moderne et complète pour la gestion de cours, événements et communauté de danse bachata.

## ✨ Fonctionnalités Principales

### 🎓 Gestion des Cours
- **Création et gestion de cours** avec niveaux (Débutant, Intermédiaire, Avancé)
- **Système d'inscription** avec gestion des paiements
- **Horaires et lieux** flexibles
- **Capacité et places disponibles** en temps réel
- **Avis et évaluations** des cours

### 📅 Gestion des Événements
- **Soirées dansantes, festivals, ateliers**
- **Inscriptions en ligne** avec options spéciales
- **Gestion des organisateurs et instructeurs**
- **Système de réservation** avec confirmation

### 👥 Gestion des Instructeurs
- **Profils détaillés** avec photos et biographies
- **Spécialisations** par style de danse
- **Expérience et certifications**
- **Cours associés** et disponibilités

### 🏢 Gestion des Lieux
- **Salles de danse** avec équipements
- **Capacités et disponibilités**
- **Informations pratiques** (parking, vestiaires, etc.)

### 👫 Système de Partenaires
- **Recherche de partenaires** de danse
- **Profils détaillés** avec niveaux et disponibilités
- **Matching intelligent** selon les préférences

### 🔔 Notifications
- **Rappels de cours** et événements
- **Confirmations d'inscription**
- **Messages système** personnalisés

### ⭐ Système d'Avis
- **Évaluations** des cours et événements
- **Commentaires** détaillés
- **Notes moyennes** calculées automatiquement

## 🛠️ Technologies Utilisées

- **Backend**: Django 4.2+
- **Frontend**: Bootstrap 5, Font Awesome
- **Base de données**: PostgreSQL/SQLite
- **Authentification**: Django Auth
- **Interface d'administration**: Django Admin

## 📋 Prérequis

- Python 3.8+
- Django 4.2+
- pip

## 🚀 Installation

1. **Cloner le repository**
```bash
git clone <repository-url>
cd bachata_app
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer la base de données**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

6. **Lancer le serveur**
```bash
python manage.py runserver
```

## 📁 Structure du Projet

```
bachata_app/
├── bachata_app/
│   ├── __init__.py
│   ├── admin.py          # Interface d'administration
│   ├── apps.py           # Configuration de l'app
│   ├── models.py         # Modèles de données
│   ├── views.py          # Vues et logique métier
│   ├── urls.py           # Configuration des URLs
│   └── templates/        # Templates HTML
│       └── bachata_app/
│           ├── base.html
│           ├── home.html
│           └── ...
├── static/               # Fichiers statiques
├── media/                # Fichiers uploadés
├── manage.py
└── requirements.txt
```

## 🗄️ Modèles de Données

### DanceStyle
- Styles de danse disponibles (Bachata, Salsa, etc.)

### Instructor
- Profils des instructeurs avec spécialisations

### Venue
- Lieux de cours et événements

### Course
- Cours avec horaires, tarifs et capacité

### Event
- Événements avec types et organisateurs

### CourseRegistration / EventRegistration
- Inscriptions aux cours et événements

### DancePartner
- Système de recherche de partenaires

### Review
- Avis et évaluations

### Notification
- Système de notifications

## 🎨 Interface Utilisateur

### Design Moderne
- **Interface responsive** adaptée à tous les écrans
- **Animations CSS** pour une expérience fluide
- **Palette de couleurs** cohérente et attrayante
- **Icônes Font Awesome** pour une navigation intuitive

### Navigation
- **Menu principal** avec accès rapide aux fonctionnalités
- **Recherche globale** intégrée
- **Menu utilisateur** avec profil et notifications
- **Breadcrumbs** pour la navigation

## 🔧 Configuration

### Variables d'Environnement
Créer un fichier `.env` :
```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
MEDIA_URL=/media/
STATIC_URL=/static/
```

### Paramètres Django
Dans `settings.py` :
```python
INSTALLED_APPS = [
    # ...
    'bachata_app',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## 📊 Fonctionnalités Avancées

### Système de Recherche
- **Recherche globale** dans tous les contenus
- **Filtres avancés** par niveau, style, lieu
- **Tri et pagination** des résultats

### Gestion des Inscriptions
- **Validation automatique** des places disponibles
- **Confirmation par email** (optionnel)
- **Gestion des annulations** et remboursements

### Statistiques
- **Tableau de bord** avec métriques
- **Rapports d'inscription** par cours/événement
- **Analytics** des performances

## 🔒 Sécurité

- **Authentification** Django standard
- **Permissions** granulaires par utilisateur
- **Protection CSRF** activée
- **Validation** des données côté serveur

## 🧪 Tests

```bash
# Lancer les tests
python manage.py test bachata_app

# Couverture de code
coverage run --source='.' manage.py test
coverage report
```

## 📈 Déploiement

### Production
1. **Configurer les variables d'environnement**
2. **Utiliser une base de données PostgreSQL**
3. **Configurer les fichiers statiques**
4. **Déployer avec Gunicorn + Nginx**

### Docker (optionnel)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "bachata_app.wsgi:application"]
```

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit les changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

- **Email**: contact@bachata-app.com
- **Documentation**: [Wiki du projet]
- **Issues**: [GitHub Issues]

## 🎯 Roadmap

### Version 1.1
- [ ] Intégration de paiements en ligne
- [ ] Système de messagerie interne
- [ ] Application mobile (React Native)

### Version 1.2
- [ ] Intégration de vidéos de cours
- [ ] Système de badges et récompenses
- [ ] API REST complète

### Version 2.0
- [ ] Intelligence artificielle pour le matching
- [ ] Réalité augmentée pour les cours
- [ ] Intégration avec les réseaux sociaux

---

**Développé avec ❤️ pour la communauté de danse bachata** 
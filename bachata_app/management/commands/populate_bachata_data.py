from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bachata_app.models import (
    DanceStyle, Instructor, Venue, Course, Event, 
    CourseRegistration, EventRegistration, DancePartner, 
    Review, Notification
)
from datetime import datetime, timedelta
from decimal import Decimal


class Command(BaseCommand):
    help = 'Peuple l\'application bachata avec des données de test'

    def handle(self, *args, **options):
        self.stdout.write('🕺 Création des données de test pour Bachata App...')
        
        # Créer les styles de danse
        self.create_dance_styles()
        
        # Créer les lieux
        self.create_venues()
        
        # Créer les utilisateurs et instructeurs
        self.create_instructors()
        
        # Créer les cours
        self.create_courses()
        
        # Créer les événements
        self.create_events()
        
        # Créer des profils de partenaires
        self.create_dance_partners()
        
        # Créer des avis
        self.create_reviews()
        
        self.stdout.write(
            self.style.SUCCESS('✅ Données de test créées avec succès !')
        )

    def create_dance_styles(self):
        """Créer les styles de danse"""
        styles_data = [
            {'name': 'Bachata', 'description': 'Danse latine sensuelle originaire de République dominicaine', 'icon': 'fas fa-heart'},
            {'name': 'Salsa', 'description': 'Danse latine énergique et rythmée', 'icon': 'fas fa-fire'},
            {'name': 'Merengue', 'description': 'Danse dominicaine rapide et festive', 'icon': 'fas fa-music'},
            {'name': 'Kizomba', 'description': 'Danse angolaise sensuelle et fluide', 'icon': 'fas fa-star'},
            {'name': 'Zouk', 'description': 'Danse brésilienne moderne et créative', 'icon': 'fas fa-magic'},
        ]
        
        for style_data in styles_data:
            style, created = DanceStyle.objects.get_or_create(
                name=style_data['name'],
                defaults=style_data
            )
            if created:
                self.stdout.write(f'  ✅ Style créé: {style.name}')

    def create_venues(self):
        """Créer les lieux de cours"""
        venues_data = [
            {
                'name': 'Studio Danse Latino',
                'address': '123 Rue de la Danse\n75001 Paris',
                'city': 'Paris',
                'postal_code': '75001',
                'phone': '01 23 45 67 89',
                'email': 'contact@studiolatino.fr',
                'website': 'https://studiolatino.fr',
                'capacity': 50,
                'description': 'Studio moderne avec parquet professionnel et système son de qualité',
                'amenities': {
                    'parking': 'Gratuit',
                    'vestiaires': 'Oui',
                    'douches': 'Oui',
                    'climatisation': 'Oui'
                }
            },
            {
                'name': 'Espace Danse Passion',
                'address': '456 Avenue des Arts\n69001 Lyon',
                'city': 'Lyon',
                'postal_code': '69001',
                'phone': '04 78 12 34 56',
                'email': 'info@dansepassion.fr',
                'website': 'https://dansepassion.fr',
                'capacity': 80,
                'description': 'Grande salle avec miroirs et éclairage professionnel',
                'amenities': {
                    'parking': 'Payant',
                    'vestiaires': 'Oui',
                    'douches': 'Non',
                    'climatisation': 'Oui'
                }
            },
            {
                'name': 'Club Danse Tropical',
                'address': '789 Boulevard du Soleil\n13001 Marseille',
                'city': 'Marseille',
                'postal_code': '13001',
                'phone': '04 91 98 76 54',
                'email': 'contact@tropical-danse.fr',
                'website': 'https://tropical-danse.fr',
                'capacity': 60,
                'description': 'Club avec ambiance tropicale et bar',
                'amenities': {
                    'parking': 'Gratuit',
                    'vestiaires': 'Oui',
                    'douches': 'Oui',
                    'climatisation': 'Oui',
                    'bar': 'Oui'
                }
            }
        ]
        
        for venue_data in venues_data:
            venue, created = Venue.objects.get_or_create(
                name=venue_data['name'],
                defaults=venue_data
            )
            if created:
                self.stdout.write(f'  ✅ Lieu créé: {venue.name}')

    def create_instructors(self):
        """Créer les instructeurs"""
        instructors_data = [
            {
                'username': 'maria_garcia',
                'first_name': 'Maria',
                'last_name': 'Garcia',
                'email': 'maria@bachata-app.com',
                'bio': 'Instructrice passionnée de bachata avec 10 ans d\'expérience. Originaire de République dominicaine, j\'enseigne la bachata authentique avec passion et patience.',
                'experience_years': 10,
                'phone': '06 12 34 56 78',
                'website': 'https://maria-garcia-danse.fr',
                'specializations': ['Bachata', 'Salsa']
            },
            {
                'username': 'carlos_rodriguez',
                'first_name': 'Carlos',
                'last_name': 'Rodriguez',
                'email': 'carlos@bachata-app.com',
                'bio': 'Instructeur professionnel spécialisé en salsa et bachata. J\'ai dansé dans de nombreux festivals internationaux et j\'aime partager ma passion.',
                'experience_years': 8,
                'phone': '06 98 76 54 32',
                'website': 'https://carlos-rodriguez-danse.fr',
                'specializations': ['Salsa', 'Bachata', 'Merengue']
            },
            {
                'username': 'sofia_martinez',
                'first_name': 'Sofia',
                'last_name': 'Martinez',
                'email': 'sofia@bachata-app.com',
                'bio': 'Danseuse et instructrice de kizomba et zouk. J\'adore enseigner ces danses modernes et créatives qui permettent une grande liberté d\'expression.',
                'experience_years': 6,
                'phone': '06 45 67 89 12',
                'website': 'https://sofia-martinez-danse.fr',
                'specializations': ['Kizomba', 'Zouk']
            }
        ]
        
        for instructor_data in instructors_data:
            # Créer l'utilisateur
            user, created = User.objects.get_or_create(
                username=instructor_data['username'],
                defaults={
                    'first_name': instructor_data['first_name'],
                    'last_name': instructor_data['last_name'],
                    'email': instructor_data['email'],
                    'is_staff': True
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
            
            # Créer le profil instructeur
            instructor, created = Instructor.objects.get_or_create(
                user=user,
                defaults={
                    'bio': instructor_data['bio'],
                    'experience_years': instructor_data['experience_years'],
                    'phone': instructor_data['phone'],
                    'website': instructor_data['website']
                }
            )
            
            # Ajouter les spécialisations
            for style_name in instructor_data['specializations']:
                try:
                    style = DanceStyle.objects.get(name=style_name)
                    instructor.specializations.add(style)
                except DanceStyle.DoesNotExist:
                    pass
            
            if created:
                self.stdout.write(f'  ✅ Instructeur créé: {instructor.user.get_full_name()}')

    def create_courses(self):
        """Créer les cours"""
        venues = list(Venue.objects.all())
        instructors = list(Instructor.objects.all())
        bachata_style = DanceStyle.objects.get(name='Bachata')
        salsa_style = DanceStyle.objects.get(name='Salsa')
        
        courses_data = [
            {
                'title': 'Bachata Débutant',
                'description': 'Découvrez les bases de la bachata dans une ambiance conviviale. Apprenez les pas de base, la posture et la connexion avec votre partenaire.',
                'instructor': instructors[0] if instructors else None,
                'venue': venues[0] if venues else None,
                'dance_style': bachata_style,
                'level': 'beginner',
                'start_date': datetime.now().date() + timedelta(days=7),
                'end_date': datetime.now().date() + timedelta(days=70),
                'day_of_week': 'Lundi',
                'start_time': '19:00',
                'end_time': '20:30',
                'price_per_session': Decimal('15.00'),
                'total_sessions': 10,
                'max_participants': 20
            },
            {
                'title': 'Salsa Intermédiaire',
                'description': 'Perfectionnez votre salsa avec des figures plus complexes et des combinaisons avancées.',
                'instructor': instructors[1] if len(instructors) > 1 else instructors[0] if instructors else None,
                'venue': venues[1] if len(venues) > 1 else venues[0] if venues else None,
                'dance_style': salsa_style,
                'level': 'intermediate',
                'start_date': datetime.now().date() + timedelta(days=5),
                'end_date': datetime.now().date() + timedelta(days=68),
                'day_of_week': 'Mercredi',
                'start_time': '20:00',
                'end_time': '21:30',
                'price_per_session': Decimal('18.00'),
                'total_sessions': 12,
                'max_participants': 16
            },
            {
                'title': 'Bachata Sensuelle Avancé',
                'description': 'Maîtrisez les figures sensuelles et les isolations de la bachata moderne.',
                'instructor': instructors[0] if instructors else None,
                'venue': venues[2] if len(venues) > 2 else venues[0] if venues else None,
                'dance_style': bachata_style,
                'level': 'advanced',
                'start_date': datetime.now().date() + timedelta(days=10),
                'end_date': datetime.now().date() + timedelta(days=73),
                'day_of_week': 'Vendredi',
                'start_time': '20:30',
                'end_time': '22:00',
                'price_per_session': Decimal('20.00'),
                'total_sessions': 8,
                'max_participants': 12
            }
        ]
        
        for course_data in courses_data:
            if course_data['instructor'] and course_data['venue']:
                course, created = Course.objects.get_or_create(
                    title=course_data['title'],
                    defaults=course_data
                )
                if created:
                    self.stdout.write(f'  ✅ Cours créé: {course.title}')

    def create_events(self):
        """Créer les événements"""
        venues = list(Venue.objects.all())
        instructors = list(Instructor.objects.all())
        bachata_style = DanceStyle.objects.get(name='Bachata')
        salsa_style = DanceStyle.objects.get(name='Salsa')
        
        events_data = [
            {
                'title': 'Soirée Bachata Passion',
                'description': 'Une soirée exceptionnelle dédiée à la bachata avec DJ international et démonstrations.',
                'event_type': 'party',
                'venue': venues[0] if venues else None,
                'start_datetime': datetime.now() + timedelta(days=14, hours=20),
                'end_datetime': datetime.now() + timedelta(days=14, hours=23),
                'price': Decimal('25.00'),
                'max_participants': 100,
                'dance_styles': [bachata_style],
                'instructors': [instructors[0]] if instructors else []
            },
            {
                'title': 'Festival Latino 2024',
                'description': 'Le plus grand festival de danses latines de l\'année avec des artistes internationaux.',
                'event_type': 'festival',
                'venue': venues[1] if len(venues) > 1 else venues[0] if venues else None,
                'start_datetime': datetime.now() + timedelta(days=30, hours=14),
                'end_datetime': datetime.now() + timedelta(days=32, hours=23),
                'price': Decimal('150.00'),
                'max_participants': 200,
                'dance_styles': [bachata_style, salsa_style],
                'instructors': instructors
            },
            {
                'title': 'Atelier Kizomba Sensuelle',
                'description': 'Atelier intensif de kizomba avec focus sur la connexion et la musicalité.',
                'event_type': 'workshop',
                'venue': venues[2] if len(venues) > 2 else venues[0] if venues else None,
                'start_datetime': datetime.now() + timedelta(days=7, hours=14),
                'end_datetime': datetime.now() + timedelta(days=7, hours=18),
                'price': Decimal('45.00'),
                'max_participants': 30,
                'dance_styles': [DanceStyle.objects.get(name='Kizomba')],
                'instructors': [instructors[2]] if len(instructors) > 2 else []
            }
        ]
        
        for event_data in events_data:
            if event_data['venue']:
                dance_styles = event_data.pop('dance_styles')
                instructors_list = event_data.pop('instructors')
                
                event, created = Event.objects.get_or_create(
                    title=event_data['title'],
                    defaults=event_data
                )
                
                if created:
                    event.dance_styles.set(dance_styles)
                    event.instructors.set(instructors_list)
                    self.stdout.write(f'  ✅ Événement créé: {event.title}')

    def create_dance_partners(self):
        """Créer des profils de partenaires de danse"""
        users_data = [
            {
                'username': 'danseur_passionne',
                'first_name': 'Thomas',
                'last_name': 'Dubois',
                'email': 'thomas@example.com',
                'level': 'intermediate',
                'looking_for': 'follower',
                'bio': 'Danseur passionné de bachata et salsa, je cherche une partenaire pour pratiquer et progresser ensemble.',
                'dance_styles': ['Bachata', 'Salsa']
            },
            {
                'username': 'danseuse_energie',
                'first_name': 'Julie',
                'last_name': 'Martin',
                'email': 'julie@example.com',
                'level': 'beginner',
                'looking_for': 'leader',
                'bio': 'Débutante enthousiaste, j\'adore la bachata et je cherche un partenaire patient pour apprendre.',
                'dance_styles': ['Bachata']
            },
            {
                'username': 'danseur_experimente',
                'first_name': 'Pierre',
                'last_name': 'Leroy',
                'email': 'pierre@example.com',
                'level': 'advanced',
                'looking_for': 'both',
                'bio': 'Danseur expérimenté en salsa et bachata, je peux guider ou suivre selon les besoins.',
                'dance_styles': ['Salsa', 'Bachata', 'Kizomba']
            }
        ]
        
        for user_data in users_data:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'email': user_data['email']
                }
            )
            
            if created:
                user.set_password('password123')
                user.save()
            
            dance_styles = user_data.pop('dance_styles')
            
            partner, created = DancePartner.objects.get_or_create(
                user=user,
                defaults={
                    'level': user_data['level'],
                    'looking_for': user_data['looking_for'],
                    'bio': user_data['bio']
                }
            )
            
            if created:
                for style_name in dance_styles:
                    try:
                        style = DanceStyle.objects.get(name=style_name)
                        partner.dance_styles.add(style)
                    except DanceStyle.DoesNotExist:
                        pass
                
                self.stdout.write(f'  ✅ Partenaire créé: {partner.user.get_full_name()}')

    def create_reviews(self):
        """Créer des avis sur les cours et événements"""
        courses = list(Course.objects.all())
        events = list(Event.objects.all())
        users = list(User.objects.filter(is_staff=False)[:3])
        
        if not users:
            return
        
        # Avis sur les cours
        for course in courses:
            for i, user in enumerate(users):
                if i < 2:  # Max 2 avis par cours
                    review, created = Review.objects.get_or_create(
                        user=user,
                        course=course,
                        defaults={
                            'rating': 4 + (i % 2),  # 4 ou 5 étoiles
                            'comment': f'Excellent cours ! L\'instructeur est très pédagogue et l\'ambiance est super.'
                        }
                    )
                    if created:
                        self.stdout.write(f'  ✅ Avis créé pour {course.title}')
        
        # Avis sur les événements
        for event in events:
            for i, user in enumerate(users):
                if i < 2:  # Max 2 avis par événement
                    review, created = Review.objects.get_or_create(
                        user=user,
                        event=event,
                        defaults={
                            'rating': 5,
                            'comment': f'Événement fantastique ! Ambiance incroyable et organisation parfaite.'
                        }
                    )
                    if created:
                        self.stdout.write(f'  ✅ Avis créé pour {event.title}') 
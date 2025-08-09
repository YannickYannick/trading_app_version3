from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal


class DanceStyle(models.Model):
    """Styles de danse disponibles"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-music')
    
    def __str__(self):
        return self.name


class Instructor(models.Model):
    """Professeurs de danse"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='instructor_profile')
    bio = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    specializations = models.ManyToManyField(DanceStyle, blank=True)
    photo = models.ImageField(upload_to='instructors/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {', '.join([s.name for s in self.specializations.all()])}"


class Venue(models.Model):
    """Lieux de cours et événements"""
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    capacity = models.PositiveIntegerField(default=50)
    description = models.TextField(blank=True)
    amenities = models.JSONField(default=dict, blank=True)  # Parking, vestiaires, etc.
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.name} - {self.city}"


class Course(models.Model):
    """Cours de bachata"""
    LEVEL_CHOICES = [
        ('beginner', 'Débutant'),
        ('intermediate', 'Intermédiaire'),
        ('advanced', 'Avancé'),
        ('all_levels', 'Tous niveaux'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name='courses')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='courses')
    dance_style = models.ForeignKey(DanceStyle, on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    
    # Horaires
    start_date = models.DateField()
    end_date = models.DateField()
    day_of_week = models.CharField(max_length=20)  # Lundi, Mardi, etc.
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Tarifs et capacité
    price_per_session = models.DecimalField(max_digits=8, decimal_places=2)
    total_sessions = models.PositiveIntegerField(default=10)
    max_participants = models.PositiveIntegerField(default=20)
    
    # Statut
    is_active = models.BooleanField(default=True)
    is_full = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.instructor.user.get_full_name()} ({self.level})"
    
    @property
    def total_price(self):
        return self.price_per_session * self.total_sessions
    
    @property
    def current_participants_count(self):
        return self.participants.count()
    
    @property
    def available_spots(self):
        return self.max_participants - self.current_participants_count


class Event(models.Model):
    """Événements de danse (soirées, festivals, etc.)"""
    EVENT_TYPES = [
        ('party', 'Soirée dansante'),
        ('festival', 'Festival'),
        ('workshop', 'Atelier'),
        ('competition', 'Compétition'),
        ('social', 'Social dance'),
        ('other', 'Autre'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='party')
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='events')
    dance_styles = models.ManyToManyField(DanceStyle, blank=True)
    
    # Date et heure
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    # Tarifs et capacité
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_participants = models.PositiveIntegerField(default=100)
    
    # Organisation
    organizers = models.ManyToManyField(User, related_name='organized_events')
    instructors = models.ManyToManyField(Instructor, blank=True, related_name='events')
    
    # Statut
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} - {self.start_datetime.strftime('%d/%m/%Y')}"


class CourseRegistration(models.Model):
    """Inscription à un cours"""
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_registrations')
    registration_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé'),
    ], default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['course', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.course.title}"


class EventRegistration(models.Model):
    """Inscription à un événement"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    registration_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'En attente'),
        ('paid', 'Payé'),
        ('cancelled', 'Annulé'),
    ], default='pending')
    payment_method = models.CharField(max_length=50, blank=True)
    special_requests = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['event', 'user']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title}"


class DancePartner(models.Model):
    """Système de recherche de partenaire de danse"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dance_profile')
    dance_styles = models.ManyToManyField(DanceStyle, related_name='dancers')
    level = models.CharField(max_length=20, choices=Course.LEVEL_CHOICES, default='beginner')
    bio = models.TextField(blank=True)
    looking_for = models.CharField(max_length=20, choices=[
        ('leader', 'Leader'),
        ('follower', 'Follower'),
        ('both', 'Les deux'),
    ], default='both')
    availability = models.JSONField(default=dict)  # Jours et heures disponibles
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.level}"


class Review(models.Model):
    """Avis sur les cours et événements"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='reviews', null=True, blank=True)
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['user', 'course'], ['user', 'event']]
    
    def __str__(self):
        if self.course:
            return f"{self.user.get_full_name()} - {self.course.title} ({self.rating}/5)"
        else:
            return f"{self.user.get_full_name()} - {self.event.title} ({self.rating}/5)"


class Notification(models.Model):
    """Notifications pour les utilisateurs"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=[
        ('course_reminder', 'Rappel de cours'),
        ('event_reminder', 'Rappel d\'événement'),
        ('payment', 'Paiement'),
        ('system', 'Système'),
        ('partner_request', 'Demande de partenaire'),
    ])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.title}" 
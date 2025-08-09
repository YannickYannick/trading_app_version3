from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    DanceStyle, Instructor, Venue, Course, Event, 
    CourseRegistration, EventRegistration, DancePartner, 
    Review, Notification
)


def home(request):
    """Page d'accueil de l'application bachata"""
    # Cours à venir
    upcoming_courses = Course.objects.filter(
        is_active=True,
        start_date__gte=timezone.now().date()
    ).order_by('start_date')[:6]
    
    # Événements à venir
    upcoming_events = Event.objects.filter(
        is_active=True,
        start_datetime__gte=timezone.now()
    ).order_by('start_datetime')[:6]
    
    # Instructeurs actifs
    active_instructors = Instructor.objects.filter(is_active=True)[:4]
    
    # Statistiques
    total_courses = Course.objects.filter(is_active=True).count()
    total_events = Event.objects.filter(is_active=True).count()
    total_instructors = Instructor.objects.filter(is_active=True).count()
    
    context = {
        'upcoming_courses': upcoming_courses,
        'upcoming_events': upcoming_events,
        'active_instructors': active_instructors,
        'total_courses': total_courses,
        'total_events': total_events,
        'total_instructors': total_instructors,
    }
    return render(request, 'bachata_app/home.html', context)


def courses_list(request):
    """Liste des cours disponibles"""
    courses = Course.objects.filter(is_active=True)
    
    # Filtres
    level = request.GET.get('level')
    dance_style = request.GET.get('dance_style')
    instructor = request.GET.get('instructor')
    venue = request.GET.get('venue')
    
    if level:
        courses = courses.filter(level=level)
    if dance_style:
        courses = courses.filter(dance_style__name=dance_style)
    if instructor:
        courses = courses.filter(instructor__user__first_name__icontains=instructor)
    if venue:
        courses = courses.filter(venue__name__icontains=venue)
    
    # Tri
    sort_by = request.GET.get('sort', 'start_date')
    if sort_by == 'price':
        courses = courses.order_by('price_per_session')
    elif sort_by == 'popularity':
        courses = courses.annotate(participant_count=Count('participants')).order_by('-participant_count')
    else:
        courses = courses.order_by('start_date')
    
    # Pagination
    paginator = Paginator(courses, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filtres disponibles
    dance_styles = DanceStyle.objects.all()
    instructors = Instructor.objects.filter(is_active=True)
    venues = Venue.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'dance_styles': dance_styles,
        'instructors': instructors,
        'venues': venues,
        'filters': {
            'level': level,
            'dance_style': dance_style,
            'instructor': instructor,
            'venue': venue,
            'sort': sort_by,
        }
    }
    return render(request, 'bachata_app/courses_list.html', context)


def course_detail(request, course_id):
    """Détails d'un cours"""
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Vérifier si l'utilisateur est inscrit
    is_registered = False
    if request.user.is_authenticated:
        is_registered = CourseRegistration.objects.filter(
            course=course, user=request.user
        ).exists()
    
    # Avis sur le cours
    reviews = Review.objects.filter(course=course).order_by('-created_at')[:5]
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Cours similaires
    similar_courses = Course.objects.filter(
        is_active=True,
        dance_style=course.dance_style,
        level=course.level
    ).exclude(id=course.id)[:3]
    
    context = {
        'course': course,
        'is_registered': is_registered,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'similar_courses': similar_courses,
    }
    return render(request, 'bachata_app/course_detail.html', context)


@login_required
def course_register(request, course_id):
    """Inscription à un cours"""
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    # Vérifier si déjà inscrit
    if CourseRegistration.objects.filter(course=course, user=request.user).exists():
        messages.warning(request, 'Vous êtes déjà inscrit à ce cours.')
        return redirect('bachata_app:course_detail', course_id=course_id)
    
    # Vérifier si le cours est complet
    if course.is_full:
        messages.error(request, 'Ce cours est complet.')
        return redirect('bachata_app:course_detail', course_id=course_id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', '')
        notes = request.POST.get('notes', '')
        
        # Créer l'inscription
        registration = CourseRegistration.objects.create(
            course=course,
            user=request.user,
            payment_method=payment_method,
            notes=notes
        )
        
        # Créer une notification
        Notification.objects.create(
            user=request.user,
            title=f'Inscription confirmée - {course.title}',
            message=f'Votre inscription au cours "{course.title}" a été confirmée.',
            notification_type='course_reminder'
        )
        
        messages.success(request, 'Inscription réussie !')
        return redirect('bachata_app:my_courses')
    
    context = {
        'course': course,
    }
    return render(request, 'bachata_app/course_register.html', context)


def events_list(request):
    """Liste des événements"""
    events = Event.objects.filter(is_active=True)
    
    # Filtres
    event_type = request.GET.get('event_type')
    dance_style = request.GET.get('dance_style')
    venue = request.GET.get('venue')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if event_type:
        events = events.filter(event_type=event_type)
    if dance_style:
        events = events.filter(dance_styles__name=dance_style)
    if venue:
        events = events.filter(venue__name__icontains=venue)
    if date_from:
        events = events.filter(start_datetime__date__gte=date_from)
    if date_to:
        events = events.filter(start_datetime__date__lte=date_to)
    
    # Tri
    sort_by = request.GET.get('sort', 'start_datetime')
    if sort_by == 'price':
        events = events.order_by('price')
    elif sort_by == 'popularity':
        events = events.annotate(participant_count=Count('participants')).order_by('-participant_count')
    else:
        events = events.order_by('start_datetime')
    
    # Pagination
    paginator = Paginator(events, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filtres disponibles
    dance_styles = DanceStyle.objects.all()
    venues = Venue.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'dance_styles': dance_styles,
        'venues': venues,
        'filters': {
            'event_type': event_type,
            'dance_style': dance_style,
            'venue': venue,
            'date_from': date_from,
            'date_to': date_to,
            'sort': sort_by,
        }
    }
    return render(request, 'bachata_app/events_list.html', context)


def event_detail(request, event_id):
    """Détails d'un événement"""
    event = get_object_or_404(Event, id=event_id, is_active=True)
    
    # Vérifier si l'utilisateur est inscrit
    is_registered = False
    if request.user.is_authenticated:
        is_registered = EventRegistration.objects.filter(
            event=event, user=request.user
        ).exists()
    
    # Avis sur l'événement
    reviews = Review.objects.filter(event=event).order_by('-created_at')[:5]
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Événements similaires
    similar_events = Event.objects.filter(
        is_active=True,
        event_type=event.event_type
    ).exclude(id=event.id)[:3]
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'similar_events': similar_events,
    }
    return render(request, 'bachata_app/event_detail.html', context)


@login_required
def event_register(request, event_id):
    """Inscription à un événement"""
    event = get_object_or_404(Event, id=event_id, is_active=True)
    
    # Vérifier si déjà inscrit
    if EventRegistration.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, 'Vous êtes déjà inscrit à cet événement.')
        return redirect('bachata_app:event_detail', event_id=event_id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', '')
        special_requests = request.POST.get('special_requests', '')
        
        # Créer l'inscription
        registration = EventRegistration.objects.create(
            event=event,
            user=request.user,
            payment_method=payment_method,
            special_requests=special_requests
        )
        
        # Créer une notification
        Notification.objects.create(
            user=request.user,
            title=f'Inscription confirmée - {event.title}',
            message=f'Votre inscription à l\'événement "{event.title}" a été confirmée.',
            notification_type='event_reminder'
        )
        
        messages.success(request, 'Inscription réussie !')
        return redirect('bachata_app:my_events')
    
    context = {
        'event': event,
    }
    return render(request, 'bachata_app/event_register.html', context)


@login_required
def my_courses(request):
    """Mes cours inscrits"""
    registrations = CourseRegistration.objects.filter(
        user=request.user
    ).select_related('course', 'course__instructor', 'course__venue').order_by('-registration_date')
    
    context = {
        'registrations': registrations,
    }
    return render(request, 'bachata_app/my_courses.html', context)


@login_required
def my_events(request):
    """Mes événements inscrits"""
    registrations = EventRegistration.objects.filter(
        user=request.user
    ).select_related('event', 'event__venue').order_by('-registration_date')
    
    context = {
        'registrations': registrations,
    }
    return render(request, 'bachata_app/my_events.html', context)


def instructors_list(request):
    """Liste des instructeurs"""
    instructors = Instructor.objects.filter(is_active=True)
    
    # Filtres
    dance_style = request.GET.get('dance_style')
    experience = request.GET.get('experience')
    
    if dance_style:
        instructors = instructors.filter(specializations__name=dance_style)
    if experience:
        instructors = instructors.filter(experience_years__gte=int(experience))
    
    # Tri
    sort_by = request.GET.get('sort', 'user__first_name')
    if sort_by == 'experience':
        instructors = instructors.order_by('-experience_years')
    else:
        instructors = instructors.order_by('user__first_name')
    
    # Pagination
    paginator = Paginator(instructors, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filtres disponibles
    dance_styles = DanceStyle.objects.all()
    
    context = {
        'page_obj': page_obj,
        'dance_styles': dance_styles,
        'filters': {
            'dance_style': dance_style,
            'experience': experience,
            'sort': sort_by,
        }
    }
    return render(request, 'bachata_app/instructors_list.html', context)


def instructor_detail(request, instructor_id):
    """Détails d'un instructeur"""
    instructor = get_object_or_404(Instructor, id=instructor_id, is_active=True)
    
    # Cours de l'instructeur
    courses = Course.objects.filter(
        instructor=instructor,
        is_active=True
    ).order_by('start_date')
    
    # Avis sur les cours de l'instructeur
    reviews = Review.objects.filter(
        course__instructor=instructor
    ).select_related('course', 'user').order_by('-created_at')[:10]
    
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    context = {
        'instructor': instructor,
        'courses': courses,
        'reviews': reviews,
        'avg_rating': avg_rating,
    }
    return render(request, 'bachata_app/instructor_detail.html', context)


def dance_partners(request):
    """Recherche de partenaires de danse"""
    partners = DancePartner.objects.filter(is_active=True)
    
    # Filtres
    dance_style = request.GET.get('dance_style')
    level = request.GET.get('level')
    looking_for = request.GET.get('looking_for')
    
    if dance_style:
        partners = partners.filter(dance_styles__name=dance_style)
    if level:
        partners = partners.filter(level=level)
    if looking_for:
        partners = partners.filter(looking_for=looking_for)
    
    # Exclure l'utilisateur connecté
    if request.user.is_authenticated:
        partners = partners.exclude(user=request.user)
    
    # Tri
    sort_by = request.GET.get('sort', 'created_at')
    if sort_by == 'level':
        partners = partners.order_by('level')
    else:
        partners = partners.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(partners, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Filtres disponibles
    dance_styles = DanceStyle.objects.all()
    
    context = {
        'page_obj': page_obj,
        'dance_styles': dance_styles,
        'filters': {
            'dance_style': dance_style,
            'level': level,
            'looking_for': looking_for,
            'sort': sort_by,
        }
    }
    return render(request, 'bachata_app/dance_partners.html', context)


@login_required
def my_dance_profile(request):
    """Mon profil de danseur"""
    try:
        dance_profile = DancePartner.objects.get(user=request.user)
    except DancePartner.DoesNotExist:
        dance_profile = None
    
    if request.method == 'POST':
        if dance_profile:
            # Mettre à jour le profil existant
            dance_profile.level = request.POST.get('level', 'beginner')
            dance_profile.looking_for = request.POST.get('looking_for', 'both')
            dance_profile.bio = request.POST.get('bio', '')
            dance_profile.save()
            
            # Mettre à jour les styles de danse
            dance_styles = request.POST.getlist('dance_styles')
            dance_profile.dance_styles.set(dance_styles)
        else:
            # Créer un nouveau profil
            dance_profile = DancePartner.objects.create(
                user=request.user,
                level=request.POST.get('level', 'beginner'),
                looking_for=request.POST.get('looking_for', 'both'),
                bio=request.POST.get('bio', '')
            )
            
            # Ajouter les styles de danse
            dance_styles = request.POST.getlist('dance_styles')
            dance_profile.dance_styles.set(dance_styles)
        
        messages.success(request, 'Profil mis à jour avec succès !')
        return redirect('bachata_app:my_dance_profile')
    
    # Styles de danse disponibles
    dance_styles = DanceStyle.objects.all()
    
    context = {
        'dance_profile': dance_profile,
        'dance_styles': dance_styles,
    }
    return render(request, 'bachata_app/my_dance_profile.html', context)


@login_required
def add_review(request):
    """Ajouter un avis"""
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        event_id = request.POST.get('event_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        if course_id:
            course = get_object_or_404(Course, id=course_id)
            # Vérifier si l'utilisateur a suivi le cours
            if not CourseRegistration.objects.filter(course=course, user=request.user).exists():
                messages.error(request, 'Vous devez être inscrit au cours pour laisser un avis.')
                return redirect('bachata_app:course_detail', course_id=course_id)
            
            # Créer ou mettre à jour l'avis
            review, created = Review.objects.get_or_create(
                user=request.user,
                course=course,
                defaults={'rating': rating, 'comment': comment}
            )
            if not created:
                review.rating = rating
                review.comment = comment
                review.save()
            
            messages.success(request, 'Avis ajouté avec succès !')
            return redirect('bachata_app:course_detail', course_id=course_id)
        
        elif event_id:
            event = get_object_or_404(Event, id=event_id)
            # Vérifier si l'utilisateur a participé à l'événement
            if not EventRegistration.objects.filter(event=event, user=request.user).exists():
                messages.error(request, 'Vous devez être inscrit à l\'événement pour laisser un avis.')
                return redirect('bachata_app:event_detail', event_id=event_id)
            
            # Créer ou mettre à jour l'avis
            review, created = Review.objects.get_or_create(
                user=request.user,
                event=event,
                defaults={'rating': rating, 'comment': comment}
            )
            if not created:
                review.rating = rating
                review.comment = comment
                review.save()
            
            messages.success(request, 'Avis ajouté avec succès !')
            return redirect('bachata_app:event_detail', event_id=event_id)
    
    return redirect('bachata_app:home')


@login_required
def notifications(request):
    """Notifications de l'utilisateur"""
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Marquer comme lues
    if request.method == 'POST':
        notification_ids = request.POST.getlist('mark_read')
        if notification_ids:
            Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            ).update(is_read=True)
            messages.success(request, 'Notifications marquées comme lues.')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'bachata_app/notifications.html', context)


def search(request):
    """Recherche globale"""
    query = request.GET.get('q', '')
    results = []
    
    if query:
        # Rechercher dans les cours
        courses = Course.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(instructor__user__first_name__icontains=query) |
            Q(instructor__user__last_name__icontains=query) |
            Q(dance_style__name__icontains=query)
        ).filter(is_active=True)[:5]
        
        # Rechercher dans les événements
        events = Event.objects.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(venue__name__icontains=query) |
            Q(dance_styles__name__icontains=query)
        ).filter(is_active=True)[:5]
        
        # Rechercher dans les instructeurs
        instructors = Instructor.objects.filter(
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(bio__icontains=query) |
            Q(specializations__name__icontains=query)
        ).filter(is_active=True)[:5]
        
        results = {
            'courses': courses,
            'events': events,
            'instructors': instructors,
        }
    
    context = {
        'query': query,
        'results': results,
    }
    return render(request, 'bachata_app/search.html', context) 
from django.urls import path
from . import views

app_name = 'bachata_app'

urlpatterns = [
    # Pages principales
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    
    # Cours
    path('courses/', views.courses_list, name='courses_list'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/register/', views.course_register, name='course_register'),
    
    # Événements
    path('events/', views.events_list, name='events_list'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/<int:event_id>/register/', views.event_register, name='event_register'),
    
    # Instructeurs
    path('instructors/', views.instructors_list, name='instructors_list'),
    path('instructors/<int:instructor_id>/', views.instructor_detail, name='instructor_detail'),
    
    # Profil utilisateur
    path('my-courses/', views.my_courses, name='my_courses'),
    path('my-events/', views.my_events, name='my_events'),
    path('my-dance-profile/', views.my_dance_profile, name='my_dance_profile'),
    path('notifications/', views.notifications, name='notifications'),
    
    # Partenaires de danse
    path('dance-partners/', views.dance_partners, name='dance_partners'),
    
    # Avis
    path('add-review/', views.add_review, name='add_review'),
] 
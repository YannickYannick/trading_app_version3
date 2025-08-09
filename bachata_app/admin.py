from django.contrib import admin
from django.utils.html import format_html
from .models import (
    DanceStyle, Instructor, Venue, Course, Event, 
    CourseRegistration, EventRegistration, DancePartner, 
    Review, Notification
)


@admin.register(DanceStyle)
class DanceStyleAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'description']
    search_fields = ['name']
    list_filter = ['name']


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['user', 'experience_years', 'specializations_display', 'is_active', 'created_at']
    list_filter = ['is_active', 'experience_years', 'specializations']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    filter_horizontal = ['specializations']
    
    def specializations_display(self, obj):
        return ', '.join([style.name for style in obj.specializations.all()])
    specializations_display.short_description = 'Spécialisations'


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'capacity', 'phone', 'is_active']
    list_filter = ['is_active', 'city']
    search_fields = ['name', 'city', 'address']
    readonly_fields = ['amenities_display']
    
    def amenities_display(self, obj):
        if obj.amenities:
            return format_html('<ul>{}</ul>', 
                ''.join([f'<li>{k}: {v}</li>' for k, v in obj.amenities.items()]))
        return 'Aucun'
    amenities_display.short_description = 'Équipements'


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'instructor', 'dance_style', 'level', 'venue', 
        'start_date', 'end_date', 'price_per_session', 'participants_count', 
        'is_active', 'is_full'
    ]
    list_filter = [
        'is_active', 'is_full', 'level', 'dance_style', 
        'instructor', 'venue', 'start_date'
    ]
    search_fields = ['title', 'instructor__user__first_name', 'instructor__user__last_name']
    readonly_fields = ['total_price', 'current_participants_count', 'available_spots']
    
    def participants_count(self, obj):
        return obj.current_participants_count
    participants_count.short_description = 'Participants'


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'event_type', 'venue', 'start_datetime', 
        'end_datetime', 'price', 'participants_count', 'is_active', 'is_featured'
    ]
    list_filter = [
        'is_active', 'is_featured', 'event_type', 'venue', 
        'start_datetime', 'dance_styles'
    ]
    search_fields = ['title', 'venue__name']
    filter_horizontal = ['dance_styles', 'organizers', 'instructors']
    readonly_fields = ['participants_count']
    
    def participants_count(self, obj):
        return obj.participants.count()
    participants_count.short_description = 'Participants'


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'course', 'registration_date', 'payment_status', 
        'payment_method'
    ]
    list_filter = ['payment_status', 'registration_date', 'course__instructor']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'course__title'
    ]
    readonly_fields = ['registration_date']


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'event', 'registration_date', 'payment_status', 
        'payment_method'
    ]
    list_filter = ['payment_status', 'registration_date', 'event__event_type']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'event__title'
    ]
    readonly_fields = ['registration_date']


@admin.register(DancePartner)
class DancePartnerAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'level', 'looking_for', 'dance_styles_display', 
        'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'level', 'looking_for', 'dance_styles']
    search_fields = ['user__first_name', 'user__last_name', 'user__email']
    filter_horizontal = ['dance_styles']
    
    def dance_styles_display(self, obj):
        return ', '.join([style.name for style in obj.dance_styles.all()])
    dance_styles_display.short_description = 'Styles de danse'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'course_or_event', 'rating', 'created_at'
    ]
    list_filter = ['rating', 'created_at']
    search_fields = [
        'user__first_name', 'user__last_name', 
        'course__title', 'event__title'
    ]
    readonly_fields = ['created_at']
    
    def course_or_event(self, obj):
        if obj.course:
            return f"Cours: {obj.course.title}"
        else:
            return f"Événement: {obj.event.title}"
    course_or_event.short_description = 'Cours/Événement'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'title', 'notification_type', 'is_read', 'created_at'
    ]
    list_filter = ['is_read', 'notification_type', 'created_at']
    search_fields = [
        'user__first_name', 'user__last_name', 'user__email',
        'title', 'message'
    ]
    readonly_fields = ['created_at'] 
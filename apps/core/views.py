import array
from multiprocessing import context
from django.shortcuts import render,redirect
from django.http import HttpResponseRedirect
from django.views import View
from django.contrib import messages
from django.db.models import Count
from django.views.generic import TemplateView,CreateView,ListView
from apps.core.models import (
    Time, Location, Post, Venue, VenueBooking,
    PostComment, PostInterest, PostReaction,
    Notification,
)
from apps.core.forms import UserPostForm, ContactForm, VenueBookingForm
from apps.core.engagement import posts_with_engagement, build_comment_tree
from apps.core.notifications import (
    notify_interest, notify_like, notify_comment,
)
from apps.core.realtime import (
    serialize_notification,
    push_unread_count,
    unread_count_for,
)
from apps.accounts.models import Profile
from django.db.models import F
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import datetime
# Create your views here.

@login_required
def global_search(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'posts': [], 'venues': [], 'users': []})

    posts = Post.objects.filter(
        Q(message__icontains=q) | Q(venue__name__icontains=q) | Q(location__name__icontains=q)
    ).select_related('venue', 'location', 'author')[:8]

    venues = Venue.objects.filter(
        Q(name__icontains=q) | Q(address__icontains=q)
    )[:5]

    users = User.objects.filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
    ).exclude(pk=request.user.pk)[:5]

    return JsonResponse({
        'posts': [
            {
                'id': p.id,
                'title': (p.message[:60] + '...') if len(p.message) > 60 else p.message,
                'subtitle': f'{p.venue} · {p.author.username if p.author else "Unknown"}',
                'url': f'/home/',
            }
            for p in posts
        ],
        'venues': [
            {'id': v.id, 'title': v.name, 'url': f'/venues/{v.slug}/'}
            for v in venues
        ],
        'users': [
            {
                'id': u.id,
                'title': u.get_full_name() or u.username,
                'url': f'/accounts/profile/',
            }
            for u in users
        ],
    })


def index(request):
    template_name='core/index.html'
    if request.user.is_authenticated:
        return redirect('/home/')
    else:
        return render(request, template_name)
    


def about(request):
    template_name='core/about.html'
    return render(request, template_name)


def partnerwithus(request):
    template_name='core/partnerwithus.html'
    return render(request, template_name)


class ContactView(View):
    template_name = 'core/contact.html'

    def get(self, request, *args, **kwargs):
        form = ContactForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save()
            contact.save()  
            email = form.cleaned_data['email']
            email_context = {
                'email': email,  
            }
            email_message = render_to_string('email/contact_template.html', email_context)
            email_subject = 'Thank You for Your Message'
            email_from = settings.EMAIL_HOST_USER
            email_to = [email]
            msg = EmailMultiAlternatives(email_subject, email_message, email_from, email_to)
            msg.attach_alternative(email_message, "text/html")
            msg.send()
            messages.success(request, 'Message submitted successfully.')
            return redirect('contact')
        else:
            return render(request, self.template_name, {'form': form})

def review(request):
    template_name='core/review.html'
    return render(request, template_name)


def _home_context(request, form=None):
    form = form or UserPostForm()
    return {
        'form': form,
        'posts': posts_with_engagement(request.user),
        'venues': Venue.objects.select_related('location').all(),
        'timess': Time.objects.all(),
        'locations': Location.objects.all(),
        'userprofiledata': Profile.objects.get(user=request.user.pk),
        'times': Time.objects.values('id', 'name', 'slug').annotate(total=Count('post')),
    }


class HomeView(LoginRequiredMixin, View):
    template_name = 'core/home.html'
    form_class = UserPostForm

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, _home_context(request))

    def post(self, request, *args, **kwargs):
        form = UserPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('home')
        return render(request, self.template_name, _home_context(request, form))

class CategoryPostListView(LoginRequiredMixin, View):
    """Same layout as home feed, filtered by time category slug."""

    def get(self, request, time_slug):
        time_slot = get_object_or_404(Time, slug=time_slug)
        context = _home_context(request, UserPostForm(initial={'time': time_slot.pk}))
        context['posts'] = posts_with_engagement(request.user).filter(time=time_slot)
        context['active_time_slug'] = time_slot.slug
        context['category_name'] = time_slot.name
        context['time_slot'] = time_slot
        return render(request, 'core/home.html', context)



class VenueListView(LoginRequiredMixin, ListView):
    model = Venue
    template_name = 'core/venuelist.html'
    context_object_name = 'venues'

    def get_queryset(self):
        return Venue.objects.select_related('location').annotate(
            booking_count=Count('bookings'),
        )


class VenueDetailView(LoginRequiredMixin, View):
    template_name = 'core/venue_detail.html'

    def get(self, request, venue_slug):
        venue = get_object_or_404(Venue.objects.select_related('location'), slug=venue_slug)
        booking_form = VenueBookingForm()
        user_bookings = VenueBooking.objects.filter(
            venue=venue, user=request.user,
        ).select_related('time_slot')[:10]
        return render(request, self.template_name, {
            'venue': venue,
            'booking_form': booking_form,
            'user_bookings': user_bookings,
        })
    
@login_required
@require_POST
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author_id != request.user.pk:
        return JsonResponse(
            {'success': False, 'error': 'You are not authorized to delete this post.'},
            status=403,
        )
    post.delete()
    return JsonResponse({'success': True, 'message': 'Match deleted successfully.'})


@login_required
@require_GET
def get_edit_data(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author_id != request.user.pk:
        return JsonResponse({'error': 'You are not authorized to edit this post.'}, status=403)
    return JsonResponse({
        'location': post.location_id,
        'venue': post.venue_id,
        'date': post.date.strftime('%Y-%m-%d') if post.date else '',
        'time': post.time_id,
        'message': post.message,
    })


@login_required
@require_POST
def update_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author_id != request.user.pk:
        return JsonResponse({'success': False, 'error': 'You are not authorized to update this post.'}, status=403)
    form = UserPostForm(request.POST, instance=post)
    if form.is_valid():
        form.save()
        return JsonResponse({'success': True, 'message': 'Event updated successfully.'})
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def venue_book(request, venue_slug):
    venue = get_object_or_404(Venue, slug=venue_slug)
    form = VenueBookingForm(request.POST)
    if form.is_valid():
        booking = form.save(commit=False)
        booking.user = request.user
        booking.venue = venue
        booking.save()
        return JsonResponse({
            'success': True,
            'message': 'Booking request submitted! We will confirm shortly.',
            'booking': {
                'date': booking.booking_date.strftime('%d %b %Y'),
                'time': booking.display_time(),
                'status': booking.get_status_display(),
            },
        })
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@require_POST
def post_toggle_interest(request, post_id):
    from apps.core.chat import ensure_dm_with_host
    from apps.core.event_guard import event_locked_response, is_event_locked

    post = get_object_or_404(Post, pk=post_id)
    if is_event_locked(post):
        return event_locked_response()
    interest, created = PostInterest.objects.get_or_create(post=post, user=request.user)
    if not created:
        interest.delete()
        interested = False
    else:
        interested = True
        notify_interest(post, request.user, True)
        ensure_dm_with_host(post, request.user)
    count = post.interests.count()
    return JsonResponse({'success': True, 'interested': interested, 'interest_count': count})


@login_required
@require_POST
def post_toggle_reaction(request, post_id):
    from apps.core.event_guard import is_event_locked, social_engagement_denied_response

    post = get_object_or_404(Post, pk=post_id)
    if is_event_locked(post):
        return social_engagement_denied_response()
    reaction_type = request.POST.get('reaction_type', PostReaction.REACTION_LIKE)
    reaction, created = PostReaction.objects.get_or_create(
        post=post, user=request.user, reaction_type=reaction_type,
    )
    if not created:
        reaction.delete()
        liked = False
    else:
        liked = True
        notify_like(post, request.user, True)
    count = post.reactions.filter(reaction_type=reaction_type).count()
    return JsonResponse({'success': True, 'liked': liked, 'like_count': count})


@login_required
@require_GET
def post_comments(request, post_id):
    get_object_or_404(Post, pk=post_id)
    return JsonResponse({'success': True, 'comments': build_comment_tree(post_id)})


@login_required
@require_POST
def post_add_comment(request, post_id):
    from apps.core.event_guard import is_event_locked, social_engagement_denied_response

    post = get_object_or_404(Post, pk=post_id)
    if is_event_locked(post):
        return social_engagement_denied_response()
    body = (request.POST.get('body') or '').strip()
    if not body:
        return JsonResponse({'success': False, 'error': 'Comment cannot be empty.'}, status=400)
    parent_id = request.POST.get('parent_id')
    parent = None
    if parent_id:
        parent = get_object_or_404(PostComment, pk=parent_id, post=post)
    PostComment.objects.create(post=post, user=request.user, parent=parent, body=body)
    notify_comment(post, request.user, parent)
    return JsonResponse({
        'success': True,
        'message': 'Comment posted.',
        'comment_count': post.comments.count(),
        'comments': build_comment_tree(post_id),
    })


@login_required
@require_POST
def post_confirm_match(request, post_id):
    from apps.core.messenger_views import confirm_post_match

    post = get_object_or_404(Post, pk=post_id)
    try:
        confirm_post_match(post, request.user)
    except PermissionError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=403)
    return JsonResponse({'success': True, 'event_status': post.event_status})


@login_required
@require_POST
def post_cancel_confirmation(request, post_id):
    from apps.core.messenger_views import _reopen_confirmed_event

    post = get_object_or_404(Post, pk=post_id)
    if post.author_id != request.user.pk:
        return JsonResponse({'success': False, 'error': 'Only the host can cancel confirmation.'}, status=403)
    if post.event_status != Post.STATUS_CONFIRMED:
        return JsonResponse({'success': False, 'error': 'This event is not confirmed.'}, status=400)
    _reopen_confirmed_event(post, request.user)
    return JsonResponse({'success': True, 'event_status': post.event_status})


@login_required
@require_GET
def notifications_poll(request):
    since_id = int(request.GET.get('since_id', 0) or 0)
    qs = Notification.objects.filter(recipient=request.user).select_related('actor', 'post')
    unread_count = qs.filter(is_read=False).count()
    new_items = qs.filter(id__gt=since_id)[:20]
    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
        'notifications': [serialize_notification(n) for n in new_items],
    })


@login_required
@require_GET
def notifications_list(request):
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    qs = Notification.objects.filter(recipient=request.user).select_related('actor', 'post')[:30]
    return JsonResponse({
        'success': True,
        'unread_count': unread_count,
        'notifications': [serialize_notification(n) for n in qs],
    })


@login_required
@require_POST
def notification_mark_read(request, notification_id):
    updated = Notification.objects.filter(
        pk=notification_id, recipient=request.user,
    ).update(is_read=True)
    unread_count = unread_count_for(request.user.pk)
    push_unread_count(request.user.pk)
    return JsonResponse({'success': bool(updated), 'unread_count': unread_count})


@login_required
@require_POST
def notifications_mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    push_unread_count(request.user.pk)
    return JsonResponse({'success': True, 'unread_count': 0})




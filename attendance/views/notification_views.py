"""
Notification Center Views: List Alerts, Filter by Category, Mark as Read.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from ..models import Notification, NotificationCategory


@login_required
def notifications_index_view(request):
    """Notification Center with filtering and read/unread status management."""
    notifications = Notification.objects.filter(recipient=request.user)

    filter_type = request.GET.get('filter', 'all')
    category_filter = request.GET.get('category', '')

    if filter_type == 'unread':
        notifications = notifications.filter(is_read=False)

    if category_filter:
        notifications = notifications.filter(category=category_filter)

    paginator = Paginator(notifications.order_by('-created_at'), 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'category_filter': category_filter,
        'categories': NotificationCategory.choices,
        'active_nav': 'notifications'
    }
    return render(request, 'notifications/index.html', context)


@login_required
def notification_mark_read_view(request, notification_id):
    """Marks a single notification as read and navigates to its action URL if available."""
    notif = get_object_or_404(Notification, id=notification_id, recipient=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])

    if notif.action_url:
        return redirect(notif.action_url)
    return redirect('notifications_index')


@login_required
def notification_mark_all_read_view(request):
    """Marks all pending notifications as read for current user."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications_index')

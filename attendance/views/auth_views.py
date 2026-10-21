"""
Authentication views, role-based redirects, profile management, and access decorators.
"""

from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from ..models import UserProfile, UserRole, StudentProfile, FacultyProfile, ParentProfile


def role_required(*allowed_roles):
    """Enforces server-side role validation for protected routes."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('login')}?next={request.path}")
            
            # Superusers always pass
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            profile = getattr(request.user, 'profile', None)
            if not profile or profile.role not in allowed_roles:
                raise PermissionDenied("You do not have authorization to access this portal.")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


admin_required = role_required(UserRole.ADMIN)
faculty_required = role_required(UserRole.FACULTY, UserRole.ADMIN)
student_required = role_required(UserRole.STUDENT, UserRole.ADMIN)
parent_required = role_required(UserRole.PARENT, UserRole.ADMIN)


def login_view(request):
    """Clean login interface with 1-click evaluation demo account buttons."""
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('dashboard_redirect')
        else:
            messages.error(request, "Invalid username or password. Please verify your credentials.")

    return render(request, 'auth/login.html')


def logout_view(request):
    """Logs out user and terminates session."""
    logout(request)
    messages.info(request, "You have been safely signed out.")
    return redirect('login')


@login_required
def dashboard_redirect_view(request):
    """Directs authenticated users to their corresponding role portal."""
    if request.user.is_superuser:
        return redirect('admin_dashboard')

    profile = getattr(request.user, 'profile', None)
    if not profile:
        return redirect('user_profile')

    if profile.role == UserRole.ADMIN:
        return redirect('admin_dashboard')
    elif profile.role == UserRole.FACULTY:
        return redirect('faculty_dashboard')
    elif profile.role == UserRole.STUDENT:
        return redirect('student_dashboard')
    elif profile.role == UserRole.PARENT:
        return redirect('parent_dashboard')
    
    return redirect('user_profile')


@login_required
def profile_view(request):
    """Displays and edits user account profile."""
    profile = getattr(request.user, 'profile', None)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()

        request.user.email = email
        request.user.save(update_fields=['email'])

        if profile:
            profile.phone = phone
            profile.address = address
            profile.save(update_fields=['phone', 'address'])

        messages.success(request, "Profile information updated successfully.")
        return redirect('user_profile')

    context = {
        'profile': profile,
        'active_nav': 'profile'
    }
    return render(request, 'auth/profile.html', context)


def custom_403_view(request, exception=None):
    """Custom rendered 403 Access Denied page."""
    return render(request, 'auth/403.html', {'exception': exception}, status=403)


def custom_404_view(request, exception=None):
    """Custom rendered 404 Not Found page."""
    return render(request, 'auth/404.html', status=404)

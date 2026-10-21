/**
 * Student Attendance Intelligence - Main Frontend Interaction Script
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Mobile Sidebar Toggle
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const appSidebar = document.getElementById('appSidebar');

    if (sidebarToggleBtn && appSidebar) {
        sidebarToggleBtn.addEventListener('click', function () {
            appSidebar.classList.toggle('sidebar-open');
        });

        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 900 && appSidebar.classList.contains('sidebar-open')) {
                if (!appSidebar.contains(e.target) && !sidebarToggleBtn.contains(e.target)) {
                    appSidebar.classList.remove('sidebar-open');
                }
            }
        });
    }

    // 2. Alert Dismissal
    document.querySelectorAll('.alert-dismiss-btn').forEach(function (btn) {
        btn.addEventListener('click', function () {
            const alertBox = btn.closest('.alert-banner');
            if (alertBox) {
                alertBox.style.opacity = '0';
                setTimeout(() => alertBox.remove(), 200);
            }
        });
    });

    // 3. CSRF Helper for fetch requests
    window.getCsrfToken = function () {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };
});

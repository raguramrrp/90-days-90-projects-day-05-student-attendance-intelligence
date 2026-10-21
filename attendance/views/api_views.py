"""
AJAX and REST API Views for Simulator, ML Inference, and Dashboard Charts.
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from ..models import StudentProfile, Subject
from ..services.calculation_engine import simulate_future_attendance, get_student_subject_attendance, get_student_overall_attendance
from ..services.ml_risk_service import predict_attendance_risk_ml


@login_required
@require_POST
def api_simulate_attendance(request):
    """
    JSON API for real-time what-if scenario simulation.
    Accepts: attended, total, future_attended, future_absent, target_percentage.
    Returns calculated projections.
    """
    try:
        effective_attended = int(request.POST.get('attended', 0))
        total_eligible = int(request.POST.get('total', 0))
        future_attended = int(request.POST.get('future_attended', 0))
        future_absent = int(request.POST.get('future_absent', 0))
        target_pct = float(request.POST.get('target', 75.0))

        result = simulate_future_attendance(
            effective_attended=effective_attended,
            total_eligible=total_eligible,
            future_attended=future_attended,
            future_absent=future_absent,
            target_percentage=target_pct
        )
        return JsonResponse({'success': True, 'data': result})
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=400)


@login_required
@require_GET
def api_ml_risk_prediction(request, student_id):
    """
    Returns Decision Tree ML inference output along with feature attribution,
    or falls back cleanly to the rule engine if model artifact is not loaded.
    """
    try:
        student = StudentProfile.objects.get(id=student_id)
        result = predict_attendance_risk_ml(student)
        return JsonResponse({'success': True, 'data': result})
    except StudentProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': "Student not found."}, status=404)
    except Exception as exc:
        return JsonResponse({'success': False, 'error': str(exc)}, status=500)

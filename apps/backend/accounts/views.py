import csv

from django.contrib.auth import get_user_model, login
# views.py
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

# Create your views here.



User = get_user_model()

@login_required
def export_users_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'

    writer = csv.writer(response)
    writer.writerow(['First Name', 'Last Name', 'Email', 'Encodings Count'])

    for user in User.objects.all():
        encoding_count = getattr(user, 'faceencoding_set', []).count()
        writer.writerow([user.first_name, user.last_name, user.email, encoding_count])

    return response


@csrf_exempt
def magic_link_authenticate(request, token):
    if request.method != 'GET':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        user = authenticate(request, token=token)
        if user is None:
            raise PermissionDenied("Invalid or expired magic link")
        
        login(request, user)
        
        # Check if face verification is required
        if FaceVerification.objects.filter(user=user, is_verified=True).exists():
            request.session['pending_face_verification'] = True
            redirect_url = reverse('face-verification') + '?next=' + request.GET.get('next', '/')
        else:
            redirect_url = request.GET.get('next', '/')
            
        return redirect(redirect_url)
    
    except Exception as e:
        logger.error(f"Magic link auth error: {str(e)}")
        raise PermissionDenied("Authentication failed")

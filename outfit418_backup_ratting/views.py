import pickle

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect

from celery import group

from allianceauth.services.hooks import get_extension_logger

from .forms import BackupForm
from .tasks import save_import, fetch_char

logger = get_extension_logger(__name__)


@login_required
@user_passes_test(lambda user: user.is_superuser)
def index(request):
    return redirect('outfit418backup:dashboard')


@login_required
@user_passes_test(lambda user: user.is_superuser)
def dashboard(request):
    if request.method == 'POST':
        form = BackupForm(request.POST, request.FILES)
        if form.is_valid():
            data = pickle.load(form.cleaned_data['file'])

            group((fetch_char.si(char_id) for char_id in data['character_list'])).delay()
            save_import.apply_async(kwargs={'data': data['rotations']}, countdown=30)
            messages.success(request, 'Backup task will start in 30 seconds!')
            return redirect('allianceauth_pve:index')
        else:
            messages.error(request, 'Form not valid!')
    else:
        form = BackupForm()
    context = {
        'form': form
    }
    return render(request, 'outfit418_backup_ratting/index.html', context=context)

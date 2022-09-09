import pickle

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect

from allianceauth.services.hooks import get_extension_logger

from .forms import BackupForm
from .tasks import save_import

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
            save_import.delay(data)

            messages.success(request, 'Backup task called successfully!')
            return redirect('allianceauth_pve:index')
    else:
        form = BackupForm()
    context = {
        'form': form
    }
    return render(request, 'outfit418_backup_ratting/index.html', context=context)

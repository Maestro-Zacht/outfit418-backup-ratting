import json

from django.contrib.auth.decorators import user_passes_test, login_required
from django.shortcuts import render, redirect


@login_required
@user_passes_test(lambda user: user.is_superuser)
def index(request):
    return redirect('outfit418backup:dashboard')


@login_required
@user_passes_test(lambda user: user.is_superuser)
def dashboard(request):
    if request.method == 'POST':
        file = request.FILES['OutfitBackup']
        data = json.load(file)
    context = {}
    return render(request, 'outfit418_backup_ratting/index.html', context=context)

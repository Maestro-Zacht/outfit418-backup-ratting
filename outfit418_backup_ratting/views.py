import pickle

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required, permission_required
from django.shortcuts import render, redirect
from django.db.models import F, Prefetch, Exists, OuterRef

from celery import group

from allianceauth.services.hooks import get_extension_logger
from allianceauth.authentication.models import CharacterOwnership

from corptools.models import CharacterAudit

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


@login_required
@permission_required('outfit418_backup_ratting.audit_corp')
def audit(request):
    corp_id = request.user.profile.main_character.corporation_id
    ownership_qs = (
        CharacterOwnership.objects
        .filter(Exists(CharacterAudit.objects.filter(character=OuterRef('character'))))
        .select_related('character')
    )
    mains = (
        CharacterAudit.objects
        .filter(
            character__character_ownership__user__profile__main_character=F('character'),
            character__corporation_id=corp_id,
        )
        .select_related('character__character_ownership__user')
        .prefetch_related(
            Prefetch(
                'character__character_ownership__user__character_ownerships',
                queryset=ownership_qs,
                to_attr='chars',
            ),
        )
    )

    return render(request, 'outfit418_backup_ratting/audit.html', context={'mains': mains})

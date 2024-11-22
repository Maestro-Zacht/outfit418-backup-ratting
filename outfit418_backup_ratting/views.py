import pickle
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required, permission_required
from django.shortcuts import render, redirect
from django.db.models import F, Prefetch, Max, Subquery, OuterRef, Case, When, Min, Exists
from django.db.models.lookups import LessThan
from django.utils import timezone

from celery import group

from allianceauth.services.hooks import get_extension_logger
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter

from corptools.models import CharacterAudit, CharacterAsset
from corptools.task_helpers.char_tasks import get_token

from .forms import BackupForm
from .tasks import save_import, fetch_char
from .models import CharacterAuditLoginData
from .utils import get_ship_names

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
        .select_related('character__characteraudit')
        .annotate(
            last_login=Subquery(
                CharacterAuditLoginData.objects
                .filter(characteraudit__character=OuterRef('character'))
                .values('last_login')
            )
        )
    )
    user_login_qs = (
        CharacterAuditLoginData.objects
        .filter(
            characteraudit__character__character_ownership__user=OuterRef('character__character_ownership__user')
        )
        .values('characteraudit__character__character_ownership__user')
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
        .annotate(
            last_login=Subquery(
                user_login_qs
                .annotate(last_login=Max('last_login'))
                .values('last_login')
            )
        )
        .annotate(
            is_updating=Case(
                When(
                    LessThan(
                        Subquery(
                            user_login_qs
                            .annotate(last_update=Min('last_update'))
                            .values('last_update')
                        ),
                        timezone.now() - timezone.timedelta(days=1),
                    ) |
                    Exists(
                        CharacterAuditLoginData.objects
                        .filter(
                            characteraudit__character__character_ownership__user=OuterRef('character__character_ownership__user'),
                            last_update__isnull=True
                        )
                    ),
                    then=False
                ),
                default=True,
            )
        )
        .annotate(
            older_last_update=Case(
                When(
                    Exists(
                        CharacterAuditLoginData.objects
                        .filter(
                            characteraudit__character__character_ownership__user=OuterRef('character__character_ownership__user'),
                            last_update__isnull=True
                        )
                    ),
                    then=None
                ),
                default=Subquery(
                    user_login_qs
                    .annotate(last_update=Min('last_update'))
                    .values('last_update')
                )
            )
        )
    )

    return render(request, 'outfit418_backup_ratting/audit.html', context={'mains': mains})


@login_required
@permission_required('outfit418_backup_ratting.find_jeremy')
def find_jeremy(request):
    thannys = CharacterAsset.objects.filter(type_name_id=23911).select_related('character__character')
    thanny_dict = defaultdict(list)
    jeremy_owners = defaultdict(list)

    for thanny in thannys:
        thanny_dict[thanny.character.character].append(thanny.item_id)

    for char, item_ids in thanny_dict.items():
        token = get_token(char.character_id, ['esi-assets.read_assets.v1'])
        if token:
            names = get_ship_names(token, item_ids)
            for name in names:
                if 'jeremy' in name.lower():
                    jeremy_owners[char].append(name)

    context = {
        'jeremy_owners': dict(jeremy_owners),
    }

    return render(request, 'outfit418_backup_ratting/find_jeremy.html', context=context)

import pickle
from collections import defaultdict

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.services.hooks import get_extension_logger
from celery import group
from corptools.models import CharacterAsset, CharacterAudit
from corptools.task_helpers.char_tasks import get_token
from django.contrib import messages
from django.contrib.auth.decorators import (
    login_required,
    permission_required,
    user_passes_test,
)
from django.db.models import (
    Case,
    Exists,
    F,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    When,
)
from django.db.models.lookups import LessThan
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import DATETIME_FORMAT, BackupForm, MemberActivityFilterForm
from .models import CharacterAuditLoginData, EventBackup, MemberActivityLocation
from .tasks import fetch_char, save_import
from .utils import get_ship_names

logger = get_extension_logger(__name__)


@login_required
@user_passes_test(lambda user: user.is_superuser)
def index(request):
    return redirect("outfit418backup:dashboard")


@login_required
@user_passes_test(lambda user: user.is_superuser)
def dashboard(request):
    if request.method == "POST":
        form = BackupForm(request.POST, request.FILES)
        if form.is_valid():
            data = pickle.load(form.cleaned_data["file"])  # noqa: S301

            group(fetch_char.si(char_id) for char_id in data["character_list"]).delay()
            save_import.apply_async(kwargs={"data": data["rotations"]}, countdown=30)
            messages.success(request, "Backup task will start in 30 seconds!")
            return redirect("allianceauth_pve:index")
        messages.error(request, "Form not valid!")
    else:
        form = BackupForm()
    context = {"form": form}
    return render(request, "outfit418_backup_ratting/index.html", context=context)


@login_required
@permission_required("outfit418_backup_ratting.audit_corp")
def audit(request):
    corp_id = request.user.profile.main_character.corporation_id
    ownership_qs = CharacterOwnership.objects.select_related(
        "character__characteraudit"
    ).annotate(
        last_login=Subquery(
            CharacterAuditLoginData.objects.filter(
                characteraudit__character=OuterRef("character")
            ).values("last_login")
        )
    )
    user_login_qs = CharacterAuditLoginData.objects.filter(
        characteraudit__character__character_ownership__user=OuterRef(
            "character__character_ownership__user"
        )
    ).values("characteraudit__character__character_ownership__user")

    mains = (
        CharacterAudit.objects.filter(
            character__character_ownership__user__profile__main_character=F(
                "character"
            ),
            character__corporation_id=corp_id,
        )
        .select_related("character__character_ownership__user")
        .prefetch_related(
            Prefetch(
                "character__character_ownership__user__character_ownerships",
                queryset=ownership_qs,
                to_attr="chars",
            ),
        )
        .annotate(
            last_login=Subquery(
                user_login_qs.annotate(last_login=Max("last_login")).values(
                    "last_login"
                )
            )
        )
        .annotate(
            is_updating=Case(
                When(
                    LessThan(
                        Subquery(
                            user_login_qs.annotate(
                                last_update=Min("last_update")
                            ).values("last_update")
                        ),
                        timezone.now() - timezone.timedelta(days=1),
                    )
                    | Exists(
                        CharacterAuditLoginData.objects.filter(
                            characteraudit__character__character_ownership__user=OuterRef(
                                "character__character_ownership__user"
                            ),
                            last_update__isnull=True,
                        )
                    ),
                    then=False,
                ),
                default=True,
            )
        )
        .annotate(
            older_last_update=Case(
                When(
                    Exists(
                        CharacterAuditLoginData.objects.filter(
                            characteraudit__character__character_ownership__user=OuterRef(
                                "character__character_ownership__user"
                            ),
                            last_update__isnull=True,
                        )
                    ),
                    then=None,
                ),
                default=Subquery(
                    user_login_qs.annotate(last_update=Min("last_update")).values(
                        "last_update"
                    )
                ),
            )
        )
    )

    return render(
        request, "outfit418_backup_ratting/audit.html", context={"mains": mains}
    )


@login_required
@permission_required("outfit418_backup_ratting.view_member_activity")
def member_activity(request):
    now = timezone.now()
    form = MemberActivityFilterForm(
        user=request.user,
        initial={
            "start": (now - timezone.timedelta(days=30)).strftime(DATETIME_FORMAT),
            "end": now.strftime(DATETIME_FORMAT),
        },
    )
    return render(
        request, "outfit418_backup_ratting/member_activity.html", context={"form": form}
    )


@login_required
@permission_required("outfit418_backup_ratting.view_member_activity")
def member_activity_data(request):
    form = MemberActivityFilterForm(request.GET, user=request.user)
    if not form.is_valid():
        return JsonResponse({"errors": form.errors}, status=400)

    main = form.cleaned_data["main_character"]
    start = form.cleaned_data["start"]
    end = form.cleaned_data["end"]
    target_user = main.userprofile.user
    now = timezone.now()

    ownerships = (
        CharacterOwnership.objects.filter(user=target_user)
        .select_related("character")
        .order_by("character__character_name")
    )
    characters = [ownership.character.character_name for ownership in ownerships]

    locations = (
        MemberActivityLocation.objects.filter(
            member_activity__login_data__characteraudit__character__character_ownership__user=target_user,
            start_time__lt=end,
        )
        .filter(Q(end_time__gt=start) | Q(end_time__isnull=True))
        .select_related(
            "system", "member_activity__login_data__characteraudit__character"
        )
        .order_by("start_time")
    )

    def ms(dt):
        return int(dt.timestamp() * 1000)

    segments = []
    for location in locations:
        seg_start = max(location.start_time, start)
        seg_end = min(location.end_time or now, end)
        if seg_end <= seg_start:
            continue
        segments.append(
            {
                "x": [ms(seg_start), ms(seg_end)],
                "y": location.member_activity.login_data.characteraudit.character.character_name,
                "online": location.is_online,
                "system": location.system.name,
            }
        )

    return JsonResponse(
        {
            "characters": characters,
            "segments": segments,
            "range": {"start": ms(start), "end": ms(end)},
        }
    )


@login_required
@permission_required("outfit418_backup_ratting.find_jeremy")
def find_jeremy(request):
    thannys = CharacterAsset.objects.filter(type_name_id=23911).select_related(
        "character__character"
    )
    thanny_dict = defaultdict(list)
    jeremy_owners = defaultdict(list)

    for thanny in thannys:
        thanny_dict[thanny.character.character].append(thanny.item_id)

    for char, item_ids in thanny_dict.items():
        token = get_token(char.character_id, ["esi-assets.read_assets.v1"])
        if token:
            names = get_ship_names(token, item_ids)
            for name in names:
                if "jeremy" in name.lower():
                    jeremy_owners[char].append(name)

    context = {
        "jeremy_owners": dict(jeremy_owners),
    }

    return render(request, "outfit418_backup_ratting/find_jeremy.html", context=context)


@login_required
@user_passes_test(lambda user: user.is_superuser)
def event_backup(request):
    events = EventBackup.objects.all()
    context = {
        "events": events,
    }
    return render(
        request, "outfit418_backup_ratting/event_backups.html", context=context
    )


@login_required
@user_passes_test(lambda user: user.is_superuser)
def restore_event(request, event_id):
    event = EventBackup.objects.get(pk=event_id)
    restored = event.restore_event()
    messages.success(request, f"Event {event.title} restored!")
    return redirect("opcalendar:event-detail", restored.pk)

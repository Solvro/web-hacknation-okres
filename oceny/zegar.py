"""Data systemowa. W trybie demo kadry mogą ją przesunąć na potrzeby demo (oznaczone w UI)."""

from datetime import date

from django.conf import settings
from django.utils import timezone


def przesunieta() -> date | None:
    if not settings.OKRES_DEMO:
        return None
    from .models import ZegarDemo

    z = ZegarDemo.objects.filter(pk=1).first()
    return z.data if z else None


def dzis() -> date:
    return przesunieta() or timezone.localdate()


def context_processor(request):
    return {"zegar_przesuniety": przesunieta()}

"""All writes to ownership history go through this module."""
from __future__ import annotations

import datetime
import uuid
from typing import Optional

from django.db import transaction

from core.integrity import (
    TransferRejected, VerifyResult, append_entry, check_transfer, verify_chain,
)

from .models import Owner, OwnershipEntry, Parcel

TRANSFER_KINDS = {"sale", "inheritance", "gift", "court_order"}
MAX_REF_LENGTH = 100


def _payload(owner_id, kind: str, ref: str, effective_date: datetime.date) -> dict:
    if not isinstance(effective_date, datetime.date):
        raise ValueError("effective_date must be a date")
    if len(ref) > MAX_REF_LENGTH:
        raise ValueError("ref is too long")
    return {
        "owner_id": str(owner_id),
        "kind": kind,
        "ref": ref,
        "effective_date": effective_date.isoformat(),
    }


def _chain(parcel: Parcel) -> list[dict]:
    return list(parcel.entries.order_by("seq").values("seq", "prev_hash", "payload", "hash"))


@transaction.atomic
def create_parcel_with_owner(*, owner: Owner, effective_date: datetime.date,
                             ref: str = "", **parcel_fields) -> Parcel:
    parcel = Parcel(**parcel_fields)
    parcel.full_clean()
    parcel.save()
    entry = append_entry([], _payload(owner.id, "initial", ref, effective_date))
    OwnershipEntry.objects.create(parcel=parcel, **entry)
    return parcel


def current_head(parcel: Parcel) -> str:
    chain = _chain(parcel)
    if not chain:
        raise ValueError("parcel has no ownership record")
    return chain[-1]["hash"]


def current_owner(parcel: Parcel) -> Owner:
    chain = _chain(parcel)
    if not chain:
        raise ValueError("parcel has no ownership record")
    return Owner.objects.get(pk=uuid.UUID(chain[-1]["payload"]["owner_id"]))


def verify_parcel(parcel: Parcel, expected_head: Optional[str] = None) -> VerifyResult:
    return verify_chain(_chain(parcel), expected_head=expected_head)


@transaction.atomic
def transfer_ownership(*, parcel_id, seller_id, buyer_id, expected_head: str,
                       kind: str, ref: str, effective_date: datetime.date) -> OwnershipEntry:
    """Apply one ownership change.

    The parcel row is locked for the duration, so two simultaneous sales of
    the same parcel are processed one after another; the second one then
    fails because its `expected_head` is no longer the head.
    """
    if kind not in TRANSFER_KINDS:
        raise ValueError(f"kind must be one of {sorted(TRANSFER_KINDS)}")
    if str(seller_id) == str(buyer_id):
        raise TransferRejected("seller and buyer are the same person")
    if not Owner.objects.filter(pk=buyer_id).exists():
        raise TransferRejected("buyer is not a registered owner")

    parcel = Parcel.objects.select_for_update().get(pk=parcel_id)
    chain = _chain(parcel)
    check_transfer(chain, str(seller_id), expected_head)
    entry = append_entry(chain, _payload(buyer_id, kind, ref, effective_date))
    return OwnershipEntry.objects.create(parcel=parcel, **entry)

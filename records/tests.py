from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.integrity import TransferRejected

from .models import ImmutableRecordError, LandType, Owner, OwnershipEntry, Parcel
from .services import (
    create_parcel_with_owner, current_head, current_owner,
    transfer_ownership, verify_parcel,
)

PARCEL = dict(district="নমুনা জেলা", upazila="নমুনা উপজেলা", mouza="নমুনা মৌজা",
              khatian_no="1245", dag_no="883", area_decimal=Decimal("33.00"),
              land_type=LandType.AGRICULTURAL)


class OwnerTests(TestCase):
    def test_nid_not_stored_in_plaintext(self):
        o = Owner.register("কাল্পনিক ক", "1234567890")
        self.assertEqual(o.nid_last4, "7890")
        self.assertNotIn("1234567890", o.nid_hmac)
        self.assertEqual(len(o.nid_hmac), 64)

    def test_bengali_digits_normalised(self):
        self.assertEqual(Owner.hash_nid("১২৩৪৫৬৭৮৯০"), Owner.hash_nid("1234567890"))

    def test_invalid_nid_rejected(self):
        for bad in ("123", "12345678901", "12345abcde", ""):
            with self.assertRaises(ValidationError):
                Owner.register("কাল্পনিক", bad)

    def test_duplicate_nid_rejected(self):
        Owner.register("কাল্পনিক ক", "1234567890")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Owner.register("কাল্পনিক খ", "1234567890")


class OwnershipTests(TestCase):
    def setUp(self):
        self.a = Owner.register("কাল্পনিক ক", "1234567890")
        self.b = Owner.register("কাল্পনিক খ", "1234567891")
        self.c = Owner.register("কাল্পনিক গ", "1234567892")
        self.parcel = create_parcel_with_owner(
            owner=self.a, effective_date=date(2020, 1, 1), **PARCEL)

    def sell(self, seller, buyer, head):
        return transfer_ownership(
            parcel_id=self.parcel.id, seller_id=seller.id, buyer_id=buyer.id,
            expected_head=head, kind="sale", ref="দলিল-নমুনা-১",
            effective_date=date(2024, 5, 1))

    def test_initial_state(self):
        self.assertEqual(current_owner(self.parcel), self.a)
        self.assertTrue(verify_parcel(self.parcel).ok)

    def test_transfer_moves_ownership(self):
        self.sell(self.a, self.b, current_head(self.parcel))
        self.assertEqual(current_owner(self.parcel), self.b)
        self.assertEqual(self.parcel.entries.count(), 2)
        self.assertTrue(verify_parcel(self.parcel).ok)

    def test_double_sale_blocked(self):
        head = current_head(self.parcel)
        self.sell(self.a, self.b, head)
        with self.assertRaises(TransferRejected):
            self.sell(self.a, self.c, head)
        self.assertEqual(current_owner(self.parcel), self.b)
        self.assertEqual(self.parcel.entries.count(), 2)

    def test_wrong_seller_blocked(self):
        with self.assertRaises(TransferRejected):
            self.sell(self.b, self.c, current_head(self.parcel))

    def test_unknown_buyer_and_self_sale_blocked(self):
        head = current_head(self.parcel)
        with self.assertRaises(TransferRejected):
            transfer_ownership(parcel_id=self.parcel.id, seller_id=self.a.id,
                               buyer_id="00000000-0000-0000-0000-000000000000",
                               expected_head=head, kind="sale", ref="",
                               effective_date=date(2024, 5, 1))
        with self.assertRaises(TransferRejected):
            self.sell(self.a, self.a, head)

    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValueError):
            transfer_ownership(parcel_id=self.parcel.id, seller_id=self.a.id,
                               buyer_id=self.b.id, expected_head=current_head(self.parcel),
                               kind="initial", ref="", effective_date=date(2024, 5, 1))

    def test_entries_are_immutable(self):
        entry = self.parcel.entries.first()
        entry.hash = "f" * 64
        with self.assertRaises(ImmutableRecordError):
            entry.save()
        with self.assertRaises(ImmutableRecordError):
            entry.delete()
        with self.assertRaises(ImmutableRecordError):
            OwnershipEntry.objects.all().update(seq=9)
        with self.assertRaises(ImmutableRecordError):
            OwnershipEntry.objects.all().delete()

    def test_duplicate_parcel_rejected(self):
        with self.assertRaises(ValidationError):
            create_parcel_with_owner(owner=self.a, effective_date=date(2021, 1, 1), **PARCEL)

    def test_zero_area_rejected(self):
        bad = dict(PARCEL, khatian_no="9999", area_decimal=Decimal("0"))
        with self.assertRaises(ValidationError):
            create_parcel_with_owner(owner=self.a, effective_date=date(2021, 1, 1), **bad)

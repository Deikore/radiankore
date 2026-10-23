"""Tests for mandate related catalogs."""

from enum import StrEnum

import pytest

from radiankore.catalogs import (
    MandateChannel,
    MandateeType,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
    MandateTime,
    MandatorType,
)


@pytest.mark.parametrize(
    ("member", "expected_value", "expected_label"),
    [
        (
            MandateOperationType.GENERAL_LIMITED_TIME,
            "431",
            "Mandato por documento General por Tiempo limitado",
        ),
        (
            MandateOperationType.GENERAL_UNLIMITED_TIME,
            "432",
            "Mandato por documento General por Tiempo Ilimitado",
        ),
        (
            MandateOperationType.LIMITED_LIMITED_TIME,
            "433",
            "Mandato por documento limitado por tiempo limitado",
        ),
        (
            MandateOperationType.LIMITED_UNLIMITED_TIME,
            "434",
            "Mandato por documento limitado por tiempo Ilimitado",
        ),
    ],
)
def test_mandate_operation_type(
    member: MandateOperationType,
    expected_value: str,
    expected_label: str,
) -> None:
    assert member.value == expected_value
    assert member.label == expected_label
    assert MandateOperationType.from_code(expected_value) is member
    assert MandateOperationType.from_code(None) is None
    assert MandateOperationType.from_code("999") is None


@pytest.mark.parametrize(
    ("member", "expected_value", "expected_label"),
    [
        (MandateNature.SPECIAL, "1", "Mandato por Poder Especial"),
        (MandateNature.GENERAL, "2", "Mandato por Poder General"),
    ],
)
def test_mandate_nature(
    member: MandateNature,
    expected_value: str,
    expected_label: str,
) -> None:
    assert member.value == expected_value
    assert member.label == expected_label


@pytest.mark.parametrize(
    ("member", "expected_value", "expected_label"),
    [
        (MandateTime.LIMITED, "1", "Tiempo limitado"),
        (MandateTime.UNLIMITED, "2", "Tiempo Ilimitado"),
    ],
)
def test_mandate_time(
    member: MandateTime,
    expected_value: str,
    expected_label: str,
) -> None:
    assert member.value == expected_value
    assert member.label == expected_label


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (MandatorType.INVOICE_ISSUER, "Mandante-FE"),
        (MandatorType.LEGITIMATE_HOLDER, "Mandante-LT"),
        (MandatorType.GUARANTOR, "Mandante-AV"),
        (MandatorType.ACQUIRER_DEBTOR, "Mandante-AD"),
    ],
)
def test_mandator_type(
    member: MandatorType,
    expected_value: str,
) -> None:
    assert member.value == expected_value


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (MandateeType.ELECTRONIC_NEGOTIATION_SYSTEM, "M-SN-e"),
        (MandateeType.FACTOR, "M-Factor"),
        (MandateeType.TECHNOLOGY_PROVIDER, "M-PT"),
        (MandateeType.INVOICE_ISSUER, "M-FE"),
    ],
)
def test_mandatee_type(
    member: MandateeType,
    expected_value: str,
) -> None:
    assert member.value == expected_value


@pytest.mark.parametrize(
    ("member", "expected_value"),
    [
        (MandateChannel.ELECTRONIC_NEGOTIATION_SYSTEM, "SNE"),
        (MandateChannel.TECHNOLOGY_PROVIDER, "PT"),
        (MandateChannel.FACTOR, "F"),
    ],
)
def test_mandate_channel(
    member: MandateChannel,
    expected_value: str,
) -> None:
    assert member.value == expected_value


@pytest.mark.parametrize(
    "member",
    [
        MandatePower.WITH_REPRESENTATION,
        MandatePower.GENERAL_DOCUMENT,
        MandatePower.ACKNOWLEDGEMENT,
        MandatePower.RADIAN_REGISTRATION,
        MandatePower.MANDATE,
        MandatePower.ECONOMIC_RIGHTS_TRANSFER_PAYMENT,
    ],
)
def test_mandate_power_labels(member: MandatePower) -> None:
    assert member.value.startswith(("MR91", "ALL17", "R"))
    assert member.label


@pytest.mark.parametrize(
    "catalog",
    [
        MandateOperationType,
        MandateNature,
        MandateTime,
        MandatorType,
        MandateeType,
        MandateChannel,
        MandatePower,
        MandateReferenceType,
    ],
)
def test_catalog_resolution_and_labels(catalog: type[StrEnum]) -> None:
    for member in catalog:
        assert catalog.from_code(member.value) is member  # type: ignore[attr-defined]
        assert member.label
    for code in (None, "", "unknown", " 1 "):
        assert catalog.from_code(code) is None  # type: ignore[attr-defined]

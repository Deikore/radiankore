"""Input constraints for mandate preparation, using synthetic identities."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime

import pytest

from radiankore.catalogs import (
    DocumentType,
    EventType,
    MandateChannel,
    MandateeType,
    MandateNature,
    MandateOperationType,
    MandatePower,
    MandateReferenceType,
)
from radiankore.models.events import (
    MandateAttachedDocument,
    MandateDocumentReference,
    MandateEvent,
    MandateScope,
    MandateValidityPeriod,
    RadianSoftware,
)


@pytest.mark.parametrize(
    "changes",
    [
        {"acceptance": False},
        {"acceptance": 1},
        {"notes": ()},
        {"notes": (" ",)},
        {"event_number": ""},
        {"document_references": ()},
        {"reference_type": MandateReferenceType.ALL},
        {"reference_type": MandateReferenceType.MULTIPLE},
        {"validity_period": MandateValidityPeriod()},
        {"operation_type": MandateOperationType.GENERAL_UNLIMITED_TIME},
        {"nature": MandateNature.GENERAL},
    ],
)
def test_reject_inconsistent_event(
    mandate_event: MandateEvent, changes: dict[str, object]
) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(mandate_event, **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "field",
    [
        "operation_type",
        "nature",
        "reference_type",
        "scope",
        "validity_period",
        "attached_contract",
        "sender_party",
        "mandatee_party",
        "issue_date",
        "issue_time",
        "effective_date",
    ],
)
def test_reject_wrong_event_types(mandate_event: MandateEvent, field: str) -> None:
    with pytest.raises(TypeError):
        replace(mandate_event, **{field: "wrong"})  # type: ignore[arg-type]


def test_role_and_representative_validation(mandate_event: MandateEvent) -> None:
    with pytest.raises(ValueError, match="MandatorType"):
        replace(mandate_event, sender_party=mandate_event.mandatee_party)
    with pytest.raises(ValueError, match="MandateeType"):
        replace(mandate_event, mandatee_party=mandate_event.sender_party)
    with pytest.raises(TypeError):
        replace(mandate_event.sender_party, representative=None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(mandate_event.sender_party, role="Mandante-FE")  # type: ignore[arg-type]
    with pytest.raises(FrozenInstanceError):
        mandate_event.event_number = "changed"  # type: ignore[misc]


@pytest.mark.parametrize("power", list(MandatePower))
@pytest.mark.parametrize("channel", list(MandateChannel))
def test_power_channel_matrix(power: MandatePower, channel: MandateChannel) -> None:
    forbidden = power.value in {"R01", "R02", "R03", "R04", "R05"} and (
        channel is MandateChannel.TECHNOLOGY_PROVIDER
    )
    if forbidden:
        with pytest.raises(ValueError, match="PT"):
            MandateScope(powers=((power, channel),))
    else:
        scope = MandateScope(powers=((power, channel),))
        assert scope.description == power.label


@pytest.mark.parametrize(
    "powers",
    [(), (("ALL17", "SNE"),), ("ALL17",), ((MandatePower.GENERAL_DOCUMENT, "SNE"),)],
)
def test_scope_rejects_invalid_types(powers: tuple[object, ...]) -> None:
    with pytest.raises((TypeError, ValueError)):
        MandateScope(powers=powers)  # type: ignore[arg-type]


def test_identity_constraints(mandate_event: MandateEvent) -> None:
    party = mandate_event.sender_party
    for changes in (
        {"verification_digit": None},
        {"verification_digit": "11"},
        {"tax_number": "900000001-1"},
        {"name": " "},
        {"identification_type": "31"},
    ):
        with pytest.raises((TypeError, ValueError)):
            replace(party, **changes)
    person = party.representative
    with pytest.raises(ValueError):
        replace(person, verification_digit="1")
    with pytest.raises(ValueError):
        replace(person, first_name=" ")
    with pytest.raises(TypeError):
        replace(party, representative="person")  # type: ignore[arg-type]


def test_reference_constraints() -> None:
    with pytest.raises(ValueError):
        MandateDocumentReference(document_number="1", uuid="bad")
    with pytest.raises(ValueError):
        MandateDocumentReference(
            document_number="1", uuid="a" * 96, document_type=DocumentType.CREDIT_NOTE
        )
    with pytest.raises(TypeError):
        MandateDocumentReference(document_number="1", uuid="a" * 96, document_type="01")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        MandateDocumentReference(document_number="1", uuid="a" * 96, scope="bad")  # type: ignore[arg-type]


def test_period_dates_are_native_and_ordered() -> None:
    with pytest.raises(ValueError):
        MandateValidityPeriod(start_date=date(2026, 1, 1))
    with pytest.raises(ValueError):
        MandateValidityPeriod(start_date=date(2026, 2, 1), end_date=date(2026, 1, 1))
    with pytest.raises(TypeError):
        MandateValidityPeriod(
            start_date=datetime(2026, 1, 1), end_date=date(2026, 1, 1)
        )


def test_pdf_evidence_and_sensitive_reprs(
    radian_software: RadianSoftware, mandate_event: MandateEvent
) -> None:
    with pytest.raises(ValueError):
        MandateAttachedDocument(document_id="1", embedded_bytes=b"not PDF")
    assert "synthetic-pin" not in repr(radian_software)
    assert "Synthetic contract" not in repr(mandate_event.attached_contract)
    with pytest.raises(ValueError):
        replace(radian_software, signer_role="third party")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        replace(radian_software, pin=" ")
    assert MandateeType.ELECTRONIC_NEGOTIATION_SYSTEM.value == "M-SN-e"


def test_reference_limits_and_scope_rules(mandate_event: MandateEvent) -> None:
    ref = mandate_event.document_references[0]
    assert (
        len(
            replace(
                mandate_event,
                reference_type=MandateReferenceType.MULTIPLE,
                document_references=(ref,) * 20,
            ).document_references
        )
        == 20
    )
    with pytest.raises(ValueError, match="Reference count"):
        replace(
            mandate_event,
            reference_type=MandateReferenceType.MULTIPLE,
            document_references=(ref,) * 21,
        )
    with pytest.raises(TypeError):
        replace(mandate_event, document_references=("bad",))  # type: ignore[arg-type]
    limited = MandateScope(
        powers=(
            (MandatePower.WITH_REPRESENTATION, MandateChannel.FACTOR),
            (MandatePower.GUARANTEE, MandateChannel.FACTOR),
        )
    )
    with pytest.raises(ValueError, match="ALL17"):
        replace(mandate_event, scope=limited)
    with pytest.raises(ValueError, match="MR91"):
        replace(mandate_event, operation_type=MandateOperationType.LIMITED_LIMITED_TIME)
    with pytest.raises(ValueError, match="Per-invoice"):
        replace(
            mandate_event,
            document_references=(replace(ref, scope=mandate_event.scope),),
        )
    override = replace(
        mandate_event,
        operation_type=MandateOperationType.LIMITED_LIMITED_TIME,
        scope=limited,
        document_references=(replace(ref, scope=limited),),
    )
    assert override.document_references[0].scope is limited
    with pytest.raises(TypeError):
        replace(mandate_event, attached_validity_note="bad")  # type: ignore[arg-type]


def test_general_evidence_requirements(mandate_event: MandateEvent) -> None:
    contract = mandate_event.attached_contract
    note = replace(contract, document_id="VALIDITY")
    with pytest.raises(ValueError, match="public deed date"):
        replace(
            mandate_event, nature=MandateNature.GENERAL, attached_validity_note=note
        )
    contract = replace(contract, effective_date=date(2026, 10, 21))
    with pytest.raises(ValueError, match="notary"):
        replace(
            mandate_event,
            nature=MandateNature.GENERAL,
            attached_contract=contract,
            attached_validity_note=note,
        )
    with pytest.raises(ValueError, match="Special powers"):
        replace(mandate_event, attached_validity_note=note)
    with pytest.raises(TypeError):
        replace(contract, embedded_bytes="PDF")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(contract, issuer="notary")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(contract, effective_date="2026-10-21")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(mandate_event, event_number=123)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        replace(mandate_event, scope=MandateScope(powers=[]))  # type: ignore[arg-type]


def test_prepared_artifact_requires_immutable_bytes() -> None:
    from radiankore import Environment
    from radiankore.models.events import PreparedRadianEvent

    prepared = PreparedRadianEvent(
        code=EventType.MANDATE,
        event_number="1",
        cude="a" * 96,
        environment=Environment.PRODUCTION,
        xml_bytes=b"xml",
        zip_bytes=b"zip",
    )
    invalid_types: tuple[dict[str, object], ...] = (
        {"xml_bytes": bytearray(b"xml")},
        {"environment": "production"},
        {"zip_bytes": None},
    )
    for changes in invalid_types:
        with pytest.raises(TypeError):
            replace(prepared, **changes)  # type: ignore[arg-type]
    invalid_values: tuple[dict[str, object], ...] = (
        {"xml_bytes": b""},
        {"cude": "bad"},
    )
    for changes in invalid_values:
        with pytest.raises(ValueError):
            replace(prepared, **changes)  # type: ignore[arg-type]

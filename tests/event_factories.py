"""Synthetic RADIAN input builders, grouped by event family."""

from collections.abc import Callable
from datetime import date, time

from radiankore.catalogs import IdentificationType, OrganizationType
from radiankore.models.events import RadianEvent


def radian_event_factory() -> Callable[[str], RadianEvent]:
    """Create every operation and blank variant using entirely synthetic inputs."""
    from dataclasses import replace
    from decimal import Decimal

    from radiankore.catalogs import (
        EndorsementForm,
        FactorType,
        PaymentMeans,
        PaymentRestriction,
        RadianOperationType,
    )
    from radiankore.models.events import (
        CirculationRestrictionEvent,
        CirculationRestrictionTerminationEvent,
        EconomicRightsNotificationEvent,
        EconomicRightsPaymentEvent,
        EconomicRightsTransferEvent,
        EconomicRightsTransferTerms,
        EndorsementCancellationEvent,
        EndorsementEvent,
        GuaranteeCommitment,
        GuaranteeEvent,
        InvoicePaymentEvent,
        MandateTerminationEvent,
        NegotiationTerms,
        PaymentReportEvent,
        ProtestAct,
        ProtestEvent,
        ProtestNotary,
        RadianEventHeader,
        RadianEventReference,
        RadianInvoiceReference,
        RadianParticipation,
        RadianParty,
        RadianPdfAttachment,
        RadianPerson,
        RadianRegistrationEvent,
        RegistrationPaymentState,
    )

    party = RadianParty(
        name="Synthetic Holder",
        tax_number="900000001",
        identification_type=IdentificationType.NIT,
        verification_digit="1",
        organization_type=OrganizationType.LEGAL_PERSON,
    )
    buyer = replace(
        party, name="Synthetic Buyer", tax_number="900000002", verification_digit="2"
    )
    debtor = replace(
        party, name="Synthetic Debtor", tax_number="900000003", verification_digit="3"
    )
    header = RadianEventHeader(
        event_number="RADIAN-TEST-1",
        issue_date=date(2026, 10, 22),
        issue_time=time(10, 30),
        notes=(
            "Declaración sintética; no constituye un acto mercantil real.",
            "Nota repetida",
            "Nota repetida",
        ),
    )
    reference = RadianInvoiceReference(
        document_number="FE-TEST-1", uuid="a" * 96, due_date=date(2026, 12, 31)
    )
    person = RadianPerson(
        identification_number="100000004",
        identification_type=IdentificationType.CITIZENSHIP_CARD,
        first_name="Synthetic",
        family_name="Representative",
    )
    endorsers = (
        RadianParticipation(party=party, amount=Decimal("60000.00")),
        RadianParticipation(
            party=replace(party, tax_number="900000004", verification_digit="4"),
            amount=Decimal("40000.00"),
        ),
    )
    endorsees = (
        RadianParticipation(
            party=buyer, amount=Decimal("55000.00"), factor_type=FactorType.FACTORING
        ),
        RadianParticipation(
            party=replace(buyer, tax_number="900000005", verification_digit="5"),
            amount=Decimal("45000.00"),
        ),
    )

    def _guarantee(op: RadianOperationType) -> RadianEvent:
        return GuaranteeEvent(
            header=header,
            reference=reference,
            title_value=Decimal("100000.00"),
            guarantors=(GuaranteeCommitment(party=party, amount=Decimal("0.00")),),
        )

    def _rights_transfer(op: RadianOperationType) -> RadianEvent:
        return EconomicRightsTransferEvent(
            header=header,
            operation_type=op,
            reference=reference,
            transferors=endorsers,
            transferees=endorsees,
            debtors=(debtor,),
            terms=EconomicRightsTransferTerms(
                transferred_value=Decimal("100000.00"),
                price=Decimal("95000.00"),
                discount_factor=Decimal("5"),
                payment_means=PaymentMeans.CASH,
            ),
        )

    def _rights_notification(op: RadianOperationType) -> RadianEvent:
        return EconomicRightsNotificationEvent(
            header=header,
            sender_party=party,
            receiver_party=debtor,
            reference=reference,
            current_value=Decimal("100000.00"),
        )

    def _rights_payment(op: RadianOperationType) -> RadianEvent:
        return EconomicRightsPaymentEvent(
            header=header,
            operation_type=op,
            reference=reference,
            payer=RadianParticipation(
                party=debtor,
                amount=Decimal("50000.00")
                if op.value == "511"
                else Decimal("100000.00"),
            ),
            restriction=PaymentRestriction.UNRESTRICTED,
            effective_date=date(2026, 10, 21),
            current_value=Decimal("100000.00"),
            remaining_value=Decimal("50000.00")
            if op.value == "511"
            else Decimal("0.00"),
        )

    def _restriction(op: RadianOperationType) -> RadianEvent:
        code = op.event_type.value
        evidence = RadianPdfAttachment(
            filename="Mandamiento de pago emitido por un Juez PDF",
            content_bytes=b"%PDF-1.7\nSynthetic authority evidence.\n%%EOF",
        )
        if code == "041":
            return CirculationRestrictionEvent(
                header=header,
                operation_type=op,
                reference=reference,
                authorities=(party, buyer),
                officials=(debtor, debtor),
                attachment=evidence,
                measure_value=Decimal("200000.00"),
            )
        return CirculationRestrictionTerminationEvent(
            header=header,
            operation_type=op,
            reference=RadianEventReference(
                document_number="RESTRICTION-1", uuid="d" * 96
            ),
            authorities=(party, buyer),
            officials=(debtor, debtor),
            attachment=evidence,
            debt_value=Decimal("200000.00"),
            restriction_value=Decimal("100000.00"),
        )

    def _protest(op: RadianOperationType) -> RadianEvent:
        from radiankore.catalogs import AcceptanceFailureType

        return ProtestEvent(
            header=header,
            operation_type=op,
            sender_party=party,
            receiver_party=debtor,
            reference=reference,
            title_value=Decimal("100000.00"),
            act=ProtestAct(
                notary_number="5",
                effective_date=date(2026, 10, 21),
                notaries=(
                    ProtestNotary(
                        first_name="Synthetic",
                        family_name="Notary",
                        job_title="Notario",
                    ),
                ),
                attachment=RadianPdfAttachment(
                    filename="Acta de protesto, PDF",
                    content_bytes=b"%PDF-1.7\nSynthetic protest act.\n%%EOF",
                ),
            ),
            acceptance_failure=AcceptanceFailureType.PARTIAL
            if op.value == "481"
            else None,
            accepted_value=Decimal("40000.00") if op.value == "481" else None,
            pending_value=Decimal("60000.00") if op.value == "481" else None,
        )

    def _mandate_termination(op: RadianOperationType) -> RadianEvent:
        return MandateTerminationEvent(
            header=header,
            operation_type=op,
            sender_party=party,
            representatives=(person,),
            reference=RadianEventReference(
                document_number="MANDATE-TEST-1", uuid="b" * 96
            ),
        )

    def _registration(op: RadianOperationType) -> RadianEvent:
        return RadianRegistrationEvent(
            header=header,
            operation_type=op,
            sender_party=party,
            reference=reference,
            payment_state=RegistrationPaymentState(
                invoice_value=Decimal("100000.00"),
                paid_value=Decimal("25000.00"),
                remaining_value=Decimal("75000.00"),
            ),
            direct_buyer=buyer if op.value in ("362", "364") else None,
        )

    def _invoice_payment(op: RadianOperationType) -> RadianEvent:
        return InvoicePaymentEvent(
            header=header,
            operation_type=op,
            reference=reference,
            payers=endorsers,
            restriction=PaymentRestriction.UNRESTRICTED,
            effective_date=date(2026, 10, 21),
            current_value=Decimal("1000000.00"),
            remaining_value=Decimal("500000.00")
            if op.value == "451"
            else Decimal("0.00"),
        )

    def _payment_report(op: RadianOperationType) -> RadianEvent:
        return PaymentReportEvent(
            header=header,
            sender_party=party,
            receiver_party=debtor,
            reference=reference,
            title_value=Decimal("100000.00"),
        )

    def _endorsement_cancellation(op: RadianOperationType) -> RadianEvent:
        return EndorsementCancellationEvent(
            header=header,
            operation_type=op,
            sender_party=party,
            receiver_party=buyer,
            reference=RadianEventReference(
                document_number="ENDORSEMENT-1", uuid="c" * 96
            ),
        )

    def _endorsement(variant: str, op: RadianOperationType) -> RadianEvent:
        code = op.event_type.value
        blank = variant.endswith("-blank")
        sale = code in ("037", "047")
        terms = NegotiationTerms(
            total_value=Decimal("100000.00"),
            price=Decimal("95000.00") if sale else None,
            discount_rate=Decimal("5") if sale else None,
            payment_means=PaymentMeans.CASH if sale else None,
        )
        return EndorsementEvent(
            header=header,
            operation_type=op,
            reference=replace(reference, due_date=date(2026, 10, 21))
            if code == "047"
            else reference,
            form=EndorsementForm.BLANK if blank else EndorsementForm.COMPLETE,
            endorsers=tuple(replace(p, party=None) for p in endorsers)
            if blank
            else endorsers,
            endorsees=endorsees,
            negotiation=terms,
            debtors=(debtor,),
        )

    def make(variant: str) -> RadianEvent:
        op = RadianOperationType(variant.removesuffix("-blank"))
        code = op.event_type.value
        if variant.endswith("-blank") and op.value not in ("371", "372", "038", "039"):
            raise ValueError(
                "Blank fixture is only defined for endorsement operations."
            )
        if code == "035":
            return _guarantee(op)
        if code == "049":
            return _rights_transfer(op)
        if code == "050":
            return _rights_notification(op)
        if code == "051":
            return _rights_payment(op)
        if code in ("041", "042"):
            return _restriction(op)
        if code == "048":
            return _protest(op)
        if code == "044":
            return _mandate_termination(op)
        if code == "036":
            return _registration(op)
        if code == "045":
            return _invoice_payment(op)
        if code == "046":
            return _payment_report(op)
        if code == "040":
            return _endorsement_cancellation(op)
        if code in ("037", "038", "039", "047"):
            return _endorsement(variant, op)
        raise ValueError(f"Unsupported RADIAN fixture variant: {variant}")

    return make

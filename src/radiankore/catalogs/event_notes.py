"""Declaration purposes from FE 1.9 and RADIAN 1.1, independent of event codes."""

from enum import StrEnum, unique

__all__ = ["EventNoteKind"]


@unique
class EventNoteKind(StrEnum):
    """Classify caller declarations without interpreting their legal truth."""

    ADDITIONAL = "additional"
    MANDATE_REPRESENTATION = "mandate_representation"
    ACTING_CAPACITY = "acting_capacity"
    TACIT_ACCEPTANCE_DIRECT = "tacit_acceptance_direct"
    TACIT_ACCEPTANCE_LEGAL_MANDATE = "tacit_acceptance_legal_mandate"
    TACIT_ACCEPTANCE_NATURAL_MANDATE = "tacit_acceptance_natural_mandate"
    GUARANTEE_NATURAL_PERSON = "guarantee_natural_person"
    GUARANTEE_LEGAL_PERSON = "guarantee_legal_person"
    SPECIAL_PAYMENT_TERMS = "special_payment_terms"
    WITHOUT_RECOURSE = "without_recourse"
    GUARANTEE_ENDORSEMENT = "guarantee_endorsement"
    COLLECTION_ENDORSEMENT = "collection_endorsement"
    COLLECTION_REVOCATION = "collection_revocation"
    MANDATE_NATURAL_PERSON = "mandate_natural_person"
    MANDATE_LEGAL_PERSON = "mandate_legal_person"
    MANDATE_TERMINATION = "mandate_termination"
    MANDATE_RATIFICATION = "mandate_ratification"
    MANDATE_NO_PENDING_ACTS = "mandate_no_pending_acts"
    PROTEST = "protest"
    ECONOMIC_RIGHTS_TRANSFER = "economic_rights_transfer"

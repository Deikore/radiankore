"""Supported DIAN deployment environments."""

from enum import StrEnum


class Environment(StrEnum):
    """Select production by default or explicitly opt into habilitation."""

    PRODUCTION = "production"
    HABILITATION = "habilitation"

    @property
    def endpoint(self) -> str:
        """Return the HTTP service endpoint, without the WSDL query string."""
        host = "vpfe" if self is Environment.PRODUCTION else "vpfe-hab"
        return f"https://{host}.dian.gov.co/WcfDianCustomerServices.svc"

    @property
    def addressing_to(self) -> str:
        """Return the WS-Addressing destination used by the verified SOAP profile."""
        return f"{self.endpoint}?WSDL"

    @property
    def profile_execution_id(self) -> str:
        """Return the DIAN environment code used in UBL documents."""
        return "1" if self is Environment.PRODUCTION else "2"

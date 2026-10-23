"""Execute the real emission guides against synthetic certificates and MockTransport."""

import re
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any, cast, get_args
from unittest.mock import patch

import httpx
import pytest
from lxml import etree

from radiankore import DianClient, DigitalCertificate, Environment
from radiankore._soap import transport
from radiankore._soap.namespaces import WCF, XSI
from radiankore.models.events import (
    PreparedRadianEvent,
    RadianEvent,
    RadianSoftware,
)


def python_blocks(path: Path) -> list[str]:
    """Read the Python code actually published, without duplicating its examples."""
    return re.findall(r"```python\n(.*?)```", path.read_text(), re.DOTALL)


def example_events(value: object) -> Iterator[RadianEvent]:
    """Find named event alternatives, including the invoice guide's event mapping."""
    if isinstance(value, get_args(RadianEvent.__value__)):
        yield cast(RadianEvent, value)
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from example_events(child)


@pytest.mark.parametrize(
    "guide,expected_codes",
    [
        ("radian-termination", {"044"}),
        ("radian-registration", {"036"}),
        ("radian-payments", {"045", "046"}),
        ("radian-endorsements", {"037", "038", "039", "040", "047"}),
        ("radian-guarantees", {"035"}),
        ("radian-economic-rights", {"049", "050", "051"}),
        ("radian-restrictions", {"041", "042"}),
        ("radian-protests", {"048"}),
        ("invoice-emission", {"030", "031", "032", "033", "034"}),
        ("mandate", {"043"}),
    ],
)
def test_emission_guides_execute_with_verified_signatures(
    guide: str,
    expected_codes: set[str],
    encrypted_pfx_path: Path,
    digital_certificate: DigitalCertificate,
    verify_event_signature: Callable[[bytes, DigitalCertificate], None],
    radian_schema: etree.XMLSchema | None,
    wrap_soap: Callable[[etree._Element], bytes],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    docs = Path(__file__).resolve().parents[1] / "docs/operations"
    if not (docs / f"{guide}.md").is_file():
        pytest.skip("Documentation examples are excluded from distributions.")
    response = etree.Element(f"{{{WCF}}}SendEventUpdateStatusResponse")
    etree.SubElement(response, f"{{{WCF}}}SendEventUpdateStatusResult").set(
        f"{{{XSI}}}nil", "true"
    )
    payload = wrap_soap(response)
    connections: list[httpx.Client] = []
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, content=payload)

    def http_client(timeout: float) -> httpx.Client:
        connection = httpx.Client(
            transport=httpx.MockTransport(handler), timeout=timeout
        )
        connections.append(connection)
        return connection

    monkeypatch.setattr(transport, "create_http_client", http_client)
    client = DianClient(
        encrypted_pfx_path,
        password="test-password",
        environment=Environment.HABILITATION,
    )
    # The mandate guide explicitly loads its example PDF before local preparation.
    (tmp_path / "contrato.pdf").write_bytes(b"%PDF-1.7\nSynthetic contract.\n%%EOF")
    monkeypatch.chdir(tmp_path)
    namespace: dict[str, Any] = {}
    seen: set[int] = set()
    held: list[RadianEvent] = []
    codes: set[str] = set()
    prepared: PreparedRadianEvent
    blocks = python_blocks(docs / f"{guide}.md")
    if guide.startswith("radian-"):
        blocks.insert(0, python_blocks(docs / "radian-emission.md")[0])
    with patch("radiankore.DianClient", return_value=client):
        for number, block in enumerate(blocks):
            exec(compile(block, f"{guide}.md:block-{number}", "exec"), namespace)
            software = namespace["software"]
            assert isinstance(software, RadianSoftware)
            for name, value in list(namespace.items()):
                if name.startswith("__"):
                    continue
                for event in example_events(value):
                    if id(event) in seen:
                        continue
                    seen.add(id(event))
                    held.append(event)
                    prepared = client.prepare_radian_event(
                        event=event, software=software
                    )
                    codes.add(prepared.code.value)
                    verify_event_signature(prepared.xml_bytes, digital_certificate)
                    if radian_schema is not None:
                        radian_schema.assertValid(etree.fromstring(prepared.xml_bytes))
    assert codes == expected_codes
    assert held
    assert all(connection.is_closed for connection in connections)
    if guide in {"mandate", "invoice-emission"}:
        assert len(requests) == 1
    else:
        assert not requests

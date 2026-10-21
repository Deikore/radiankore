"""Read the SOAP response and its Base64-encoded download URL."""

import csv
from io import BytesIO, StringIO
from urllib.parse import urlsplit
from zipfile import BadZipFile, ZipFile
from zlib import error as ZlibError

import httpx

from radiankore._soap.namespaces import EXCHANGE_EMAIL_RESPONSE
from radiankore._soap.parsing import (
    decode_base64_text,
    element_text,
    read_boolean,
    soap_result,
)
from radiankore.exceptions import DianResponseError
from radiankore.models.responses import ExchangeEmailsResult


def _download_url(value: str | None) -> str | None:
    if value is None:
        return None
    data = decode_base64_text(value, field_name="CsvBase64Bytes")
    try:
        url = data.decode("utf-8").strip()
        if not url:
            return None
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or "#" in url
            or any(character.isspace() or ord(character) < 32 for character in url)
        ):
            raise ValueError(
                "Expected an absolute HTTPS URL without credentials or fragment."
            )
        # Accessing port validates its syntax and range without rewriting signed URLs.
        _ = parts.port
        httpx.URL(url)
        return url
    except (UnicodeError, ValueError, httpx.InvalidURL) as exc:
        raise DianResponseError("Invalid download URL in GetExchangeEmails.") from exc


def parse_exchange_emails_response(data: bytes) -> ExchangeEmailsResult | None:
    """Decode the URL without performing HTTP or interpreting business statuses."""
    result = soap_result(data, "GetExchangeEmails")
    if result is None:
        return None
    return ExchangeEmailsResult(
        success=read_boolean(
            result, EXCHANGE_EMAIL_RESPONSE, "Success", operation="GetExchangeEmails"
        ),
        status_code=element_text(result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}StatusCode"),
        message=element_text(result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}Message"),
        download_url=_download_url(
            element_text(result, f"{{{EXCHANGE_EMAIL_RESPONSE}}}CsvBase64Bytes")
        ),
    )


def extract_exchange_emails_csv(data: bytes) -> bytes:
    """Read the single CSV member in memory without interpreting its encoding."""
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = [
                entry
                for entry in archive.infolist()
                if not entry.is_dir() and entry.filename.lower().endswith(".csv")
            ]
            if len(entries) != 1:
                raise ValueError("Expected exactly one CSV member in the archive.")
            return archive.read(entries[0])
    except (
        BadZipFile,
        RuntimeError,
        NotImplementedError,
        OSError,
        EOFError,
        ValueError,
        ZlibError,
    ) as exc:
        raise DianResponseError("Invalid CSV archive in GetExchangeEmails.") from exc


def parse_exchange_emails_csv(data: bytes) -> tuple[dict[str, str], ...]:
    """Read UTF-8 CSV records with native csv, preserving all values as text."""
    try:
        text = extract_exchange_emails_csv(data).decode("utf-8-sig")
        try:
            dialect = csv.Sniffer().sniff(text[:65536], delimiters=",;|\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(
            StringIO(text, newline=""), dialect=dialect, strict=True
        )
        headers = reader.fieldnames
        if headers is None:
            return ()
        if not headers or any(not header.strip() for header in headers):
            raise ValueError("CSV headers must not be empty.")
        if len(set(headers)) != len(headers):
            raise ValueError("CSV headers must be unique.")
        rows: list[dict[str, str]] = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("CSV rows must match the header column count.")
            rows.append({header: row[header] for header in headers})
        return tuple(rows)
    except (UnicodeError, csv.Error, ValueError) as exc:
        raise DianResponseError("Invalid CSV content in GetExchangeEmails.") from exc

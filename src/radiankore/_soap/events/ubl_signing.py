"""XAdES-EPES UBL signature, calculated by xmlsec on the final tree."""

from base64 import b64encode
from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import xmlsec
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding
from lxml import etree

from radiankore._soap.namespaces import DS, EXT, XADES
from radiankore._soap.signing import certificate_key
from radiankore.certificate import DigitalCertificate
from radiankore.exceptions import DianSignatureError

_DIAN_SIGNATURE_POLICY_URL = (
    "https://facturaelectronica.dian.gov.co/politicadefirma/v2/politicadefirmav2.pdf"
)
_DIAN_SIGNATURE_POLICY_HASH = "dMoMvtcG5aIzgYo0tIsSQeVJBDnUnfSOfBpxXrmor0Y="


def _iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_key_info(
    certificate: DigitalCertificate, key_info_id: str
) -> etree._Element:
    key_info = etree.Element(f"{{{DS}}}KeyInfo", Id=key_info_id)
    x509_data = etree.SubElement(key_info, f"{{{DS}}}X509Data")
    cert_der = certificate.certificate.public_bytes(Encoding.DER)
    cert_b64 = b64encode(cert_der).decode("ascii")
    x509_cert = etree.SubElement(x509_data, f"{{{DS}}}X509Certificate")
    x509_cert.text = cert_b64

    for additional in certificate.additional_certificates:
        etree.SubElement(x509_data, f"{{{DS}}}X509Certificate").text = b64encode(
            additional.public_bytes(Encoding.DER)
        ).decode("ascii")

    public_key = certificate.certificate.public_key()
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise DianSignatureError("DIAN UBL signing requires an RSA public key.")
    public_numbers = public_key.public_numbers()
    key_value = etree.SubElement(key_info, f"{{{DS}}}KeyValue")
    rsa_key_value = etree.SubElement(key_value, f"{{{DS}}}RSAKeyValue")
    modulus = etree.SubElement(rsa_key_value, f"{{{DS}}}Modulus")
    modulus.text = b64encode(
        public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
    ).decode("ascii")
    exponent = etree.SubElement(rsa_key_value, f"{{{DS}}}Exponent")
    exponent.text = b64encode(
        public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")
    ).decode("ascii")
    return key_info


def _build_xades_object(
    certificate: DigitalCertificate,
    signature_id: str,
    object_id: str,
    signed_props_id: str,
    reference_id: str,
    signer_role: str,
    signing_time: datetime | None = None,
) -> etree._Element:
    obj = etree.Element(f"{{{DS}}}Object", Id=object_id)
    qualifying = etree.SubElement(
        obj,
        f"{{{XADES}}}QualifyingProperties",
        Target=f"#{signature_id}",
    )
    signed_props = etree.SubElement(
        qualifying,
        f"{{{XADES}}}SignedProperties",
        Id=signed_props_id,
    )
    sig_props = etree.SubElement(signed_props, f"{{{XADES}}}SignedSignatureProperties")
    etree.SubElement(sig_props, f"{{{XADES}}}SigningTime").text = (
        _iso_now()
        if signing_time is None
        else signing_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    signing_cert = etree.SubElement(sig_props, f"{{{XADES}}}SigningCertificate")
    cert_node = etree.SubElement(signing_cert, f"{{{XADES}}}Cert")
    cert_digest = etree.SubElement(cert_node, f"{{{XADES}}}CertDigest")
    etree.SubElement(
        cert_digest,
        f"{{{DS}}}DigestMethod",
        Algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
    )
    cert_der = certificate.certificate.public_bytes(Encoding.DER)
    etree.SubElement(cert_digest, f"{{{DS}}}DigestValue").text = b64encode(
        sha256(cert_der).digest()
    ).decode("ascii")
    issuer_serial = etree.SubElement(cert_node, f"{{{XADES}}}IssuerSerial")
    etree.SubElement(
        issuer_serial, f"{{{DS}}}X509IssuerName"
    ).text = certificate.certificate.issuer.rfc4514_string()
    etree.SubElement(issuer_serial, f"{{{DS}}}X509SerialNumber").text = str(
        certificate.certificate.serial_number
    )

    policy_id = etree.SubElement(sig_props, f"{{{XADES}}}SignaturePolicyIdentifier")
    policy_id_inner = etree.SubElement(policy_id, f"{{{XADES}}}SignaturePolicyId")
    sig_policy_id = etree.SubElement(policy_id_inner, f"{{{XADES}}}SigPolicyId")
    etree.SubElement(
        sig_policy_id, f"{{{XADES}}}Identifier"
    ).text = _DIAN_SIGNATURE_POLICY_URL
    etree.SubElement(
        sig_policy_id, f"{{{XADES}}}Description"
    ).text = "Política de firma para facturas electrónicas de la República de Colombia."
    sig_policy_hash = etree.SubElement(policy_id_inner, f"{{{XADES}}}SigPolicyHash")
    etree.SubElement(
        sig_policy_hash,
        f"{{{DS}}}DigestMethod",
        Algorithm="http://www.w3.org/2001/04/xmlenc#sha256",
    )
    etree.SubElement(
        sig_policy_hash, f"{{{DS}}}DigestValue"
    ).text = _DIAN_SIGNATURE_POLICY_HASH

    role_node = etree.SubElement(sig_props, f"{{{XADES}}}SignerRole")
    claimed_roles = etree.SubElement(role_node, f"{{{XADES}}}ClaimedRoles")
    etree.SubElement(claimed_roles, f"{{{XADES}}}ClaimedRole").text = signer_role

    data_obj_props = etree.SubElement(
        signed_props, f"{{{XADES}}}SignedDataObjectProperties"
    )
    data_format = etree.SubElement(
        data_obj_props,
        f"{{{XADES}}}DataObjectFormat",
        ObjectReference=f"#{reference_id}",
    )
    etree.SubElement(data_format, f"{{{XADES}}}MimeType").text = "text/xml"
    etree.SubElement(data_format, f"{{{XADES}}}Encoding").text = "UTF-8"

    return obj


def sign_application_response(
    application_response: etree._Element,
    certificate: DigitalCertificate,
    *,
    signer_role: str,
    signing_time: datetime | None = None,
) -> None:
    """Sign the final tree once; do not format or mutate the signed output."""
    if signer_role not in ("supplier", "thirdparty"):
        raise ValueError("Invalid DIAN signer role.")
    if not isinstance(certificate.private_key, rsa.RSAPrivateKey):
        raise DianSignatureError("DIAN UBL signing requires an RSA private key.")
    extensions = application_response.find(f"{{{EXT}}}UBLExtensions")
    if (
        extensions is None
        or application_response.find(f".//{{{DS}}}Signature") is not None
    ):
        raise DianSignatureError("Expected an unsigned UBL document with extensions.")
    try:
        sid = f"Signature-{uuid4().hex}"
        kid, pid, rid = f"{sid}-KeyInfo", f"{sid}-SignedProperties", f"{sid}-Reference"
        signature = xmlsec.template.create(
            application_response,
            xmlsec.constants.TransformInclC14N,
            xmlsec.constants.TransformRsaSha256,
            id=sid,
            ns="ds",
        )
        document_ref = xmlsec.template.add_reference(
            signature, xmlsec.constants.TransformSha256, id=rid, uri=""
        )
        xmlsec.template.add_transform(document_ref, xmlsec.constants.TransformEnveloped)
        xmlsec.template.add_transform(document_ref, xmlsec.constants.TransformInclC14N)
        xmlsec.template.add_reference(
            signature, xmlsec.constants.TransformSha256, uri=f"#{kid}"
        )
        xmlsec.template.add_reference(
            signature,
            xmlsec.constants.TransformSha256,
            uri=f"#{pid}",
            type="http://uri.etsi.org/01903#SignedProperties",
        )
        signature.append(_build_key_info(certificate, kid))
        signature.append(
            _build_xades_object(
                certificate, sid, f"{sid}-Object", pid, rid, signer_role, signing_time
            )
        )
        content = etree.SubElement(
            etree.SubElement(extensions, f"{{{EXT}}}UBLExtension"),
            f"{{{EXT}}}ExtensionContent",
        )
        content.append(signature)
        xmlsec.tree.add_ids(application_response, ["Id"])
        context = xmlsec.SignatureContext()
        context.key = certificate_key(certificate)
        context.sign(signature)
    except xmlsec.Error as exc:
        raise DianSignatureError(
            "Unable to sign the UBL ApplicationResponse document."
        ) from exc

"""Namespace and operation constants for the verified DIAN SOAP profile."""

SOAP = "http://www.w3.org/2003/05/soap-envelope"
WSA = "http://www.w3.org/2005/08/addressing"
WCF = "http://wcf.dian.colombia"
WSSE = (
    "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd"
)
WSU = (
    "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd"
)
DS = "http://www.w3.org/2000/09/xmldsig#"
EC = "http://www.w3.org/2001/10/xml-exc-c14n#"
X509_V3 = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-x509-token-profile-1.0#X509v3"
BASE64_BINARY = "http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary"
RESPONSE = "http://schemas.datacontract.org/2004/07/DianResponse"
ARRAY = "http://schemas.microsoft.com/2003/10/Serialization/Arrays"
AR = "urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
STS = "dian:gov:co:facturaelectronica:Structures-2-1"
XADES = "http://uri.etsi.org/01903/v1.3.2#"
XADES141 = "http://uri.etsi.org/01903/v1.4.1#"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ACQUIRER = "http://schemas.datacontract.org/2004/07/Gosocket.Dian.Services.Utils.Common"
ACTION_PREFIX = f"{WCF}/IWcfDianCustomerServices"

EVENT_RESPONSE = "http://schemas.datacontract.org/2004/07/EventResponse"

EXCHANGE_EMAIL_RESPONSE = (
    "http://schemas.datacontract.org/2004/07/ExchangeEmailResponse"
)

NUMBER_RANGE_LIST = "http://schemas.datacontract.org/2004/07/NumberRangeResponseList"
NUMBER_RANGE = "http://schemas.datacontract.org/2004/07/NumberRangeResponse"

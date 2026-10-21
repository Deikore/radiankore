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
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ACQUIRER = "http://schemas.datacontract.org/2004/07/Gosocket.Dian.Services.Utils.Common"
ACTION_PREFIX = f"{WCF}/IWcfDianCustomerServices"

EVENT_RESPONSE = "http://schemas.datacontract.org/2004/07/EventResponse"

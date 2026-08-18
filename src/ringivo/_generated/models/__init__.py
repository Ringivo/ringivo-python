"""Contains all the data models used in inputs/outputs"""

from .cancel_fax_result import CancelFaxResult
from .cancel_fax_result_data import CancelFaxResultData
from .collection_links import CollectionLinks
from .cover_page_request import CoverPageRequest
from .cover_page_type_0 import CoverPageType0
from .document_meta import DocumentMeta
from .error import Error
from .error_code import ErrorCode
from .error_document import ErrorDocument
from .error_meta import ErrorMeta
from .error_source import ErrorSource
from .fax_account_attributes import FaxAccountAttributes
from .fax_account_collection_document import FaxAccountCollectionDocument
from .fax_account_create_request import FaxAccountCreateRequest
from .fax_account_create_request_data import FaxAccountCreateRequestData
from .fax_account_create_request_data_attributes import FaxAccountCreateRequestDataAttributes
from .fax_account_create_request_data_relationships import FaxAccountCreateRequestDataRelationships
from .fax_account_create_request_data_relationships_customer import (
    FaxAccountCreateRequestDataRelationshipsCustomer,
)
from .fax_account_create_request_data_type import FaxAccountCreateRequestDataType
from .fax_account_document_response import FaxAccountDocumentResponse
from .fax_account_relationships import FaxAccountRelationships
from .fax_account_resource import FaxAccountResource
from .fax_account_resource_type import FaxAccountResourceType
from .fax_account_status import FaxAccountStatus
from .fax_account_update_request import FaxAccountUpdateRequest
from .fax_account_update_request_data import FaxAccountUpdateRequestData
from .fax_account_update_request_data_attributes import FaxAccountUpdateRequestDataAttributes
from .fax_account_update_request_data_type import FaxAccountUpdateRequestDataType
from .fax_account_user_attributes import FaxAccountUserAttributes
from .fax_account_user_collection_document import FaxAccountUserCollectionDocument
from .fax_account_user_create_request import FaxAccountUserCreateRequest
from .fax_account_user_create_request_data import FaxAccountUserCreateRequestData
from .fax_account_user_create_request_data_relationships import (
    FaxAccountUserCreateRequestDataRelationships,
)
from .fax_account_user_create_request_data_relationships_fax_account import (
    FaxAccountUserCreateRequestDataRelationshipsFaxAccount,
)
from .fax_account_user_create_request_data_relationships_user import (
    FaxAccountUserCreateRequestDataRelationshipsUser,
)
from .fax_account_user_create_request_data_type import FaxAccountUserCreateRequestDataType
from .fax_account_user_document_response import FaxAccountUserDocumentResponse
from .fax_account_user_resource import FaxAccountUserResource
from .fax_account_user_resource_relationships import FaxAccountUserResourceRelationships
from .fax_account_user_resource_type import FaxAccountUserResourceType
from .fax_account_writable_attributes import FaxAccountWritableAttributes
from .fax_attempt_attributes import FaxAttemptAttributes
from .fax_attempt_attributes_transport_profile_type_0 import (
    FaxAttemptAttributesTransportProfileType0,
)
from .fax_attempt_resource import FaxAttemptResource
from .fax_attempt_resource_type import FaxAttemptResourceType
from .fax_attributes import FaxAttributes
from .fax_collection_document import FaxCollectionDocument
from .fax_direction import FaxDirection
from .fax_document_metadata import FaxDocumentMetadata
from .fax_document_metadata_kind import FaxDocumentMetadataKind
from .fax_document_response import FaxDocumentResponse
from .fax_event import FaxEvent
from .fax_event_data import FaxEventData
from .fax_failure_code_type_1 import FaxFailureCodeType1
from .fax_failure_code_type_2_type_1 import FaxFailureCodeType2Type1
from .fax_failure_code_type_3_type_1 import FaxFailureCodeType3Type1
from .fax_received_event import FaxReceivedEvent
from .fax_received_event_data import FaxReceivedEventData
from .fax_relationships import FaxRelationships
from .fax_resolution import FaxResolution
from .fax_resource import FaxResource
from .fax_resource_type import FaxResourceType
from .fax_status import FaxStatus
from .fax_update_request import FaxUpdateRequest
from .fax_update_request_data import FaxUpdateRequestData
from .fax_update_request_data_attributes import FaxUpdateRequestDataAttributes
from .fax_update_request_data_type import FaxUpdateRequestDataType
from .get_fax_include import GetFaxInclude
from .get_fax_media_format import GetFaxMediaFormat
from .get_webhook_delivery_include import GetWebhookDeliveryInclude
from .list_faxes_filtertag import ListFaxesFiltertag
from .list_faxes_include import ListFaxesInclude
from .list_webhook_deliveries_include import ListWebhookDeliveriesInclude
from .media_link import MediaLink
from .o_auth_error import OAuthError
from .phone_number_collection_document import PhoneNumberCollectionDocument
from .phone_number_resource import PhoneNumberResource
from .phone_number_resource_attributes import PhoneNumberResourceAttributes
from .phone_number_resource_attributes_status_type_1 import PhoneNumberResourceAttributesStatusType1
from .phone_number_resource_attributes_status_type_2_type_1 import (
    PhoneNumberResourceAttributesStatusType2Type1,
)
from .phone_number_resource_attributes_status_type_3_type_1 import (
    PhoneNumberResourceAttributesStatusType3Type1,
)
from .phone_number_resource_relationships import PhoneNumberResourceRelationships
from .phone_number_resource_type import PhoneNumberResourceType
from .relationship_to_many import RelationshipToMany
from .relationship_to_one import RelationshipToOne
from .resource_identifier import ResourceIdentifier
from .resource_links import ResourceLinks
from .send_fax_accepted import SendFaxAccepted
from .send_fax_accepted_data import SendFaxAcceptedData
from .send_fax_multipart_request import SendFaxMultipartRequest
from .send_fax_url_request import SendFaxUrlRequest
from .tags_type_0 import TagsType0
from .token_request import TokenRequest
from .token_request_grant_type import TokenRequestGrantType
from .token_response import TokenResponse
from .webhook_delivery_attributes import WebhookDeliveryAttributes
from .webhook_delivery_collection_document import WebhookDeliveryCollectionDocument
from .webhook_delivery_document_response import WebhookDeliveryDocumentResponse
from .webhook_delivery_resource import WebhookDeliveryResource
from .webhook_delivery_resource_relationships import WebhookDeliveryResourceRelationships
from .webhook_delivery_resource_type import WebhookDeliveryResourceType
from .webhook_delivery_status import WebhookDeliveryStatus
from .webhook_endpoint_attributes import WebhookEndpointAttributes
from .webhook_endpoint_collection_document import WebhookEndpointCollectionDocument
from .webhook_endpoint_create_request import WebhookEndpointCreateRequest
from .webhook_endpoint_create_request_data import WebhookEndpointCreateRequestData
from .webhook_endpoint_create_request_data_attributes import (
    WebhookEndpointCreateRequestDataAttributes,
)
from .webhook_endpoint_create_request_data_type import WebhookEndpointCreateRequestDataType
from .webhook_endpoint_document_response import WebhookEndpointDocumentResponse
from .webhook_endpoint_resource import WebhookEndpointResource
from .webhook_endpoint_resource_type import WebhookEndpointResourceType
from .webhook_endpoint_update_request import WebhookEndpointUpdateRequest
from .webhook_endpoint_update_request_data import WebhookEndpointUpdateRequestData
from .webhook_endpoint_update_request_data_attributes import (
    WebhookEndpointUpdateRequestDataAttributes,
)
from .webhook_endpoint_update_request_data_type import WebhookEndpointUpdateRequestDataType
from .webhook_event_envelope import WebhookEventEnvelope
from .webhook_event_type import WebhookEventType
from .webhook_scope_type import WebhookScopeType

__all__ = (
    "CancelFaxResult",
    "CancelFaxResultData",
    "CollectionLinks",
    "CoverPageRequest",
    "CoverPageType0",
    "DocumentMeta",
    "Error",
    "ErrorCode",
    "ErrorDocument",
    "ErrorMeta",
    "ErrorSource",
    "FaxAccountAttributes",
    "FaxAccountCollectionDocument",
    "FaxAccountCreateRequest",
    "FaxAccountCreateRequestData",
    "FaxAccountCreateRequestDataAttributes",
    "FaxAccountCreateRequestDataRelationships",
    "FaxAccountCreateRequestDataRelationshipsCustomer",
    "FaxAccountCreateRequestDataType",
    "FaxAccountDocumentResponse",
    "FaxAccountRelationships",
    "FaxAccountResource",
    "FaxAccountResourceType",
    "FaxAccountStatus",
    "FaxAccountUpdateRequest",
    "FaxAccountUpdateRequestData",
    "FaxAccountUpdateRequestDataAttributes",
    "FaxAccountUpdateRequestDataType",
    "FaxAccountUserAttributes",
    "FaxAccountUserCollectionDocument",
    "FaxAccountUserCreateRequest",
    "FaxAccountUserCreateRequestData",
    "FaxAccountUserCreateRequestDataRelationships",
    "FaxAccountUserCreateRequestDataRelationshipsFaxAccount",
    "FaxAccountUserCreateRequestDataRelationshipsUser",
    "FaxAccountUserCreateRequestDataType",
    "FaxAccountUserDocumentResponse",
    "FaxAccountUserResource",
    "FaxAccountUserResourceRelationships",
    "FaxAccountUserResourceType",
    "FaxAccountWritableAttributes",
    "FaxAttemptAttributes",
    "FaxAttemptAttributesTransportProfileType0",
    "FaxAttemptResource",
    "FaxAttemptResourceType",
    "FaxAttributes",
    "FaxCollectionDocument",
    "FaxDirection",
    "FaxDocumentMetadata",
    "FaxDocumentMetadataKind",
    "FaxDocumentResponse",
    "FaxEvent",
    "FaxEventData",
    "FaxFailureCodeType1",
    "FaxFailureCodeType2Type1",
    "FaxFailureCodeType3Type1",
    "FaxReceivedEvent",
    "FaxReceivedEventData",
    "FaxRelationships",
    "FaxResolution",
    "FaxResource",
    "FaxResourceType",
    "FaxStatus",
    "FaxUpdateRequest",
    "FaxUpdateRequestData",
    "FaxUpdateRequestDataAttributes",
    "FaxUpdateRequestDataType",
    "GetFaxInclude",
    "GetFaxMediaFormat",
    "GetWebhookDeliveryInclude",
    "ListFaxesFiltertag",
    "ListFaxesInclude",
    "ListWebhookDeliveriesInclude",
    "MediaLink",
    "OAuthError",
    "PhoneNumberCollectionDocument",
    "PhoneNumberResource",
    "PhoneNumberResourceAttributes",
    "PhoneNumberResourceAttributesStatusType1",
    "PhoneNumberResourceAttributesStatusType2Type1",
    "PhoneNumberResourceAttributesStatusType3Type1",
    "PhoneNumberResourceRelationships",
    "PhoneNumberResourceType",
    "RelationshipToMany",
    "RelationshipToOne",
    "ResourceIdentifier",
    "ResourceLinks",
    "SendFaxAccepted",
    "SendFaxAcceptedData",
    "SendFaxMultipartRequest",
    "SendFaxUrlRequest",
    "TagsType0",
    "TokenRequest",
    "TokenRequestGrantType",
    "TokenResponse",
    "WebhookDeliveryAttributes",
    "WebhookDeliveryCollectionDocument",
    "WebhookDeliveryDocumentResponse",
    "WebhookDeliveryResource",
    "WebhookDeliveryResourceRelationships",
    "WebhookDeliveryResourceType",
    "WebhookDeliveryStatus",
    "WebhookEndpointAttributes",
    "WebhookEndpointCollectionDocument",
    "WebhookEndpointCreateRequest",
    "WebhookEndpointCreateRequestData",
    "WebhookEndpointCreateRequestDataAttributes",
    "WebhookEndpointCreateRequestDataType",
    "WebhookEndpointDocumentResponse",
    "WebhookEndpointResource",
    "WebhookEndpointResourceType",
    "WebhookEndpointUpdateRequest",
    "WebhookEndpointUpdateRequestData",
    "WebhookEndpointUpdateRequestDataAttributes",
    "WebhookEndpointUpdateRequestDataType",
    "WebhookEventEnvelope",
    "WebhookEventType",
    "WebhookScopeType",
)

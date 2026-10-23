"""Ringivo API client for Python.

    from ringivo import Ringivo

    with Ringivo(
        base_url="https://api.yourprovider.example",
        client_id="...",
        client_secret="...",
        tenant="...",
        scopes=["fax:read", "fax:write"],
    ) as client:
        fax = client.faxes.send(
            fax_account="0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70",
            to="+13025556789",
            file=Path("chart-4471.pdf"),
        )

`AsyncRingivo` is the same client for callers on asyncio — the same
arguments, the same methods, awaited, and `async with` in place of `with`:

    from ringivo import AsyncRingivo

    async with AsyncRingivo(...) as client:
        fax = await client.faxes.get(fax_id)

Fax accounts are `client.fax_accounts` — list them, read one, open one for
a customer, change its settings, delete it, and read the numbers routed to
it. Reads need `fax:read`; every write needs `fax-accounts:write`.

`client.fax_account_users` is who may READ one account's faxes. A grant is
a pair and a fact — this user, this account — with no settings and no
update route: you withdraw one by deleting it. Listing and reading grants
needs `fax:read`; granting and withdrawing needs `fax-accounts:write`.

`client.customers` reads your customers: list them, or read one. A
customer's `id` is what `customer=` takes on the `client.pbx` lists. It
needs `customers:read`, which only an account-wide credential can hold.

`client.pbx` is your customers' phone systems: `pbx.subscribers` are every
extension on them — people and machines, told apart by `kind` —
`pbx.devices` are the registrations their phones have made, and
`pbx.call_records` is the call log — newest first, and the date range decides
which months are read. `pbx.subscribers.call()` asks a subscriber's phone to
ring and dial somebody. Reads need `pbx-users:read` (subscribers AND devices) or
`pbx-call-records:read`; the call needs `pbx-calls:write`.

Webhooks have two namespaces. `client.webhook_endpoints` registers where the
platform should call you and with what signing secret — and the secret is
readable ONCE, in the answer to the create or the rotate that minted it.
`client.webhook_deliveries` is the evidence of what could not be delivered:
a delivery that lands leaves no row, so `list(status="dead")` is what an
outage cost you. Both need `webhooks:read`/`webhooks:write`, except on a
`fax_account`-scoped endpoint, which a `fax:*` token already reaches.

The base URL has no default and no hostname is compiled into this package:
your provider gives you theirs. `scopes` has no default either, and an
empty one is refused: a token minted without scopes carries none, and every
route refuses it.

`client.messages.record()` records a text your own system already sent
through your own messaging-provider account, so staff see it in their
threads. It needs `messages:record`. `ringivo.sender_label()` makes any text
a label that keeps the API's label rule.

`client.inbound_messages` reads the texts somebody sent to your numbers:
list them, or read one. It needs `numbers:read` or `numbers:messaging`.

Webhook receivers want `ringivo.webhooks.verify()`, which needs no client
and no network — it is pure computation, so both clients share the one.
`ringivo.webhooks.parse_message_event()` reads a verified
`message.received`, `message.sent`, `message.delivered` or `message.failed`
body as a `MessageEvent`: one class per event type (`MessageReceivedEvent`,
`MessageSentEvent`, `MessageDeliveredEvent`, `MessageFailedEvent`), or
`UnknownMessageEvent` for anything else. Branch on `event.type`,
`isinstance()` or `match`.

`ringivo.is_retryable(error)` says whether the API's contract allows the
same call again (no answer, 408, 429, 5xx, and a 409
`idempotency_key_in_use`); `ApiError.retry_after` says how long the server
asked you to wait. The client never retries by itself, apart from one
resend with a fresh token after a 401.
"""

from . import webhooks
from ._version import __version__
from .async_client import AsyncRingivo
from .async_customers import AsyncCustomers
from .async_fax_account_users import AsyncFaxAccountUsers
from .async_fax_accounts import AsyncFaxAccounts
from .async_faxes import AsyncFaxes
from .async_inbound_messages import AsyncInboundMessages
from .async_messages import AsyncMessages
from .async_pbx import (
    AsyncPbx,
    AsyncPbxCallRecords,
    AsyncPbxDevices,
    AsyncPbxSubscribers,
)
from .async_webhook_deliveries import AsyncWebhookDeliveries
from .async_webhook_endpoints import AsyncWebhookEndpoints
from .client import Ringivo
from .customers import Customers
from .errors import (
    ApiError,
    ApiErrorDetail,
    AuthenticationError,
    RecordingAudioMissingError,
    RingivoError,
    SignatureVerificationError,
    TranscriptionCappedError,
    TranscriptRequestLimitedError,
    is_retryable,
)
from .fax_account_users import FaxAccountUsers
from .fax_accounts import NOT_GIVEN, FaxAccounts, NotGiven
from .faxes import Faxes
from .inbound_messages import InboundMessages
from .messages import Messages, sender_label
from .models import (
    CallRecord,
    CallRecordPage,
    Customer,
    CustomerPage,
    FailureCause,
    Fax,
    FaxAccount,
    FaxAccountNumber,
    FaxAccountPage,
    FaxAccountUser,
    FaxAccountUserPage,
    FaxDocument,
    FaxPage,
    InboundMessage,
    InboundMessageMediaItem,
    InboundMessageMediaWithLink,
    InboundMessagePage,
    MediaLink,
    MessageDeliveredEvent,
    MessageEvent,
    MessageFailedEvent,
    MessageFailedEventData,
    MessageReceivedEvent,
    MessageReceivedEventData,
    MessageSender,
    MessageSentEvent,
    OutboundMessage,
    OutboundMessageEventData,
    OutboundMessageMediaItem,
    PbxCall,
    PbxDevice,
    PbxDevicePage,
    PbxSubscriber,
    PbxSubscriberPage,
    Recording,
    Transcript,
    TranscriptChannel,
    TranscriptSegment,
    UnknownMessageEvent,
    WebhookDelivery,
    WebhookDeliveryPage,
    WebhookEndpoint,
    WebhookEndpointPage,
)
from .pbx import Pbx, PbxCallRecords, PbxDevices, PbxSubscribers
from .webhook_deliveries import WebhookDeliveries
from .webhook_endpoints import WebhookEndpoints

__all__ = [
    "ApiError",
    "ApiErrorDetail",
    "AsyncCustomers",
    "AsyncFaxAccountUsers",
    "AsyncFaxAccounts",
    "AsyncFaxes",
    "AsyncInboundMessages",
    "AsyncMessages",
    "AsyncPbx",
    "AsyncPbxCallRecords",
    "AsyncPbxDevices",
    "AsyncPbxSubscribers",
    "AsyncRingivo",
    "AsyncWebhookDeliveries",
    "AsyncWebhookEndpoints",
    "AuthenticationError",
    "CallRecord",
    "CallRecordPage",
    "Customer",
    "CustomerPage",
    "Customers",
    "FailureCause",
    "Fax",
    "FaxAccount",
    "FaxAccountNumber",
    "FaxAccountPage",
    "FaxAccountUser",
    "FaxAccountUserPage",
    "FaxAccountUsers",
    "FaxAccounts",
    "FaxDocument",
    "FaxPage",
    "Faxes",
    "InboundMessage",
    "InboundMessageMediaItem",
    "InboundMessageMediaWithLink",
    "InboundMessagePage",
    "InboundMessages",
    "MediaLink",
    "MessageDeliveredEvent",
    "MessageEvent",
    "MessageFailedEvent",
    "MessageFailedEventData",
    "MessageReceivedEvent",
    "MessageReceivedEventData",
    "MessageSender",
    "MessageSentEvent",
    "Messages",
    "NOT_GIVEN",
    "NotGiven",
    "OutboundMessage",
    "OutboundMessageEventData",
    "OutboundMessageMediaItem",
    "Pbx",
    "PbxCall",
    "PbxCallRecords",
    "PbxDevice",
    "PbxDevicePage",
    "PbxDevices",
    "PbxSubscriber",
    "PbxSubscriberPage",
    "PbxSubscribers",
    "Recording",
    "RecordingAudioMissingError",
    "Ringivo",
    "RingivoError",
    "SignatureVerificationError",
    "Transcript",
    "TranscriptRequestLimitedError",
    "TranscriptChannel",
    "TranscriptSegment",
    "TranscriptionCappedError",
    "UnknownMessageEvent",
    "WebhookDeliveries",
    "WebhookDelivery",
    "WebhookDeliveryPage",
    "WebhookEndpoint",
    "WebhookEndpointPage",
    "WebhookEndpoints",
    "__version__",
    "is_retryable",
    "sender_label",
    "webhooks",
]

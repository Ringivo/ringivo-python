# Release notes

## 0.24.0 (2026-10-23) — Added

- **`pbx.subscribers.call()` sends an `Idempotency-Key`.** The API is about
  to require the header on click-to-dial and to refuse a call without it
  with a 400 `idempotency_key_required`. Versions before this one send no
  key, so their `call()` stops working when the API change ships. Pass
  `idempotency_key=` to retry a call whose answer you never saw: the same
  key with the same request returns the first call's 202, with the same id,
  and nothing is dialled. With no key, a fresh UUID is made for each call,
  and the client's own 401 retry sends that same key again. The same key
  with a different request is a 422 `idempotency_key_reused`; while the
  first request still runs it is a 409 `idempotency_key_in_use`. Applies to
  both clients. The TypeScript client has the same change, as
  `idempotencyKey`.
- **`PbxCall.idempotent_replay`**: True when the API replayed an earlier
  call sent with the same key, and False for a call it accepted now. The
  body is the same either way, so this is the only way to tell them apart.
  Migration: none; the field is new and has a default.

## 0.24.0 (2026-10-23) — Changed

- **`is_retryable()` is True for a 409 `idempotency_key_in_use`.** The API
  is about to answer that 409 when a request with the same
  `Idempotency-Key` still runs. Its contract is to send the same request
  again, WITH THE SAME KEY, after `retry_after`; a new key could send the
  fax or ring the phone twice. Every other 409 stays False. Applies to both
  clients. Migration: a queue that gave up on every 409 now retries this
  one; keep the key with the queued job.
- **An empty `idempotency_key` is sent as given.** `faxes.send()` and
  `pbx.subscribers.call()` used to replace `""` with a fresh UUID; only
  `None` gets one now. The API refuses a blank key with a 400
  `idempotency_key_required`, so a retry key that came out blank fails
  loudly instead of becoming a new key that sends or dials again. This is
  the TypeScript client's behaviour too. Migration: pass `None`, not `""`,
  to have a key generated.
- **The `faxes.send()` docs name the API's new answers to a reused key**: a
  422 `idempotency_key_reused` for the same key with a different request,
  and a 409 `idempotency_key_in_use` while the first send still runs.

## 0.23.0 (2026-10-22) — Breaking

These removals are part of one clean breaking release (0.23.0). The package
no longer carries code for the API's v1 naming cleanup.

- **Filter-name bridge removed.** The client no longer retries a refused
  filter with the old snake_case name. List calls send the camelCase names
  only (`filter[faxAccount]`, `filter[createdAfter]`, and so on). Migration:
  none for calls through `client.faxes`, `client.webhook_endpoints` and the
  other wrappers; against an API from before the rename, stay on 0.22.x.
- **`ringivo._bridge`, `Ringivo._request_filtered()` and
  `AsyncRingivo._request_filtered()` removed.** These were private. Migration:
  call `client.request("GET", path, params=...)` with camelCase names.
- **Snake_case response members no longer read.** `Fax` from `send()` and
  `cancel()` reads `clientReference` and `createdAt` only; `MediaLink` reads
  `expiresAt` and `byteSize` only; `Recording` reads
  `byteSize`, `contentUrl` and `expiresAt` only (not the kebab-case
  `byte-size`, `content-url`, `expires-at`). Migration: none, unless you
  parse raw bodies yourself; read the camelCase keys.
- **`faxes.send(cover_page=...)` takes camelCase keys only.** `to_name` and
  `from_name` are no longer renamed, and the API answers them with a 400
  `unknown_member` naming `coverPage.to_name`. Applies to `faxes.send` on both
  clients. Migration: pass `toName` and `fromName`.
- **`Ringivo._request` and `AsyncRingivo._request` removed.** Migration: call
  `client.request(...)`.
- **`webhooks.MESSAGE_EVENT_TYPES` removed.** Migration: use
  `webhooks.INBOUND_MESSAGE_EVENT_TYPES | webhooks.OUTBOUND_MESSAGE_EVENT_TYPES`
  if you need all four type names. To route a delivery, parse it first and
  check the class (see the next item): a check against a set does not narrow
  the type.
- **Message events split into one class per event type; `MessageEventData`
  removed; `MessageEvent` is now a union.** `webhooks.parse_message_event()`
  now returns a `MessageEvent`: one class per event type, named after it, or
  `UnknownMessageEvent`. Each class has only its own members. The names and
  the shapes are the same as in the TypeScript client.
  - `MessageReceivedEvent` for `message.received`. Its `message` is a
    `MessageReceivedEventData`, with no `source`, `status`, `sent_by`,
    `sent_at`, `provider_message_id`, `provider_part_ids` or
    `failure_cause`.
  - `MessageSentEvent` for `message.sent` and `MessageDeliveredEvent` for
    `message.delivered`. Their `message` is an `OutboundMessageEventData`,
    with no `received_at` and no `failure_cause`.
  - `MessageFailedEvent` for `message.failed`. Its `message` is a
    `MessageFailedEventData`: a subclass of `OutboundMessageEventData` that
    adds `failure_cause`.
  - `UnknownMessageEvent` for any other body: another event type, a type
    this release does not know, or no JSON object. Its `type` is `None` and
    it has no `message`. The type that arrived is on `raw`, or `raw` is `{}`
    when the body was not a JSON object. Before, such a body parsed as a
    `MessageEvent` with every message member `None`.

  `type` is a `Literal` on each class, so `event.type == "message.sent"` (and
  each other type), `event.type is None`, `isinstance()` and `match` narrow
  to one class in pyright. `failure_cause` is typed
  `FailureCause | str | None`: the new `FailureCause` `Literal` and the new
  `webhooks.FAILURE_CAUSES` `frozenset` hold the seven causes the API
  documents today. A cause this release does not know still parses, as a
  `str`. Treat it as a failure.

  Migration:
  - **Code that reads `event.message` without narrowing first now raises
    `AttributeError` at run time.** An `UnknownMessageEvent` has no
    `message`, so `{}`, `{"data": "x"}` or any type this release does not
    know raises on `event.message`. A received message has no outbound
    members, so `event.message.source` raises on a `message.received` body.
    Before, both read `None`. Code with no type checker does not see this
    until a delivery arrives. In a webhook handler it is then a 500, and the
    platform delivers the event again. Narrow on `type` first:

    ```python
    event = webhooks.parse_message_event(payload)
    if not isinstance(event, (MessageSentEvent, MessageDeliveredEvent, MessageFailedEvent)):
        return  # a received text, or not a message event: accept it and ignore it
    ```

  - **`MessageEvent` is the same name with a new meaning.** It was one
    class; it is now the type alias `MessageReceivedEvent | MessageSentEvent
    | MessageDeliveredEvent | MessageFailedEvent | UnknownMessageEvent`. A
    `MessageEvent` annotation still type-checks, but `event.message` on it
    is now an error until you narrow. `isinstance(x, MessageEvent)` is now
    true for any of the five classes. `MessageEvent(...)` no longer works:
    build one class instead.
  - Narrow before you read `event.message`. Replace a routing check such as
    `if payload.get("type") in webhooks.OUTBOUND_MESSAGE_EVENT_TYPES:`
    followed by `parse_message_event(payload).message` with a parse first,
    then `isinstance()` or `match` on the classes.
  - Read `failure_cause` only on a `MessageFailedEvent`. It is no longer a
    member of a sent or delivered message.
  - Remove every read of an outbound member on a received message, and of
    `received_at` on a sent one: those members were always `None` there.
  - Replace `MessageEventData` with the data class of the event you handle:
    `OutboundMessageEventData` for a sent, delivered or failed handler (it
    also accepts a `MessageFailedEventData`, which is a subclass), and
    `MessageReceivedEventData` for a received one.

### The API's messaging contract changes

These items follow a change to the API itself. The TypeScript client changes
in the same way and uses the same names.

**Use 0.23.0 only with an API that has the change.** A mix of versions
fails as follows:

- **0.23.0 with an API from before the change** (for example, after the API
  change is rolled back): the API refuses EVERY record with a 400, also a
  record with no media. `messages.record()` always sends `mediaUrls` (as
  `[]` when you give no links), and that API does not know the member.
- **0.22.x with an API that has the change:** a record with no media still
  works. A record with `media_urls` gets a 422, because 0.22.x sends
  `media`. Nothing is stored, and a retry gets the same 422.

- **`messages.record()` sends `mediaUrls`, a list of strings, in place of
  `media: [{url}]`.** The `media_urls` argument does not change. Migration:
  none, unless you build the request body yourself with `client.request()`:
  then send `"mediaUrls": ["https://…"]`. The API answers `media` with a 422.
- **`MessageMediaPart` removed. Two classes replace it:**
  `OutboundMessageMediaItem(content_type, size)` and
  `InboundMessageMediaItem(content_type, filename, size)`. The wire members
  changed: `bytes` became `size`, and `encoding` is gone.
  - `OutboundMessage.media` and `OutboundMessageEventData.media` (on
    `message.sent`, `message.delivered` and `message.failed`) hold
    `OutboundMessageMediaItem`. It has no `filename`: the platform keeps
    none for a message sent from your number.
  - `InboundMessage.media` and `MessageReceivedEventData.media` hold
    `InboundMessageMediaItem`. `filename` is the name the sender's carrier
    gave the item, or `None`.

  Migration: replace `MessageMediaPart` with the class of the side you read.
  Replace `part.byte_size` with `item.size`. Remove every read of
  `encoding`, and of `filename` on an outbound item.
- **The failure cause `send_interrupted` replaces `outcome_unknown` and
  `submission_interrupted`.** It means the send was interrupted before the
  carrier confirmed it: treat the text as not sent (rarely, it may still
  arrive). The platform never sends it again. `FailureCause` and
  `webhooks.FAILURE_CAUSES` hold seven causes. Migration: replace each check
  for `outcome_unknown` or `submission_interrupted` with `send_interrupted`.
  A new event about a message that failed before the change also carries
  `send_interrupted`. A redelivered old event does not (next item).
- **A redelivered webhook keeps the values it was built with.** When the
  API delivers an event again, it sends the stored body unchanged. So an
  event built before the API change still carries the old values, and the
  parser reads them as follows:
  - A media item with `bytes` and `encoding`: `size` is `None`; `bytes` and
    `encoding` stay on `raw`.
  - The cause `outcome_unknown` or `submission_interrupted`: `failure_cause`
    is that plain `str`, not in `FAILURE_CAUSES`. Treat it as
    `send_interrupted`.
  - `providerPartIds: []`: `provider_part_ids` is `()`.

  The parser never raises on these. Migration: handle the old cause names
  until no event from before the change can be delivered again.
- **`provider_part_ids` is `None` for a message the provider never
  accepted**, not `()`. It is `None` exactly when `provider_message_id` is
  `None`. Migration: test `provider_part_ids is None`, or test
  `provider_message_id`.
- **`messages.record()` waits at least 35 seconds, not 25**
  (`RECORD_MIN_TIMEOUT_SECONDS` is `35.0`). The API now fetches all media
  links at once, each within 10 seconds of the call, and ends any request at 30
  seconds of its own time. The client's clock starts first, so the floor
  adds a 5-second margin: you always get the API's own answer. The floor
  is the wait for the answer (the read timeout). A longer client timeout is
  still kept.
- **A media link that fails has its own `code`.** If any link fails, nothing
  is stored, and `errors[0].source["pointer"]` names the link
  (`/data/attributes/mediaUrls/<index>`). 422 `media_rejected`: fix the
  link. 504 `media_timeout` and 502 `media_unreachable`: retry after
  `retry_after` with a new link. 503 `media_store_unavailable`: retry after
  `retry_after`. Before, a link fault was a 422 or a 503 with no `code`.
  `is_retryable()` is True for the 502, 503 and 504. When the links pass
  20 MB together, the 422 `media_rejected` points at the list,
  `/data/attributes/mediaUrls`, not at one link.
- **`messages.record()` no longer answers 404 or the "media in flight" 429.**
  The API removed both: a record is stored (201) while the copy into the
  staff threads is paused on its side, and the limit of two records with
  media in flight is gone. The rate limit of 300 records a minute stays.

## 0.23.0 (2026-10-22) — Fixed

- **An id of `.` or `..` is refused before any request.** Every method that
  puts an id in a URL path now raises `ValueError` for `""`, `.` and `..`,
  on both clients. Before, `.` and `..` went out unchanged, and the URL rules
  removed them: `inbound_messages.get(".")` read the list endpoint, and
  `get("..")` read `/v1/`. The TypeScript client refuses the same three
  values.

## Earlier upgrade notes

Moved here from the README unchanged; each applies to the version named.

### 0.19.0

**0.19.0 removed `transcript.provider` and `transcript.model`.** The API
stopped sending them on 2026-10-01: which speech-to-text service made a
transcript is not part of it. Remove every read of them. Nothing replaces
them. The same release changed more, with the API:

- **Added:** `transcript.channels`, a tuple of `TranscriptChannel` (`channel`,
  `party`, `role`), and `segment.channel` (0 or 1). `party` is an extension
  or an E.164 number; `role` is `caller` or `callee`, and `None` when the API
  does not know. Which side is on which channel is NOT fixed, so read
  `channels` and never assume channel 0 is the caller. `channels` is `None`
  where it is not served (`transcripts()` and `request_transcript()`), `()` for
  a one-channel (mono) recording, and only `transcript()` serves it.
- **Removed from `Transcript`:** `ccc_id`, `byte_size`, `sha256`,
  `content_url` and `expires_at`. The transcript download is gone: read the
  words from `segments`. **Removed from `Recording`:** `ccc_id`.
- **Deprecated:** `transcript.status` still works but raises a
  `DeprecationWarning` on read. Read `transcript_status` instead. Code that
  BUILDS a `Transcript` itself (a constructor call or `dataclasses.replace()`)
  must pass `_status=`, not `status=`.
- **Code that reads a removed field now fails:** `transcript.ccc_id`,
  `transcript.content_url`, `transcript.expires_at` and `recording.ccc_id`
  raise `AttributeError`. Remove those reads before you upgrade.
- **Faxes:** `send()`, `cancel()`, `media_link()` and `thumbnail_link()` now
  ask for JSON:API. `send()` and `cancel()` return a complete `Fax`, and
  `MediaLink` gains `id`, `kind` and `content_type` (`None` when an older
  server answers). `MediaLink.url` keeps its name.

### 0.18.0

`call.has_recording` is **deprecated** in 0.18.0, and reading it raises a
`DeprecationWarning`. It is `True` exactly when `recording_status` is
`available`, so it cannot tell "on its way" from "never recorded" from
"lost". Read `recording_status` instead. The API still serves the old
member until a later, announced release.

### Upgrading from 0.13.x

`pbx.users` is now `pbx.subscribers`, and the
API path `/v1/pbx/users` is gone — there is no alias. `PbxUser` is
`PbxSubscriber`, `PbxUserPage` is `PbxSubscriberPage` and its rows are
`page.subscribers`, and `PbxUsers`/`AsyncPbxUsers` are
`PbxSubscribers`/`AsyncPbxSubscribers`. `get()` and `call()` take
`subscriber_id` where they took `pbx_user_id`. Click-to-dial is
`pbx.subscribers.call(...)`, with the same arguments. The list now returns
machines too, so a people-only list needs `kind="user"`. The links back to a
subscriber moved too: `PbxDevice.pbx_user_id` is `PbxDevice.subscriber_id`,
`CallRecord.from_pbx_user_id`/`to_pbx_user_id` are
`from_subscriber_id`/`to_subscriber_id`, and `user=` on `devices.list()`
and `call_records.list()` is `subscriber=`. `user=` on
`subscribers.list()` is unchanged: it is the extension. The scope is still
`pbx-users:read`.

### 0.10.0, 0.11.0 and 0.12.0

**0.10.0 rebuilt the call log (`pbx.call_records`) with no backward compatibility, 0.11.0
renamed one member of it, and 0.12.0 renamed one value.** The console owns both decisions (one clean shape
mattered more than a migration path), so `0.9.x`'s `vendor_type`,
`from_user`, `from_uri`, `to_user`, `to_uri`, `dialed`, `by_user`,
`term_user` and `tag` are all gone rather than deprecated. There is no
argument or attribute standing in for them: reach for the extended tier
(see "The call log" in the README) for the raw material they used to carry.

**Upgrading from 0.11.x:** the `direction` value `onNet` is now `internal`,
and `call_records.list(direction="onNet")` is now
`call_records.list(direction="internal")`. The API refuses `onNet` with a
400. The value names a call that stayed inside one domain — extension to
extension, a call to voicemail, or a call into a conference. A call between
two domains was never `onNet`: it arrives as two records, `outbound` on the
caller's side and `inbound` on the called side. Nothing else moved.

**Upgrading from 0.10.x:** `CallRecord.type` is now `CallRecord.direction`,
and `call_records.list(type=...)` is now `call_records.list(direction=...)`.
JSON:API reserves `type` for the resource object itself and forbids an
attribute of that name, which is the defect this rename fixes. Take the
0.11.x step above too.

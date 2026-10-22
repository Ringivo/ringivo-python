# Release notes

## Unreleased — Breaking

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
  `expiresAt` and `byteSize` only; `Recording` and `Transcript` read
  `byteSize`, `contentUrl` and `expiresAt` only (not the kebab-case
  `byte-size`, `content-url`, `expires-at`). Migration: none, unless you
  parse raw bodies yourself; read the camelCase keys.
- **`faxes.send(cover_page=...)` takes camelCase keys only.** `to_name` and
  `from_name` are no longer renamed. Migration: pass `toName` and `fromName`.
- **`Ringivo._request` and `AsyncRingivo._request` removed.** Migration: call
  `client.request(...)`.
- **`webhooks.MESSAGE_EVENT_TYPES` removed.** Migration: use
  `webhooks.INBOUND_MESSAGE_EVENT_TYPES | webhooks.OUTBOUND_MESSAGE_EVENT_TYPES`
  for all four types, or route on the two sets directly.

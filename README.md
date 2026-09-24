# ringivo

The Python client for the Ringivo API: send a fax, read one, list them,
cancel one, fetch its pages, read your customers, manage their fax accounts,
register the webhooks that tell you what happened, and verify what arrives.
It also reads your customers' phone systems — the subscribers, their
registrations and the call log — and places a call from one.

```
pip install ringivo
```

Python 3.10 or newer. Two runtime dependencies: `httpx`, and
`typing-extensions` (4.10 or newer) on every supported interpreter — the
generated types use `TypedDict(closed=True)`, which no version of the
standard library's `typing` carries.

**There are two clients: `Ringivo` and `AsyncRingivo`.** They take the same
arguments and have the same methods; the async one awaits them. Pick the one
that matches your program and do not mix them: each client's authentication
refuses the other's transport rather than quietly sending your requests
without a token, so an `httpx.AsyncClient` handed `Ringivo`'s auth — or an
`httpx.Client` handed `AsyncRingivo`'s — raises `NotImplementedError` naming
the reason.

## Your base URL and your credential

There is no default host, and none is compiled in. Your provider gives you
the API root, a client id, a client secret, and the id of the tenant your
credential acts for; everything in this README uses
`https://api.yourprovider.example` where yours goes.

```python
with Ringivo(
    base_url="https://api.yourprovider.example",
    client_id="0198c4a1-1f2e-7a3b-9c40-5f6e7d8a9b01",
    client_secret="9tK2xr4mQ7vBnZ1sD5hL0pWfC8jY3aE6",
    tenant="0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8",
    scopes=["fax:read", "fax:write"],
) as client:
    ...
```

On the first call the client sends all of that in one request and gets back
a bearer token that lasts about a quarter of an hour. It caches the token,
mints a new one a minute before that one expires, and mints another if the
platform ever refuses one — you never handle the token.

**Ask for the scopes you need.** The client refuses to construct without
`scopes=`, and raises `ValueError` naming the fix: a request that asks for
no scopes authorises nothing, so the platform refuses it — a 400 you would
otherwise meet on your first call rather than on the line that caused it.
Ask for more than your credential was granted and the extra is dropped
rather than refused, as long as one scope survives, so a call can still fail
later at the resource. The scopes this client's calls need are `fax:read`
and `fax:write` for faxes, and `fax-accounts:write` for opening, changing or
deleting a fax account — a reseller-tier scope, so a credential issued for
one customer cannot hold it however it is asked for. The webhook calls need
`webhooks:read` and `webhooks:write`, except on an endpoint scoped to one fax
account: a `fax:*` token already reaches those. The phone-system calls need
`pbx-users:read` for subscribers and their devices, `pbx-call-records:read`
for the call log, and `pbx-calls:write` to place a call.

A client that provisions accounts and then reads them asks for both:

```python
with Ringivo(
    base_url="https://api.yourprovider.example",
    client_id="0198c4a1-1f2e-7a3b-9c40-5f6e7d8a9b01",
    client_secret="9tK2xr4mQ7vBnZ1sD5hL0pWfC8jY3aE6",
    tenant="0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8",
    scopes=["fax:read", "fax-accounts:write"],
) as provisioning:
    account = provisioning.fax_accounts.create(
        customer="0198c4a1-4d5e-7f60-a172-3c4d5e6f7081",
        name="Front desk",
    )
    print(account.id, account.retention_days)
```

**`tenant=` is required**, and it is a required argument rather than a
checked one: leave it out and Python refuses the constructor by name. There
is no inference behind it — a mint that names no tenant is refused.

Pass `customer=` as well when your credential was issued for one customer
inside that tenant. Both selectors NAME a grant your provider already wrote
for your credential; they never widen one, and a selector no grant covers is
refused with a 400 however good your credentials are.

## Send a fax

```python
from pathlib import Path

from ringivo import Ringivo

with Ringivo(
    base_url="https://api.yourprovider.example",
    client_id="0198c4a1-1f2e-7a3b-9c40-5f6e7d8a9b01",
    client_secret="9tK2xr4mQ7vBnZ1sD5hL0pWfC8jY3aE6",
    tenant="0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8",
    scopes=["fax:read", "fax:write"],
) as client:
    fax = client.faxes.send(
        fax_account="0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70",
        to="+13025556789",
        file=Path("chart-4471.pdf"),
        client_reference="chart-4471",
    )

    print(fax.id, fax.status)   # 0198c4a1-… queued
```

`send()` returns as soon as the fax is **accepted**. The render and the call
happen afterwards, so `status` is `queued` here — read the fax again to see
how it ended:

```python
    finished = client.faxes.get(fax.id)
    print(finished.status, finished.pages_transferred)
```

Point at pages instead of uploading them with `urls=[...]` (up to five
`https` links). Uploads and URLs cannot be mixed in one request.

### Retrying a send safely

Every send carries an `Idempotency-Key`, and the client invents one when you
do not pass it. If you intend to **retry** a send whose response you never
saw — a timeout, a dropped connection — pass your own key and reuse it. The
server replays the first fax instead of sending a second, and tells you it
did:

```python
    fax = client.faxes.send(
        fax_account=account_id,
        to="+13025556789",
        file=pdf_bytes,
        idempotency_key="chart-4471-attempt-1",
    )

    if fax.idempotent_replay:
        print("this was already sent")
```

## Read, list, cancel, download

```python
    fax = client.faxes.get(fax_id)

    page = client.faxes.list(direction="inbound", read=False, tags={"clinic": "north"})
    for fax in page:
        print(fax.id, fax.from_, fax.pages_total)

    if page.next_cursor:                       # newest first; follow the cursor
        page = client.faxes.list(after=page.next_cursor)

    client.faxes.cancel(fax_id)                # before the far end answers

    pdf = client.faxes.media(fax_id)           # the document's bytes
    Path("received.pdf").write_bytes(pdf)
```

`media()` mints a short-lived download link and follows it for you. Use
`media_link()` instead if you want the URL and its expiry — but do not cache
it or pass it on: anyone holding it reads that document.

### Walking the whole collection

A page holds 25 rows by default, up to a ceiling of 100 with `page_size=`.
To backfill every fax matching a filter, follow `next_cursor` — the
server's own cursor — until it comes back `None`:

```python
    faxes = []
    after = None
    while True:
        page = client.faxes.list(direction="inbound", after=after)
        faxes.extend(page)
        if page.next_cursor is None:            # the last page
            break
        after = page.next_cursor
```

`after=` walks forward; `before=` walks backward from a cursor instead —
how you poll for rows that arrived since your last read.

## Fax accounts

A fax account is a customer's container: the numbers routed to it, the faxes
sent and received on it, and the settings that govern both. Opening,
changing and deleting one is `client.fax_accounts`.

```python
    account = client.fax_accounts.create(
        customer="0198c4a1-4d5e-7f60-a172-3c4d5e6f7081",
        name="Front desk",
        header_text="ACME VETERINARY",
        retention_days=365,
    )

    page = client.fax_accounts.list(customer="0198c4a1-4d5e-7f60-a172-3c4d5e6f7081")
    for account in page:
        print(account.id, account.name, account.status)

    for number in client.fax_accounts.numbers(account.id):
        print(number.e164, number.status)

    client.fax_accounts.update(account.id, status="suspended")   # receive only
    client.fax_accounts.delete(account.id)
```

**An account belongs to one customer for its whole life.** Every fax it
holds carries the customer it was sent or received for, so there is no way
to move it and no argument that would try.

**Numbers are attached through the routing API, not here.** A number points
at one destination, and that rule belongs to the number:
`POST /v1/phone-numbers/{id}/routing` with `target_type: fax`, through
`client.request()`. `numbers()` reads back what is pointed at this account —
all of them, walking the pages for you, because a half-list of a fax
account's numbers looks exactly like a full one.

### Retention: two rules, either of them off

Retention here DELETES; it never holds anything back.

| Setting | What it does | Off |
|---|---|---|
| `retention_days` | Delete a fax's pages once they are older than this many days. | `None` — kept for ever |
| `retention_pages` | Keep only this many of the newest pages on the account. | `None` — no page limit |

A new account gets your provider's defaults — a year, and no page limit, at
the time of writing — because this client sends nothing for an argument you
did not name.

```python
    client.fax_accounts.update(account.id, retention_days=90, retention_pages=5000)
    client.fax_accounts.update(account.id, retention_days=None)     # keep for ever
```

Deleting a FAX is never blocked by retention: `DELETE /v1/faxes/{id}`
removes its pages now.

### Changing one setting changes one setting

`update()` is a sparse PATCH: it sends only the arguments you pass, so
suspending an account leaves its retention rules exactly as they were.
`None` is a value rather than an omission — it clears a nullable field.

```python
    client.fax_accounts.update(account.id, default_from_e164=None)   # clears it
    client.fax_accounts.update(account.id)                           # ValueError
```

### Deleting an account

`delete()` DESTROYS the stored pages of every fax on the account and cannot
be undone — download anything worth keeping first. The account then leaves
your listings and the people granted it lose access; the fax records
themselves survive as the billing and audit evidence, and nothing bills
after the delete.

It is refused while any number still routes to the account:

```python
    try:
        client.fax_accounts.delete(account.id)
    except ApiError as refusal:
        if refusal.code == "fax_account_has_routed_numbers":
            print("move or release its numbers first")
```

Branch on `code`, not on the 409: a fax that cannot be cancelled is a 409
too, and it carries no code at all.

### Who may read an account's faxes

Holding the account write permission lets somebody manage an account
without being granted it. A GRANT is how you hand ONE account's faxes and
pages to somebody who holds no such permission — a customer-facing staffer
who should see this customer's faxes and no others. That is
`client.fax_account_users`.

```python
    grant = client.fax_account_users.create(
        fax_account=account.id,
        user="0198c4a1-7081-72a3-d4a5-6f7081920314",
    )

    for row in client.fax_account_users.list(fax_account=account.id):
        print(row.user_email, row.user_id)

    client.fax_account_users.delete(grant.id)     # withdraw it
```

A grant is a pair and a fact — this user, this account — and it holds no
settings, so there is no `update()`: you withdraw one by deleting it and
re-make it by creating another. Withdrawing takes nothing else with it, and
somebody who reaches the account by permission rather than by a grant still
reaches it.

Listing and reading grants needs `fax:read`; making and withdrawing them
needs `fax-accounts:write`. The account you grant may be one you hold no
grant on yourself — administering an account is permission-gated while
reading its content is grant-gated, so somebody has to be able to add the
first member.

## Webhook endpoints

An endpoint is where the platform calls you, and what it calls you about.
Registering one is `client.webhook_endpoints`; checking what arrives is
`webhooks.verify()`, further down this page.

```python
    endpoint = client.webhook_endpoints.create(
        url="https://hooks.acme-vet.example/faxes",
        scope_type="fax_account",
        scope_id=account.id,
        events=["fax.received", "fax.delivered"],
    )

    # whsec_… — the only time this is readable. Put it where your
    # receiver can find it; no call reads it back.
    secret = endpoint.secret
```

**The signing secret is in that answer and nowhere else, ever.** Store it
before you do anything else. Every later read of the endpoint publishes
`secret=None`, and that is the platform saying it keeps no readable copy, not
this client failing to find one. Lose it and your only way back is
`rotate_secret()`.

`scope_type` is `tenant`, `customer` or `fax_account`, and `scope_id` names
the one you mean. The three are a containment order, so a reseller-wide
endpoint and a per-account one both hear about the same fax. Neither
`scope_type` nor `scope_id` can be changed afterwards: the delivery record is
the evidence of what that scope was told, so a different scope is a new
endpoint.

`events` is the list you want — **required, and it must name at least one.**
There is no spelling left that means "every event in scope": `None` and `[]`
are each refused before the request is built, exactly as the platform
refuses them. An event name the platform does not publish is a 422 — a typo
would otherwise subscribe you to silence.

Registering needs `webhooks:write`, or `fax:write` for a `fax_account`-scoped
endpoint only. Naming a customer or tenant scope with a `fax:*` token is a
422. Reading needs `webhooks:read`, and a `fax:read` token lists
fax-account-scoped endpoints alone — the wider ones are absent from its page
rather than refused, so an empty result under a `fax:*` token says nothing
about whether a wider endpoint exists.

### Adding an event to an endpoint you already have

`update()` is a sparse PATCH, like `fax_accounts.update()`: it sends only the
arguments you pass. So the fix for "we registered for `fax.received` and the
outbound events never arrived" is one call, and it leaves the URL and the
switch exactly as they were:

```python
    client.webhook_endpoints.update(
        endpoint.id,
        events=["fax.received", "fax.sending", "fax.delivered", "fax.failed"],
    )
```

The list is REPLACED, not merged — send every event you want, not just the
new ones, and it must still name at least one: `[]` is refused. `None` is not
sent as `null` here — passing it alone is the same as naming nothing.

Switching an endpoint off keeps it and its events, and stops the fan-out:

```python
    client.webhook_endpoints.update(endpoint.id, active=False)   # deaf, not gone
    client.webhook_endpoints.delete(endpoint.id)                 # gone
```

`delete()` stops the fan-out at once and **keeps the delivery record** — "why
did our integration stop hearing about faxes?" is answered by the deliveries
of the endpoint somebody removed. Both need `webhooks:write`, or `fax:write`
on a fax-account-scoped endpoint.

### Rotating the secret

```python
    rotated = client.webhook_endpoints.rotate_secret(endpoint.id)

    print(rotated.secret)                        # the new one, once
    print(rotated.secret_previous_expires_at)    # when the old one stops
```

A rotation does not replace the secret at once. It mints a new one and starts
a 24-hour clock: the PREVIOUS secret goes on signing until
`secret_previous_expires_at`, and during that window a delivery's header
carries two `v1` signatures, newest first. `webhooks.verify()` tries every one
of them, so a rotation costs you no deliveries as long as your own copy is
rolled before the deadline. Needs `webhooks:write`, or `fax:write` on a
fax-account-scoped endpoint.

### What we could not deliver

`client.webhook_deliveries` is evidence of failure, not a delivery history. A
delivery that reaches your endpoint leaves NO ROW: a row appears when an
attempt fails, moves along the retry ladder, and is removed the moment a
later attempt succeeds.

```python
    for delivery in client.webhook_deliveries.list(status="dead"):
        print(delivery.event_id, delivery.event_type, delivery.status_code)
```

So `status="dead"` is the query this collection exists for — what an outage
cost you, and the only place that list exists. `pending` is everything still
on the ladder. **There is no `delivered`**: the API answers 400 to it rather
than handing back an empty page. An empty page for either real status is the
good news.

Filter by `endpoint=` and `event_type=` too, and read one row with
`client.webhook_deliveries.get(delivery_id)`. The body that was POSTed is
never published here — only `payload_sha256`, the digest of the exact bytes
that were signed, so an integrator who kept what they received can prove it is
what was sent. Reading needs `webhooks:read`; a delivery borrows its
endpoint's reach, so a `fax:read` token sees the deliveries of
fax-account-scoped endpoints alone.

## Customers

`client.customers` reads the businesses you sell to: list them, or read one.
It needs `customers:read`, and only a credential issued for your whole
reseller account can hold that scope. A credential issued for one customer
never carries it.

```python
    page = client.customers.list(code="jpz3k")
    for customer in page:
        print(customer.id, customer.name, customer.pbx, customer.effective_region)

    customer = client.customers.get("0198c4a1-7a10-7c3e-9d21-4f5a6b7c8d9e")
```

**A customer's `id` is what the rest of this client asks for.** Pass it as
`customer=` to `client.pbx.subscribers.list`, `client.pbx.devices.list` and
`client.pbx.call_records.list`, and to the fax-account calls:

```python
    for subscriber in client.pbx.subscribers.list(customer=customer.id):
        print(subscriber.user, subscriber.display_name, subscriber.kind)
```

The list is newest first. It walks by cursor, like every other list here.
`code=` finds the one customer whose code is exactly that value, and `ids=`
reads several customers by id in one request — the ids `list()` and `get()`
hand back. The two combine. A customer that is not on your account answers
404 on `get()`, the same as an id that names nothing.

When `customer.pbx` is False, the five phone-system fields —
`residential`, `call_limit`, `call_limit_external`, `transports` and
`provisioning_state` — are None. `transports` keeps the server's order,
because the order is the DNS preference.

## Call records, subscribers, devices and click-to-dial

`client.pbx` is your customers' phone systems: `pbx.subscribers` are every
extension on them — people AND machines — `pbx.devices` are the
registrations their phones have made, and `pbx.call_records` is the call
log. Reading needs `pbx-users:read` —
which covers subscribers AND their devices, because a registration is read
as part of the subscriber it belongs to — or `pbx-call-records:read` for
the call log, which is a separate scope because who called whom is a
different sensitivity from a directory.

```python
    for subscriber in client.pbx.subscribers.list(search="perkins"):
        print(subscriber.user, subscriber.display_name, subscriber.kind)

    for device in client.pbx.devices.list(user=subscriber.id, registered=True):
        print(device.aor, device.user_agent)
```

**`kind` says what a subscriber is.** A phone system holds people and
machines: auto attendants, call queues, AI agents, the domain's settings
template. `kind` is `user` for a person, and otherwise one of
`autoAttendant`, `callQueue`, `aiAgent`, `conference`, `department`,
`site`, `ringGroup`, `trunk`, `timeOfDay`, `domain` or `system`. `system`
is any machine the platform has no word for yet — an unknown marker is
never read as `user`. `kind` is a plain `str`, so a word added later parses
as itself; read a word you do not know as `system`.

**For a click-to-call picker, ask for the people who have a phone:**

```python
    page = client.pbx.subscribers.list(kind="user", has_devices=True)
```

`kind=` takes one word, a comma list (`"callQueue,autoAttendant"`) or a
list of words; a word the API does not know is a 400 that names the
accepted words. `has_devices=False` asks for the subscribers with no
registered device. A subscriber's own devices are `subscriber.device_ids`.

**Upgrading from 0.13.x:** `pbx.users` is now `pbx.subscribers`, and the
API path `/v1/pbx/users` is gone — there is no alias. `PbxUser` is
`PbxSubscriber`, `PbxUserPage` is `PbxSubscriberPage` and its rows are
`page.subscribers`, and `PbxUsers`/`AsyncPbxUsers` are
`PbxSubscribers`/`AsyncPbxSubscribers`. `get()` and `call()` take
`subscriber_id` where they took `pbx_user_id`. Click-to-dial is
`pbx.subscribers.call(...)`, with the same arguments. The list now returns
machines too, so a people-only list needs `kind="user"`. The scope is still
`pbx-users:read`, and `PbxDevice.pbx_user_id` and `CallRecord`'s
`from_pbx_user_id`/`to_pbx_user_id` keep their names; they are
`subscribers` ids.

**Every `/v1/pbx/` read is narrowed to your customers' phone systems**, and
there is no unscoped form. A credential that reaches no customer with a
phone system is refused with a 400 rather than handed an empty page, so
"nobody has a phone system yet" never reads as "nobody has any subscribers".

The two collections take a `user=` argument that means different things,
and it is worth knowing which is which: `subscribers.list(user=...)` is an
EXACT extension — `101` does not match `1010` — while
`devices.list(user=...)` is a `subscribers` id. A device points back at its subscriber as
`device.pbx_user_id`, named that way because JSON:API forbids a
relationship sharing the name of the `user` attribute beside it.

### The call log, one date range at a time

**0.10.0 rebuilt this resource with no backward compatibility, 0.11.0
renamed one member of it, and 0.12.0 renamed one value.** The console owns both decisions (one clean shape
mattered more than a migration path), so `0.9.x`'s `vendor_type`,
`from_user`, `from_uri`, `to_user`, `to_uri`, `dialed`, `by_user`,
`term_user` and `tag` are all gone rather than deprecated. There is no
argument or attribute standing in for them: reach for the extended tier
below for the raw material they used to carry.

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

```python
    page = client.pbx.call_records.list(
        customer="0198c4a1-4d5e-7f60-a172-3c4d5e6f7081",
        started_after="2026-09-01T00:00:00Z",
        started_before="2026-09-30T23:59:59Z",
        direction="inbound",
    )

    for call in page:
        print(call.started_at, call.from_number, call.to_number, call.duration_seconds)
```

**The date range decides which months are read.** The phone system keeps
one table per month, so `started_after` and `started_before` choose which
are opened at all. Pass neither and you get the current and previous month
— not everything there is. A range wider than 13 months is refused with a
400, so a longer backfill is walked one window at a time.

Records the phone system marks hidden are **left out of the list and served
on a direct read** — the same asymmetry its own portal has. Ask for them
with `include_hidden=True`, or read one by id:

```python
    call = client.pbx.call_records.get(call_id)      # served even if hidden
```

`call.direction` is `inbound`, `outbound` or `internal`, and
`call.disposition` is `answered` or `missed` — only `inbound` can be either.
The list filters on `direction` but not on disposition: read
`call.disposition` on each record instead. The phone system records ONE
integer carrying both, and an integer this API has no word for arrives as
its own digits in `direction` rather than as null, so match on the values
you know and let the rest fall through — the set is not closed.

`call.has_recording` says a recording is held; it is not itself the audio.
Fetch the call's captures with `call_records.recordings(call.id)` — see
[Recordings and transcripts](#recordings-and-transcripts) below.

**A `*_number` field is E.164 or nothing.** `call.from_number`,
`call.to_number` and `call.dialed_number` carry `+14075550101` or `None` —
never an extension, a dial code or a star code; the console normalises and
then checks, so this client has nothing left to reshape. `from_number` is
the external party on an inbound call and the caller id sent on an outbound
one; `to_number` is the party actually dialled; `dialed_number` is what was
typed before the dial plan rewrote it. An extension is in
`call.from_extension`, `call.routed_by_extension` or
`call.answering_extension` instead.

#### Two tiers: standard, and extended behind a sparse fieldset

Every `list()` and `get()` response carries the **standard** tier — the
fields above, plus `tenant_id`, `domain`, `territory`, `release_code`,
`release_text` and `hidden`. The **extended** tier is the phone system's own
raw material, served only when you name it in `fields=`:

```python
    page = client.pbx.call_records.list(
        fields=["direction", "startedAt", "origCallId", "terminatedTo"],
    )
```

`fields=` is a JSON:API sparse fieldset, so it **narrows** rather than
adds: name every field you want, standard ones included, in the API's own
camelCase spelling — not this client's snake_case attribute names. Leave it
off and you get the standard tier alone; every extended attribute then
reads back `None`.

| Tier | Attributes |
|---|---|
| Standard (always served) | `type`, `disposition`, `tenant_id`, `domain`, `territory`, `from_number`, `from_extension`, `from_name`, `to_number`, `dialed_number`, `routed_by_extension`, `answering_extension`, `started_at`, `answered_at`, `released_at`, `duration_seconds`, `talk_seconds`, `release_code`, `release_text`, `has_recording`, `hidden` |
| Extended (needs `fields=`) | `vendor_id`, `orig_call_id`, `term_call_id`, `by_action`, `terminated_to`, `codec`, `hostname`, `raw_from_uri`, `raw_from_user`, `raw_to_user`, `raw_request_user` |

`call.customer_id`, `call.from_pbx_user_id` and `call.to_pbx_user_id` come
off the `customer`, `fromPbxUser` and `toPbxUser` relationships — read-only
in every tier, and each `None` on a leg with no subscriber to point at, such
as an outside caller on an inbound call.

### Recordings and transcripts

```python
    for recording in client.pbx.call_records.recordings(call.id):
        print(recording.id, recording.duration, recording.content_url)

    for transcript in client.pbx.call_records.transcripts(call.id):
        print(transcript.id, transcript.status)   # "ready" or "pending"
```

Both answer every **capture** of one call — a call can have more than one,
because the phone system's own capture id is `(call id, ccc id)` — and
neither is paginated: this is the captures of one call, bounded by its two
legs, never a walk over a growing table, so there is no `after`/`before`
cursor and nothing beyond the tuple you get back.

`recording.content_url` and `transcript.content_url` are signed,
time-limited links minted fresh on every call. Do not cache one past its
`expires_at` or hand it to anyone else — whoever holds the URL can fetch
that document with no further authorization.

`transcripts()` answers one item per **recording**, not one per transcript
that exists: a capture with no words yet still appears, as a `Transcript`
with `status="pending"` and every other field `None`, so you can tell "no
transcript yet" from "no recording at all". Needs `pbx-call-records:read`
to fetch the call at all, and `pbx-transcripts:read` — a separate grant,
because the words of a call are searchable and cheap to mine at scale in a
way the call log itself is not — to see whether anyone spoke.

### Two kinds of timestamp, and why

A call record's `started_at`, `answered_at` and `released_at` are
`datetime`s. A user's and a device's timestamps are **`str`** — served
exactly as the phone system stores them, in a format the switch has never
published. Parsing them here would be a guess, and a wrong guess is silent:
an instant off by a time zone still looks like an instant. Read
`device.registered` rather than comparing `device.registration_expires_at`
yourself; the API derives that one for you.

### Click-to-dial

```python
    placed = client.pbx.subscribers.call(subscriber.id, destination="+13025556789")

    print(placed.id, placed.status)        # 0198c7f2-… requested
```

The phone system rings that subscriber's phone and connects it to
`destination`, so the call goes out as them rather than as you. Needs
`pbx-calls:write`.

The answer is a 202 and says exactly that much: the request was accepted
and handed to the phone system. Nothing here says a phone rang or anybody
answered, and `status` is `requested` — the only value this endpoint
publishes.

**The id you get back is not a call-record id, but it finds the call's
records.** It names the call on the phone system: it is the SIP call id the
call is placed under. A call record's own id comes from the switch's
call-detail row, so the two ids differ. Pass this id as `call_id=` to the
call-record list:

```python
    placed = client.pbx.subscribers.call(subscriber.id, destination="+13025556789")

    # Later, once the call has ended. With no range, only the current and
    # the previous month are searched.
    for record in client.pbx.call_records.list(call_id=placed.id):
        print(record.id, record.disposition, record.duration_seconds)
```

The call record appears once the call has ended.

**The date range still applies.** The call id is matched only inside the
months your range covers, and with no `started_after` or `started_before`
that is the current and the previous month. To find an older call, pass a
range that covers when it was placed. So an empty page means the call has
not ended yet, it was placed outside the range, or the id names no call. It
is never an error.

One call writes two records: by default the list returns the visible
dial-out record, and the hidden leg that rang the subscriber comes back
only with `include_hidden=True`.

**Do not retry this blindly.** A call is undoable by nothing, and unlike
`faxes.send()` it carries no idempotency key: a retry is a second phone
call to a real person. If you never saw the answer, find out what happened
first.

A **502** is the one refusal you can act on without checking: the phone
system said no or could not be reached, nothing was dialled, and the
status it answered with is in `error.errors[0].meta["vendor_status"]` — so
a refusal and an outage can be told apart before you try again.

Name a `caller_id` to present a different number — E.164 with or without
the `+`, or a ten-digit North American number — `auto_answer=True` to ask
the subscriber's own phone to go off-hook instead of ringing, and `device=`
to choose which of that subscriber's registrations the call is placed from.
The device must be that subscriber's own: one that is not is refused with a
422 and nothing is dialled, whether it belongs to somebody else or does not
exist, because the two must not be distinguishable from outside.

The answer echoes what was actually **sent to the phone system**, which is
not always what you typed — this platform stores every caller id as E.164
*without* the plus, so `caller_id="+14074366118"` comes back as
`placed.caller_id == "14074366118"`.

## The async client

`AsyncRingivo` is the same client for programs already running on asyncio.
The constructor is identical, every method is awaited, and `async with`
replaces `with`:

```python
import asyncio
from pathlib import Path

from ringivo import AsyncRingivo


async def main():
    async with AsyncRingivo(
        base_url="https://api.yourprovider.example",
        client_id="0198c4a1-1f2e-7a3b-9c40-5f6e7d8a9b01",
        client_secret="9tK2xr4mQ7vBnZ1sD5hL0pWfC8jY3aE6",
        tenant="0198c4a1-3d4e-7f50-a1b2-c3d4e5f6a7b8",
        scopes=["fax:read", "fax:write"],
    ) as client:
        fax = await client.faxes.send(
            fax_account="0198c4a1-3c4d-7e5f-9061-2b3c4d5e6f70",
            to="+13025556789",
            file=Path("chart-4471.pdf"),
        )

        terminal = {"delivered", "partial", "cancelled", "failed"}
        while fax.status not in terminal:          # a rendered PDF needs one of these
            await asyncio.sleep(5)
            fax = await client.faxes.get(fax.id)

        if fax.status == "delivered":
            pdf = await client.faxes.media(fax.id)

asyncio.run(main())
```

Outside a context manager, release the connections with `await
client.aclose()` — the async spelling of `close()`.

Everything else reads the same. The exceptions are the same classes, the
returned `Fax`, `FaxPage` and `MediaLink` are the same frozen dataclasses,
and `webhooks.verify()` is the same function: it is pure computation with no
network, so there is nothing to await.

## Verify a webhook

Every delivery carries a `Ringivo-Signature` header. Check it before you
trust the body — this needs no client and no network:

```python
from ringivo import SignatureVerificationError, webhooks

@app.post("/hooks/fax")
def receive(request):
    try:
        webhooks.verify(
            request.body,                                  # the RAW bytes
            request.headers[webhooks.SIGNATURE_HEADER],
            secret="whsec_...",
        )
    except SignatureVerificationError:
        return Response(status=400)

    event = json.loads(request.body)
    ...
    return Response(status=202)
```

Two rules decide whether this works:

- **Give it the raw body.** Parsing the JSON and re-encoding it before
  verifying will fail, and correctly so — key order, escaping and number
  formatting are free choices no two encoders make alike. Reach for your
  framework's raw-body accessor.
- **Answer any 2XX to accept.** Deliveries are at-least-once: dedupe on
  `event_id`, because a retry carries the same one.

`verify()` returns None and raises `SignatureVerificationError` on any
failure — a stale timestamp, the wrong secret, a malformed header. During a
secret rotation the header carries two signatures and either secret
verifies, so a rotation costs you no deliveries.

## When something is refused

```python
from ringivo import ApiError, AuthenticationError

try:
    client.faxes.send(fax_account=account_id, to="not-e164", file=pdf)
except ApiError as error:
    error.status_code        # 422
    error.code               # "validation_failed" — the vocabulary to branch on
    error.errors[0].detail   # "The to field format is invalid."
    error.errors[0].source   # {"parameter": "to"}
```

`AuthenticationError` (a subclass) means the credential itself was refused —
the client had already replaced its token and retried once by then.
Connection failures, timeouts and TLS errors are httpx's own exceptions and
are deliberately not wrapped.

## What is in the box

| | Scope | |
|---|---|---|
| `Ringivo(base_url, client_id, client_secret, *, tenant, customer=None, scopes=None, timeout=30.0)` | — | The client. A context manager, or call `close()`. `tenant` is required. `scopes` is spelled as a keyword but required too — an empty one raises. |
| `AsyncRingivo(…same arguments…)` | — | The asyncio twin. An async context manager, or await `aclose()`. Every method below is awaited. |
| `client.faxes.send(*, fax_account, to, file=…\|urls=…, …)` | `fax:write` | Send one fax. Returns the accepted `Fax`. |
| `client.faxes.get(fax_id, *, include=None)` | `fax:read` | One fax, complete. |
| `client.faxes.list(*, filters…, after=None, before=None, page_size=None)` | `fax:read` | A `FaxPage`: iterable, with `next_cursor`. Default page size 25, ceiling 100. |
| `client.faxes.cancel(fax_id)` | `fax:write` | Withdraw a fax before it is answered. |
| `client.faxes.media(fax_id, *, format="pdf")` | `fax:read` | The document's `bytes`. |
| `client.faxes.media_link(fax_id, *, format="pdf")` | `fax:read` | The URL and its expiry, as a `MediaLink`. |
| `client.fax_accounts.list(*, customer=None, status=None, after=None, before=None, page_size=None)` | `fax:read` | A `FaxAccountPage`: iterable, with `next_cursor`. |
| `client.fax_accounts.get(fax_account_id)` | `fax:read` | One `FaxAccount`. |
| `client.fax_accounts.numbers(fax_account_id)` | `fax:read` | Every `FaxAccountNumber` routed to it, all pages walked. |
| `client.fax_accounts.create(*, customer, name, header_text=…, default_from_e164=…, retention_days=…, retention_pages=…)` | `fax-accounts:write` | Open an account for a customer. |
| `client.fax_accounts.update(fax_account_id, *, name=…, header_text=…, default_from_e164=…, retention_days=…, retention_pages=…, status=…)` | `fax-accounts:write` | A sparse PATCH: only what you pass. |
| `client.fax_accounts.delete(fax_account_id)` | `fax-accounts:write` | Delete the account and its pages. 409 while numbers route to it. |
| `client.fax_account_users.list(*, fax_account=None, user=None, after=None, before=None, page_size=None)` | `fax:read` | A `FaxAccountUserPage` of grants: iterable, with `next_cursor`. The two filters are "who can see this account?" and "what can this person see?". |
| `client.fax_account_users.get(fax_account_user_id)` | `fax:read` | One `FaxAccountUser`. |
| `client.fax_account_users.create(*, fax_account, user)` | `fax-accounts:write` | Grant this user access to this account's content. Both are required; neither can be changed afterwards. |
| `client.fax_account_users.delete(fax_account_user_id)` | `fax-accounts:write` | Withdraw the grant. The only way to undo one — there is no update route. |
| `client.webhook_endpoints.list(*, scope_type=None, scope_id=None, active=None, after=None, before=None, page_size=None)` | `webhooks:read` | A `WebhookEndpointPage`: iterable, with `next_cursor`. A `fax:read` token sees fax-account-scoped rows only. |
| `client.webhook_endpoints.get(webhook_endpoint_id)` | `webhooks:read` | One `WebhookEndpoint`. `secret` is always None here. |
| `client.webhook_endpoints.create(*, url, scope_type, scope_id, events, active=…)` | `webhooks:write` | Register an endpoint. `events` is required and must name at least one type. The only answer that carries the signing secret — store it. `fax:write` for a `fax_account` scope. |
| `client.webhook_endpoints.update(webhook_endpoint_id, *, url=…, events=…, active=…)` | `webhooks:write` | A sparse PATCH: only what you pass. The event list replaces the old one and must still name at least one type; `None` is never sent. The scope cannot change. |
| `client.webhook_endpoints.delete(webhook_endpoint_id)` | `webhooks:write` | Remove it. The fan-out stops; the deliveries stay. |
| `client.webhook_endpoints.rotate_secret(webhook_endpoint_id)` | `webhooks:write` | Mint a new secret and start the 24-hour grace window. |
| `client.webhook_deliveries.list(*, endpoint=None, event_type=None, status=None, after=None, before=None, page_size=None)` | `webhooks:read` | A `WebhookDeliveryPage` of what is still owed or was given up on. `status="dead"` is the one to ask after an outage. |
| `client.webhook_deliveries.get(webhook_delivery_id)` | `webhooks:read` | One `WebhookDelivery`. |
| `client.customers.list(*, ids=None, code=None, after=None, before=None, page_size=None)` | `customers:read` | A `CustomerPage`, newest first: iterable, with `next_cursor`. `ids=` reads several customers by id in one request — the ids `list()` and `get()` hand back — and combines with `code=`. A customer's `id` is what `client.pbx.*.list(customer=...)` takes. |
| `client.customers.get(customer_id)` | `customers:read` | One `Customer`. A customer that is not on your account is a 404, not a 403. |
| `client.pbx.subscribers.list(*, customer=None, user=None, search=None, kind=None, has_devices=None, after=None, before=None, page_size=None)` | `pbx-users:read` | A `PbxSubscriberPage`: iterable, with `next_cursor`. `user` is an EXACT extension; `search` is the directory search box; `kind` is one word, a comma list or a list of words; `has_devices` narrows to subscribers with (or without) a device. |
| `client.pbx.subscribers.get(subscriber_id)` | `pbx-users:read` | One `PbxSubscriber`. A subscriber you cannot reach is a 404, not a 403. |
| `client.pbx.subscribers.call(subscriber_id, *, destination, caller_id=None, auto_answer=False, device=None)` | `pbx-calls:write` | Ring this subscriber and dial `destination`. Returns the accepted `PbxCall` — a 202, no idempotency key, and an id that names the call on the phone system rather than a call record. Pass that id to `call_records.list(call_id=...)` once the call has ended. |
| `client.pbx.devices.list(*, customer=None, user=None, registered=None, after=None, before=None, page_size=None)` | `pbx-users:read` | A `PbxDevicePage`. `user` here is a `subscribers` ID, not an extension. |
| `client.pbx.devices.get(pbx_device_id)` | `pbx-users:read` | One `PbxDevice` — one registration, not one handset. |
| `client.pbx.call_records.list(*, customer=None, started_after=None, started_before=None, direction=None, fields=None, user=None, call_id=None, include_hidden=None, after=None, before=None, page_size=None)` | `pbx-call-records:read` | A `CallRecordPage`, newest first. The date range decides which months are read; no range means the current and previous one. `fields=` asks for the extended tier — a sparse fieldset, so it narrows rather than adds. `call_id` finds the records of one `subscribers.call()`, matched only inside the range's months. |
| `client.pbx.call_records.get(call_record_id)` | `pbx-call-records:read` | One `CallRecord`. A hidden record IS served here. |
| `client.pbx.call_records.recordings(call_record_id)` | `pbx-call-records:read` | Every capture of that call, as a plain `tuple[Recording, ...]` — NOT paginated: this is the captures of one call, not a walk over a table. Each `Recording.content_url` is a freshly minted, short-lived link. |
| `client.pbx.call_records.transcripts(call_record_id)` | `pbx-call-records:read` + `pbx-transcripts:read` | One `Transcript` per capture — `status="pending"` and every other field `None` for one with no words yet. Also NOT paginated. |
| `webhooks.verify(payload, header, secret, *, tolerance=300)` | — | Raises unless the body is genuine and fresh. |

`CallRecord`, `CallRecordPage`, `Customer`, `CustomerPage`, `Fax`,
`FaxAccount`, `FaxAccountNumber`, `FaxAccountPage`, `FaxAccountUser`,
`FaxAccountUserPage`, `FaxDocument`, `FaxPage`, `MediaLink`, `PbxCall`,
`PbxDevice`, `PbxDevicePage`, `PbxSubscriber`, `PbxSubscriberPage`, `Recording`,
`Transcript`, `WebhookDelivery`, `WebhookDeliveryPage`, `WebhookEndpoint`
and `WebhookEndpointPage` are frozen dataclasses, and each keeps the JSON
it was built from in `.raw` — so a field the API adds after this release
reaches you without a new SDK.

`NOT_GIVEN` is the sentinel the `create()` and `update()` calls on
`fax_accounts` and `webhook_endpoints` default every optional argument to.
You never need to pass it; it exists so that `None` can mean "clear this
field" on `fax_accounts`, rather than "I said nothing".

### Reaching an endpoint this client does not wrap

The table above is the fax, customer, webhook and phone-system surfaces.
For anything else the API offers, use `client.request()` — the same escape
hatch in both clients, awaited on the async one:

```python
response = client.request("GET", "/v1/sip-trunks")
trunks = response.json()["data"]
```

It carries your credential, your timeout, your User-Agent and the same
typed errors, and it hands back the `httpx.Response` untouched: past that
line the JSON is the API's own, not one of the frozen objects above.

`spec/openapi.yaml` in this repository is the reference for what those
endpoints take and answer. The same shapes are generated into
`ringivo._generated_types` as `TypedDict`s, which your type checker can
read; that module is private, machine-written, and rewritten wholesale
whenever the spec changes.

## Licence

MIT.

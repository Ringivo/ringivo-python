# ringivo

The Python client for the Ringivo fax API: send a fax, read one, list them,
cancel one, fetch its pages, and verify the webhooks that tell you what
happened.

```
pip install ringivo
```

Python 3.10 or newer. The only runtime dependency is `httpx` — plus
`typing-extensions` on Python 3.10, where `typing` does not yet carry
`NotRequired`.

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
`scopes=`, and raises `ValueError` naming the fix: a token minted without
them carries no scopes at all, so every route would refuse it — a 403 you
would otherwise meet in production rather than on the line that caused it.
Ask for more than your credential was granted and the extra is dropped
rather than refused, so a call can still fail later at the resource. The
scopes this client's calls need are `fax:read` and `fax:write`.

Pass `customer=` as well when your credential was issued for one customer
inside that tenant. Both selectors NAME a grant your provider already wrote
for your credential; they never widen one, and a selector no grant covers is
refused with a 403 however good your credentials are.

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

| | |
|---|---|
| `Ringivo(base_url, client_id, client_secret, *, tenant=None, customer=None, scopes=None, timeout=30.0)` | The client. A context manager, or call `close()`. `scopes` is spelled as a keyword but required — an empty one raises. |
| `AsyncRingivo(…same arguments…)` | The asyncio twin. An async context manager, or await `aclose()`. Every method below is awaited. |
| `client.faxes.send(*, fax_account, to, file=…\|urls=…, …)` | Send one fax. Returns the accepted `Fax`. |
| `client.faxes.get(fax_id, *, include=None)` | One fax, complete. |
| `client.faxes.list(*, filters…, after=None, before=None, page_size=None)` | A `FaxPage`: iterable, with `next_cursor`. Default page size 25, ceiling 100. |
| `client.faxes.cancel(fax_id)` | Withdraw a fax before it is answered. |
| `client.faxes.media(fax_id, *, format="pdf")` | The document's `bytes`. |
| `client.faxes.media_link(fax_id, *, format="pdf")` | The URL and its expiry, as a `MediaLink`. |
| `webhooks.verify(payload, header, secret, *, tolerance=300)` | Raises unless the body is genuine and fresh. |

`Fax`, `FaxDocument`, `FaxPage` and `MediaLink` are frozen dataclasses, and
each keeps the JSON it was built from in `.raw` — so a field the API adds
after this release reaches you without a new SDK.

### Reaching an endpoint this client does not wrap

The table above is the fax surface. For anything else the API offers, use
`client.request()` — the same escape hatch in both clients, awaited on the
async one:

```python
response = client.request("GET", "/v1/webhook-endpoints")
endpoints = response.json()["data"]
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

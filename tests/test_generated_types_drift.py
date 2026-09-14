"""The generated-types drift lock: every field a model reads off the wire
must still exist in `ringivo._generated_types`.

`_generated_types.py` is rewritten wholesale by `scripts/generate.sh`
whenever `spec/openapi.yaml` changes (see its own module docstring). Nothing
in this package CONSTRUCTS one of those `TypedDict`s, so pyright checking
them proves only that the file is internally consistent — a key a
`_from_*` classmethod in models.py reads could vanish from the regenerated
module, or get renamed, and every existing test would stay green: the
dataclasses in models.py read the wire defensively (`.get(key)`, never
`dict[key]`), so a missing key just becomes `None` on the object, silently.

This test makes the generated types LOAD-BEARING instead of merely
type-checked: it reads, off each classmethod in models.py that builds an
object from JSON, exactly which key it reads for each field, and asserts
that key is still a member of the matching generated `TypedDict`.

Two things keep this honest, in the same spirit as
test_grey_label.py::test_no_packaged_file_names_a_platform_brand_or_a_provider_host:

- The read table below is compared, per model, against the dataclass's OWN
  fields (`dataclasses.fields()`) — introspected, not retyped. A field
  added to a model without being added HERE (mapped to a generated key, or
  explicitly excluded with a reason) fails loudly, so nobody can add a
  field this test does not know about.
- Every failure is collected and reported together, naming the model, the
  field, and the generated `TypedDict` it went missing from — not just the
  first one found.
"""

from __future__ import annotations

import dataclasses
import typing

from ringivo import _generated_types as generated
from ringivo import models
from ringivo.models import MediaLink as MediaLinkModel  # models.MediaLink shadows generated.MediaLink


@dataclasses.dataclass(frozen=True)
class _Read:
    """One field a `_from_*` classmethod reads, and where it reads it from."""

    model: type
    field: str
    typed_dict: type
    key: str
    source: str  # which classmethod this read came from — for the failure message


def _phone_number_attributes() -> type:
    """The generated TypedDict for a phone-number's attributes block.

    FOUND BY ITS CONTENTS, NOT BY ITS NAME. The block is inline in the
    OpenAPI document, so datamodel-code-generator names it positionally —
    `Attributes1` at the time of writing — and that number moves whenever an
    inline schema is added ahead of it in the document. Naming it here would
    make this test fail on a renumbering that changed nothing, or worse,
    silently read a DIFFERENT block that had taken the name.

    The search reports its own denominator: zero matches and two matches are
    both broken, and neither may look like a pass.
    """
    wanted = {"e164", "status", "country", "activatedAt", "createdAt"}
    found = [
        value
        for value in vars(generated).values()
        if isinstance(value, type) and wanted <= set(getattr(value, "__annotations__", {}))
    ]
    assert len(found) == 1, (
        f"{len(found)} generated types carry {sorted(wanted)} "
        f"({[t.__name__ for t in found]}) — the lookup is broken, not the spec"
    )
    return found[0]


PhoneNumberAttributes = _phone_number_attributes()


def _webhook_delivery_relationships() -> type:
    """The generated TypedDict for a webhook delivery's relationships block.

    FOUND BY ITS CONTENTS, NOT BY ITS NAME, for the reason
    `_phone_number_attributes` gives: the block is inline in the OpenAPI
    document, so datamodel-code-generator names it positionally —
    `Relationships4` at the time of writing — and that number moves whenever
    an inline schema is added ahead of it.

    `endpoint` is the whole block and it is unique in the generated module,
    which is what makes one member enough to identify it. The search reports
    its own denominator either way.
    """
    wanted = {"endpoint"}
    found = [
        value
        for value in vars(generated).values()
        if isinstance(value, type) and wanted <= set(getattr(value, "__annotations__", {}))
    ]
    assert len(found) == 1, (
        f"{len(found)} generated types carry {sorted(wanted)} "
        f"({[t.__name__ for t in found]}) — the lookup is broken, not the spec"
    )
    return found[0]


WebhookDeliveryRelationships = _webhook_delivery_relationships()


def _fax_account_user_relationships() -> type:
    """The generated TypedDict for a grant's relationships block.

    REACHED THROUGH THE RESOURCE THAT DECLARES IT, not by a contents search
    like the two helpers above — because a contents search cannot tell this
    block apart from the one in the CREATE REQUEST. Both carry exactly
    `{faxAccount, user}` and nothing else, so `wanted <= annotations` matches
    two types and the denominator assertion those helpers rely on would fail
    on a spec that is perfectly healthy. Their optional-ness does not
    separate them either: the generated module is written with
    `from __future__ import annotations`, so every `NotRequired[...]` is an
    unresolved string and `__required_keys__` reports both blocks as fully
    required at runtime.

    `get_type_hints` resolves the `NotRequired[Relationships1]` forward
    reference to the class itself, which makes this exact rather than
    heuristic: it is the block THIS resource declares, whatever the
    generator numbered it.
    """
    hints = typing.get_type_hints(generated.FaxAccountUserResource)
    block = hints.get("relationships")
    assert isinstance(block, type), (
        f"FaxAccountUserResource declares no resolvable `relationships` member "
        f"(got {block!r}) — the lookup is broken, not the spec"
    )
    return block


FaxAccountUserRelationships = _fax_account_user_relationships()


# Every field a `_from_*` classmethod in models.py reads off a JSON shape,
# paired with the exact generated TypedDict and key that shape names it —
# read straight off the classmethod bodies, not guessed from the dataclass
# field name (which is why `from_` maps to the JSON key `"from"`, and why
# `client_reference` maps to `"clientReference"` from one classmethod and to
# `"client_reference"` from another — two different wire shapes, both real).
_READS: tuple[_Read, ...] = (
    # -- FaxDocument._from_json reads a FaxDocumentMetadata -----------------
    _Read(models.FaxDocument, "kind", generated.FaxDocumentMetadata, "kind", "FaxDocument._from_json"),
    _Read(models.FaxDocument, "ordinal", generated.FaxDocumentMetadata, "ordinal", "FaxDocument._from_json"),
    _Read(
        models.FaxDocument,
        "content_type",
        generated.FaxDocumentMetadata,
        "contentType",
        "FaxDocument._from_json",
    ),
    _Read(
        models.FaxDocument, "byte_size", generated.FaxDocumentMetadata, "byteSize", "FaxDocument._from_json"
    ),
    _Read(models.FaxDocument, "sha256", generated.FaxDocumentMetadata, "sha256", "FaxDocument._from_json"),
    _Read(models.FaxDocument, "pages", generated.FaxDocumentMetadata, "pages", "FaxDocument._from_json"),
    # -- Fax._from_resource reads a FaxResource (id) + its FaxAttributes ----
    _Read(models.Fax, "id", generated.FaxResource, "id", "Fax._from_resource"),
    _Read(models.Fax, "status", generated.FaxAttributes, "status", "Fax._from_resource"),
    _Read(models.Fax, "direction", generated.FaxAttributes, "direction", "Fax._from_resource"),
    _Read(models.Fax, "from_", generated.FaxAttributes, "from", "Fax._from_resource"),
    _Read(models.Fax, "to", generated.FaxAttributes, "to", "Fax._from_resource"),
    _Read(models.Fax, "failure_code", generated.FaxAttributes, "failureCode", "Fax._from_resource"),
    _Read(models.Fax, "pages_total", generated.FaxAttributes, "pagesTotal", "Fax._from_resource"),
    _Read(
        models.Fax, "pages_transferred", generated.FaxAttributes, "pagesTransferred", "Fax._from_resource"
    ),
    _Read(models.Fax, "partial", generated.FaxAttributes, "partial", "Fax._from_resource"),
    _Read(models.Fax, "attempt_count", generated.FaxAttributes, "attemptCount", "Fax._from_resource"),
    _Read(models.Fax, "resolution", generated.FaxAttributes, "resolution", "Fax._from_resource"),
    _Read(
        models.Fax, "client_reference", generated.FaxAttributes, "clientReference", "Fax._from_resource"
    ),
    _Read(models.Fax, "cover_page", generated.FaxAttributes, "coverPage", "Fax._from_resource"),
    _Read(models.Fax, "read", generated.FaxAttributes, "read", "Fax._from_resource"),
    _Read(models.Fax, "archived", generated.FaxAttributes, "archived", "Fax._from_resource"),
    _Read(models.Fax, "tags", generated.FaxAttributes, "tags", "Fax._from_resource"),
    _Read(models.Fax, "documents", generated.FaxAttributes, "documents", "Fax._from_resource"),
    _Read(models.Fax, "created_at", generated.FaxAttributes, "createdAt", "Fax._from_resource"),
    _Read(models.Fax, "completed_at", generated.FaxAttributes, "completedAt", "Fax._from_resource"),
    # -- Fax._from_acknowledgement reads the flat, already-snake_cased ------
    # `data` object `send()` answers — Data1 (SendFaxAccepted), the fuller
    # of the two acknowledgement shapes. `cancel()`'s answer is Data2, a
    # strict subset (id + status only); the other fields simply read back
    # None for a cancelled fax, which is correct, not a gap.
    _Read(models.Fax, "id", generated.Data1, "id", "Fax._from_acknowledgement"),
    _Read(models.Fax, "status", generated.Data1, "status", "Fax._from_acknowledgement"),
    _Read(models.Fax, "direction", generated.Data1, "direction", "Fax._from_acknowledgement"),
    _Read(models.Fax, "from_", generated.Data1, "from", "Fax._from_acknowledgement"),
    _Read(models.Fax, "to", generated.Data1, "to", "Fax._from_acknowledgement"),
    _Read(
        models.Fax,
        "client_reference",
        generated.Data1,
        "client_reference",
        "Fax._from_acknowledgement",
    ),
    _Read(models.Fax, "created_at", generated.Data1, "created_at", "Fax._from_acknowledgement"),
    # -- MediaLink._from_json reads the generated MediaLink verbatim --------
    # (same names on both sides: this endpoint's JSON is already
    # snake_cased, unlike the JSON:API attribute blocks above).
    _Read(MediaLinkModel, "url", generated.MediaLink, "url", "MediaLink._from_json"),
    _Read(MediaLinkModel, "expires_at", generated.MediaLink, "expires_at", "MediaLink._from_json"),
    _Read(MediaLinkModel, "byte_size", generated.MediaLink, "byte_size", "MediaLink._from_json"),
    _Read(MediaLinkModel, "sha256", generated.MediaLink, "sha256", "MediaLink._from_json"),
    # -- FaxAccount._from_resource reads a FaxAccountResource (id) + its ----
    # FaxAccountAttributes, plus the customer LINKAGE off its relationships.
    _Read(models.FaxAccount, "id", generated.FaxAccountResource, "id", "FaxAccount._from_resource"),
    _Read(models.FaxAccount, "name", generated.FaxAccountAttributes, "name", "FaxAccount._from_resource"),
    _Read(
        models.FaxAccount,
        "header_text",
        generated.FaxAccountAttributes,
        "headerText",
        "FaxAccount._from_resource",
    ),
    _Read(
        models.FaxAccount,
        "default_from_e164",
        generated.FaxAccountAttributes,
        "defaultFromE164",
        "FaxAccount._from_resource",
    ),
    _Read(
        models.FaxAccount,
        "retention_days",
        generated.FaxAccountAttributes,
        "retentionDays",
        "FaxAccount._from_resource",
    ),
    _Read(
        models.FaxAccount,
        "retention_pages",
        generated.FaxAccountAttributes,
        "retentionPages",
        "FaxAccount._from_resource",
    ),
    _Read(
        models.FaxAccount, "status", generated.FaxAccountAttributes, "status", "FaxAccount._from_resource"
    ),
    # The one read that starts on the RELATIONSHIPS block rather than the
    # attributes: `customer_id` walks customer -> data -> id, and the member
    # it reads off a shape the generator names is `customer`.
    _Read(
        models.FaxAccount,
        "customer_id",
        generated.FaxAccountRelationships,
        "customer",
        "FaxAccount._from_resource",
    ),
    _Read(
        models.FaxAccount,
        "created_at",
        generated.FaxAccountAttributes,
        "createdAt",
        "FaxAccount._from_resource",
    ),
    _Read(
        models.FaxAccount,
        "updated_at",
        generated.FaxAccountAttributes,
        "updatedAt",
        "FaxAccount._from_resource",
    ),
    # -- FaxAccountNumber._from_resource reads a PhoneNumberResource -------
    _Read(
        models.FaxAccountNumber,
        "id",
        generated.PhoneNumberResource,
        "id",
        "FaxAccountNumber._from_resource",
    ),
    _Read(
        models.FaxAccountNumber, "e164", PhoneNumberAttributes, "e164", "FaxAccountNumber._from_resource"
    ),
    _Read(
        models.FaxAccountNumber,
        "status",
        PhoneNumberAttributes,
        "status",
        "FaxAccountNumber._from_resource",
    ),
    _Read(
        models.FaxAccountNumber,
        "country",
        PhoneNumberAttributes,
        "country",
        "FaxAccountNumber._from_resource",
    ),
    _Read(
        models.FaxAccountNumber,
        "activated_at",
        PhoneNumberAttributes,
        "activatedAt",
        "FaxAccountNumber._from_resource",
    ),
    _Read(
        models.FaxAccountNumber,
        "created_at",
        PhoneNumberAttributes,
        "createdAt",
        "FaxAccountNumber._from_resource",
    ),
    # -- FaxAccountUser._from_resource reads a FaxAccountUserResource (id) -
    # + its FaxAccountUserAttributes, plus BOTH halves of the pair off the
    # relationships block. A grant is a pair and a fact, so the two linkage
    # reads are the substance of it rather than a decoration on it.
    _Read(
        models.FaxAccountUser,
        "id",
        generated.FaxAccountUserResource,
        "id",
        "FaxAccountUser._from_resource",
    ),
    _Read(
        models.FaxAccountUser,
        "fax_account_id",
        FaxAccountUserRelationships,
        "faxAccount",
        "FaxAccountUser._from_resource",
    ),
    _Read(
        models.FaxAccountUser,
        "user_id",
        FaxAccountUserRelationships,
        "user",
        "FaxAccountUser._from_resource",
    ),
    _Read(
        models.FaxAccountUser,
        "user_email",
        generated.FaxAccountUserAttributes,
        "userEmail",
        "FaxAccountUser._from_resource",
    ),
    _Read(
        models.FaxAccountUser,
        "created_at",
        generated.FaxAccountUserAttributes,
        "createdAt",
        "FaxAccountUser._from_resource",
    ),
    _Read(
        models.FaxAccountUser,
        "updated_at",
        generated.FaxAccountUserAttributes,
        "updatedAt",
        "FaxAccountUser._from_resource",
    ),
    # -- WebhookEndpoint._from_resource reads a WebhookEndpointResource ----
    # (id) + its WebhookEndpointAttributes. `secret` is read like any other
    # attribute: the platform sends it exactly once per secret, and the read
    # is the same one either way.
    _Read(
        models.WebhookEndpoint,
        "id",
        generated.WebhookEndpointResource,
        "id",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "scope_type",
        generated.WebhookEndpointAttributes,
        "scopeType",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "scope_id",
        generated.WebhookEndpointAttributes,
        "scopeId",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "url",
        generated.WebhookEndpointAttributes,
        "url",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "events",
        generated.WebhookEndpointAttributes,
        "events",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "active",
        generated.WebhookEndpointAttributes,
        "active",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "secret",
        generated.WebhookEndpointAttributes,
        "secret",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "secret_previous_expires_at",
        generated.WebhookEndpointAttributes,
        "secretPreviousExpiresAt",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "created_at",
        generated.WebhookEndpointAttributes,
        "createdAt",
        "WebhookEndpoint._from_resource",
    ),
    _Read(
        models.WebhookEndpoint,
        "updated_at",
        generated.WebhookEndpointAttributes,
        "updatedAt",
        "WebhookEndpoint._from_resource",
    ),
    # -- WebhookDelivery._from_resource reads a WebhookDeliveryResource ----
    # (id) + its WebhookDeliveryAttributes, plus the endpoint LINKAGE off
    # its relationships.
    _Read(
        models.WebhookDelivery,
        "id",
        generated.WebhookDeliveryResource,
        "id",
        "WebhookDelivery._from_resource",
    ),
    # The read that starts on the RELATIONSHIPS block rather than the
    # attributes, the way FaxAccount.customer_id does: `endpoint_id` walks
    # endpoint -> data -> id, and the member it reads is `endpoint`.
    _Read(
        models.WebhookDelivery,
        "endpoint_id",
        WebhookDeliveryRelationships,
        "endpoint",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "event_id",
        generated.WebhookDeliveryAttributes,
        "eventId",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "event_type",
        generated.WebhookDeliveryAttributes,
        "eventType",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "payload_sha256",
        generated.WebhookDeliveryAttributes,
        "payloadSha256",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "status",
        generated.WebhookDeliveryAttributes,
        "status",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "attempt_no",
        generated.WebhookDeliveryAttributes,
        "attemptNo",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "status_code",
        generated.WebhookDeliveryAttributes,
        "statusCode",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "duration_ms",
        generated.WebhookDeliveryAttributes,
        "durationMs",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "error",
        generated.WebhookDeliveryAttributes,
        "error",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "next_attempt_at",
        generated.WebhookDeliveryAttributes,
        "nextAttemptAt",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "dead_at",
        generated.WebhookDeliveryAttributes,
        "deadAt",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "created_at",
        generated.WebhookDeliveryAttributes,
        "createdAt",
        "WebhookDelivery._from_resource",
    ),
    _Read(
        models.WebhookDelivery,
        "updated_at",
        generated.WebhookDeliveryAttributes,
        "updatedAt",
        "WebhookDelivery._from_resource",
    ),
)

# Fields a model carries that no `_from_*` classmethod reads off a generated
# shape — named individually, with why, so a field landing here by mistake
# (rather than by a deliberate choice) is a one-line diff to catch in
# review.
_EXCLUDED: dict[tuple[type, str], str] = {
    (models.FaxDocument, "raw"): "holds the whole source mapping this object was built from",
    (models.Fax, "raw"): "holds the whole source mapping this object was built from",
    (models.Fax, "idempotent_replay"): (
        "read off the Idempotent-Replay response HEADER in faxes.py, never off the JSON body"
    ),
    (MediaLinkModel, "raw"): "holds the whole source mapping this object was built from",
    (models.FaxAccount, "raw"): "holds the whole source mapping this object was built from",
    (models.FaxAccountNumber, "raw"): "holds the whole source mapping this object was built from",
    (models.FaxAccountUser, "raw"): "holds the whole source mapping this object was built from",
    (models.WebhookEndpoint, "raw"): "holds the whole source mapping this object was built from",
    (models.WebhookDelivery, "raw"): "holds the whole source mapping this object was built from",
}

# The other direction, and the only entry that needs it: a key the generated
# types DO carry which no model reads ON PURPOSE. `_EXCLUDED` above cannot
# say this — it is keyed by a dataclass field, and the point here is that
# there is no field.
#
# Recorded rather than merely omitted, because a silent omission and an
# oversight look identical in a diff, and this one is a decision: the spec
# documents `deliveredAt` as ALWAYS null, kept only so a client generated
# against an older spec still parses, and warns against reading it as a
# status. Reading it into `WebhookDelivery` would invite exactly that.
#
# The assertion below is that the key still EXISTS. That is what keeps this
# note honest: the day the API drops the member, this fails and the right fix
# is to delete these lines, not to add a field.
_NOT_READ: dict[tuple[type, str], str] = {
    (generated.WebhookDeliveryAttributes, "deliveredAt"): (
        "always null and kept only for clients generated against an older spec; a delivery "
        "that lands leaves no row at all, and `status` is pending or dead and nothing else"
    ),
}

# The five page models — `FaxPage`, `FaxAccountPage`, `FaxAccountUserPage`,
# `WebhookEndpointPage` and `WebhookDeliveryPage` — are deliberately not
# covered: unlike the models above, none has a `_from_*` classmethod of its
# own. `faxes.py`, `fax_accounts.py`, `fax_account_users.py`,
# `webhook_endpoints.py` and `webhook_deliveries.py` build them directly,
# reading `meta.page.nextCursor` and `links.next` with their own module-level
# helpers, not a method models.py owns. This test's scope is "what models.py
# reads"; a drift lock for those modules' own reads would be a second test.
_MODELS: tuple[type, ...] = (
    models.FaxDocument,
    models.Fax,
    MediaLinkModel,
    models.FaxAccount,
    models.FaxAccountNumber,
    models.FaxAccountUser,
    models.WebhookEndpoint,
    models.WebhookDelivery,
)


def _generated_keys(typed_dict: type) -> set[str]:
    """Every key `typed_dict` declares, inheritance included.

    Unlike an ordinary class, a `TypedDict`'s metaclass merges an
    inheriting class's own fields with every base's AT CLASS-CREATION TIME
    and stores the merged result directly on the subclass — so
    `typed_dict.__annotations__` already carries inherited keys, with no
    MRO walk needed. Confirmed against `FaxReceivedEventData(FaxEventData)`:
    its own `__annotations__` holds all 19 keys (`FaxEventData`'s 18 plus
    its own `render_failed`), not 1.
    """
    return set(typed_dict.__annotations__)


def test_every_field_a_model_reads_is_covered_by_the_read_table() -> None:
    """The DENOMINATOR check: a model this test forgot about is not a model
    with nothing wrong — it is a model never examined. `dataclasses.fields()`
    is the independent source of truth for what each dataclass actually
    carries; `_READS` and `_EXCLUDED` above must account for every one of
    them, in both directions, or this whole test proves nothing about that
    model.
    """
    assert len(_MODELS) == 8, f"only {[m.__name__ for m in _MODELS]} was searched — the sweep is broken"

    mismatches: dict[str, str] = {}
    for model in _MODELS:
        actual = {f.name for f in dataclasses.fields(model)}
        covered = {r.field for r in _READS if r.model is model}
        excluded = {field for (m, field) in _EXCLUDED if m is model}
        accounted = covered | excluded
        if accounted != actual:
            missing = actual - accounted
            extra = accounted - actual
            mismatches[model.__name__] = (
                f"missing from the read table or exclusion list: {sorted(missing)}; "
                f"listed but not an actual field any more: {sorted(extra)}"
            )

    assert mismatches == {}, mismatches


def test_every_field_a_model_reads_exists_in_the_generated_types() -> None:
    assert len(_READS) >= 80, f"only {len(_READS)} reads were checked — the sweep is broken"

    failures: list[str] = []
    for read in _READS:
        if read.key not in _generated_keys(read.typed_dict):
            failures.append(
                f"{read.model.__name__}.{read.field} ({read.source}) reads "
                f"{read.typed_dict.__name__}[{read.key!r}], which no longer exists"
            )

    assert failures == [], "\n".join(failures)


def test_every_deliberately_unread_key_still_exists_to_be_unread() -> None:
    """The `_NOT_READ` table above says "the API sends this and we ignore it,
    for this reason". That is a claim about the generated types as much as
    about the models, so it is checked: a key that has since been removed
    makes the note a statement about a shape nobody sends any more, and the
    fix is to delete the note rather than to leave a reader believing a field
    was skipped on purpose when it no longer arrives at all.
    """
    assert _NOT_READ, "the not-read table is empty — either say so or delete this test"

    stale = [
        f"{typed_dict.__name__}[{key!r}] is recorded as deliberately unread "
        f"({reason}), but it is not a member any more"
        for (typed_dict, key), reason in _NOT_READ.items()
        if key not in _generated_keys(typed_dict)
    ]

    assert stale == [], "\n".join(stale)

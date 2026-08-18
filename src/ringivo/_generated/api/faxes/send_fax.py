from http import HTTPStatus
from typing import Any

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.error_document import ErrorDocument
from ...models.send_fax_accepted import SendFaxAccepted
from ...models.send_fax_multipart_request import SendFaxMultipartRequest
from ...models.send_fax_url_request import SendFaxUrlRequest
from ...types import UNSET, Response


def _get_kwargs(
    *,
    body: SendFaxMultipartRequest | SendFaxUrlRequest | Unset = UNSET,
    idempotency_key: str,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["Idempotency-Key"] = idempotency_key

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/v1/faxes",
    }

    if isinstance(body, SendFaxMultipartRequest):
        _kwargs["files"] = body.to_multipart()

        headers["Content-Type"] = "multipart/form-data; boundary=+++"
    if isinstance(body, SendFaxUrlRequest):
        _kwargs["json"] = body.to_dict()

        headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> ErrorDocument | SendFaxAccepted | None:
    if response.status_code == 202:
        response_202 = SendFaxAccepted.from_dict(response.json())

        return response_202

    if response.status_code == 401:
        response_401 = ErrorDocument.from_dict(response.json())

        return response_401

    if response.status_code == 403:
        response_403 = ErrorDocument.from_dict(response.json())

        return response_403

    if response.status_code == 409:
        response_409 = ErrorDocument.from_dict(response.json())

        return response_409

    if response.status_code == 413:
        response_413 = ErrorDocument.from_dict(response.json())

        return response_413

    if response.status_code == 415:
        response_415 = ErrorDocument.from_dict(response.json())

        return response_415

    if response.status_code == 422:
        response_422 = ErrorDocument.from_dict(response.json())

        return response_422

    if response.status_code == 429:
        response_429 = ErrorDocument.from_dict(response.json())

        return response_429

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[ErrorDocument | SendFaxAccepted]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: SendFaxMultipartRequest | SendFaxUrlRequest | Unset = UNSET,
    idempotency_key: str,
) -> Response[ErrorDocument | SendFaxAccepted]:
    """Send a fax

     Accepts one outbound fax and answers **202** — the render and the call happen after this
    returns. Watch it finish with `GET /v1/faxes/{fax}`; there is no callback to wait on, and no
    retry to perform.

    **The body is flat, and it is not a JSON:API document.** A body carrying `data` is refused
    outright rather than half-obeyed. Send either `multipart/form-data` with `documents[]` file
    parts, or JSON whose `documents` is a list of `https` URLs — never both in one request.

    **`Idempotency-Key` is mandatory.** A second POST carrying the same key replays the first
    rather than sending a second fax, and the replay is marked with an `Idempotent-Replay: true`
    response header. That header is the ONLY thing that tells the two apart: the body is the
    same fax either way.

    Args:
        idempotency_key (str):
        body (SendFaxMultipartRequest): Upload the pages themselves. Up to five parts, sniffed on
            their bytes rather than on their
            names — PDF, TIFF, PNG and JPEG are what a fax can be made of.

            Send the `tags` and `cover_page` parts as plain JSON text, not as a `Blob`: append the
            JSON
            string directly as the part body, because a `Blob` part gains a filename and arrives as an
            upload instead of a field, which fails validation without saying why.
        body (SendFaxUrlRequest): Point at the pages instead of uploading them. Every URL must be
            `https` on a public host, and
            uploads and URLs may not be mixed in one request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | SendFaxAccepted]
    """

    kwargs = _get_kwargs(
        body=body,
        idempotency_key=idempotency_key,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: SendFaxMultipartRequest | SendFaxUrlRequest | Unset = UNSET,
    idempotency_key: str,
) -> ErrorDocument | SendFaxAccepted | None:
    """Send a fax

     Accepts one outbound fax and answers **202** — the render and the call happen after this
    returns. Watch it finish with `GET /v1/faxes/{fax}`; there is no callback to wait on, and no
    retry to perform.

    **The body is flat, and it is not a JSON:API document.** A body carrying `data` is refused
    outright rather than half-obeyed. Send either `multipart/form-data` with `documents[]` file
    parts, or JSON whose `documents` is a list of `https` URLs — never both in one request.

    **`Idempotency-Key` is mandatory.** A second POST carrying the same key replays the first
    rather than sending a second fax, and the replay is marked with an `Idempotent-Replay: true`
    response header. That header is the ONLY thing that tells the two apart: the body is the
    same fax either way.

    Args:
        idempotency_key (str):
        body (SendFaxMultipartRequest): Upload the pages themselves. Up to five parts, sniffed on
            their bytes rather than on their
            names — PDF, TIFF, PNG and JPEG are what a fax can be made of.

            Send the `tags` and `cover_page` parts as plain JSON text, not as a `Blob`: append the
            JSON
            string directly as the part body, because a `Blob` part gains a filename and arrives as an
            upload instead of a field, which fails validation without saying why.
        body (SendFaxUrlRequest): Point at the pages instead of uploading them. Every URL must be
            `https` on a public host, and
            uploads and URLs may not be mixed in one request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | SendFaxAccepted
    """

    return sync_detailed(
        client=client,
        body=body,
        idempotency_key=idempotency_key,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: SendFaxMultipartRequest | SendFaxUrlRequest | Unset = UNSET,
    idempotency_key: str,
) -> Response[ErrorDocument | SendFaxAccepted]:
    """Send a fax

     Accepts one outbound fax and answers **202** — the render and the call happen after this
    returns. Watch it finish with `GET /v1/faxes/{fax}`; there is no callback to wait on, and no
    retry to perform.

    **The body is flat, and it is not a JSON:API document.** A body carrying `data` is refused
    outright rather than half-obeyed. Send either `multipart/form-data` with `documents[]` file
    parts, or JSON whose `documents` is a list of `https` URLs — never both in one request.

    **`Idempotency-Key` is mandatory.** A second POST carrying the same key replays the first
    rather than sending a second fax, and the replay is marked with an `Idempotent-Replay: true`
    response header. That header is the ONLY thing that tells the two apart: the body is the
    same fax either way.

    Args:
        idempotency_key (str):
        body (SendFaxMultipartRequest): Upload the pages themselves. Up to five parts, sniffed on
            their bytes rather than on their
            names — PDF, TIFF, PNG and JPEG are what a fax can be made of.

            Send the `tags` and `cover_page` parts as plain JSON text, not as a `Blob`: append the
            JSON
            string directly as the part body, because a `Blob` part gains a filename and arrives as an
            upload instead of a field, which fails validation without saying why.
        body (SendFaxUrlRequest): Point at the pages instead of uploading them. Every URL must be
            `https` on a public host, and
            uploads and URLs may not be mixed in one request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorDocument | SendFaxAccepted]
    """

    kwargs = _get_kwargs(
        body=body,
        idempotency_key=idempotency_key,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: SendFaxMultipartRequest | SendFaxUrlRequest | Unset = UNSET,
    idempotency_key: str,
) -> ErrorDocument | SendFaxAccepted | None:
    """Send a fax

     Accepts one outbound fax and answers **202** — the render and the call happen after this
    returns. Watch it finish with `GET /v1/faxes/{fax}`; there is no callback to wait on, and no
    retry to perform.

    **The body is flat, and it is not a JSON:API document.** A body carrying `data` is refused
    outright rather than half-obeyed. Send either `multipart/form-data` with `documents[]` file
    parts, or JSON whose `documents` is a list of `https` URLs — never both in one request.

    **`Idempotency-Key` is mandatory.** A second POST carrying the same key replays the first
    rather than sending a second fax, and the replay is marked with an `Idempotent-Replay: true`
    response header. That header is the ONLY thing that tells the two apart: the body is the
    same fax either way.

    Args:
        idempotency_key (str):
        body (SendFaxMultipartRequest): Upload the pages themselves. Up to five parts, sniffed on
            their bytes rather than on their
            names — PDF, TIFF, PNG and JPEG are what a fax can be made of.

            Send the `tags` and `cover_page` parts as plain JSON text, not as a `Blob`: append the
            JSON
            string directly as the part body, because a `Blob` part gains a filename and arrives as an
            upload instead of a field, which fails validation without saying why.
        body (SendFaxUrlRequest): Point at the pages instead of uploading them. Every URL must be
            `https` on a public host, and
            uploads and URLs may not be mixed in one request.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorDocument | SendFaxAccepted
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            idempotency_key=idempotency_key,
        )
    ).parsed

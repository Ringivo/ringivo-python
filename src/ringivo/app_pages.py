"""The app page: one web page of yours in the menu of your customers' phone apps.

The calls are on the two namespaces whose ids they take:
`customers.set_app_page()`, `get_app_page()` and `clear_app_page()` for a
customer, and the same three on `pbx.subscribers` for one subscriber. This
module holds what the six share: the body a set sends and the reading of
the answer.

-- ONE PAGE: AN ADDRESS, A LABEL AND AN ICON -----------------------------------
A page is shown as one entry in the menu of the iOS app, the Android app
and the web phone. It is set for a customer, or for one of its subscribers.
A subscriber with no page of its own gets the customer's.

-- YOUR PAGE SIGNS ITS USERS IN ITSELF ------------------------------------------
The apps load the address exactly as you set it, and give your page nothing
about the user. Use your own sign-in on the page. NEVER PUT A SECRET IN THE
ADDRESS: anyone can read it. A value of your own in it, such as a customer
id, is a hint only and proves nothing about the user. To match a user who
signed in on your page to a phone user, read `pbx.subscribers.list()`.

-- A SET IS A WHOLE REPLACEMENT, AND SAFE TO SEND AGAIN -----------------------
`set_app_page()` sends `url`, `label` and, when you pass one, `icon`, and
replaces the whole page. It is a POST with a FLAT JSON body, not a JSON:API
document. Sending the same set again changes nothing, so after a 502 (the
phone system failed part way) or a 409 (another change of the same page is
running), send the same call again. The phone system applies a change some
seconds after it answers; a read shows it a few seconds later.

-- WHAT IS REFUSED -------------------------------------------------------------
The API checks the address and the label, and this client passes them
through unchanged: a refused member is an `ApiError` with status 422 whose
`errors[0].source.pointer` names it (`/url`, `/label`, `/icon`), and
nothing is written. A customer with no phone system is a 409.

Setting and clearing need `pbx-app-pages:write`, on a credential for your
whole account. Reading needs `pbx-app-pages:read`, which the write scope
includes.
"""

from __future__ import annotations

from typing import Any

from .faxes import _data_object
from .models import AppPage

__all__: list[str] = []


def _app_page_body(*, url: str, label: str, icon: str | None) -> dict[str, str]:
    """The flat JSON body of a set. `icon` is left off when it is None, and
    the API then uses `open_in_new`."""
    body = {"url": url, "label": label}
    if icon is not None:
        body["icon"] = icon
    return body


def _app_page(payload: Any) -> AppPage:
    """One `AppPageDocument`, as the object this package hands back."""
    return AppPage._from_resource(_data_object(payload))

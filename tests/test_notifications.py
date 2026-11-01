from upb.notifications import (
    Notification,
    classify,
    clear_all_notifications,
    clear_notification,
    deduplicate,
    fetch_notification_body,
    fetch_notifications,
    parse_alert,
)


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, data):
        self._data = data
        self.calls = []

    def get(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return FakeResponse(self._data)


SAMPLE_ALERT = {
    "id": 15098093,
    "event": "asn.new.assignment",
    "eventDate": {"epochSecond": 1793185813, "nano": 76000000},
    "formattedEventDate": "28/10/2026, 11:10",
    "fromDisplayName": "Nuno Romeu Cardoso Sequeira",
    "fromUser": "4bd0e301-1658-4679-8c5a-0d69a9973497",
    "toUser": "1f64a6ea-bdef-437f-8b23-a5d227e54ce7",
    "title": "Functional Prototype",
    "siteId": "6c18216c-afe8-11f1-a582-a684bbaf23e5",
    "siteTitle": "SIA (26/1.4)",
    "url": "https://virtual.ipb.pt/portal/directtool/...",
    "ref": "/assignment/a/6c18216c-afe8-11f1-a582-a684bbaf23e5/d2978956",
    "deferred": False,
}


def test_parse_alert():
    n = parse_alert(SAMPLE_ALERT)
    assert n.notif_id == 15098093
    assert n.event == "asn.new.assignment"
    assert n.category == "assignment"
    assert n.title == "Functional Prototype"
    assert n.site_title == "SIA (26/1.4)"
    assert n.from_display_name == "Nuno Romeu Cardoso Sequeira"
    assert n.event_date is not None
    assert n.formatted_event_date == "28/10/2026, 11:10"
    assert n.deferred is False


def test_fetch_notifications():
    client = FakeClient({"alerts": [SAMPLE_ALERT]})
    notifs = fetch_notifications(client)
    assert len(notifs) == 1
    assert notifs[0].notif_id == 15098093
    assert client.calls[0][0] == "direct/portal/bullhornAlerts.json"


def test_classify():
    assert classify("asn.new.assignment") == "assignment"
    assert classify("annc.new") == "announcement"
    assert classify("msg.new") == "message"
    assert classify("forums.new") == "forum"
    assert classify("profile.friend.request") == "social"
    assert classify("something.unknown") == "other"
    assert classify(None) == "other"


def test_clear_notification():
    client = FakeClient({})
    clear_notification(client, 123)
    assert client.calls[0][0] == "direct/portal/clearBullhornAlert"
    assert client.calls[0][1] == {"params": {"id": 123}}


def test_clear_all_notifications():
    client = FakeClient({})
    clear_all_notifications(client)
    assert client.calls[0][0] == "direct/portal/clearAllBullhornAlerts"


def test_deduplicate_keeps_latest_per_ref():
    a = Notification(notif_id=1, ref="/assignment/x", title="Old")
    b = Notification(notif_id=2, ref="/assignment/x", title="New")
    c = Notification(notif_id=3, ref=None, title="NoRef")
    out = deduplicate([a, b, c])
    kept_ids = {n.notif_id for n in out}
    assert kept_ids == {2, 3}
    assert len(out) == 2


def test_deduplicate_keeps_distinct_refs():
    a = Notification(notif_id=1, ref="/assignment/x")
    b = Notification(notif_id=2, ref="/assignment/y")
    assert len(deduplicate([a, b])) == 2


def test_deduplicate_orders_most_recent_first():
    a = Notification(notif_id=1, ref="/announcement/x")
    b = Notification(notif_id=5, ref="/assignment/x")
    c = Notification(notif_id=3, ref=None)
    out = deduplicate([a, b, c])
    assert [n.notif_id for n in out] == [5, 3, 1]


def test_fetch_notification_body():
    client = FakeClient({"body": "<p>Hello</p><p>World</p>"})
    html, text = fetch_notification_body(client, "/announcement/msg/x/main/y")
    assert html == "<p>Hello</p><p>World</p>"
    assert text == "Hello\nWorld"
    assert client.calls[0][0] == "direct/announcement/msg/x/main/y.json"


def test_fetch_notification_body_missing():
    client = FakeClient({"title": "no body"})
    html, text = fetch_notification_body(client, "/announcement/msg/x/main/y")
    assert html is None
    assert text is None


class RoutingClient:
    def __init__(self, routes):
        self.routes = routes

    def get(self, path, **kwargs):
        return FakeResponse(self.routes.get(path, {}))


def test_fetch_notifications_includes_bodies():
    client = RoutingClient(
        {
            "direct/portal/bullhornAlerts.json": {"alerts": [SAMPLE_ALERT]},
            "direct" + SAMPLE_ALERT["ref"] + ".json": {"body": "<p>Hi there</p>"},
        }
    )
    notifs = fetch_notifications(client)
    assert len(notifs) == 1
    assert notifs[0].body == "<p>Hi there</p>"
    assert notifs[0].body_text == "Hi there"

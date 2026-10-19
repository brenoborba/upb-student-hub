from upb.models import Assignment, Attachment


def test_attachment_fields():
    a = Attachment(name="enunciado.pdf", url="https://example.com/a.pdf")
    assert a.name == "enunciado.pdf"
    assert a.url == "https://example.com/a.pdf"


def test_assignment_defaults():
    a = Assignment(course="Matemática", title="Trabalho 2")
    assert a.course == "Matemática"
    assert a.title == "Trabalho 2"
    assert a.url is None
    assert a.open_at is None
    assert a.due_at is None
    assert a.status is None
    assert a.status_label is None
    assert a.description is None
    assert a.description_text is None
    assert a.attachments == []


def test_to_dict():
    a = Assignment(
        course="Matemática",
        title="Trabalho 2",
        url="https://virtual.ipb.pt/portal/site/x",
        open_at="2026-10-01T09:00:00+01:00",
        due_at="2026-11-05T23:55:00+00:00",
        status="submitted",
        status_label="Entregue",
        description="<p>...</p>",
        description_text="Instruções",
        attachments=[Attachment("enunciado.pdf", "https://example.com/e.pdf")],
    )
    d = a.to_dict()
    assert d["course"] == "Matemática"
    assert d["assignment"] == "Trabalho 2"
    assert d["open_at"] == "2026-10-01T09:00:00+01:00"
    assert d["due_at"] == "2026-11-05T23:55:00+00:00"
    assert d["status"] == "submitted"
    assert d["status_label"] == "Entregue"
    assert d["description"] == "<p>...</p>"
    assert d["description_text"] == "Instruções"
    assert d["attachments"] == [
        {"name": "enunciado.pdf", "url": "https://example.com/e.pdf"}
    ]
    assert d["url"] == "https://virtual.ipb.pt/portal/site/x"


def test_to_dict_empty_attachments():
    a = Assignment(course="C", title="T")
    assert a.to_dict()["attachments"] == []

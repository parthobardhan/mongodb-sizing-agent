from scripts.clear_local_mongo import slugify_use_case


def test_slugify_use_case():
    assert slugify_use_case("claims-document-history") == "sizing_claims_document_history"


def test_slugify_strips_special_chars():
    assert slugify_use_case("Claims Document History!!!") == "sizing_claims_document_history"
    assert slugify_use_case("  foo/bar  ") == "sizing_foo_bar"

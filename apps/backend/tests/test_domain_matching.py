from luneta.services import domain_matching


def test_domain_matching_placeholder() -> None:
    # Real tests will cover subdomain handling like correo.ugr.es.
    assert hasattr(domain_matching, "__doc__")


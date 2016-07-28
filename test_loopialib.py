import pytest

from loopialib import Loopia, LoopiaError, DnsRecord
from mock import Mock

try:
    ustr = unicode
except NameError:
    ustr = str

class MockRpcClient(object):
    def __init__(self):
        self._intercepts = {}

    def intercept(self, method):
        def wrapper(func):
            self._intercepts[method] = Mock(wraps=func)
            return self._intercepts[method]
        return wrapper

    def __getattr__(self, attr):
        try:
            return super(MockRpcClient, self).__getattr__(sattr)
        except AttributeError:
            return self._intercepts[attr]

class LoopiaMock(Loopia):
    def __init__(self, user, password):
        self.user = user
        self.password = password
        self._client = MockRpcClient()

    def intercept(self, method):
        return self._client.intercept(method)


@pytest.fixture
def record():
    return DnsRecord(type="A", ttl=3600, priority=0, data="127.0.0.1", id=1)


@pytest.fixture
def record_obj():
    return {
        "type": "A",
        "ttl": 3600,
        "priority": 0,
        "rdata": "127.0.0.1",
        "record_id": 1
    }


@pytest.fixture
def loopia():
    return LoopiaMock("user", "password")


def test_dns_record(record):
    assert record.type == "A"
    assert record.ttl == 3600
    assert record.priority == 0
    assert record.data == "127.0.0.1"
    assert record.id == 1


def test_dns_record_equality():
    r1 = DnsRecord(type="A", ttl=3600, priority=0, data="127.0.0.1", id=1)
    r2 = DnsRecord(type="A", ttl=3600, priority=0, data="127.0.0.1", id=1)
    r3 = DnsRecord(type="A", ttl=3600, priority=0, data="127.0.0.1", id=2)

    assert r1 == r2
    assert r1 != r3
    assert r2 != r3


def test_dns_record_replace(record):
    assert record.replace(type="TXT").type == "TXT"
    assert record.type == "A"


@pytest.mark.parametrize("type", [
    "A",
    "AAAA",
    "CERT",
    "CNAME",
    "HINFO",
    "HIP",
    "IPSECKEY",
    "LOC",
    "MX",
    "NAPTR",
    "NS",
    "SRV",
    "SSHFP",
    "TXT",
])
def test_dns_record_types(record, type):
    assert record.replace(type=type).type == type


@pytest.mark.parametrize("type", [
    "a",
    "ANAME",
    "TEXT",
])
def test_dns_record_invalid_type(record, type):
    with pytest.raises(ValueError):
        record.replace(type=type)


@pytest.mark.parametrize("ttl, exc_cls", [
    ("900", TypeError),
    (True, TypeError),
    (-1, ValueError),
])
def test_dns_record_invalid_ttl(record, ttl, exc_cls):
    with pytest.raises(exc_cls):
        record.replace(ttl=ttl)


@pytest.mark.parametrize("priority, exc_cls", [
    ("900", TypeError),
    (True, TypeError),
    (-1, ValueError),
])
def test_dns_record_invalid_priority(record, priority, exc_cls):
    with pytest.raises(exc_cls):
        record.replace(priority=priority)

@pytest.mark.parametrize("id, exc_cls", [
    ("900", TypeError),
    (True, TypeError),
    (-1, ValueError),
])
def test_dns_record_invalid_ttl(record, id, exc_cls):
    with pytest.raises(exc_cls):
        record.replace(id=id)


def test_dns_record_repr(record):
    assert repr(record) == \
        "DnsRecord(type='A', ttl=3600, priority=0, data='127.0.0.1', id=1)"


def test_dns_record_from_dict(record_obj, record):
    assert DnsRecord.from_dict(record_obj) == record


def test_dns_record_to_dict(record, record_obj):
    assert record.to_dict() == record_obj


@pytest.mark.parametrize("code", [
    "AUTH_ERROR",
    "DOMAIN_OCCUPIED",
    "RATE_LIMITED",
    "BAD_INDATA",
    "INSUFFICIENT_FUNDS",
])
def test_loopia_error_from_code(code):
    assert not ustr(LoopiaError.from_code(code)).startswith("Unknown")


def test_loopia_construct():
    loopia = Loopia("user", "password")
    assert loopia.user == "user"
    assert loopia.password == "password"


def test_loopia_get_zone_records(loopia, record_obj, record):
    @loopia.intercept("getZoneRecords")
    def get_zone_records(user, password, domain, sub_domain):
        assert user == loopia.user
        assert password == loopia.password
        assert domain == "foo.bar"
        assert sub_domain == "@"

        return [record_obj]

    assert not get_zone_records.called
    assert loopia.get_zone_records("foo.bar", sub_domain=None) == [record]
    assert get_zone_records.called


def test_loopia_get_zone_records_wrong_domain(loopia):
    @loopia.intercept("getZoneRecords")
    def get_zone_records(user, password, domain, sub_domain):
        assert domain == "foo.bar"
        assert sub_domain == "@"

        return ["UNKNOWN_ERROR"]

    with pytest.raises(LoopiaError):
        loopia.get_zone_records("foo.bar", sub_domain=None)


def test_update_zone_record(loopia, record_obj, record):
    @loopia.intercept("updateZoneRecord")
    def update_zone_record(user, password, domain, sub_domain, r_obj):
        assert user == loopia.user
        assert password == loopia.password
        assert domain == "foo.bar"
        assert sub_domain == "@"
        assert r_obj == record_obj

        return ["OK"]

    assert not update_zone_record.called
    loopia.update_zone_record(record, "foo.bar", sub_domain=None)
    assert update_zone_record.called


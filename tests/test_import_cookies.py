import io

from scripts.import_cookies import parse_cookie_string, read_cookie_input


def test_parse_cookie_string_adds_playwright_fields():
    cookies = parse_cookie_string("a=1; bigmodel_token_production=token")

    assert cookies == [
        {
            "name": "a",
            "value": "1",
            "domain": "bigmodel.cn",
            "path": "/",
            "httpOnly": False,
            "secure": True,
        },
        {
            "name": "bigmodel_token_production",
            "value": "token",
            "domain": "bigmodel.cn",
            "path": "/",
            "httpOnly": False,
            "secure": True,
        },
    ]


def test_read_cookie_input_supports_stdin():
    cookie_string, account_id = read_cookie_input(
        ["--stdin", "2"],
        stdin=io.StringIO("session=abc\n"),
        env={},
    )

    assert cookie_string == "session=abc"
    assert account_id == 2


def test_read_cookie_input_supports_env_var():
    cookie_string, account_id = read_cookie_input(
        ["--env", "BIGMODEL_COOKIE", "3"],
        stdin=io.StringIO(""),
        env={"BIGMODEL_COOKIE": "session=abc"},
    )

    assert cookie_string == "session=abc"
    assert account_id == 3


def test_read_cookie_input_keeps_legacy_argument_mode():
    cookie_string, account_id = read_cookie_input(
        ["session=abc", "4"],
        stdin=io.StringIO(""),
        env={},
    )

    assert cookie_string == "session=abc"
    assert account_id == 4

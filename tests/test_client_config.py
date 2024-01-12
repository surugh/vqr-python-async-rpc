"""
Test module exposing various errors which can occur when configuring `VqrcoinRPC`.
"""

import pytest

from bitcoinrpc import VqrcoinRPC


def test_unknown_httpx_option_provided_raises() -> None:
    """`httpx.AsyncClient` is strict about its init kwargs."""
    with pytest.raises(TypeError):
        VqrcoinRPC.from_config(
            "http://localhost:8332",
            ("rpc_user", "rpc_passwd"),
            unknown_httpx_kwarg="foo",
        )


def test_incorrect_httpx_option_provided_raises() -> None:
    """Existing option, but incorrectly used, results in `httpx.AsyncClient` error."""
    with pytest.raises(AttributeError):
        VqrcoinRPC.from_config(
            "http://localhost:8332",
            ("rpc_user", "rpc_passwd"),
            limits="Not like this.",
        )

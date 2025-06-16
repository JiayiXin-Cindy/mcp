"""Tests for SMUS-admin-agent module."""

import pytest


@pytest.mark.xfail
def test_that_you_wrote_tests():
    """Test that you wrote tests."""
    from textwrap import dedent

    assertion_string = dedent(
        """\
    No, you have not written tests.

    However, unless a test is run, the pytest execution will fail
    due to no tests or missing coverage. So, write a real test and
    then remove this!
    """
    )
    assert False, assertion_string


def test_smus_admin_agent_importable():
    """Test smus_admin_agent is importable."""
    import smus_admin_agent  # noqa: F401

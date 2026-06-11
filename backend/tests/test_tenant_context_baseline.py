import pytest
from fastapi import HTTPException

from app.core.principal import Principal
from app.core.tenant_context import assert_same_tenant, tenant_filter


def test_assert_same_tenant_allows_matching_tenant():
    principal = Principal(
        user_id="user_1",
        tenant_id="tenant_a",
        roles=["customer_admin"],
    )

    assert_same_tenant("tenant_a", principal)


def test_assert_same_tenant_blocks_cross_tenant_access():
    principal = Principal(
        user_id="user_1",
        tenant_id="tenant_a",
        roles=["customer_admin"],
    )

    with pytest.raises(HTTPException) as exc:
        assert_same_tenant("tenant_b", principal)

    assert exc.value.status_code == 404
    assert exc.value.detail["error"]["code"] == "NOT_FOUND"


def test_assert_same_tenant_blocks_missing_resource_tenant():
    principal = Principal(
        user_id="user_1",
        tenant_id="tenant_a",
        roles=["customer_admin"],
    )

    with pytest.raises(HTTPException) as exc:
        assert_same_tenant(None, principal)

    assert exc.value.status_code == 404


def test_tenant_filter_uses_principal_tenant_only():
    principal = Principal(
        user_id="user_1",
        tenant_id="tenant_a",
        roles=["customer_admin"],
    )

    assert tenant_filter(principal) == {"tenant_id": "tenant_a"}

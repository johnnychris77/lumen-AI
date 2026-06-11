import pytest
from fastapi import HTTPException

from app.core.object_authorization import ProtectedObject, require_object_permission
from app.core.principal import Principal


def test_customer_admin_can_access_own_tenant_object():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["customer_admin"])
    obj = ProtectedObject(object_id="obj1", tenant_id="tenant_a", workflow_type="capa")

    require_object_permission(principal, obj, action="read")


def test_cross_tenant_object_access_returns_404():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["customer_admin"])
    obj = ProtectedObject(object_id="obj1", tenant_id="tenant_b", workflow_type="capa")

    with pytest.raises(HTTPException) as exc:
        require_object_permission(principal, obj, action="read")

    assert exc.value.status_code == 404
    assert exc.value.detail["error"]["code"] == "NOT_FOUND"


def test_auditor_can_read_audit_object():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["auditor"])
    obj = ProtectedObject(object_id="obj1", tenant_id="tenant_a", workflow_type="audit")

    require_object_permission(principal, obj, action="read")


def test_auditor_cannot_update_object():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["auditor"])
    obj = ProtectedObject(object_id="obj1", tenant_id="tenant_a", workflow_type="audit")

    with pytest.raises(HTTPException) as exc:
        require_object_permission(principal, obj, action="update")

    assert exc.value.status_code == 403
    assert exc.value.detail["error"]["code"] == "ACCESS_DENIED"


def test_vendor_user_can_access_assigned_vendor_object():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["vendor_user"])
    obj = ProtectedObject(
        object_id="obj1",
        tenant_id="tenant_a",
        workflow_type="vendor",
        vendor_id="vendor_a",
    )

    require_object_permission(
        principal,
        obj,
        action="read",
        principal_vendor_id="vendor_a",
    )


def test_vendor_user_cannot_access_other_vendor_object():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["vendor_user"])
    obj = ProtectedObject(
        object_id="obj1",
        tenant_id="tenant_a",
        workflow_type="vendor",
        vendor_id="vendor_b",
    )

    with pytest.raises(HTTPException) as exc:
        require_object_permission(
            principal,
            obj,
            action="read",
            principal_vendor_id="vendor_a",
        )

    assert exc.value.status_code == 404


def test_quality_manager_can_access_quality_workflow():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["quality_manager"])
    obj = ProtectedObject(object_id="obj1", tenant_id="tenant_a", workflow_type="inspection")

    require_object_permission(principal, obj, action="read")


def test_quality_manager_cannot_access_vendor_workflow():
    principal = Principal(user_id="u1", tenant_id="tenant_a", roles=["quality_manager"])
    obj = ProtectedObject(object_id="obj1", tenant_id="tenant_a", workflow_type="vendor")

    with pytest.raises(HTTPException) as exc:
        require_object_permission(principal, obj, action="read")

    assert exc.value.status_code == 403

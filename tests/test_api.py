VALID_CEDAR = b'permit(principal, action, resource);'
INVALID_CEDAR = b'this is not cedar { garbage'


def test_login_success(client, seeded_data):
    resp = client.post("/api/auth/login", json={"username": "alice_test", "password": "alicepw"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "alice_test"


def test_login_wrong_password(client, seeded_data):
    resp = client.post("/api/auth/login", json={"username": "alice_test", "password": "wrong"})
    assert resp.status_code == 401


def test_protected_endpoint_requires_token(client, seeded_data):
    resp = client.get("/api/tenants")
    assert resp.status_code == 401


def test_list_tenants_scoped_to_user(client, seeded_data, login):
    headers = login("alice_test", "alicepw")
    resp = client.get("/api/tenants", headers=headers)
    assert {t["slug"] for t in resp.json()} == {"acme-prod-test"}


def test_upload_valid_cedar_succeeds(client, seeded_data, login):
    headers = login("alice_test", "alicepw")
    tenant_id = seeded_data["acme_prod"].id
    resp = client.post(
        f"/api/tenants/{tenant_id}/policy-files", headers=headers,
        files={"file": ("policy.cedar", VALID_CEDAR, "text/plain")},
    )
    assert resp.status_code == 201
    assert resp.json()["current_commit_hash"]


def test_upload_invalid_cedar_rejected(client, seeded_data, login):
    headers = login("alice_test", "alicepw")
    tenant_id = seeded_data["acme_prod"].id
    resp = client.post(
        f"/api/tenants/{tenant_id}/policy-files", headers=headers,
        files={"file": ("bad.cedar", INVALID_CEDAR, "text/plain")},
    )
    assert resp.status_code == 400
    assert "Invalid Cedar policy syntax" in resp.json()["detail"]


def test_upload_duplicate_filename_conflicts(client, seeded_data, login):
    headers = login("alice_test", "alicepw")
    tenant_id = seeded_data["acme_prod"].id
    client.post(f"/api/tenants/{tenant_id}/policy-files", headers=headers,
                files={"file": ("dup.cedar", VALID_CEDAR, "text/plain")})
    resp = client.post(f"/api/tenants/{tenant_id}/policy-files", headers=headers,
                        files={"file": ("dup.cedar", VALID_CEDAR, "text/plain")})
    assert resp.status_code == 409


def test_upload_to_tenant_user_does_not_belong_to_returns_404(client, seeded_data, login):
    headers = login("alice_test", "alicepw")  # alice only has acme-prod
    globex_id = seeded_data["globex_prod"].id
    resp = client.post(f"/api/tenants/{globex_id}/policy-files", headers=headers,
                        files={"file": ("x.cedar", VALID_CEDAR, "text/plain")})
    assert resp.status_code == 404


def test_download_own_tenant_file(client, seeded_data, login):
    headers = login("alice_test", "alicepw")
    tenant_id = seeded_data["acme_prod"].id
    upload = client.post(f"/api/tenants/{tenant_id}/policy-files", headers=headers,
                          files={"file": ("policy.cedar", VALID_CEDAR, "text/plain")})
    file_id = upload.json()["id"]

    resp = client.get(f"/api/tenants/{tenant_id}/policy-files/{file_id}/download", headers=headers)
    assert resp.status_code == 200
    assert resp.content == VALID_CEDAR


def test_cross_tenant_download_is_blocked(client, seeded_data, login):
    """The critical isolation test: carol (globex) must not be able to
    download acme-prod's file, even with a hand-crafted request using the
    real acme-prod tenant_id and a real file_id."""
    alice_headers = login("alice_test", "alicepw")
    acme_id = seeded_data["acme_prod"].id
    upload = client.post(f"/api/tenants/{acme_id}/policy-files", headers=alice_headers,
                          files={"file": ("secret.cedar", VALID_CEDAR, "text/plain")})
    file_id = upload.json()["id"]

    carol_headers = login("carol_test", "carolpw")
    resp = client.get(f"/api/tenants/{acme_id}/policy-files/{file_id}/download", headers=carol_headers)
    assert resp.status_code == 404  # not 403 -- doesn't confirm the tenant exists


def test_cross_tenant_delete_is_blocked(client, seeded_data, login):
    alice_headers = login("alice_test", "alicepw")
    acme_id = seeded_data["acme_prod"].id
    upload = client.post(f"/api/tenants/{acme_id}/policy-files", headers=alice_headers,
                          files={"file": ("secret2.cedar", VALID_CEDAR, "text/plain")})
    file_id = upload.json()["id"]

    carol_headers = login("carol_test", "carolpw")
    resp = client.delete(f"/api/tenants/{acme_id}/policy-files/{file_id}", headers=carol_headers)
    assert resp.status_code == 404

    list_resp = client.get(f"/api/tenants/{acme_id}/policy-files", headers=alice_headers)
    assert "secret2.cedar" in {f["filename"] for f in list_resp.json()}  # confirm it wasn't actually deleted


def test_delete_own_file_succeeds(client, seeded_data, login):
    headers = login("alice_test", "alicepw")
    tenant_id = seeded_data["acme_prod"].id
    upload = client.post(f"/api/tenants/{tenant_id}/policy-files", headers=headers,
                          files={"file": ("todelete.cedar", VALID_CEDAR, "text/plain")})
    file_id = upload.json()["id"]

    resp = client.delete(f"/api/tenants/{tenant_id}/policy-files/{file_id}", headers=headers)
    assert resp.status_code == 204

    list_resp = client.get(f"/api/tenants/{tenant_id}/policy-files", headers=headers)
    assert "todelete.cedar" not in {f["filename"] for f in list_resp.json()}


def test_download_nonexistent_file_id_404s(client, seeded_data, login):
    headers = login("alice_test", "alicepw")
    tenant_id = seeded_data["acme_prod"].id
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/tenants/{tenant_id}/policy-files/{fake_id}/download", headers=headers)
    assert resp.status_code == 404
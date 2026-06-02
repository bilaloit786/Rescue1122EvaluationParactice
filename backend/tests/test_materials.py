class TestLearningMaterials:
    async def test_list_requires_login(self, client):
        resp = await client.get("/api/materials")
        assert resp.status_code == 401

    async def test_admin_uploads_and_staff_lists_downloads(self, client, admin_headers, staff_headers):
        files = {"file": ("rescue-guide.pdf", b"%PDF-1.4\nsample pdf\n%%EOF", "application/pdf")}
        resp = await client.post(
            "/api/admin/materials",
            headers=admin_headers,
            data={"title": "Rescue Guide"},
            files=files,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Rescue Guide"
        assert body["filename"] == "rescue-guide.pdf"
        assert body["file_size"] > 0

        list_resp = await client.get("/api/materials", headers=staff_headers)
        assert list_resp.status_code == 200
        materials = list_resp.json()
        assert len(materials) == 1
        assert materials[0]["title"] == "Rescue Guide"

        download_resp = await client.get(f"/api/materials/{body['id']}/download", headers=staff_headers)
        assert download_resp.status_code == 200
        assert download_resp.headers["content-type"].startswith("application/pdf")
        assert download_resp.headers["content-disposition"].startswith("attachment;")
        assert download_resp.content.startswith(b"%PDF")

    async def test_staff_cannot_upload(self, client, staff_headers):
        files = {"file": ("staff.pdf", b"%PDF-1.4\nsample pdf\n%%EOF", "application/pdf")}
        resp = await client.post(
            "/api/admin/materials",
            headers=staff_headers,
            data={"title": "Staff Upload"},
            files=files,
        )
        assert resp.status_code == 403

    async def test_rejects_non_pdf_upload(self, client, admin_headers):
        files = {"file": ("notes.txt", b"plain text", "text/plain")}
        resp = await client.post(
            "/api/admin/materials",
            headers=admin_headers,
            data={"title": "Notes"},
            files=files,
        )
        assert resp.status_code == 400

    async def test_accepts_pdf_with_generic_browser_content_type(self, client, admin_headers, staff_headers):
        files = {"file": ("browser-upload.pdf", b" \n%PDF-1.4\nsample pdf\n%%EOF", "application/octet-stream")}
        resp = await client.post(
            "/api/admin/materials",
            headers=admin_headers,
            data={"title": "Browser Upload"},
            files=files,
        )
        assert resp.status_code == 201
        material_id = resp.json()["id"]

        list_resp = await client.get("/api/materials", headers=staff_headers)
        assert list_resp.status_code == 200
        assert list_resp.json()[0]["title"] == "Browser Upload"

        download_resp = await client.get(f"/api/materials/{material_id}/download", headers=staff_headers)
        assert download_resp.status_code == 200
        assert download_resp.content.lstrip().startswith(b"%PDF")

    async def test_admin_delete_hides_material(self, client, admin_headers, staff_headers):
        files = {"file": ("delete-me.pdf", b"%PDF-1.4\nsample pdf\n%%EOF", "application/pdf")}
        created = await client.post(
            "/api/admin/materials",
            headers=admin_headers,
            data={"title": "Delete Me"},
            files=files,
        )
        material_id = created.json()["id"]

        delete_resp = await client.delete(f"/api/admin/materials/{material_id}", headers=admin_headers)
        assert delete_resp.status_code == 204

        list_resp = await client.get("/api/materials", headers=staff_headers)
        assert list_resp.status_code == 200
        assert list_resp.json() == []

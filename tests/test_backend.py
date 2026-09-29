"""Offline backend regressions. Never discover or execute test_full_system.py."""
import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import Mock, patch
import uuid

ROOT = Path(__file__).resolve().parents[1]


class BackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT / ".test-data" / f"backend_{uuid.uuid4().hex}"
        cls.environment = patch.dict(os.environ, {"KIDS_STUDIO_TESTING": "1", "KIDS_STUDIO_DATA_DIR": str(cls.root)})
        cls.environment.start()
        original_connect = socket.socket.connect

        def isolated_connect(sock, address):
            # Windows asyncio constructs its self-pipe with a loopback socket pair.
            if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
                return original_connect(sock, address)
            raise AssertionError("External network access forbidden in offline tests")

        cls.network = patch("socket.socket.connect", new=isolated_connect)
        cls.network.start()
        try:
            from fastapi.testclient import TestClient
            cls.storage = importlib.import_module("app.storage")
            cls.config = importlib.import_module("app.config")
            cls.projects = importlib.import_module("app.services.project_service")
            cls.ai = importlib.import_module("app.services.ai_service")
            cls.youtube = importlib.import_module("app.services.youtube_service")
            cls.models = importlib.import_module("app.models")
            cls.main = importlib.import_module("app.main")
            cls.TestClient = TestClient
        except Exception:
            cls.network.stop()
            cls.environment.stop()
            shutil.rmtree(cls.root, ignore_errors=True)
            raise

    @classmethod
    def tearDownClass(cls):
        cls.network.stop()
        cls.environment.stop()
        shutil.rmtree(cls.root, ignore_errors=True)
        try:
            cls.root.parent.rmdir()
        except OSError:
            pass

    def setUp(self):
        self.data = self.root / uuid.uuid4().hex
        self.data.mkdir(parents=True)
        self.patches = [
            patch.object(self.storage, "DATA_DIR", self.data),
            patch.object(self.storage, "PROJECTS_DIR", self.data / "projects"),
            patch.object(self.projects, "PROJECTS_DIR", self.data / "projects"),
            patch.object(self.youtube, "PROJECTS_DIR", self.data / "projects"),
            patch.object(self.youtube, "CONFIG_DIR", self.data / "config"),
            patch.object(self.youtube, "TOKEN_FILE", self.data / "config" / "google_token.json"),
            patch.object(self.youtube, "CLIENT_SECRET_FILE", self.data / "config" / "client_secret.json"),
            patch.object(self.config, "CONFIG_FILE", self.data / "config" / "studio_settings.json"),
            patch("requests.sessions.Session.request", side_effect=AssertionError("Provider call forbidden")),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])
        self.client = self.TestClient(self.main.app)
        self.addCleanup(self.client.close)
        response = self.client.get("/api/session")
        self.assertEqual(response.status_code, 200)
        self.headers = {"X-Studio-Token": response.json()["csrf_token"]}
        self.youtube._oauth_states.clear()
        self.youtube.UPLOAD_JOBS.clear()

    def save(self, project_id="sample", **data):
        return self.projects.save_project(project_id, {"title_english": "Example", **data})

    def test_paths_reject_windows_and_posix_escapes(self):
        for value in ("..", "../outside", "..\\outside", "C:\\outside", "\\\\server\\share", "/outside", "x:stream", "x.", "CON", "nul.mp4"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.storage.contained_path(self.data, value)
        for value in ("..", "x\\y", "x/y", "C:", "CON", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.storage.project_path(value)
        self.assertEqual(self.storage.project_path("safe-slug", "renders", "clip.mp4"), self.data / "projects" / "safe-slug" / "renders" / "clip.mp4")

    def test_symlink_escape_rejected(self):
        target = self.data / "outside"
        target.mkdir()
        base = self.data / "base"
        base.mkdir()
        try:
            (base / "escape").symlink_to(target, target_is_directory=True)
        except OSError:
            self.skipTest("Host does not permit test symlinks")
        with self.assertRaises(ValueError):
            self.storage.contained_path(base, "escape", "file.json")
        projects = self.data / "projects"
        projects.mkdir()
        (projects / "victim").mkdir()
        (projects / "alias").symlink_to(projects / "victim", target_is_directory=True)
        with self.assertRaises(ValueError):
            self.storage.project_path("alias")

    def test_atomic_failure_preserves_original(self):
        path = self.data / "state.json"
        self.storage.atomic_write_json(path, {"revision": 1})
        with patch("app.storage.os.replace", side_effect=OSError("simulated failure")):
            with self.assertRaises(OSError):
                self.storage.atomic_write_json(path, {"revision": 2})
        self.assertEqual(json.loads(path.read_text())["revision"], 1)
        self.assertEqual(list(self.data.glob("*.pending")), [])

    def test_atomic_staging_basename_is_short_and_same_directory(self):
        path = self.data / "destination.json"
        with patch("app.storage.os.replace", wraps=os.replace) as replace:
            self.storage.atomic_write_json(path, {"saved": True})
        staging, destination = map(Path, replace.call_args.args)
        self.assertEqual(destination, path)
        self.assertEqual(staging.parent, path.parent)
        self.assertRegex(staging.name, r"^\.[0-9a-f]{32}\.pending$")
        self.assertEqual(json.loads(path.read_text()), {"saved": True})

    def test_legacy_revision_and_conflicts(self):
        path = self.storage.project_path("legacy", "project.json")
        self.storage.atomic_write_json(path, {"title_english": "Legacy", "scenes": []})
        project = self.projects.get_project("legacy")
        self.assertEqual(project["revision"], 0)
        saved = self.projects.save_project("legacy", project)
        self.assertEqual(saved["revision"], 1)
        with self.assertRaises(self.projects.RevisionConflict):
            self.projects.save_project("legacy", project)
        self.assertEqual(self.projects.get_project("legacy")["revision"], 1)

    def test_api_save_conflict_and_nested_validation(self):
        original = self.save()
        first = self.client.put("/api/projects/sample", json={"project_data": original}, headers=self.headers)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["project"]["revision"], 2)
        stale = self.client.put("/api/projects/sample", json={"project_data": original}, headers=self.headers)
        self.assertEqual(stale.status_code, 409)
        invalid = self.client.put("/api/projects/sample", json={"project_data": {"scenes": [None]}}, headers=self.headers)
        self.assertEqual(invalid.status_code, 422)

    def test_corrupt_project_preserved(self):
        path = self.storage.project_path("broken", "project.json")
        path.parent.mkdir(parents=True)
        path.write_text("{bad", encoding="utf-8")
        response = self.client.get("/api/projects/broken")
        self.assertEqual(response.status_code, 409)
        with self.assertRaises(self.projects.ProjectCorruptError):
            self.save("broken")
        self.assertEqual(path.read_text(), "{bad")
        self.assertEqual(self.projects.list_projects()[0]["error"], "project_unreadable")

    def test_delete_recoverable_and_does_not_reseed(self):
        self.save()
        self.assertTrue(self.projects.delete_project("sample"))
        self.assertIsNone(self.projects.get_project("sample"))
        self.assertEqual(self.projects.list_projects(), [])
        self.assertEqual(len(list((self.data / "trash").glob("sample_*/project.json"))), 1)

    def test_media_lease_blocks_delete_and_cannot_recreate_deleted_project(self):
        self.save()
        with self.storage.project_operation("sample"):
            self.assertTrue(self.storage.project_is_busy("sample"))
            response = self.client.delete("/api/projects/sample", headers=self.headers)
            self.assertEqual(response.status_code, 409)
            self.assertIsNotNone(self.projects.get_project("sample"))
        self.assertFalse(self.storage.project_is_busy("sample"))
        self.assertTrue(self.projects.delete_project("sample"))
        with self.assertRaises(self.storage.StorageError):
            with self.storage.project_operation("sample"):
                self.fail("Deleted project acquired a media lease")
        self.assertFalse(self.storage.project_path("sample").exists())

    def test_audio_render_lease_blocks_delete_but_allows_save(self):
        project = self.save()
        with self.storage.project_operation("sample"):
            response = self.client.delete("/api/projects/sample", headers=self.headers)
            self.assertEqual(response.status_code, 409)
            saved = self.client.put("/api/projects/sample", json={"project_data": project}, headers=self.headers)
            self.assertEqual(saved.status_code, 200)
        self.assertTrue(self.projects.delete_project("sample"))

    @unittest.skipUnless(os.path.normcase("SAMPLE") == os.path.normcase("sample"), "Filesystem case normalization test requires Windows")
    def test_windows_case_alias_shares_lease_and_rejects_different_spelling(self):
        project = self.save("MixedCase")
        self.assertEqual(project["id"], "MixedCase")
        with self.storage.project_operation("MixedCase"):
            self.assertTrue(self.storage.project_is_busy("mixedcase"))
            self.assertEqual(self.client.delete("/api/projects/MIXEDCASE", headers=self.headers).status_code, 409)
        self.assertFalse(self.storage.project_is_busy("MIXEDCASE"))
        self.assertEqual(self.projects.get_project("MixedCase")["id"], "MixedCase")
        with self.assertRaises(self.storage.StorageError):
            self.projects.get_project("mixedcase")
        with self.assertRaises(self.storage.StorageError):
            self.storage.media_input_fingerprint({**project, "id": "MIXEDCASE", "episode_id": "MIXEDCASE"})
        self.assertEqual(self.client.get("/api/projects/mixedcase").status_code, 400)

    @unittest.skipUnless(os.path.normcase("SAMPLE") == os.path.normcase("sample"), "Filesystem case normalization test requires Windows")
    def test_windows_case_alias_concurrent_save_cannot_lose_revision(self):
        path = self.storage.project_path("sample", "project.json")
        self.storage.atomic_write_json(path, {"id": "sample", "episode_id": "sample", "revision": 7, "scenes": []})
        project = self.projects.get_project("sample")
        ready = threading.Barrier(2)

        def save_case(identifier):
            ready.wait(timeout=5)
            try:
                return self.projects.save_project(identifier, copy.deepcopy(project))["revision"]
            except self.storage.StorageError:
                return "alias_rejected"

        with ThreadPoolExecutor(max_workers=2) as workers:
            outcomes = list(workers.map(save_case, ["sample", "SAMPLE"]))
        self.assertCountEqual(outcomes, [8, "alias_rejected"])
        self.assertEqual(self.projects.get_project("sample")["revision"], 8)
        key = os.path.normcase("sample")
        self.assertIn(key, self.storage._locks)
        self.assertNotIn("SAMPLE", self.storage._locks)

    def test_legacy_media_removed_in_response_only(self):
        path = self.storage.project_path("legacy", "project.json")
        legacy = {"scenes": [{"audio_url": "/api/audio/clip/scene_01_voice.wav"}], "rendered_video": {"filename": "episode_old.mp4"}}
        self.storage.atomic_write_json(path, legacy)
        response = self.projects.get_project("legacy")
        self.assertNotIn("audio_url", response["scenes"][0])
        self.assertNotIn("rendered_video", response)
        self.assertTrue(response["migration_warnings"])
        self.assertEqual(json.loads(path.read_text()), legacy)

    def test_cross_project_media_suffix_is_removed(self):
        audio = self.storage.project_path("sample", "audio", "clip.wav")
        audio.parent.mkdir(parents=True)
        audio.write_bytes(b"synthetic")
        project = self.save(scenes=[{"audio_url": "/api/audio/clip/sample/../other/clip.wav"}])
        self.assertNotIn("audio_url", project["scenes"][0])
        self.assertTrue(project["migration_warnings"])

    def test_session_required_and_cross_origin_rejected(self):
        self.assertEqual(self.client.post("/api/settings/", json={}).status_code, 403)
        self.assertEqual(self.client.get("/api/settings/", headers={"Origin": "https://evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/api/session", headers={"Sec-Fetch-Site": "cross-site"}).status_code, 403)
        self.assertEqual(self.client.get("/api/health", headers={"Host": "evil.example"}).status_code, 403)
        self.assertEqual(self.client.get("/api/health", headers={"Origin": "http://testserver:9999"}).status_code, 403)
        with patch.dict(os.environ, {"KIDS_STUDIO_TESTING": "0"}):
            self.assertEqual(self.client.get("/api/health").status_code, 403)

    def test_settings_redaction_preserve_and_explicit_clear(self):
        body = {"openai_api_key": "synthetic-test-value", "active_provider": "openai", "active_model": "gpt-example"}
        response = self.client.post("/api/settings/", json=body, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("synthetic-test-value", response.text)
        self.assertTrue(response.json()["settings"]["openai_api_key_configured"])
        self.client.post("/api/settings/", json={"active_model": "gpt-other"}, headers=self.headers)
        self.assertEqual(self.config.load_settings().openai_api_key, "synthetic-test-value")
        self.client.post("/api/settings/", json={"openai_api_key": ""}, headers=self.headers)
        self.assertFalse(self.client.get("/api/settings/").json()["openai_api_key_configured"])

    def test_corrupt_settings_not_reset_by_get(self):
        self.config.CONFIG_FILE.parent.mkdir(parents=True)
        self.config.CONFIG_FILE.write_text("{broken")
        self.assertEqual(self.client.get("/api/settings/").status_code, 409)
        self.assertEqual(self.config.CONFIG_FILE.read_text(), "{broken")

    def test_documented_environment_settings_and_original_model_default(self):
        environment = {
            "KIDS_STUDIO_TESTING": "1",
            "AZURE_OPENAI_API_KEY": "synthetic-documented-key",
            "AZURE_API_KEY": "synthetic-legacy-alias",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
            "OLLAMA_URL": "http://127.0.0.1:11435",
        }
        with patch.dict(os.environ, environment, clear=True):
            settings = self.config.load_settings()
            self.assertEqual(settings.active_model, "gemini-3.6-flash")
            self.assertEqual(settings.azure_api_key, "synthetic-documented-key")
            self.assertEqual(settings.azure_endpoint, "https://example.openai.azure.com")
            self.assertEqual(settings.ollama_url, "http://127.0.0.1:11435")
            del os.environ["AZURE_OPENAI_API_KEY"]
            self.assertEqual(self.config.load_settings().azure_api_key, "synthetic-legacy-alias")
        self.assertFalse(self.config.CONFIG_FILE.exists())

    def test_persisted_cleared_settings_are_not_overlaid_by_environment(self):
        self.config.save_settings(self.config.StudioSettings(azure_api_key="", azure_endpoint="", ollama_url="http://localhost:11434"))
        with patch.dict(os.environ, {
            "AZURE_OPENAI_API_KEY": "synthetic-environment-key",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com",
            "OLLAMA_URL": "http://127.0.0.1:11435",
        }):
            settings = self.config.load_settings()
        self.assertEqual(settings.azure_api_key, "")
        self.assertEqual(settings.azure_endpoint, "")
        self.assertEqual(settings.ollama_url, "http://localhost:11434")

    def test_provider_selection_not_model_name(self):
        settings = self.config.StudioSettings(active_provider="ollama", active_model="mistral")
        with patch.object(self.ai, "load_settings", return_value=settings), patch.object(self.ai, "call_ollama", return_value="local") as local, patch.object(self.ai, "call_gemini") as cloud:
            self.assertEqual(self.ai.generate_ai_text("example"), "local")
            local.assert_called_once()
            cloud.assert_not_called()

    def test_endpoint_settings_reject_remote_ollama(self):
        response = self.client.post("/api/settings/", json={"ollama_url": "http://example.com"}, headers=self.headers)
        self.assertEqual(response.status_code, 422)
        response = self.client.post("/api/settings/", json={"active_provider": "unknown"}, headers=self.headers)
        self.assertEqual(response.status_code, 422)

    def test_malformed_ai_json_is_failure(self):
        with patch.object(self.ai, "generate_ai_text", return_value="[null]"):
            with self.assertRaises(self.ai.GenerationError):
                self.ai.brainstorm_ideas("Letters", "Toddlers", "Sharing")
        idea = self.ai.get_grounded_topic_ideas("Letters", "Toddlers")[0]
        with patch.object(self.ai, "generate_ai_text", return_value='{"scenes":"abcde"}'):
            with self.assertRaises(self.ai.GenerationError):
                self.ai.generate_full_script(idea, ["dad"])

    def test_fallback_is_explicit_and_labelled(self):
        with patch.object(self.ai, "generate_ai_text", side_effect=self.ai.GenerationError("offline")):
            failed = self.client.post("/api/ideas/generate", json={"topic": "Numbers"}, headers=self.headers)
            self.assertEqual(failed.status_code, 502)
            fallback = self.client.post("/api/ideas/generate", json={"topic": "Numbers", "allow_fallback": True}, headers=self.headers)
            self.assertEqual(fallback.status_code, 200)
            self.assertEqual(fallback.json()["status"], "fallback")
            self.assertEqual(fallback.json()["provenance"], "offline_template")

    def test_fingerprint_ignores_revision_not_content(self):
        project = self.save()
        fingerprint = self.models.project_fingerprint(project)
        project.update({"revision": 33, "updated_at": "later", "_ui_state": "selected"})
        self.assertEqual(self.models.project_fingerprint(project), fingerprint)
        project["title_english"] = "Changed"
        self.assertEqual(self.models.project_fingerprint(project), fingerprint)
        project["scenes"] = [{"cantonese": "Changed dialogue"}]
        self.assertNotEqual(self.models.project_fingerprint(project), fingerprint)

    def test_fingerprint_canonical_identity_and_caption_options(self):
        base = {"id": "sample", "scenes": [{}]}
        equivalent = {"episode_id": "sample", "scenes": [{}], "subtitle_options": {}, "caption_options": {}, "rendered_video": {"filename": "ignored.mp4"}}
        fingerprint = self.storage.media_input_fingerprint(base)
        self.assertEqual(self.storage.media_input_fingerprint(equivalent), fingerprint)
        normalized = self.models.ProjectData.model_validate(base).model_dump(mode="json")
        self.assertEqual(self.storage.media_input_fingerprint(normalized), fingerprint)
        self.assertEqual(self.storage.media_input_fingerprint({**base, "episode_id": "sample"}), fingerprint)
        with self.assertRaises(ValueError):
            self.storage.media_input_fingerprint({**base, "episode_id": "other"})
        with self.assertRaises(ValueError):
            self.models.ProjectData.model_validate({**base, "episode_id": "other"})
        for key in ("subtitle_options", "caption_options"):
            changed = {**base, key: {"font_size": 50}}
            self.assertNotEqual(self.storage.media_input_fingerprint(changed), fingerprint)
        self.assertNotEqual(self.storage.media_input_fingerprint({**base, "id": "other"}), fingerprint)

    def test_fingerprint_null_semantics_match_persistence(self):
        raw = {
            "id": "sample",
            "scenes": [{
                "audio_url": None, "master_audio_url": None,
                "characters": [{"name": "dad", "custom": None}],
                "stickers": [{"custom": None}],
                "custom": {"nested": None},
            }],
            "subtitle_options": {"custom": None},
            "caption_options": None,
        }
        model = self.models.ProjectData.model_validate(raw)
        persisted = model.model_dump(mode="json", exclude_none=True)
        fingerprint = self.storage.media_input_fingerprint(raw)
        self.assertEqual(self.storage.media_input_fingerprint(persisted), fingerprint)
        self.assertEqual(self.storage.media_input_fingerprint(model), fingerprint)
        self.assertNotIn("audio_url", persisted["scenes"][0])
        self.assertNotIn("custom", persisted["scenes"][0]["characters"][0])
        self.assertEqual(persisted["scenes"][0]["custom"], {"nested": None})
        self.assertEqual(persisted["subtitle_options"], {"custom": None})
        changed = copy.deepcopy(raw)
        changed["scenes"][0]["audio_url"] = "/api/audio/clip/sample/recording.wav"
        self.assertNotEqual(self.storage.media_input_fingerprint(changed), fingerprint)

    def test_silent_scene_render_fingerprint_survives_put_and_publish_validation(self):
        saved = self.save(scenes=[{"cantonese": ""}])
        original = copy.deepcopy(saved)
        original["scenes"][0]["audio_url"] = None
        fingerprint = self.storage.media_input_fingerprint(original)
        video = self.storage.project_path("sample", "renders", "silent.mp4")
        video.parent.mkdir(parents=True)
        video.write_bytes(b"synthetic offline render")
        self.storage.atomic_write_json(video.with_name(video.name + ".input.json"), original)
        self.storage.atomic_write_json(video.with_name(video.name + ".json"), {
            "status": "done", "project_id": "sample", "video_filename": "silent.mp4",
            "input_fingerprint": fingerprint,
        })
        original["rendered_video"] = {"filename": "silent.mp4", "input_fingerprint": fingerprint}
        response = self.client.put("/api/projects/sample", json={"project_data": original}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        persisted = response.json()["project"]
        self.assertNotIn("audio_url", persisted["scenes"][0])
        self.assertEqual(self.storage.media_input_fingerprint(persisted), fingerprint)
        with patch.object(self.youtube, "start_youtube_upload") as upload:
            response = self.client.post("/api/youtube/upload", json={
                "project_id": "sample", "video_filename": "silent.mp4",
                "input_fingerprint": fingerprint, "title": "Silent example",
                "description": "", "tags": [],
            }, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            upload.assert_called_once()

    def test_publish_rejects_missing_or_stale_render(self):
        project = self.save()
        request = {"project_id": "sample", "title": "Example", "description": "", "tags": [], "video_filename": "test.mp4", "input_fingerprint": "0" * 64}
        with patch.object(self.youtube, "start_youtube_upload") as upload:
            self.assertEqual(self.client.post("/api/youtube/upload", json=request, headers=self.headers).status_code, 409)
            video = self.storage.project_path("sample", "renders", "test.mp4")
            video.parent.mkdir(parents=True)
            video.write_bytes(b"fake video; never uploaded")
            project["rendered_video"] = {"filename": "test.mp4", "input_fingerprint": "stale"}
            self.projects.save_project("sample", project)
            self.assertEqual(self.client.post("/api/youtube/upload", json=request, headers=self.headers).status_code, 409)
            upload.assert_not_called()

    def test_publish_private_and_scoped_by_default(self):
        project = self.save()
        video = self.storage.project_path("sample", "renders", "test.mp4")
        video.parent.mkdir(parents=True)
        video.write_bytes(b"fake video; never uploaded")
        project["rendered_video"] = {"filename": "test.mp4", "input_fingerprint": self.models.project_fingerprint(project)}
        self.storage.atomic_write_json(video.with_name(video.name + ".json"), {"status": "done", "project_id": "sample", "video_filename": "test.mp4", "input_fingerprint": self.models.project_fingerprint(project)})
        self.storage.atomic_write_json(video.with_name(video.name + ".input.json"), project)
        self.projects.save_project("sample", project)
        request = {"project_id": "sample", "title": "Example", "description": "", "tags": [], "video_filename": "test.mp4", "input_fingerprint": self.models.project_fingerprint(project)}
        with patch.object(self.youtube, "start_youtube_upload") as upload:
            mismatch = self.client.post("/api/youtube/upload", json={**request, "video_filename": "different.mp4"}, headers=self.headers)
            self.assertEqual(mismatch.status_code, 409)
            mismatch = self.client.post("/api/youtube/upload", json={**request, "input_fingerprint": "0" * 64}, headers=self.headers)
            self.assertEqual(mismatch.status_code, 409)
            self.storage.atomic_write_json(video.with_name(video.name + ".input.json"), {**project, "id": "other"})
            mismatch = self.client.post("/api/youtube/upload", json=request, headers=self.headers)
            self.assertEqual(mismatch.status_code, 409)
            self.storage.atomic_write_json(video.with_name(video.name + ".input.json"), project)
            upload.assert_not_called()
            response = self.client.post("/api/youtube/upload", json=request, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(upload.call_args.args[1], str(video))
            self.assertEqual(upload.call_args.args[5], "private")
            request["privacy_status"] = "invalid"
            self.assertEqual(self.client.post("/api/youtube/upload", json=request, headers=self.headers).status_code, 422)

    def test_frame_traversal_rejected(self):
        response = self.client.get("/api/youtube/frame/sample/..%5C..%5Cconfig%5Cgoogle_token.json")
        self.assertEqual(response.status_code, 400)

    def test_oauth_state_session_bound_single_use(self):
        flow = Mock()
        self.youtube._oauth_states["state"] = {"session": "owner", "flow": flow, "redirect_uri": "http://localhost/callback", "expires": float("inf")}
        with self.assertRaises(self.youtube.OAuthStateError):
            self.youtube.consume_oauth_state("state", "other", "http://localhost/callback")
        self.assertIs(self.youtube.consume_oauth_state("state", "owner", "http://localhost/callback"), flow)
        with self.assertRaises(self.youtube.OAuthStateError):
            self.youtube.consume_oauth_state("state", "owner", "http://localhost/callback")

    def test_oauth_error_html_escaped_and_state_consumed(self):
        session = self.client.cookies.get("studio_session")
        self.youtube._oauth_states["safe"] = {"session": session, "flow": Mock(), "redirect_uri": "http://testserver/api/youtube/auth/callback", "expires": float("inf")}
        response = self.client.get("/api/youtube/auth/callback", params={"state": "safe", "error": "<script>alert(1)</script>"}, headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("<script>", response.text)
        self.assertIn("&lt;script&gt;", response.text)
        self.assertNotIn("safe", self.youtube._oauth_states)

    def test_persisted_upload_survives_memory_loss(self):
        job = {"job_id": "yt_test", "project_id": "sample", "status": "complete", "video_id": "synthetic", "input_fingerprint": "fingerprint"}
        self.youtube._persist_job(job)
        self.youtube.UPLOAD_JOBS.clear()
        self.assertEqual(self.youtube.get_upload_job("yt_test")["video_id"], "synthetic")

    def test_interrupted_upload_requires_channel_review(self):
        job = {"job_id": "yt_test", "project_id": "sample", "status": "uploading", "input_fingerprint": "fingerprint"}
        self.youtube._persist_job(job)
        self.youtube.UPLOAD_JOBS.clear()
        self.assertEqual(self.youtube.get_upload_job("yt_test")["status"], "interrupted")


if __name__ == "__main__":
    unittest.main()

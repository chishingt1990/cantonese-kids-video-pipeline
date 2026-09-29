"""Offline media regressions. Fixtures live only in a unique repository test directory."""
import asyncio
import copy
import io
import json
import os
import shutil
import threading
import unittest
import uuid
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from PIL import Image, ImageFont

from app import storage
from app.main import app
from app.routers import audio
from app.services import audio_service as mixing
from app.services import asset_manifest
from app.services import project_service
from app.services import render_service as rendering
from app.services import tts_service as tts
from app.services import voice_clone_service as cloning


def wav_bytes(seconds=1, sample_rate=44100, channels=1):
    data = io.BytesIO()
    with wave.open(data, "wb") as stream:
        stream.setnchannels(channels)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        stream.writeframes(b"\0\0" * round(seconds * sample_rate) * channels)
    return data.getvalue()


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent / (".media-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root, True)
        patches = [
            patch.dict(os.environ, {"KIDS_STUDIO_TESTING": "1",
                                    "KIDS_STUDIO_DATA_DIR": str(self.root),
                                    "KIDS_STUDIO_FFMPEG": "ffmpeg", "KIDS_STUDIO_FFPROBE": "ffprobe"}),
            patch.object(storage, "PROJECTS_DIR", self.root / "projects"),
            patch.object(project_service, "PROJECTS_DIR", self.root / "projects"),
            patch.object(asset_manifest, "ROOT", self.root),
            patch.object(asset_manifest, "MASTER_ASSETS", self.root / "assets"),
            patch.object(audio, "PROJECTS_DIR", self.root / "projects"),
            patch.object(cloning, "PROJECTS_DIR", self.root / "projects"),
            patch.object(cloning, "ROOT", self.root),
            patch.object(mixing.shutil, "which", side_effect=lambda name: name),
            patch("requests.post", side_effect=AssertionError("Live provider call prohibited in media tests")),
            patch("subprocess.run", side_effect=AssertionError("Unmocked subprocess prohibited")),
            patch("subprocess.Popen", side_effect=AssertionError("Unmocked encoder prohibited")),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        for project_id in ("alpha", "beta"):
            path = storage.project_path(project_id, "project.json")
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"id": project_id, "scenes": []}), encoding="utf-8")
        backgrounds = self.root / "assets" / "backgrounds"
        backgrounds.mkdir(parents=True)
        Image.new("RGB", (8, 8)).save(backgrounds / "bg_living_room.png")
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        token = self.client.get("/api/session").json()["csrf_token"]
        self.client.headers["X-Studio-Token"] = token
        rendering.JOBS.clear()
        rendering._CONTROLS.clear()

    def clip(self, project="alpha", seconds=1, channels=1):
        path = storage.project_path(project, "audio", uuid.uuid4().hex + ".wav")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(wav_bytes(seconds, channels=channels))
        return path, f"/api/audio/clip/{project}/{path.name}"

    def snapshot(self, **scene_fields):
        scene = {"scene_number": 1, "duration_sec": 6, "cantonese": "",
                 "background": "living_room", "characters": [], "stickers": []}
        scene.update(scene_fields)
        return {"id": "alpha", "scenes": [scene]}

    def test_audio_api_requires_project_and_explicit_stock_selection(self):
        response = self.client.post("/api/audio/tts/scene", json={"scene_idx": 1, "text": "hello"})
        self.assertEqual(response.status_code, 422)
        response = self.client.post("/api/audio/tts/scene", json={
            "project_id": "alpha", "scene_idx": 1, "text": "hello"})
        self.assertEqual(response.status_code, 422)

    def test_generation_is_immutable_and_project_scoped(self):
        async def fake_generate(text, persona, output):
            self.assertTrue(storage.project_is_busy("alpha") or storage.project_is_busy("beta"))
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(wav_bytes())
            return output
        with patch.object(tts, "generate_cantonese_tts", side_effect=fake_generate):
            first = tts.synthesize_scene_voice(1, "a", "dad", project_id="alpha")
            second = tts.synthesize_scene_voice(1, "b", "mom", project_id="alpha")
            other = tts.synthesize_scene_voice(1, "c", "dad", project_id="beta")
        self.assertNotEqual(first["audio_url"], second["audio_url"])
        self.assertIn("/beta/", other["audio_url"])
        self.assertTrue(mixing.resolve_project_audio("alpha", first["audio_url"]).exists())
        self.assertEqual(first["voice_provenance"]["kind"], "stock")

    def test_cross_project_legacy_and_traversal_audio_rejected(self):
        _, other = self.clip("beta")
        for url in (other, "/api/audio/clip/scene_01_voice.wav",
                    "/api/audio/clip/alpha/%2e%2e%5cproject.json",
                    "https://example.com/api/audio/clip/alpha/x.wav"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                mixing.resolve_project_audio("alpha", url)

    def test_clip_endpoint_scoped_and_legacy_endpoint_removed(self):
        _, url = self.clip()
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.get("/api/audio/clip/scene_01_voice.wav").status_code, 404)
        self.assertEqual(self.client.get(url.replace("/alpha/", "/beta/")).status_code, 404)

    def test_clone_failure_never_calls_stock_provider(self):
        with patch.object(audio, "synthesize_scene_cloned_voice", side_effect=RuntimeError("provider failure")), \
                patch.object(audio, "synthesize_scene_voice") as stock:
            response = self.client.post("/api/audio/voice-clone/synthesize", json={
                "project_id": "alpha", "scene_idx": 1, "text": "hello", "voice_id": "voice_parent"})
        self.assertEqual(response.status_code, 502)
        stock.assert_not_called()

    def test_child_mapping_and_bulk_blank_clears_old_audio(self):
        self.assertEqual(tts.speaker_persona("Child", "dad"), "child")
        _, old_url = self.clip()
        with patch.object(audio, "synthesize_scene_voice") as stock:
            response = self.client.post("/api/audio/tts/all", json={
                "project_id": "alpha", "default_persona": "dad",
                "scenes": [{"scene_number": 1, "cantonese": "", "audio_url": old_url, "duration_sec": 8}]})
        self.assertEqual(response.status_code, 200)
        result = response.json()["scenes"][0]
        self.assertIsNone(result["audio_url"])
        self.assertEqual(result["duration_sec"], 8)
        stock.assert_not_called()
        self.assertTrue(mixing.resolve_project_audio("alpha", old_url).exists())

    def test_bulk_invalid_later_scene_does_not_start_generation(self):
        with patch.object(audio, "synthesize_scene_voice") as stock:
            response = self.client.post("/api/audio/tts/all", json={
                "project_id": "alpha", "default_persona": "dad",
                "scenes": [{"scene_number": 1, "cantonese": "hello"},
                           {"scene_number": 2, "cantonese": "hello", "duration_sec": -1}]})
        self.assertEqual(response.status_code, 400)
        stock.assert_not_called()

    def test_single_blank_is_explicit_silence(self):
        response = self.client.post("/api/audio/tts/scene", json={
            "project_id": "alpha", "scene_idx": 1, "text": " ", "persona": "dad"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["voice_provenance"]["kind"], "none")
        self.assertIsNone(response.json()["audio_url"])

    def test_silent_scene_fingerprint_survives_project_save(self):
        project = self.snapshot(audio_url=None, voice_provenance={"kind": "none"})
        before = storage.media_input_fingerprint(project)
        response = self.client.put("/api/projects/alpha", json={"project_data": project})
        self.assertEqual(response.status_code, 200)
        saved = response.json()["project"]
        self.assertEqual(before, storage.media_input_fingerprint(saved))

    def test_timing_and_mixer_refuse_truncation_and_wrong_format(self):
        self.assertEqual(mixing.scene_duration(6, 5.1), 7)
        path, _ = self.clip(seconds=2)
        output = self.root / "mixed.wav"
        with self.assertRaisesRegex(ValueError, "exceeds"):
            mixing.mix_scene_audio([str(path)], [1], str(output))
        stereo, _ = self.clip(channels=2)
        with self.assertRaisesRegex(ValueError, "normalized"):
            mixing.mix_scene_audio([str(stereo)], [2], str(output))
        self.assertFalse(output.exists())

    def test_mixer_preserves_requested_timeline(self):
        path, _ = self.clip(seconds=0.1)
        output = self.root / "mixed.wav"
        mixing.mix_scene_audio([str(path), None], [0.25, 0.25], str(output))
        self.assertEqual(mixing.get_audio_duration(str(output)), 0.5)

    def test_ffprobe_used_for_compressed_reference_and_trim_applied(self):
        source = self.root / "reference.mp3"
        source.write_bytes(b"compressed fixture")
        calls = []
        def fake_run(command, **kwargs):
            calls.append(command)
            if command[0] == "ffprobe":
                return SimpleNamespace(returncode=0, stdout="65.0")
            return SimpleNamespace(returncode=0)
        with patch("subprocess.run", side_effect=fake_run):
            cloning._prepare_reference_wav(str(source), self.root)
        self.assertEqual(calls[0][0], "ffprobe")
        self.assertIn("-t", calls[1])
        self.assertEqual(calls[1][calls[1].index("-t") + 1], "30")

    def test_normalization_cannot_overwrite_existing_audio(self):
        source, _ = self.clip()
        original = source.read_bytes()
        with self.assertRaisesRegex(ValueError, "immutable"):
            mixing.normalize_audio(source, source)
        self.assertEqual(source.read_bytes(), original)

    def test_missing_ffmpeg_is_actionable_and_prevents_provider_call(self):
        with patch.object(mixing.shutil, "which", return_value=None), \
                patch.object(tts.edge_tts, "Communicate") as provider:
            response = self.client.post("/api/audio/tts/scene", json={
                "project_id": "alpha", "scene_idx": 1, "text": "hello", "persona": "dad"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("KIDS_STUDIO_FFMPEG", response.json()["detail"])
        self.assertIn("PATH", response.json()["detail"])
        provider.assert_not_called()

    def test_missing_ffprobe_upload_error_explains_prerequisite(self):
        with patch("subprocess.run", side_effect=FileNotFoundError("mock missing executable")):
            response = self.client.post("/api/audio/upload_scene", data={
                "project_id": "alpha", "scene_idx": 1,
            }, files={"audio_file": ("recording.webm", b"mock compressed audio", "audio/webm")})
        self.assertEqual(response.status_code, 503)
        self.assertIn("KIDS_STUDIO_FFPROBE", response.json()["detail"])
        self.assertFalse(list(self.root.rglob("*.upload")))

    def test_missing_encoder_rejects_render_before_job_launch(self):
        with patch.object(mixing.shutil, "which", return_value=None), \
                patch.object(rendering.threading, "Thread") as thread:
            response = self.client.post("/api/render/start", json={"project_data": self.snapshot()})
        self.assertEqual(response.status_code, 503)
        self.assertIn("KIDS_STUDIO_FFMPEG", response.json()["detail"])
        thread.assert_not_called()
        self.assertTrue(rendering._RENDER_SLOT.acquire(blocking=False))
        rendering._RENDER_SLOT.release()

    def test_clone_requires_real_supplied_reference(self):
        with patch.object(cloning, "_require_api_key", return_value="mock-key"), \
                patch("requests.post") as provider:
            with self.assertRaisesRegex(ValueError, "reference recording"):
                cloning.create_cloned_voice()
        provider.assert_not_called()

    def test_configured_ffmpeg_path_with_spaces_remains_one_argument(self):
        source, _ = self.clip()
        output = self.root / "normalized.wav"
        executable = r"C:\Media Tools\ffmpeg.exe"
        def execute(command, **kwargs):
            self.assertEqual(command[0], executable)
            self.assertNotIn("shell", kwargs)
            output.write_bytes(wav_bytes())
            return SimpleNamespace(returncode=0)
        with patch.dict(os.environ, {"KIDS_STUDIO_FFMPEG": executable}), \
                patch("subprocess.run", side_effect=execute):
            self.assertEqual(mixing.normalize_audio(source, output), 1)

    def test_render_requires_owned_audio_and_sufficient_duration(self):
        _, other = self.clip("beta")
        with self.assertRaisesRegex(ValueError, "different project"):
            rendering.validate_render_snapshot(self.snapshot(cantonese="hello", audio_url=other))
        _, own = self.clip(seconds=7)
        with self.assertRaisesRegex(ValueError, "at least"):
            rendering.validate_render_snapshot(self.snapshot(cantonese="hello", audio_url=own))
        with self.assertRaisesRegex(ValueError, "no approved audio"):
            rendering.validate_render_snapshot(self.snapshot(cantonese="hello"))

    def test_render_rejects_missing_stage_assets(self):
        with self.assertRaisesRegex(ValueError, "asset is missing"):
            rendering.validate_render_snapshot(self.snapshot(background="missing"))

    def test_render_resolves_generated_assets_from_shared_manifest(self):
        background = asset_manifest.image_path("backgrounds", "bg_custom_room.png")
        sprite = asset_manifest.image_path("sprites", "dad_custom_pose.png")
        for path in (background, sprite):
            path.parent.mkdir(parents=True, exist_ok=True)
            Image.new("RGBA", (8, 8)).save(path)
        _, snapshot = rendering.validate_render_snapshot(self.snapshot(
            background="custom_room", characters=[{"name": "dad", "pose": "custom_pose"}]))
        self.assertEqual(Path(snapshot["scenes"][0]["_background_path"]), background)
        self.assertEqual(Path(snapshot["scenes"][0]["characters"][0]["_sprite_path"]), sprite)

    def test_render_never_substitutes_missing_character_pose(self):
        sprites = self.root / "assets" / "sprites"
        sprites.mkdir()
        Image.new("RGBA", (8, 8)).save(sprites / "dad_default.png")
        with self.assertRaisesRegex(ValueError, "asset is missing"):
            rendering.validate_render_snapshot(self.snapshot(characters=[{"name": "dad", "pose": "missing"}]))
        response = self.client.post("/api/render/start", json={"project_data": self.snapshot(
            characters=[{"name": "dad", "pose": "missing"}])})
        self.assertEqual(response.status_code, 400)
        self.assertIn("asset is missing", response.json()["detail"])

    def test_snapshot_copies_assets_and_input_without_mutating_caller(self):
        _, url = self.clip()
        original = self.snapshot(cantonese="hello", audio_url=url)
        expected = copy.deepcopy(original)
        _, snapshot = rendering.validate_render_snapshot(original)
        work = self.root / "frozen"
        work.mkdir()
        frozen = rendering._freeze_assets(snapshot, work)
        source = mixing.resolve_project_audio("alpha", url)
        source.unlink()
        self.assertTrue(Path(frozen["scenes"][0]["_audio_path"]).exists())
        self.assertEqual(original, expected)

    def test_encoder_failure_and_empty_output_not_success(self):
        output = self.root / "out.mp4"
        with self.assertRaisesRegex(RuntimeError, "exit code"):
            rendering._verify_encoder_output(Mock(wait=Mock(return_value=1)), output)
        output.touch()
        with self.assertRaisesRegex(RuntimeError, "no usable output"):
            rendering._verify_encoder_output(Mock(wait=Mock(return_value=0)), output)
        output.write_bytes(b"mock mp4 fixture")
        rendering._verify_encoder_output(Mock(wait=Mock(return_value=0)), output)

    def test_render_worker_persists_verified_completion_and_cleans_process(self):
        for exit_code in (0, 1):
            with self.subTest(exit_code=exit_code):
                job_id = f"worker{exit_code}"
                _, snapshot = rendering.validate_render_snapshot(self.snapshot(duration_sec=1 / 30))
                work = storage.project_path("alpha", "renders", f".job_{job_id}")
                work.mkdir(parents=True)
                snapshot = rendering._freeze_assets(snapshot, work)
                output = work.parent / f"{job_id}.mp4"
                rendering.JOBS[job_id] = {
                    "project_id": "alpha", "job_id": job_id, "status": "queued",
                    "input_fingerprint": "test-fingerprint", "progress": 0,
                }
                rendering._CONTROLS[job_id] = {"cancel": threading.Event(), "proc": None, "workdir": str(work)}
                proc = Mock(stdin=io.BytesIO(), poll=Mock(return_value=exit_code))
                def finish(timeout):
                    if not output.exists():
                        output.write_bytes(b"mock encoder output")
                    return exit_code
                proc.wait.side_effect = finish
                self.assertTrue(rendering._RENDER_SLOT.acquire(blocking=False))
                with patch.object(rendering, "mix_scene_audio"), \
                        patch.object(rendering, "get_font", return_value=ImageFont.load_default()), \
                        patch.object(rendering.subprocess, "Popen", return_value=proc), \
                        patch.object(rendering.threading, "Thread"):
                    rendering.render_project_video(snapshot, job_id, str(output))
                job = rendering.get_render_job(job_id)
                self.assertEqual(job["status"], "done" if exit_code == 0 else "error")
                if exit_code == 0:
                    self.assertEqual(job["filename"], job["video_filename"])
                self.assertEqual(output.exists(), exit_code == 0)
                self.assertEqual(Path(str(output) + ".json").exists(), exit_code == 0)
                self.assertFalse(work.exists())
                self.assertTrue(proc.stdin.closed)
                self.assertNotIn(job_id, rendering._CONTROLS)
                self.assertTrue(rendering._RENDER_SLOT.acquire(blocking=False))
                rendering._RENDER_SLOT.release()

    def test_cancelled_worker_does_not_start_encoder(self):
        work = storage.project_path("alpha", "renders", ".job_cancelled")
        work.mkdir(parents=True)
        event = threading.Event()
        event.set()
        rendering.JOBS["cancelled"] = {"project_id": "alpha", "status": "queued"}
        rendering._CONTROLS["cancelled"] = {"cancel": event, "proc": None, "workdir": str(work)}
        self.assertTrue(rendering._RENDER_SLOT.acquire(blocking=False))
        with patch.object(rendering.threading, "Thread"), patch.object(rendering.subprocess, "Popen") as encoder:
            rendering.render_project_video(self.snapshot(), "cancelled", str(work.parent / "cancelled.mp4"))
        self.assertEqual(rendering.JOBS["cancelled"]["status"], "cancelled")
        encoder.assert_not_called()

    def test_render_capacity_and_cancel_terminates_owned_process(self):
        self.assertTrue(rendering._RENDER_SLOT.acquire(blocking=False))
        try:
            with self.assertRaises(rendering.RenderBusyError):
                rendering.start_render_job(self.snapshot(), "busy")
        finally:
            rendering._RENDER_SLOT.release()
        proc = Mock(poll=Mock(return_value=None))
        event = threading.Event()
        rendering.JOBS["cancel"] = {"status": "rendering"}
        rendering._CONTROLS["cancel"] = {"cancel": event, "proc": proc}
        self.assertTrue(rendering.cancel_render_job("cancel"))
        self.assertTrue(event.is_set())
        proc.kill.assert_called_once()

    def test_started_render_holds_project_lease_until_cancel_cleanup(self):
        original = self.snapshot()
        with patch.object(rendering.threading, "Thread") as thread:
            job = rendering.start_render_job(original, "leased")
            self.assertEqual(job["status"], "queued")
            canonical = dict(original, id="alpha", episode_id="alpha")
            self.assertEqual(job["input_fingerprint"], storage.media_input_fingerprint(canonical))
            self.assertTrue(mixing.project_media_busy("alpha"))
            self.assertTrue(storage.project_is_busy("alpha"))
            snapshot, job_id, output = thread.call_args.kwargs["args"]
            original["scenes"][0]["background"] = "changed_after_start"
            self.assertEqual(snapshot["scenes"][0]["background"], "living_room")
            self.assertTrue(rendering.cancel_render_job(job_id))
            rendering.render_project_video(snapshot, job_id, output)
        self.assertFalse(mixing.project_media_busy("alpha"))
        self.assertEqual(rendering.get_render_job("leased")["status"], "cancelled")

    def test_upload_returns_scoped_provenance_and_releases_lease(self):
        def normalize(source, output, **kwargs):
            self.assertTrue(mixing.project_media_busy("alpha"))
            self.assertTrue(storage.project_is_busy("alpha"))
            with self.assertRaises(project_service.RevisionConflict):
                project_service.delete_project("alpha")
            Path(output).write_bytes(wav_bytes())
            return 1.0
        with patch.object(audio, "normalize_audio", side_effect=normalize):
            response = self.client.post("/api/audio/upload_scene", data={
                "project_id": "alpha", "scene_idx": 1, "duration_sec": 8,
            }, files={"audio_file": ("recording.webm", b"mock recording", "audio/webm")})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["voice_provenance"], {"kind": "recorded"})
        self.assertEqual(result["duration_sec"], 8)
        self.assertTrue(mixing.resolve_project_audio("alpha", result["audio_url"]).exists())
        self.assertFalse(mixing.project_media_busy("alpha"))
        self.assertFalse(list(self.root.rglob("*.upload")))

    def test_render_startup_failure_releases_shared_lease(self):
        with patch.object(rendering.threading, "Thread") as thread:
            thread.return_value.start.side_effect = RuntimeError("mock thread startup failure")
            with self.assertRaisesRegex(RuntimeError, "startup failure"):
                rendering.start_render_job(self.snapshot(), "failed_start")
        self.assertFalse(storage.project_is_busy("alpha"))
        self.assertFalse(mixing.project_media_busy("alpha"))
        self.assertNotIn("failed_start", rendering._CONTROLS)
        self.assertTrue(rendering._RENDER_SLOT.acquire(blocking=False))
        rendering._RENDER_SLOT.release()

    def test_legacy_media_lease_name_uses_shared_registry(self):
        self.assertIs(mixing.media_operation, storage.project_operation)
        with mixing.media_operation("alpha"):
            self.assertTrue(storage.project_is_busy("alpha"))
            with self.assertRaises(project_service.RevisionConflict):
                project_service.delete_project("alpha")
        self.assertFalse(storage.project_is_busy("alpha"))

    def test_deleted_project_cannot_recreate_directories_on_render_start(self):
        shutil.rmtree(storage.project_path("alpha"))
        with self.assertRaises(ValueError):
            rendering.start_render_job(self.snapshot(), "deleted_start")
        self.assertFalse(storage.project_path("alpha").exists())
        self.assertFalse(storage.project_is_busy("alpha"))
        self.assertTrue(rendering._RENDER_SLOT.acquire(blocking=False))
        rendering._RENDER_SLOT.release()

    def test_persisted_active_job_reports_interrupted_after_restart(self):
        path = storage.project_path("alpha", "jobs", "render_interrupted.json")
        storage.atomic_write_json(path, {"project_id": "alpha", "status": "rendering", "progress": 25})
        result = rendering.get_render_job("interrupted", "alpha")
        self.assertEqual(result["status"], "error")
        self.assertIn("restart", result["error"])

    def test_caption_split_bounds_punctuation_free_cantonese(self):
        chunks = rendering._split_caption_lines("爸爸今日帶我哋去公園一齊開心玩遊戲", 10)
        self.assertTrue(all(len(chunk) <= 10 for chunk in chunks))
        self.assertEqual(len(chunks), 2)

    def test_cjk_font_failure_is_explicit(self):
        with patch.object(rendering.os.path, "exists", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "CJK font"):
                rendering.get_font(24)

    def test_cancelled_async_request_waits_for_file_worker(self):
        started = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        def worker():
            started.set()
            release.wait(timeout=5)
            finished.set()
        async def scenario():
            task = asyncio.create_task(mixing.run_blocking(worker))
            while not started.is_set():
                await asyncio.sleep(0.001)
            task.cancel()
            await asyncio.sleep(0.01)
            self.assertFalse(task.done())
            release.set()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertTrue(finished.is_set())
        asyncio.run(scenario())

    def test_legacy_engines_fail_without_fake_or_missing_outputs(self):
        from src.voice import tts_engine, google_tts
        engine = tts_engine.TTSEngine.__new__(tts_engine.TTSEngine)
        engine.config = {"voice": {"clones": {}}}
        engine.api_key = ""
        with patch.object(tts_engine, "PROJECT_ROOT", self.root):
            with self.assertRaisesRegex(RuntimeError, "no audio was generated"):
                engine.synthesize("hello", output_filename="missing.mp3")
        google = google_tts.GoogleCantoneseTTS.__new__(google_tts.GoogleCantoneseTTS)
        google.access_token = None
        with patch.dict(os.environ, {"GEMINI_API_KEY": "", "GOOGLE_API_KEY": ""}), \
                patch.object(google_tts, "OUTPUT_DIR", self.root):
            with self.assertRaisesRegex(RuntimeError, "no audio was generated"):
                google.synthesize("hello", output_filename="missing.mp3")
        self.assertFalse(list(self.root.rglob("*.mp3")))


if __name__ == "__main__":
    unittest.main()

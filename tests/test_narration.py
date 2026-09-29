"""Offline narration regressions; all provider and model calls are mocked."""
import copy
import json
import os
import shutil
import threading
import unittest
import uuid
import wave
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import storage
from app.routers import narration as routes
from app.services import narration_service as service
from app.services import project_service, voice_clone_service


class NarrationTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent / (".narration-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.project = {
            "id": "alpha", "revision": 3,
            "voice_options": {"voice_id": "voice_dad", "use_cloned": True, "style": "calm"},
            "scenes": [{"scene_number": 1, "cantonese": "爸爸你好。"},
                       {"scene_number": 2, "cantonese": "大家一齊玩！"}],
        }
        patches = [
            patch.object(storage, "PROJECTS_DIR", self.root / "projects"),
            patch.object(project_service, "PROJECTS_DIR", self.root / "projects"),
            patch.object(service, "_SLOT", threading.BoundedSemaphore(1)),
            patch.object(voice_clone_service, "list_cloned_voices", return_value=[{"voice_id": "voice_dad"}]),
            patch.object(voice_clone_service, "_require_api_key", return_value="test-key"),
            patch.object(service, "require_media_tools"),
            patch.object(service, "alignment_preflight",
                         side_effect=service.NarrationError("alignment_unavailable", "Install local model", 503)),
            patch.object(service, "_launch_worker", side_effect=lambda args: service._worker(*args)),
            patch.object(service, "get_audio_duration", return_value=120.0),
            patch.object(voice_clone_service, "synthesize_story_cloned_voice", side_effect=self.synthesize),
            patch("requests.post", side_effect=AssertionError("No live provider calls")),
        ]
        self.mocks = []
        for item in patches:
            self.mocks.append(item.start())
            self.addCleanup(item.stop)
        self.generator = self.mocks[9]
        self.save()
        app = FastAPI()
        app.include_router(routes.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def save(self):
        storage.atomic_write_json(storage.project_path("alpha", "project.json"), self.project)

    def synthesize(self, text, voice_id, path, style):
        self.assertTrue(storage.project_is_busy("alpha"))
        Path(path).write_bytes(b"mock normalized audio")

    def start(self, **kwargs):
        request = {"project_id": "alpha", "revision": 3, "voice_id": "voice_dad",
                   "style": "calm", "allow_estimated_alignment": True}
        request.update(kwargs)
        result = service.start_job(**request)
        return service.get_job("alpha", result["job_id"])

    def test_preflight_rejects_before_provider_without_estimated_opt_in(self):
        with self.assertRaises(service.NarrationError) as error:
            self.start(allow_estimated_alignment=False)
        self.assertEqual(error.exception.code, "alignment_unavailable")
        self.generator.assert_not_called()

    def test_preflight_http_error_is_typed_and_arbitrary_text_is_rejected(self):
        body = {"project_id": "alpha", "revision": 3, "voice_id": "voice_dad", "style": "calm"}
        result = self.client.post("/api/narration/start", json=body)
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json()["detail"]["code"], "alignment_unavailable")
        body["full_text"] = "Not the saved story"
        self.assertEqual(self.client.post("/api/narration/start", json=body).status_code, 422)
        self.generator.assert_not_called()

    def test_capabilities_exposes_styles_without_provider_or_model_probe(self):
        with patch.object(routes, "list_cloned_voices", return_value=[
                {"voice_id": "voice_dad", "name": "Dad", "profile_verified": True, "private": "do not expose"}]), \
                patch.object(routes, "is_voice_clone_available", return_value=True), \
                patch.object(routes, "require_media_tools"), \
                patch.object(service, "_load_model", side_effect=AssertionError("No model load")), \
                patch("requests.get", side_effect=AssertionError("No remote probe")):
            result = self.client.get("/api/narration/capabilities")
        self.assertEqual(result.status_code, 200)
        data = result.json()
        self.assertEqual(data["styles"], ["calm", "warm_playful", "excited"])
        self.assertTrue(data["provider_configured"])
        self.assertFalse(data["capability_verified"])
        self.assertFalse(data["alignment_available"])
        self.assertEqual(data["alignment_message"], "Install local model")
        self.assertTrue(data["media_available"])
        self.assertNotIn("private", data["voices"][0])
        self.generator.assert_not_called()

    def test_asr_job_preserves_real_word_boundaries(self):
        words = [{"text": text, "start_sec": start, "end_sec": end, "probability": .99}
                 for text, start, end in [("爸爸", 2, 3), ("你好", 7, 9),
                                          ("大家", 70, 72), ("一齊玩", 90, 95)]]
        with patch.object(service, "alignment_preflight", return_value="local-model"), \
                patch.object(service, "_load_model"), patch.object(service, "_asr_words", return_value=words):
            job = self.start(allow_estimated_alignment=False)
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["narration"]["alignment_method"], "asr")
        self.assertEqual(job["narration"]["scenes"][0]["words"][1]["start_sec"], 7)
        self.assertEqual(self.generator.call_args.args[0], "爸爸你好。\n\n大家一齊玩！")

    def test_saved_revision_and_selected_known_voice_required(self):
        for changes, code in [
            ({"revision": 2}, "revision_conflict"),
            ({"voice_id": "voice_other"}, "voice_mismatch"),
            ({"style": "excited"}, "voice_mismatch"),
            ({"project_id": "missing"}, "project_missing"),
        ]:
            with self.subTest(code=code), self.assertRaises(service.NarrationError) as error:
                self.start(**changes)
            self.assertEqual(error.exception.code, code)
        self.mocks[3].return_value = []
        with self.assertRaises(service.NarrationError) as error:
            self.start()
        self.assertEqual(error.exception.code, "voice_unknown")

    def test_success_is_project_scoped_immutable_and_does_not_save_project(self):
        job = self.start()
        self.assertEqual(job["status"], "done")
        take = job["narration"]
        self.assertEqual(take["alignment_method"], "estimated")
        self.assertTrue(take["allow_estimated_alignment"])
        self.assertEqual(take["scenes"][0]["start_sec"], 0)
        self.assertEqual(take["scenes"][-1]["end_sec"], 120)
        self.assertEqual(self.generator.call_count, 1)
        self.assertEqual(project_service.get_project("alpha")["revision"], 3)
        self.assertFalse(storage.project_is_busy("alpha"))
        self.assertFalse(job["stale"])
        attached = dict(self.project, narration=take)
        self.assertEqual(service.validate_narration(attached)["take_id"], take["take_id"])
        other = self.start()
        self.assertNotEqual(take["take_id"], other["narration"]["take_id"])
        self.assertTrue(service.narration_audio_path("alpha", take["take_id"]).exists())

    def test_bounded_background_job_and_deletion_lease(self):
        captured = {}
        def deferred(args):
            captured.update(args=args)
        with patch.object(service, "_launch_worker", side_effect=deferred):
            result = service.start_job("alpha", 3, "voice_dad", "calm", True)
            self.assertEqual(service.get_job("alpha", result["job_id"])["status"], "queued")
            self.assertTrue(storage.project_is_busy("alpha"))
            with self.assertRaises(service.NarrationError) as error:
                self.start()
            self.assertEqual(error.exception.code, "narration_busy")
            with self.assertRaises(project_service.RevisionConflict):
                project_service.delete_project("alpha")
        service._worker(*captured["args"])
        self.assertFalse(storage.project_is_busy("alpha"))

    def test_duration_failures_preserve_take_without_padding(self):
        for duration in (119.9, 240.1):
            with self.subTest(duration=duration), patch.object(service, "get_audio_duration", return_value=duration):
                job = self.start()
            self.assertEqual(job["status"], "error")
            self.assertEqual(job["error_code"], "duration_out_of_range")
            take = job["narration"]
            self.assertEqual(take["duration_sec"], duration)
            self.assertTrue(service.narration_audio_path("alpha", take["take_id"]).exists())
            self.assertEqual(take["alignment_method"], "none")

    def test_timeout_never_retried(self):
        self.generator.side_effect = requests.exceptions.Timeout()
        job = self.start()
        self.assertEqual(job["error_code"], "provider_outcome_unknown")
        self.assertEqual(self.generator.call_count, 1)
        self.assertFalse(storage.project_is_busy("alpha"))

    def test_model_load_failure_precedes_synthesis(self):
        with patch.object(service, "alignment_preflight", return_value="local-model"), \
                patch.object(service, "_load_model", side_effect=RuntimeError("bad model")):
            job = self.start(allow_estimated_alignment=False)
        self.assertEqual(job["error_code"], "alignment_unavailable")
        self.generator.assert_not_called()

    def test_worker_launch_failure_releases_lease_and_records_error(self):
        with patch.object(service, "_launch_worker", side_effect=RuntimeError("thread failure")):
            with self.assertRaises(RuntimeError):
                self.start()
        self.assertFalse(storage.project_is_busy("alpha"))
        paths = list(storage.project_path("alpha", "narration_jobs").glob("*.json"))
        self.assertEqual(json.loads(paths[0].read_text())["status"], "error")
        self.assertTrue(service._SLOT.acquire(blocking=False))
        service._SLOT.release()

    def test_failed_completion_write_does_not_leave_job_running_forever(self):
        write = service.atomic_write_json
        def fail_completion(path, value):
            if "job_id" in value and value.get("status") == "done":
                raise PermissionError("simulated sync lock")
            return write(path, value)
        with patch.object(service, "atomic_write_json", side_effect=fail_completion), \
                patch.object(service.logger, "exception"):
            job = self.start()
        self.assertEqual(job["status"], "needs_alignment")
        self.assertEqual(job["narration"]["alignment_method"], "estimated")
        self.assertFalse(storage.project_is_busy("alpha"))
        self.assertEqual(self.generator.call_count, 1)

    def test_alignment_failure_recovers_without_resynthesis_and_keeps_original(self):
        with patch.object(service, "alignment_preflight", return_value="local-model"), \
                patch.object(service, "_load_model"), \
                patch.object(service, "_asr_words", return_value=[]):
            job = self.start(allow_estimated_alignment=False)
        self.assertEqual(job["status"], "needs_alignment")
        original = job["narration"]
        retry = service.start_job("alpha", 3, take_id=original["take_id"], allow_estimated_alignment=True)
        recovered = service.get_job("alpha", retry["job_id"])["narration"]
        self.assertEqual(self.generator.call_count, 1)
        self.assertNotEqual(original["take_id"], recovered["take_id"])
        self.assertEqual(recovered["source_digest"], original["source_digest"])
        self.assertEqual(service.load_manifest("alpha", original["take_id"])["alignment_method"], "none")

    def test_script_fingerprint_ignores_staging_but_not_text_voice_style(self):
        original = service.script_fingerprint(self.project)
        modified = copy.deepcopy(self.project)
        modified["scenes"][0].update(background="park", stickers=[{"id": "foo"}], duration_sec=15)
        self.assertEqual(original, service.script_fingerprint(modified))
        for field, value in [("voice_id", "voice_other"), ("style", "excited")]:
            changed = copy.deepcopy(modified)
            changed["voice_options"][field] = value
            self.assertNotEqual(original, service.script_fingerprint(changed))
        modified["scenes"][0]["cantonese"] += "啊"
        self.assertNotEqual(original, service.script_fingerprint(modified))

    def test_stale_artifact_recoverable_but_not_renderable(self):
        job = self.start()
        self.project["scenes"][0]["cantonese"] = "新的故事"
        self.save()
        self.assertTrue(service.get_job("alpha", job["job_id"])["stale"])
        with self.assertRaises(service.NarrationError) as error:
            service.validate_narration(dict(self.project, narration=job["narration"]))
        self.assertEqual(error.exception.code, "narration_stale")
        self.assertEqual(self.client.get(job["narration"]["audio_url"]).status_code, 200)

    def test_renderer_ignores_forged_client_timing_and_rejects_modified_audio(self):
        take = self.start()["narration"]
        forged = dict(take, scenes=[], duration_sec=999, audio_url="C:\\secret.wav")
        self.assertEqual(service.validate_narration(dict(self.project, narration=forged))["duration_sec"], 120)
        with self.assertRaises(service.NarrationError) as error:
            service.validate_narration(dict(self.project, narration=take, voice_options="invalid"))
        self.assertEqual(error.exception.code, "voice_invalid")
        service.narration_audio_path("alpha", take["take_id"]).write_bytes(b"tampered")
        with self.assertRaises(service.NarrationError):
            service.validate_narration(dict(self.project, narration=take))

    def test_cross_project_jobs_audio_and_traversal_rejected(self):
        job = self.start()
        self.assertEqual(self.client.get(f"/api/narration/status/{job['job_id']}?project_id=beta").status_code, 404)
        take = job["narration"]["take_id"]
        self.assertEqual(self.client.get(f"/api/narration/audio/beta/{take}").status_code, 404)
        with self.assertRaises(ValueError):
            service.load_manifest("alpha", "..\\beta")
        response = self.client.post("/api/narration/start", json={
            "project_id": "alpha", "revision": 3, "voice_id": "voice_dad", "style": "calm",
            "audio_path": "C:\\secret.wav"})
        self.assertEqual(response.status_code, 422)

    def test_restart_status_never_resubmits_uncertain_job(self):
        path = service._job_path("alpha", "interrupted")
        storage.atomic_write_json(path, {"job_id": "interrupted", "project_id": "alpha",
                                        "status": "running", "process_id": "old"})
        self.assertEqual(service.get_job("alpha", "interrupted")["error_code"], "interrupted")
        self.generator.assert_not_called()

    def test_restart_recovers_completed_paid_wav_before_manifest_was_written(self):
        take_id = uuid.uuid4().hex
        audio = service.narration_audio_path("alpha", take_id)
        audio.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(audio), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(44100)
            for _ in range(120):
                stream.writeframes(b"\0\0" * 44100)
        storage.atomic_write_json(service._job_path("alpha", "recover"), {
            "job_id": "recover", "project_id": "alpha", "take_id": take_id,
            "status": "running", "process_id": "previous", "source_revision": 3,
            "binding": {"voice_id": "voice_dad", "style": "calm",
                        "script_fingerprint": service.script_fingerprint(self.project),
                        "allow_estimated_alignment": False},
        })
        job = service.get_job("alpha", "recover")
        self.assertEqual(job["status"], "needs_alignment")
        self.assertEqual(job["narration"]["take_id"], take_id)
        self.assertEqual(self.client.get(job["narration"]["audio_url"]).status_code, 200)
        self.generator.assert_not_called()

    def test_fractional_pcm_durations_do_not_exceed_final_endpoint(self):
        for duration in (120.03174603174604, 181.17, 239.99999):
            with patch.object(service, "get_audio_duration", return_value=duration):
                job = self.start()
            self.assertEqual(job["status"], "done")
            manifest = service.validate_narration(dict(self.project, narration=job["narration"]))
            self.assertEqual(manifest["scenes"][-1]["end_sec"], duration)

    def test_media_fingerprint_changes_with_take_and_voice_only_when_narration_present(self):
        original = storage.media_input_fingerprint(self.project)
        no_take = copy.deepcopy(self.project)
        no_take["voice_options"]["style"] = "excited"
        self.assertEqual(original, storage.media_input_fingerprint(no_take))
        take = self.start()["narration"]
        with_take = dict(self.project, narration=take)
        fingerprint = storage.media_input_fingerprint(with_take)
        with_take = copy.deepcopy(with_take)
        with_take["voice_options"]["style"] = "excited"
        self.assertNotEqual(fingerprint, storage.media_input_fingerprint(with_take))

    def test_promoting_legacy_project_to_narration_first_invalidates_render_identity(self):
        original = storage.media_input_fingerprint(self.project)
        promoted = dict(self.project, workflow="narration_first")
        self.assertNotEqual(original, storage.media_input_fingerprint(promoted))
        self.assertEqual(original, storage.media_input_fingerprint(dict(self.project, workflow="legacy")))

    def test_transient_legacy_consent_is_not_part_of_media_identity(self):
        original = storage.media_input_fingerprint(self.project)
        for consent in (True, False):
            self.assertEqual(original, storage.media_input_fingerprint(
                dict(self.project, silent_legacy_confirmed=consent)))

    def test_media_fingerprint_binds_normalized_synthesized_backing_options(self):
        project = dict(self.project, narration=self.start()["narration"])
        fingerprint = storage.media_input_fingerprint(project)
        project["audio_options"] = {"bgm_enabled": True, "bgm_volume": .025}
        self.assertEqual(fingerprint, storage.media_input_fingerprint(project))
        project["audio_options"]["bgm_enabled"] = False
        self.assertNotEqual(fingerprint, storage.media_input_fingerprint(project))
        project["audio_options"] = {"bgm_volume": .01}
        self.assertNotEqual(fingerprint, storage.media_input_fingerprint(project))
        for volume in (float("nan"), float("inf"), True, -.1, .06):
            project["audio_options"] = {"bgm_volume": volume}
            with self.assertRaises(ValueError):
                storage.media_input_fingerprint(project)

    def test_real_synthetic_120_second_wav_is_measured(self):
        from app.services.audio_service import get_audio_duration
        def synthetic(text, voice_id, path, style):
            with wave.open(str(path), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(44100)
                for _ in range(120):
                    stream.writeframes(b"\0\0" * 44100)
        self.generator.side_effect = synthetic
        with patch.object(service, "get_audio_duration", side_effect=get_audio_duration):
            job = self.start()
        self.assertEqual(job["status"], "done")
        self.assertEqual(job["narration"]["duration_sec"], 120)


class AlignmentTests(unittest.TestCase):
    def test_synthesized_bed_ducks_and_preserves_samples_and_immutable_output(self):
        import numpy as np
        from app.services.audio_service import mix_narration_with_bgm
        root = Path(__file__).parent / (".bed-" + uuid.uuid4().hex)
        root.mkdir()
        self.addCleanup(shutil.rmtree, root, True)
        samples = np.zeros(44100 * 3, dtype=np.int16)
        voice = samples.copy()
        voice[44100:88200] = 6554
        for name, data in (("silence", samples), ("voice", voice)):
            with wave.open(str(root / (name + ".wav")), "wb") as stream:
                stream.setnchannels(1)
                stream.setsampwidth(2)
                stream.setframerate(44100)
                stream.writeframes(data.tobytes())
            mix_narration_with_bgm(root / (name + ".wav"), root / (name + "-mix.wav"))
        with wave.open(str(root / "voice-mix.wav"), "rb") as stream:
            self.assertEqual(stream.getnframes(), len(voice))
            mixed_voice = np.frombuffer(stream.readframes(len(voice)), dtype=np.int16).astype(float)
        with wave.open(str(root / "silence-mix.wav"), "rb") as stream:
            mixed_bed = np.frombuffer(stream.readframes(len(voice)), dtype=np.int16).astype(float)
        window = slice(60000, 70000)
        residual = mixed_voice[window] - voice[window]
        self.assertLess(np.linalg.norm(residual), np.linalg.norm(mixed_bed[window]) * .3)
        with self.assertRaises(ValueError):
            mix_narration_with_bgm(root / "voice.wav", root / "voice-mix.wav")
        mix_narration_with_bgm(root / "voice.wav", root / "dry.wav", enabled=False)
        with wave.open(str(root / "dry.wav"), "rb") as stream:
            self.assertEqual(stream.readframes(len(voice)), voice.tobytes())

    def test_preflight_requires_local_cantonese_capable_model_without_download(self):
        root = Path(__file__).parent / (".alignment-" + uuid.uuid4().hex)
        root.mkdir()
        self.addCleanup(shutil.rmtree, root, True)
        (root / "model.bin").write_bytes(b"fixture")
        (root / "config.json").write_text(json.dumps({"lang_ids": [50358], "alignment_heads": [[1, 1]]}))
        (root / "tokenizer.json").write_text(json.dumps({"added_tokens": [{"content": "<|yue|>", "id": 50358}]}))
        (root / "preprocessor_config.json").write_text(json.dumps({"feature_size": 128}))
        with patch.dict(os.environ, {"KIDS_STUDIO_WHISPER_MODEL": str(root)}), \
                patch.object(service.importlib.util, "find_spec", return_value=object()):
            self.assertEqual(service.alignment_preflight(), str(root.resolve()))
            (root / "preprocessor_config.json").write_text(json.dumps({"feature_size": 80}))
            with self.assertRaises(service.NarrationError):
                service.alignment_preflight()
        with patch.dict(os.environ, {"KIDS_STUDIO_WHISPER_MODEL": "large-v3"}):
            with self.assertRaises(service.NarrationError):
                service.alignment_preflight()

    def test_whole_story_provider_timeout_has_exactly_one_post(self):
        with patch.object(voice_clone_service, "list_cloned_voices", return_value=[{"voice_id": "voice_dad"}]), \
                patch.object(voice_clone_service, "_require_api_key", return_value="test-key"), \
                patch.object(voice_clone_service, "require_media_tools"), \
                patch.object(voice_clone_service.requests, "post", side_effect=requests.exceptions.Timeout()) as post:
            with self.assertRaises(requests.exceptions.Timeout):
                voice_clone_service.synthesize_story_cloned_voice("爸爸你好", "voice_dad", "unused.wav", "calm")
        self.assertEqual(post.call_count, 1)
        self.assertEqual(post.call_args.kwargs["timeout"], 300)
        self.assertEqual(post.call_args.kwargs["json"]["generation_config"]["speech_config"],
                         [{"voice": "voice_dad"}])

    def test_normalized_punctuation_and_absolute_pauses(self):
        scenes = [{"scene_number": 1, "cantonese": "爸爸，你好！"},
                  {"scene_number": 2, "cantonese": "大家一齊玩。"}]
        texts = ["爸爸，", "你好！", "大家", "一齊玩。"]
        words = [{"text": t, "start_sec": a, "end_sec": b, "probability": .99}
                 for t, a, b in zip(texts, [1, 4, 70, 90], [3, 6, 75, 100])]
        aligned = service.align_words(scenes, words, 120)
        self.assertEqual(aligned[0]["start_sec"], 0)
        self.assertEqual(aligned[0]["end_sec"], 38)
        self.assertEqual(aligned[1]["start_sec"], 38)
        self.assertEqual(aligned[1]["end_sec"], 120)
        self.assertEqual(aligned[0]["words"][1]["start_sec"], 4)

    def test_poor_matching_or_confidence_is_not_silent_success(self):
        scenes = [{"scene_number": 1, "cantonese": "爸爸你好"}]
        for text, confidence in [("錯誤文字", .99), ("爸爸你好", .1)]:
            with self.assertRaises(service.NarrationError):
                service.align_words(scenes, [{"text": text, "start_sec": 0,
                                             "end_sec": 1, "probability": confidence}], 120)

    def test_repeated_phrases_align_monotonically(self):
        scenes = [{"scene_number": i, "cantonese": "爸爸你好"} for i in (1, 2)]
        words = [{"text": "爸爸你好", "start_sec": a, "end_sec": a + 3, "probability": .99}
                 for a in (1, 80)]
        aligned = service.align_words(scenes, words, 120)
        self.assertEqual(aligned[1]["words"][0]["start_sec"], 80)


class VoiceImportTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parent / (".voice-import-" + uuid.uuid4().hex)
        self.root.mkdir()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.legacy = self.root / "legacy"
        self.data = self.root / "isolated"
        patches = [
            patch.object(storage, "DATA_DIR", self.data),
            patch.object(voice_clone_service, "ROOT", self.legacy),
            patch.object(voice_clone_service, "_require_api_key", return_value="test-secret"),
            patch.object(voice_clone_service.requests, "post", side_effect=AssertionError("Never create or synthesize")),
            patch.object(voice_clone_service.requests, "get"),
            patch.object(voice_clone_service, "require_media_tools", side_effect=AssertionError("Import needs no media tools")),
        ]
        self.mocks = []
        for item in patches:
            self.mocks.append(item.start())
            self.addCleanup(item.stop)
        self.remote = self.mocks[4]
        self.remote.return_value = Mock(status_code=200)
        self.remote.return_value.json.return_value = {
            "id": "voice_existing", "type": "replicated", "display_name": "Original profile",
            "replicated": {"source_audio": {"data": "PRIVATE"}, "consent_audio": {"data": "PRIVATE"}},
        }
        app = FastAPI()
        app.include_router(routes.router)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_verified_import_uses_one_get_and_persists_only_allowlisted_metadata(self):
        response = self.client.post("/api/narration/voices/import",
                                    json={"voice_id": "voice_existing", "name": "Dad"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "imported")
        self.assertEqual(data["voice"]["name"], "Dad")
        self.assertTrue(data["voice"]["profile_verified"])
        self.assertFalse(data["voice"]["capability_verified"])
        self.assertEqual(data["voice"]["provider_display_name"], "Original profile")
        self.assertEqual(self.remote.call_count, 1)
        self.assertEqual(self.remote.call_args.args[0],
                         "https://generativelanguage.googleapis.com/v1beta/voices/voice_existing")
        self.assertFalse(self.remote.call_args.kwargs["allow_redirects"])
        self.assertEqual(self.remote.call_args.kwargs["headers"]["x-goog-api-key"], "test-secret")
        saved = (self.data / "config" / "cloned_voices.json").read_text(encoding="utf-8")
        self.assertNotIn("PRIVATE", saved)
        self.assertNotIn("test-secret", saved)
        self.assertNotIn("source_audio", saved)
        self.assertEqual(voice_clone_service.list_cloned_voices()[0]["voice_id"], "voice_existing")
        self.mocks[3].assert_not_called()
        self.mocks[5].assert_not_called()

    def test_remote_failure_and_unverified_or_different_profile_never_save(self):
        for status in (401, 403, 404, 429, 500, 302):
            with self.subTest(status=status):
                self.remote.return_value.status_code = status
                result = self.client.post("/api/narration/voices/import", json={"voice_id": "voice_existing"})
                self.assertEqual(result.status_code, status if status in (401, 403, 404, 429) else 502)
                self.assertIn("code", result.json()["detail"])
                self.assertEqual(voice_clone_service.list_cloned_voices(), [])
        self.remote.return_value.status_code = 200
        for payload in (
            {"id": "voice_other", "type": "replicated"},
            {"id": "voice_existing", "type": "prompted"},
            {"id": "voice_existing"},
            {"type": "replicated"},
        ):
            self.remote.return_value.json.return_value = payload
            result = self.client.post("/api/narration/voices/import", json={"voice_id": "voice_existing"})
            self.assertGreaterEqual(result.status_code, 400)
            self.assertEqual(voice_clone_service.list_cloned_voices(), [])

    def test_invalid_ids_do_not_reach_google(self):
        for voice_id in ("voicekey_secret", "../voice_existing", "voice_existing?key=foo",
                         "https://example.com/voice_existing", "voice_existing/other", ""):
            with self.subTest(voice_id=voice_id):
                result = self.client.post("/api/narration/voices/import", json={"voice_id": voice_id})
                self.assertIn(result.status_code, (400, 422))
        self.remote.assert_not_called()

    def test_timeout_and_malformed_response_are_typed_without_retries(self):
        self.remote.side_effect = requests.exceptions.Timeout()
        result = self.client.post("/api/narration/voices/import", json={"voice_id": "voice_existing"})
        self.assertEqual(result.status_code, 504)
        self.assertEqual(self.remote.call_count, 1)
        self.remote.side_effect = None
        self.remote.return_value.json.side_effect = ValueError("raw credential-bearing invalid response")
        result = self.client.post("/api/narration/voices/import", json={"voice_id": "voice_existing"})
        self.assertEqual(result.status_code, 502)
        self.assertNotIn("credential-bearing", result.text)
        self.assertEqual(voice_clone_service.list_cloned_voices(), [])

    def test_discovery_is_explicit_filtered_and_does_not_import(self):
        self.remote.return_value.json.return_value = {
            "voices": [
                {"id": "voice_existing", "type": "replicated", "display_name": "Remote name"},
                {"id": "voice_stock", "type": "stock"},
            ],
            "next_page_token": "more",
        }
        response = self.client.post("/api/narration/voices/discover")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([v["voice_id"] for v in response.json()["voices"]], ["voice_existing"])
        self.assertFalse(response.json()["imported"])
        self.assertTrue(response.json()["has_more"])
        self.assertEqual(self.remote.call_args.kwargs["params"], {"type": "replicated"})
        self.assertEqual(voice_clone_service.list_cloned_voices(), [])
        self.remote.return_value.json.return_value = {}
        self.assertEqual(self.client.post("/api/narration/voices/discover").json()["voices"], [])

    def test_custom_storage_never_reads_or_modifies_global_legacy_profiles(self):
        legacy_path = self.legacy / "config" / "cloned_voices.json"
        storage.atomic_write_json(legacy_path, [{"voice_id": "voice_private", "name": "Other storage"}])
        before = legacy_path.read_bytes()
        self.assertEqual(voice_clone_service.list_cloned_voices(), [])
        voice_clone_service.import_cloned_voice("voice_existing")
        self.assertEqual([v["voice_id"] for v in voice_clone_service.list_cloned_voices()], ["voice_existing"])
        self.assertEqual(legacy_path.read_bytes(), before)
        with patch.object(storage, "DATA_DIR", self.legacy):
            self.assertEqual(voice_clone_service.list_cloned_voices()[0]["voice_id"], "voice_private")

    def test_reimport_verifies_again_updates_instead_of_duplicate(self):
        voice_clone_service.import_cloned_voice("voice_existing", "Dad")
        voice_clone_service.import_cloned_voice("voice_existing", "爸爸")
        self.assertEqual(self.remote.call_count, 2)
        self.assertEqual(len(voice_clone_service.list_cloned_voices()), 1)
        self.assertEqual(voice_clone_service.list_cloned_voices()[0]["name"], "爸爸")

    def test_missing_configuration_does_not_request_google(self):
        self.mocks[2].side_effect = voice_clone_service.VoiceCloneUnavailableError("Configure the parent voice provider")
        result = self.client.post("/api/narration/voices/import", json={"voice_id": "voice_existing"})
        self.assertEqual(result.status_code, 503)
        self.remote.assert_not_called()


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import scripts
from app.services.ai_service import get_vehicle_ideas


class ExplicitOfflineStoryTests(unittest.TestCase):
    def test_template_does_not_attempt_an_ai_request_and_labels_provenance(self):
        app = FastAPI()
        app.include_router(scripts.router)
        with TestClient(app) as client, \
                patch.object(scripts, "generate_full_script", side_effect=AssertionError("No provider call")):
            response = client.post("/api/scripts/template", json={
                "idea": get_vehicle_ideas()[0], "target_duration_sec": 180,
            })
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["provenance"], "offline_template")
        self.assertEqual(payload["status"], "template")
        self.assertEqual(len(payload["script"]["scenes"]), 20)
        self.assertEqual(payload["script"]["planned_duration_sec"], 180)
        self.assertIn("no AI request", payload["warning"])

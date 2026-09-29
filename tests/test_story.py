import copy
import json
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.models import GeneratedScript, ProjectData, GENERATED_SCENE_TYPES
from app.services import ai_service


class StoryTests(unittest.TestCase):
    def setUp(self):
        self.idea = ai_service.get_vehicle_ideas()[0]
        self.script = ai_service._generate_dynamic_fallback_script(self.idea, ["dad", "levi", "luca"])

    def test_six_curated_concepts_are_complete_and_independent(self):
        concepts = ai_service.get_vehicle_ideas()
        self.assertEqual([idea["id"] for idea in concepts], [f"idea_car_{index}" for index in range(1, 7)])
        self.assertEqual([idea["target_vocab"][0]["chinese"] for idea in concepts], ["消防車", "挖土機", "救護車", "警車", "垃圾車", "賽車"])
        concepts[0]["title_english"] = "Changed locally"
        self.assertNotEqual(ai_service.get_vehicle_ideas()[0]["title_english"], "Changed locally")

    def test_all_vehicle_templates_have_twenty_chinese_dad_scenes(self):
        for idea in ai_service.get_vehicle_ideas():
            for target in (120, 180, 240):
                with self.subTest(idea=idea["id"], target=target):
                    script = ai_service._generate_dynamic_fallback_script(idea, ["mom"], target)
                    validated = GeneratedScript.model_validate(script)
                    self.assertEqual(len(validated.scenes), 20)
                    self.assertEqual(validated.planned_duration_sec, target)
                    self.assertTrue(all(scene.speaker == "Dad" for scene in validated.scenes))
                    self.assertTrue(all(any(character.name == "dad" for character in scene.characters) for scene in validated.scenes))
                    spoken = "".join(scene.cantonese for scene in validated.scenes)
                    self.assertNotRegex(spoken, r"[A-Za-z0-9]")
                    self.assertIn("哥哥", spoken)
                    self.assertIn("細佬", spoken)
                    self.assertIn("爸爸", spoken)

    def test_template_arc_types_and_chorus_intervals(self):
        scenes = self.script["scenes"]
        self.assertEqual([scene["act"] for scene in scenes], [1] * 3 + [2] * 7 + [3] * 3 + [4] * 4 + [5] * 3)
        self.assertEqual(set(scene["scene_type"] for scene in scenes), set(GENERATED_SCENE_TYPES))
        self.assertTrue(all(left["scene_type"] != right["scene_type"] for left, right in zip(scenes, scenes[1:])))
        chorus_positions = [scene["scene_number"] for scene in scenes if scene["scene_type"] == "CHORUS"]
        self.assertEqual(chorus_positions, [5, 10, 15, 19])
        self.assertTrue(all(scene["chorus"] in scene["cantonese"] for scene in scenes if scene["scene_type"] == "CHORUS"))
        self.assertEqual(scenes[10]["scene_type"], "CHALLENGE")
        self.assertEqual(scenes[11]["scene_type"], "COMFORT")
        self.assertEqual(scenes[13]["scene_type"], "TRY-AGAIN")

    def test_longer_target_adds_narration_not_only_duration(self):
        short = ai_service._generate_dynamic_fallback_script(self.idea, ["dad"], 120)
        medium = ai_service._generate_dynamic_fallback_script(self.idea, ["dad"], 180)
        long = ai_service._generate_dynamic_fallback_script(self.idea, ["dad"], 240)
        lengths = [sum(len(scene["cantonese"]) for scene in script["scenes"]) for script in (short, medium, long)]
        self.assertLess(lengths[0], lengths[1])
        self.assertLess(lengths[1], lengths[2])
        self.assertLess(min(scene["duration_sec"] for scene in short["scenes"]), 6)
        GeneratedScript.model_validate(short)

    def test_latin_names_digits_and_nonchinese_spoken_metadata_rejected(self):
        for field, value in (("cantonese", "爸爸同Levi一齊玩。"), ("cantonese", "爸爸數到3。"), ("cantonese", "。。。"), ("chorus", "Vroom！"), ("interaction_prompt", "Your turn")):
            invalid = copy.deepcopy(self.script)
            invalid["scenes"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                GeneratedScript.model_validate(invalid)
            ProjectData.model_validate(invalid)
        valid = copy.deepcopy(self.script)
        valid["scenes"][0]["english"] = "Daddy, Levi and Luca count 1, 2, 3."
        GeneratedScript.model_validate(valid)

    def test_generated_dad_rule_does_not_restrict_manual_projects(self):
        invalid = copy.deepcopy(self.script)
        invalid["scenes"][0]["speaker"] = "Mom"
        with self.assertRaises(ValidationError):
            GeneratedScript.model_validate(invalid)
        ProjectData.model_validate(invalid)

    def test_metadata_optional_but_validated_when_present(self):
        sparse = copy.deepcopy(self.script)
        sparse.pop("chorus")
        for scene in sparse["scenes"]:
            for key in ("act", "scene_type", "chorus", "interaction_prompt"):
                scene.pop(key, None)
        GeneratedScript.model_validate(sparse)
        invalid = copy.deepcopy(self.script)
        invalid["scenes"][1]["scene_type"] = invalid["scenes"][0]["scene_type"]
        with self.assertRaises(ValidationError):
            GeneratedScript.model_validate(invalid)

    def test_prompt_carries_five_act_and_clean_language_rules(self):
        with patch.object(ai_service, "generate_ai_text", return_value=json.dumps(self.script)) as generate:
            result = ai_service.generate_full_script(self.idea, ["dad"])
        prompt = generate.call_args.args[0]
        schema = generate.call_args.kwargs["response_schema"]
        self.assertEqual(generate.call_args.kwargs["timeout_ms"], 120_000)
        self.assertEqual(schema["properties"]["scenes"]["type"], "array")
        self.assertEqual(schema["properties"]["scenes"]["items"]["properties"]["speaker"]["type"], "string")
        for rule in ("18–22", "FIVE-ACT ARC", "CHORUS", "哥哥", "細佬", 'speaker exactly "Dad"', "CHINESE-ONLY"):
            self.assertIn(rule, prompt)
        self.assertEqual(result["planned_duration_sec"], 180)

    def test_provider_schema_omits_rejected_constraints_but_local_model_keeps_them(self):
        from app.models import generated_story_response_schema
        forbidden = {"minItems", "maxItems", "minimum", "maximum", "enum"}

        def check(node):
            if isinstance(node, dict):
                self.assertTrue(forbidden.isdisjoint(node))
                for value in node.values():
                    check(value)
            elif isinstance(node, list):
                for value in node:
                    check(value)

        schema = generated_story_response_schema()
        check(schema)
        self.assertIn("scenes", schema["required"])
        self.assertIn("duration_sec", schema["properties"]["scenes"]["items"]["required"])
        local = GeneratedScript.model_json_schema()
        self.assertEqual(local["properties"]["scenes"]["minItems"], 18)
        self.assertEqual(local["properties"]["scenes"]["maxItems"], 22)
        self.assertEqual(local["$defs"]["GeneratedScene"]["properties"]["speaker"]["const"], "Dad")
        for change in ({"speaker": "Mom"}, {"scene_type": "NOT-A-TYPE"}, {"duration_sec": 0}, {"act": 6}):
            invalid = copy.deepcopy(self.script)
            invalid["scenes"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValidationError):
                GeneratedScript.model_validate(invalid)

    def test_brainstorm_uses_explicit_sixty_second_budget(self):
        ideas = ai_service.get_grounded_topic_ideas("Numbers", "Toddlers")
        with patch.object(ai_service, "generate_ai_text", return_value=json.dumps(ideas)) as generate:
            result = ai_service.brainstorm_ideas("Numbers", "Toddlers", "Sharing")
        self.assertEqual(len(result), 3)
        self.assertEqual(generate.call_args.kwargs, {"timeout_ms": 60_000})

    def test_semantic_failure_is_safe_and_not_fallback(self):
        for field, value, code in (
            ("cantonese", "Levi!", "invalid_spoken_language"),
            ("speaker", "Mom", "invalid_narrator"),
        ):
            invalid = copy.deepcopy(self.script)
            invalid["scenes"][0][field] = value
            with self.subTest(field=field), patch.object(ai_service, "generate_ai_text", return_value=json.dumps(invalid)):
                with self.assertRaises(ai_service.GenerationError) as caught:
                    ai_service.generate_full_script(self.idea, ["dad"])
                self.assertEqual(caught.exception.code, code)

    def test_generic_letter_template_keeps_printed_letters_out_of_spoken_fields(self):
        idea = ai_service.get_grounded_topic_ideas("ABCs", "Toddlers")[0]
        script = ai_service._generate_dynamic_fallback_script(idea, ["dad"])
        self.assertNotRegex("".join(scene["cantonese"] for scene in script["scenes"]), r"[A-Za-z0-9]")
        self.assertEqual(script["planned_duration_sec"], 180)
        self.assertEqual([word["chinese"] for word in script["vocab_words"]], ["蘋果", "香蕉", "小貓"])
        self.assertEqual([word["english"] for word in script["vocab_words"]], ["Apple", "Banana", "Cat"])
        self.assertIn("蘋果", script["chorus"])
        self.assertNotIn("係，係", script["chorus"])
        spoken = "".join(scene["cantonese"] for scene in script["scenes"])
        for word in ("蘋果", "香蕉", "小貓"):
            self.assertIn(word, spoken)

    def test_unknown_mixed_vocabulary_is_rejected_not_stripped_to_particles(self):
        idea = copy.deepcopy(self.idea)
        idea["target_vocab"] = [{"chinese": "X係Unknown", "english": "Unknown"}]
        with self.assertRaises(ai_service.GenerationError) as caught:
            ai_service._generate_dynamic_fallback_script(idea, ["dad"])
        self.assertEqual(caught.exception.code, "unsupported_fallback_vocabulary")
        self.assertNotIn("Unknown", str(caught.exception))
        idea["target_vocab"] = [{"chinese": "B係Bird", "english": "Bird"}]
        script = ai_service._generate_dynamic_fallback_script(idea, ["dad"])
        self.assertEqual(script["vocab_words"][0]["chinese"], "小鳥")

    def test_grossly_short_and_long_narration_rejected_despite_valid_total(self):
        for text in ("好。", "好" * 10000):
            invalid = copy.deepcopy(self.script)
            for scene in invalid["scenes"]:
                scene["cantonese"] = text
                scene["duration_sec"] = 9
            with self.subTest(length=len(text)), self.assertRaises(ValidationError):
                GeneratedScript.model_validate(invalid)
            ProjectData.model_validate(invalid)
        short_hook = copy.deepcopy(self.script)
        difference = short_hook["scenes"][0]["duration_sec"] - 2
        short_hook["scenes"][0].update(cantonese="咦！", duration_sec=2)
        short_hook["scenes"][1]["duration_sec"] += difference
        GeneratedScript.model_validate(short_hook)

    def test_pacing_failure_is_actionable_without_implicit_fallback(self):
        invalid = copy.deepcopy(self.script)
        for scene in invalid["scenes"]:
            scene.update(cantonese="好。", duration_sec=9)
        with patch.object(ai_service, "generate_ai_text", return_value=json.dumps(invalid)):
            with self.assertRaises(ai_service.GenerationError) as caught:
                ai_service.generate_full_script(self.idea, ["dad"])
        self.assertEqual(caught.exception.code, "invalid_lesson_pacing")


if __name__ == "__main__":
    unittest.main()

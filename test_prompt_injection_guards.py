import unittest

from ai_engine import (
    SAFE_DOSAGE_FALLBACK,
    _contains_template_payload,
    get_medicine_dosage_info,
    search_medicine_fallback_ai,
)


class PromptInjectionGuardTests(unittest.TestCase):
    def test_template_probe_is_detected(self):
        self.assertTrue(_contains_template_payload("{{7*7}}"))
        self.assertTrue(_contains_template_payload({"dosage": "${7*7}mg"}))
        self.assertFalse(_contains_template_payload("Paracetamol IP 650mg"))

    def test_dosage_info_blocks_template_probe_before_llm(self):
        result = get_medicine_dosage_info("{{7*7}}", "Paracetamol")

        self.assertEqual(result, SAFE_DOSAGE_FALLBACK)
        self.assertNotEqual(result["dosage"], "49mg")

    def test_search_fallback_blocks_template_probe_before_llm(self):
        result = search_medicine_fallback_ai("{{7*7}}")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()

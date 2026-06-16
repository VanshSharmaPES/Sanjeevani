import unittest
import time

from ai_engine import (
    SAFE_DOSAGE_FALLBACK,
    _contains_template_payload,
    get_medicine_dosage_info,
    search_medicine_fallback_ai,
    _extract_json_from_text,
)


class PromptInjectionGuardTests(unittest.TestCase):
    def test_template_probe_is_detected(self):
        self.assertTrue(_contains_template_payload("{{7*7}}"))
        self.assertTrue(_contains_template_payload({"dosage": "${7*7}mg"}))
        self.assertTrue(_contains_template_payload("^(a+)+$"))
        self.assertTrue(_contains_template_payload("some (a*)* text"))
        self.assertFalse(_contains_template_payload("Paracetamol IP 650mg"))

    def test_dosage_info_blocks_template_probe_before_llm(self):
        result = get_medicine_dosage_info("{{7*7}}", "Paracetamol")

        self.assertEqual(result, SAFE_DOSAGE_FALLBACK)
        self.assertNotEqual(result["dosage"], "49mg")

    def test_search_fallback_blocks_template_probe_before_llm(self):
        result = search_medicine_fallback_ai("{{7*7}}")

        self.assertIsNone(result)


class ReDoSAndJsonExtractionTests(unittest.TestCase):
    def test_json_extraction_with_surrounding_prose(self):
        raw_text = "Here is the response: {\"medicineName\": \"Paracetamol\"} hope this helps!"
        result = _extract_json_from_text(raw_text)
        self.assertEqual(result, {"medicineName": "Paracetamol"})

    def test_json_extraction_with_nested_braces(self):
        raw_text = "```json\n{\"outer\": {\"inner\": 123}}\n```"
        result = _extract_json_from_text(raw_text)
        self.assertEqual(result, {"outer": {"inner": 123}})

    def test_redos_prevention_on_unmatched_braces(self):
        # Create a large string starting with '{' followed by 50,000 characters and NO '}'
        # If using vulnerable regex \{.*\}, it would perform significant backtracking
        large_unmatched = "{" + ("A" * 50000)
        
        start_time = time.time()
        with self.assertRaises(ValueError):
            _extract_json_from_text(large_unmatched)
        duration = time.time() - start_time
        
        # The O(N) find/rfind search should complete in less than 50 milliseconds
        self.assertLess(duration, 0.05, f"JSON extraction took too long ({duration:.4f}s), potential ReDoS vulnerability!")


if __name__ == "__main__":
    unittest.main()

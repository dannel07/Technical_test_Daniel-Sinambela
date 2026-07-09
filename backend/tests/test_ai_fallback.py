import unittest
from datetime import date
from types import SimpleNamespace

from app.ai_service import build_task_context, should_use_llm
from app.main import build_ai_reply, choose_best_reply, get_llm_reply


class AIFallbackTests(unittest.TestCase):
    def test_incomplete_tasks_reply_contains_pending_items(self):
        tasks = [
            SimpleNamespace(title="Design review", status="Todo", deadline="2026-07-10", assignee=SimpleNamespace(name="Admin")),
            SimpleNamespace(title="Deploy app", status="Done", deadline="2026-07-11", assignee=SimpleNamespace(name="Bob")),
        ]

        reply = build_ai_reply(tasks, "Tampilkan semua task yang statusnya belum selesai")

        self.assertIn("Design review", reply)
        self.assertIn("Todo", reply)
        self.assertIn("belum selesai", reply.lower())

    def test_completed_count_reply_reports_done_tasks(self):
        tasks = [
            SimpleNamespace(title="Design review", status="Done", deadline="2026-07-10", assignee=SimpleNamespace(name="Admin")),
            SimpleNamespace(title="Deploy app", status="Done", deadline="2026-07-11", assignee=SimpleNamespace(name="Bob")),
            SimpleNamespace(title="Write docs", status="Todo", deadline="2026-07-12", assignee=SimpleNamespace(name="Carol")),
        ]

        reply = build_ai_reply(tasks, "Berapa jumlah task yang sudah selesai?")

        self.assertIn("2", reply)
        self.assertIn("selesai", reply.lower())

    def test_deadline_today_reply_lists_todays_tasks(self):
        today = date.today().isoformat()
        tasks = [
            SimpleNamespace(title="Design review", status="Todo", deadline=today, assignee=SimpleNamespace(name="Admin")),
            SimpleNamespace(title="Deploy app", status="Done", deadline="2099-01-01", assignee=SimpleNamespace(name="Bob")),
        ]

        reply = build_ai_reply(tasks, "Tugas apa saja yang deadlinenya hari ini?")

        self.assertIn("Design review", reply)
        self.assertIn("hari ini", reply.lower())

    def test_assignee_lookup_reply_finds_assignee_for_task(self):
        tasks = [
            SimpleNamespace(title="Design review", status="Todo", deadline="2026-07-10", assignee=SimpleNamespace(name="Admin")),
            SimpleNamespace(title="Deploy app", status="Done", deadline="2026-07-11", assignee=SimpleNamespace(name="Bob")),
        ]

        reply = build_ai_reply(tasks, "Siapa assignee dari task Design review?")

        self.assertIn("Admin", reply)
        self.assertIn("assignee", reply.lower())

    def test_description_lookup_reply_finds_task_description(self):
        tasks = [
            SimpleNamespace(title="Design review", status="Todo", deadline="2026-07-10", description="Diskusi kebutuhan akhir", assignee=SimpleNamespace(name="Admin")),
            SimpleNamespace(title="Deploy app", status="Done", deadline="2026-07-11", description="Upload ke server", assignee=SimpleNamespace(name="Bob")),
        ]

        reply = build_ai_reply(tasks, "Apa deskripsi dari task Design review?")

        self.assertIn("Diskusi kebutuhan akhir", reply)
        self.assertIn("deskripsi", reply.lower())

    def test_choose_best_reply_prefers_fallback_for_generic_llm_answer(self):
        fallback = "Deskripsi dari task 'Design review' adalah: Diskusi kebutuhan akhir"
        llm_generic = "Maaf, saya tidak memiliki informasi tentang task 'Design review'."

        chosen = choose_best_reply("Apa deskripsi dari task Design review?", fallback, llm_generic)

        self.assertEqual(chosen, fallback)

    def test_llm_reply_uses_configured_client(self):
        class FakeCompletions:
            def create(self, **kwargs):
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Jawaban dari LLM"))])

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.chat = SimpleNamespace(completions=FakeCompletions())

        reply, error = get_llm_reply("- Design review | status: Todo", "Apa saja task pending?", client=FakeClient())

        self.assertEqual(reply, "Jawaban dari LLM")
        self.assertIsNone(error)

    def test_simple_queries_skip_llm(self):
        tasks = [
            SimpleNamespace(title="Design review", status="Todo", deadline="2026-07-10", assignee=SimpleNamespace(name="Admin")),
            SimpleNamespace(title="Deploy app", status="Done", deadline="2026-07-11", assignee=SimpleNamespace(name="Bob")),
        ]

        self.assertFalse(should_use_llm(tasks, "Tampilkan semua task yang statusnya belum selesai"))

    def test_build_task_context_filters_to_relevant_tasks(self):
        tasks = [
            SimpleNamespace(title="Design review", status="Todo", deadline="2026-07-10", assignee=SimpleNamespace(name="Admin")),
            SimpleNamespace(title="Deploy app", status="Done", deadline="2026-07-11", assignee=SimpleNamespace(name="Bob")),
        ]

        context = build_task_context(tasks, "Tampilkan semua task yang statusnya belum selesai")

        self.assertIn("Design review", context)
        self.assertNotIn("Deploy app", context)


if __name__ == "__main__":
    unittest.main()

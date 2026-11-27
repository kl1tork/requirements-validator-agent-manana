"""Автотесты агента без обращения к реальной модели.

Реальная LLM подменяется FakeLLM с заранее заданными ответами — так проверяются
чтение документа, привязка цитат, обработка «галлюцинаций», перепроверка и отчёт.
Запуск: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from reqval.document import load_document
from reqval.grounding import Grounder, normalize
from reqval.jsonutil import parse_json
from reqval.lint import lint
from reqval.llm import LLMClient, LLMConfig
from reqval.pipeline import run
from reqval.segment import explicit_ids, rule_segments

FIX = Path(__file__).parent / "fixtures" / "sample_requirements.md"


class FakeLLM(LLMClient):
    """Отвечает по ключевым словам задачи в промпте."""

    def __init__(self):
        super().__init__(LLMConfig(provider="ollama", model="fake-model"), verbose=False)
        self.prompts: list[str] = []

    def complete(self, system, user, json_mode=True, stage=""):
        self.prompts.append(user)
        self.calls += 1
        if user.startswith("Задача: выдели"):
            return json.dumps({"requirements": [
                {"doc_id": "FR-1", "section": "ФТ", "line_start": 7, "line_end": 7,
                 "quote": "Система должна быстро отправлять напоминание клиенту.", "summary": "Быстрая отправка",
                 "kind": "функциональное"},
                # FR-2 модель «пропустила» — парсер должен добавить
                {"doc_id": "FR-3", "section": "ФТ", "line_start": 9, "line_end": 9,
                 "quote": "Напоминание отправляется за 5 дней до даты платежа.", "summary": "За 5 дней",
                 "kind": "функциональное"},
                {"doc_id": None, "section": "НФТ", "line_start": 13, "line_end": 13,
                 "quote": "Сервис должен быть удобным и надёжным.", "summary": "Удобство", "kind": "нефункциональное"},
                # галлюцинация: такого текста нет и строка пустая
                {"doc_id": None, "section": "?", "line_start": 999, "line_end": 999,
                 "quote": "Система шифрует всё по ГОСТ", "summary": "?", "kind": "ограничение"},
            ]}, ensure_ascii=False)
        if user.startswith("Задача: проверь КАЖДОЕ"):
            return json.dumps({"results": [
                {"id": "R-01", "criteria": {"verifiable": "violation"}, "issues": [
                    {"criterion": "verifiable", "severity": "critical", "line": 7, "quote": "быстро отправлять",
                     "problem": "«Быстро» не измеримо.", "fix": "Указать срок, например 60 с."}]},
                {"id": "R-04", "criteria": {"unambiguous": "violation"}, "issues": [
                    {"criterion": "unambiguous", "severity": "major", "line": 13, "quote": "удобным и надёжным",
                     "problem": "Размытые характеристики.", "fix": "Задать метрики."},
                    {"criterion": "singular", "severity": "minor", "line": 13,
                     "quote": "текст, которого в документе нет", "problem": "Галлюцинация.", "fix": ""}]},
            ]}, ensure_ascii=False)
        if user.startswith("Задача: проверь НАБОР"):
            return json.dumps({"criteria": {"set_consistent": {"status": "violation", "comment": "FR-2 vs FR-3"},
                                            "ranked": {"status": "violation", "comment": "нет приоритетов"}},
                               "issues": [
                {"criterion": "set_consistent", "severity": "critical",
                 "locations": [{"line": 8, "quote": "за 3 дня до даты платежа"},
                               {"line": 9, "quote": "за 5 дней до даты платежа"}],
                 "related": ["R-02", "R-03"], "problem": "Разный срок напоминания.", "fix": "Выбрать один срок."},
                {"criterion": "ranked", "severity": "minor", "locations": [{"line": 5, "quote": "Функциональные требования"}],
                 "related": [], "problem": "Нет приоритетов.", "fix": "Добавить MoSCoW."}]}, ensure_ascii=False)
        if user.startswith("Задача: независимая"):
            return json.dumps({"verdicts": [
                {"id": "V-001", "decision": "confirm", "severity": "critical"},
                {"id": "V-002", "decision": "confirm", "severity": "major"},
                {"id": "V-005", "decision": "reject", "reason": "придирка", "duplicate_of": None}],
                "summary": "Есть противоречие сроков.",
                "priorities": [{"text": "Согласовать срок напоминания", "issues": ["V-004"]}]}, ensure_ascii=False)
        raise AssertionError("неожиданный промпт")


class DocumentTests(unittest.TestCase):
    def test_load_markdown(self):
        d = load_document(FIX)
        self.assertEqual(d.title, "Учебный пример: напоминание об оплате")
        self.assertEqual(d.line(7).strip()[:9], "* **FR-1.")
        self.assertIn("Функциональные требования", d.section_of(8))
        self.assertEqual(explicit_ids(d), {"FR-1": 7, "FR-2": 8, "FR-3": 9})

    def test_rule_segments(self):
        reqs = rule_segments(load_document(FIX))
        self.assertTrue(any(r.doc_id == "FR-2" for r in reqs))
        self.assertTrue(all(r.rid.startswith("R-") for r in reqs))

    def test_lint(self):
        rules = {(h.line, h.rule) for h in lint(load_document(FIX))}
        self.assertIn((7, "vague"), rules)
        self.assertIn((25, "empty_value"), rules)

    def test_pdf_and_docx(self):
        try:
            import docx  # noqa: F401
        except ImportError:
            self.skipTest("python-docx не установлен")
        import docx as D

        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.docx"
            doc = D.Document()
            doc.add_heading("Тест", 1)
            doc.add_paragraph("Ф-1. Система отправляет push.")
            t = doc.add_table(rows=1, cols=2)
            t.rows[0].cells[0].text, t.rows[0].cells[1].text = "A", "B"
            doc.save(p)
            d = load_document(p)
            self.assertIn("# Тест", d.text())
            self.assertIn("| A | B |", d.text())


class GroundingTests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize("**Порог** 1 000 ₸ — «да»"), 'порог 1000 ₸ - "да"')

    def test_locate(self):
        g = Grounder(load_document(FIX))
        self.assertEqual(g.locate("за 5 дней до даты платежа", 3).line_start, 9)
        loc = g.locate("СИСТЕМА  должна быстро отправлять", None)
        self.assertTrue(loc.grounded)
        self.assertEqual(loc.line_start, 7)
        self.assertFalse(g.locate("совершенно посторонний текст про ГОСТ", 7).grounded)

    def test_parse_json(self):
        self.assertEqual(parse_json('```json\n{"a": [1,2,],}\n```'), {"a": [1, 2]})


class PipelineTests(unittest.TestCase):
    def test_end_to_end(self):
        llm = FakeLLM()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.md"
            paths = run(FIX, out, llm)
            md = out.read_text("utf-8")
            data = json.loads(paths[1].read_text("utf-8"))

        for section in ("## 1. Паспорт прогона", "## 2. Как агент нарезал требования",
                        "## 3. Проверка каждого требования", "## 4. Проверка всего набора требований",
                        "## 5. Сводка", "## 6. Итог"):
            self.assertIn(section, md)
        self.assertIn("fake-model", md)
        # FR-2, пропущенный моделью, добавлен парсером
        self.assertIn("FR-2", [r["doc_id"] for r in data["requirements"]])
        # галлюцинированное требование отброшено
        self.assertNotIn("ГОСТ", md.split("## 3.")[0])
        # противоречие сослалось на обе строки
        self.assertIn("строка 8", md)
        self.assertIn("строка 9", md)
        # замечание с несуществующей цитатой не вошло в выводы
        issues = [i for r in data["requirement_results"].values() for i in r["issues"]]
        self.assertTrue(any(i["status"] == "ungrounded" for i in issues))
        # отклонённое при перепроверке — в приложении A
        set_issues = data["set_result"]["issues"]
        self.assertEqual([i["status"] for i in set_issues], ["confirmed", "rejected"])
        self.assertTrue(data["verdict"].startswith("НЕТ"))
        self.assertIn("Согласовать срок напоминания (V-004)", md)


class FallbackTest(unittest.TestCase):
    """Переключение на запасную модель при 404 и при повторяющихся 503 (без сети)."""

    def _client(self, behaviour: dict):
        from reqval import llm as llm_mod

        cfg = LLMConfig(provider="gemini", model="main", api_key="k", max_retries=6,
                        fallback_models=("spare1", "spare2"), switch_after=3)
        client = LLMClient(cfg, verbose=False)
        seen: list[str] = []

        def fake_call(system, user, json_mode):
            seen.append(client.cfg.model)
            kind = behaviour.get(client.cfg.model, "ok")
            if kind == "404":
                raise llm_mod._ModelGone("HTTP 404")
            if kind == "503":
                raise llm_mod._Retryable("HTTP 503", delay=0)
            return '{"ok": true}'

        client._call_gemini = fake_call
        from unittest import mock
        patcher = mock.patch.object(llm_mod.time, "sleep", lambda s: None)
        patcher.start()
        self.addCleanup(patcher.stop)
        return client, seen

    def test_404_switches_immediately(self):
        client, seen = self._client({"main": "404"})
        self.assertEqual(client.complete("s", "u"), '{"ok": true}')
        self.assertEqual(seen, ["main", "spare1"])
        self.assertEqual(client.models_used, ["main", "spare1"])

    def test_503_switches_after_three_attempts(self):
        client, seen = self._client({"main": "503", "spare1": "503"})
        client.complete("s", "u")
        self.assertEqual(seen, ["main"] * 3 + ["spare1"] * 3 + ["spare2"])
        # следующий запрос сразу идёт в рабочую модель
        client.complete("s", "u2")
        self.assertEqual(seen[-1], "spare2")

    def test_exhausted_quota_switches_without_waiting(self):
        from reqval import llm as llm_mod
        client, seen = self._client({})

        def quota(system, user, json_mode):
            seen.append(client.cfg.model)
            if client.cfg.model == "main":
                raise llm_mod._Retryable("HTTP 429", delay=81496)
            return '{"ok": true}'

        client._call_gemini = quota
        client.complete("s", "u")
        self.assertEqual(seen, ["main", "spare1"])

    def test_returns_to_overloaded_model_when_spares_exhausted(self):
        from reqval import llm as llm_mod
        client, seen = self._client({})
        state = {"main_calls": 0}

        def call(system, user, json_mode):
            seen.append(client.cfg.model)
            if client.cfg.model == "main":
                state["main_calls"] += 1
                if state["main_calls"] <= 3:
                    raise llm_mod._Retryable("HTTP 503", delay=0)
                return '{"ok": true}'
            raise llm_mod._Retryable("HTTP 429", delay=81496)

        client._call_gemini = call
        self.assertEqual(client.complete("s", "u"), '{"ok": true}')
        self.assertEqual(seen, ["main"] * 3 + ["spare1", "spare2", "main"])

    def test_no_fallbacks_left_raises(self):
        client, _ = self._client({"main": "404", "spare1": "404", "spare2": "404"})
        from reqval.llm import LLMError
        with self.assertRaises(LLMError):
            client.complete("s", "u")


if __name__ == "__main__":
    unittest.main()

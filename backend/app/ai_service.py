import os
import re
from datetime import date
from typing import Iterable


def _normalize_status(status: str | None) -> str:
    return (status or "").strip().lower()


def _is_done_task(task) -> bool:
    return _normalize_status(getattr(task, "status", "")) in {"done", "selesai", "completed", "complete"}


def _is_simple_task_query(message: str) -> bool:
    normalized = (message or "").strip().lower()
    simple_patterns = [
        "belum selesai",
        "todo",
        "selesai",
        "jumlah",
        "count",
        "deadline hari ini",
        "deadlinenya hari ini",
        "ringkasan",
        "summary",
        "daftar task",
        "semua task",
        "status task",
        "assignee",
        "deskripsi",
        "deadline",
    ]
    return any(pattern in normalized for pattern in simple_patterns)


def should_use_llm(tasks: Iterable, message: str) -> bool:
    if not _is_simple_task_query(message):
        return True
    if not list(tasks):
        return False
    return False


def build_task_context(tasks: Iterable, message: str) -> str:
    task_list = list(tasks)
    if not task_list:
        return "Tidak ada task."

    normalized = (message or "").strip().lower()

    if "belum selesai" in normalized or "todo" in normalized or "incomplete" in normalized:
        relevant = [task for task in task_list if not _is_done_task(task)]
    elif "selesai" in normalized or "done" in normalized:
        relevant = [task for task in task_list if _is_done_task(task)]
    elif "deadline hari ini" in normalized or "deadlinenya hari ini" in normalized or "today" in normalized:
        today = date.today().isoformat()
        relevant = [task for task in task_list if getattr(task, "deadline", None) == today]
    else:
        relevant = task_list[:8]

    if not relevant:
        return "Tidak ada task yang relevan."

    lines = []
    for task in relevant:
        assignee = getattr(getattr(task, "assignee", None), "name", "Unassigned")
        title = getattr(task, "title", "")
        status = getattr(task, "status", "")
        deadline = getattr(task, "deadline", "")
        lines.append(f"- {title} | status: {status} | deadline: {deadline} | assignee: {assignee}")
    return "\n".join(lines)

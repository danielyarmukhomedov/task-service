#!/usr/bin/env python3
"""Verify a running Task Service using only the Python standard library."""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Verification:
    def __init__(self, base_url, mailpit_url, output):
        self.base = base_url.rstrip("/")
        self.mailpit = mailpit_url.rstrip("/")
        self.output = output
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def log(self, message):
        print(message, flush=True)
        self.output.write(message + "\n")
        self.output.flush()

    def request(self, method, path, payload=None, expected=(200,), mailpit=False, quiet=False):
        base = self.mailpit if mailpit else self.base
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"} if body is not None else {}
        request = urllib.request.Request(base + path, data=body, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=12) as response:
                code, raw = response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            code, raw = error.code, error.read().decode("utf-8", errors="replace")
        if not quiet:
            self.log(f"{method} {base}{path} -> HTTP {code}")
        if code not in expected:
            raise RuntimeError(f"Expected HTTP {expected}, received {code}: {raw[:500]}")
        try:
            return json.loads(raw) if raw.strip() else None
        except ValueError:
            return raw

    def wait_ready(self, path, mailpit=False, timeout=600):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self.request("GET", path, mailpit=mailpit, quiet=True)
                self.log("READY " + (self.mailpit if mailpit else self.base) + path)
                return
            except (OSError, RuntimeError, ValueError):
                time.sleep(1)
        raise RuntimeError("Readiness timeout: " + path)

    def show(self, data):
        self.log(json.dumps(data, ensure_ascii=False, sort_keys=True))

    def find_task(self, task_id):
        tasks = self.request("GET", "/tasks")
        if not isinstance(tasks, list):
            raise RuntimeError("GET /tasks must return a JSON array")
        return next((task for task in tasks if task.get("id") == task_id), None)

    def find_message(self, subject):
        inbox = self.request("GET", "/api/v1/messages", mailpit=True)
        return next((mail for mail in inbox.get("messages", []) if mail.get("Subject") == subject), None)

    def run(self, check_persistence):
        self.log("Task Service verification — " + datetime.now(timezone.utc).isoformat())
        for path in ["/health/gateway", "/health/api", "/health/notifications", "/analytics", "/mail/readyz"]:
            self.wait_ready(path)
        self.wait_ready("/readyz", mailpit=True)
        test_id = uuid4().hex[:12]
        task_id = None
        try:
            created = self.request("POST", "/tasks", {
                "title": "Проверка проекта " + test_id,
                "description": "Создание задачи через HTTP API", "priority": "High"
            }, expected=(201,))
            self.show(created)
            task_id = created["id"]
            if created.get("completed") is not False:
                raise RuntimeError("A new task must be incomplete")

            updated = self.request("PUT", f"/tasks/{task_id}", {
                "title": "Обновлённая задача " + test_id,
                "description": "Изменение названия и приоритета", "priority": "Low"
            })
            self.show(updated)
            if updated.get("priority") != "Low" or updated.get("title") != "Обновлённая задача " + test_id:
                raise RuntimeError("Task details were not updated")

            completed = self.request("PATCH", f"/tasks/{task_id}/completion", {"completed": True})
            self.show(completed)
            saved = self.find_task(task_id)
            if completed.get("completed") is not True or saved is None or saved.get("completed") is not True:
                raise RuntimeError("Completion was not persisted")
            self.log("PASS create, read, update and completion")

            self.request("POST", "/tasks", {"title": " ", "priority": "High"}, expected=(400,))
            self.request("POST", "/tasks", {"title": "Invalid priority", "priority": "Critical"}, expected=(400,))
            self.log("PASS invalid task input returns HTTP 400")

            before = self.request("GET", "/analytics")["total_tasks"]
            self.request("POST", "/analytics/increment")
            after = self.request("GET", "/analytics")["total_tasks"]
            if after != before + 1:
                raise RuntimeError("Go event counter did not increment")
            self.show({"analytics_before": before, "analytics_after": after})
            self.log("PASS Go analytics")

            subject = "Проверка SMTP " + test_id
            queued = self.request("POST", "/notify", {
                "email": "professor@example.com", "subject": subject,
                "message": "Письмо для проверки Task Service. Код проверки: " + test_id
            }, expected=(202,))
            self.show(queued)
            notification_id = queued["notification_id"]
            deadline = time.monotonic() + 90
            while True:
                job = self.request("GET", "/notify/" + notification_id)
                if job.get("status") == "sent":
                    self.show(job)
                    break
                if job.get("status") == "failed":
                    raise RuntimeError("SMTP delivery failed: " + str(job.get("error")))
                if time.monotonic() >= deadline:
                    raise RuntimeError("SMTP delivery timed out")
                time.sleep(1)
            if self.find_message(subject) is None:
                raise RuntimeError("The SMTP message is absent from Mailpit")
            self.log("PASS SMTP accepted and message found in Mailpit")

            if check_persistence:
                command = ["docker", "compose", "up", "-d", "--no-deps", "--force-recreate",
                           "--wait", "--wait-timeout", "180", "db", "mailpit"]
                self.log("RUN " + " ".join(command))
                result = subprocess.run(command, cwd=Path(__file__).resolve().parent.parent,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.log(result.stdout.rstrip())
                result.check_returncode()
                result = subprocess.run(["docker", "compose", "restart", "api"],
                                        cwd=Path(__file__).resolve().parent.parent,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                self.log(result.stdout.rstrip())
                result.check_returncode()
                self.wait_ready("/health/api")
                self.wait_ready("/health/notifications")
                self.wait_ready("/readyz", mailpit=True)
                saved = self.find_task(task_id)
                if saved is None or saved.get("completed") is not True or saved.get("priority") != "Low":
                    raise RuntimeError("Task did not survive database container recreation")
                if self.find_message(subject) is None:
                    raise RuntimeError("Message did not survive Mailpit container recreation")
                self.log("PASS PostgreSQL db_data and Mailpit mailpit_data survive container recreation")
            else:
                self.log("SKIP container recreation: use --check-persistence with Docker Compose")

            self.request("DELETE", f"/tasks/{task_id}", expected=(204,))
            if self.find_task(task_id) is not None:
                raise RuntimeError("Deleted task is still present")
            self.request("DELETE", f"/tasks/{task_id}", expected=(404,))
            task_id = None
            self.log("PASS delete and repeated delete returns HTTP 404")
            self.log("RESULT: PASS")
        finally:
            if task_id is not None:
                try:
                    self.request("DELETE", f"/tasks/{task_id}", expected=(204, 404))
                except Exception as error:
                    self.log("Cleanup of the test task failed: " + str(error))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8088")
    parser.add_argument("--mailpit-url", default="http://127.0.0.1:8025/mail")
    parser.add_argument("--check-persistence", action="store_true",
                        help="Recreate db and mailpit containers while preserving their volumes")
    parser.add_argument("--output", type=Path, default=Path("docs/evidence/runtime/api-check.txt"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as output:
        verification = Verification(args.base_url, args.mailpit_url, output)
        try:
            verification.run(args.check_persistence)
        except Exception as error:
            verification.log("RESULT: FAIL — " + str(error))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

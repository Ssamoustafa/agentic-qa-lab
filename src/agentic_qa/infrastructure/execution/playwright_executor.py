from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import (
    BrowserContext,
    Page,
    Request,
    Route,
    WebSocketRoute,
    sync_playwright,
)
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from agentic_qa.domain.models import (
    Action,
    EvidenceReference,
    ExecutionConstraints,
    OracleKind,
    OracleVerdict,
    Outcome,
    ScenarioResult,
    TestScenario,
    TestStep,
)
from agentic_qa.domain.oracle import (
    evaluate_contains_text,
    evaluate_http_status,
    evaluate_visibility,
)
from agentic_qa.infrastructure.evidence.store import FilesystemEvidenceStore

_MAX_ENTRIES = 200
_MAX_TEXT = 500
_MAX_REASON = 300
_SCREENSHOT_GRACE_MS = 500.0
_SCREENSHOT_MAX_MS = 5000.0
_HTTP_SCHEMES = frozenset({"http", "https"})
_DURATION_EXCEEDED = "duration budget exceeded"
_HOSTNAME = re.compile(r"[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?")


@dataclass(slots=True)
class _Recorder:
    """Bounded observations; unbounded growth would let a page exhaust memory."""

    console: list[dict[str, str]] = field(default_factory=list)
    page_errors: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)
    truncated: bool = False

    def add_console(self, kind: str, text: str) -> None:
        if len(self.console) >= _MAX_ENTRIES:
            self.truncated = True
            return
        self.console.append({"type": kind, "text": text[:_MAX_TEXT]})

    def add_page_error(self, text: str) -> None:
        if len(self.page_errors) >= _MAX_ENTRIES:
            self.truncated = True
            return
        self.page_errors.append(text[:_MAX_TEXT])

    def add_blocked(self, url: str) -> None:
        if url[:_MAX_TEXT] in self.blocked:
            return
        if len(self.blocked) >= _MAX_ENTRIES:
            self.truncated = True
            return
        self.blocked.append(url[:_MAX_TEXT])

    def payload(self) -> dict[str, object]:
        return {
            "console": self.console,
            "page_errors": self.page_errors,
            "blocked_requests": self.blocked,
            "truncated": self.truncated,
        }


def _first_line(message: str) -> str:
    lines = message.strip().splitlines()
    return (lines[0] if lines else "unknown error")[:_MAX_REASON]


def _host_allowed(url: str, schemes: frozenset[str], allowed_hosts: frozenset[str]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in schemes and parsed.hostname in allowed_hosts


def _resolver_rules(allowed_hosts: frozenset[str]) -> str:
    """Chromium refuses to resolve every host except the allowlist, including redirect hops."""
    for host in allowed_hosts:
        if not _HOSTNAME.fullmatch(host):
            raise ValueError(f"allowed host cannot be enforced by the browser: {host!r}")
    excluded = ", ".join(f"EXCLUDE {host}" for host in sorted(allowed_hosts))
    return "MAP * ~NOTFOUND" + (", " + excluded if excluded else "")


class PlaywrightScenarioExecutor:
    """Runs one approved scenario in a fresh browser; the browser is never shared.

    A new browser and context per call trades speed for isolation: no cookies, storage,
    cache or service worker can leak between scenarios. Worker pooling is a later concern.
    """

    def __init__(
        self,
        store: FilesystemEvidenceStore,
        *,
        headless: bool = True,
        step_timeout_ms: int = 5000,
    ) -> None:
        if step_timeout_ms <= 0:
            raise ValueError("step_timeout_ms must be positive")
        self._store = store
        self._headless = headless
        self._step_timeout_ms = step_timeout_ms

    def execute(
        self, scenario: TestScenario, *, run_id: str, constraints: ExecutionConstraints
    ) -> ScenarioResult:
        started = time.perf_counter()
        directory = self._store.scenario_directory(run_id, scenario.scenario_id)
        deadline = started + constraints.budget.max_duration_seconds
        recorder = _Recorder()
        verdicts: list[OracleVerdict] = []
        screenshot = directory / "final.png"
        trace = directory / "trace.zip"

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=self._headless,
                args=[f"--host-resolver-rules={_resolver_rules(constraints.allowed_hosts)}"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1280, "height": 720},
                    locale="en-US",
                    timezone_id="UTC",
                    service_workers="block",
                    accept_downloads=False,
                )
                try:
                    self._install_egress_guard(context, constraints.allowed_hosts, recorder)
                    context.tracing.start(screenshots=True, snapshots=True)
                    try:
                        page = context.new_page()
                        self._observe(page, recorder, constraints.allowed_hosts)
                        failure = self._run_steps(page, scenario, deadline, verdicts, recorder)
                        remaining_ms = (deadline - time.perf_counter()) * 1000
                        capture_ms = min(
                            _SCREENSHOT_MAX_MS, max(_SCREENSHOT_GRACE_MS, remaining_ms)
                        )
                        self._capture_screenshot(page, screenshot, capture_ms)
                    finally:
                        context.tracing.stop(path=str(trace))
                finally:
                    context.close()
            finally:
                browser.close()

        console = self._store.write_json(directory, "console.json", recorder.payload())
        evidence = self._evidence(screenshot, trace, console)
        outcome, reason = self._outcome(failure, verdicts)
        duration_ms = round((time.perf_counter() - started) * 1000)
        return ScenarioResult(
            scenario.scenario_id, outcome, duration_ms, evidence, tuple(verdicts), reason
        )

    def _install_egress_guard(
        self, context: BrowserContext, allowed_hosts: frozenset[str], recorder: _Recorder
    ) -> None:
        def guard_http(route: Route) -> None:
            url = route.request.url
            if _host_allowed(url, _HTTP_SCHEMES, allowed_hosts):
                route.continue_()
                return
            recorder.add_blocked(url)
            route.abort("blockedbyclient")

        def guard_websocket(websocket: WebSocketRoute) -> None:
            # Never connected to a server, so nothing leaves the browser. Sync Playwright calls
            # such as close() deadlock inside route handlers, so the handler only records.
            recorder.add_blocked(websocket.url)

        context.route("**/*", guard_http)
        context.route_web_socket("**/*", guard_websocket)

    @staticmethod
    def _observe(page: Page, recorder: _Recorder, allowed_hosts: frozenset[str]) -> None:
        def on_request_failed(request: Request) -> None:
            if not _host_allowed(request.url, _HTTP_SCHEMES, allowed_hosts):
                recorder.add_blocked(request.url)

        page.on("console", lambda message: recorder.add_console(message.type, message.text))
        page.on("pageerror", lambda error: recorder.add_page_error(str(error)))
        page.on("requestfailed", on_request_failed)

    def _run_steps(
        self,
        page: Page,
        scenario: TestScenario,
        deadline: float,
        verdicts: list[OracleVerdict],
        recorder: _Recorder,
    ) -> str | None:
        for index, step in enumerate(scenario.steps):
            remaining_ms = (deadline - time.perf_counter()) * 1000
            if remaining_ms <= 0:
                return _DURATION_EXCEEDED
            budget_bound = remaining_ms <= self._step_timeout_ms
            timeout_ms = min(float(self._step_timeout_ms), remaining_ms)
            try:
                verdict = self._execute_step(page, step, index, timeout_ms)
            except PlaywrightError as exc:
                if recorder.blocked:
                    return self._egress_reason(recorder)
                if budget_bound and isinstance(exc, PlaywrightTimeoutError):
                    return _DURATION_EXCEEDED
                return f"step {index} ({step.action.value}) failed: {_first_line(str(exc))}"
            if recorder.blocked:
                return self._egress_reason(recorder)
            if verdict is not None:
                verdicts.append(verdict)
                if not verdict.passed:
                    return f"step {index} ({step.action.value}) failed its oracle"
        if recorder.blocked:
            return self._egress_reason(recorder)
        return None

    @staticmethod
    def _egress_reason(recorder: _Recorder) -> str:
        hosts = sorted({urlparse(url).hostname or "unknown" for url in recorder.blocked})
        return f"egress blocked by host allowlist: {', '.join(hosts)}"[:_MAX_REASON]

    @staticmethod
    def _execute_step(
        page: Page, step: TestStep, index: int, timeout_ms: float
    ) -> OracleVerdict | None:
        if step.action is Action.NAVIGATE:
            response = page.goto(step.target, timeout=timeout_ms)
            if response is None:
                return None
            return evaluate_http_status(step.target, response.status, step_index=index)

        locator = page.locator(step.target)
        if step.action is Action.CLICK:
            locator.click(timeout=timeout_ms)
        elif step.action is Action.FILL:
            locator.fill(step.value or "", timeout=timeout_ms)
        elif step.action is Action.ASSERT_VISIBLE:
            try:
                locator.wait_for(state="visible", timeout=timeout_ms)
                visible = True
            except PlaywrightTimeoutError:
                visible = False
            return evaluate_visibility(step.target, visible=visible, step_index=index)
        elif step.action is Action.ASSERT_TEXT:
            actual = locator.inner_text(timeout=timeout_ms)
            return evaluate_contains_text(
                step.target, expected=step.value or "", actual=actual, step_index=index
            )
        return None

    @staticmethod
    def _capture_screenshot(page: Page, path: Path, timeout_ms: float) -> None:
        try:
            page.screenshot(path=str(path), full_page=True, timeout=timeout_ms)
        except PlaywrightError:
            # A crashed page has nothing to capture; the missing file is then detected downstream.
            return

    def _evidence(
        self, screenshot: Path, trace: Path, console: Path
    ) -> tuple[EvidenceReference, ...]:
        candidates = (("screenshot", screenshot), ("playwright_trace", trace), ("console", console))
        return tuple(
            self._store.reference(kind, path) for kind, path in candidates if path.is_file()
        )

    @staticmethod
    def _outcome(failure: str | None, verdicts: list[OracleVerdict]) -> tuple[Outcome, str | None]:
        if failure is not None:
            return Outcome.FAILED, failure
        if not any(verdict.oracle is OracleKind.DETERMINISTIC for verdict in verdicts):
            return Outcome.FAILED, "scenario produced no deterministic verdict"
        return Outcome.PASSED, None

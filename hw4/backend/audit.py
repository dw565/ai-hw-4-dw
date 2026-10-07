"""Append-only audit trail of the agent loop: output/audit_trail.json.

One AuditEntry per model response (plus one for turns that stop early). The file
is a JSON array; each write takes an exclusive file lock, appends, and swaps the
file in atomically, so concurrent writers and crashes can't lose earlier runs.
"""

import fcntl
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel
from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

from db import ROOT
from models import (
    Alternatives,
    AuditEntry,
    AuditToolCall,
    ChatReply,
    ProductDetails,
    SearchResults,
    StockCheck,
    StopReason,
)

AUDIT_FILE = ROOT / "output" / "audit_trail.json"
LOCK_FILE = AUDIT_FILE.with_suffix(".lock")


def _short(value, limit: int = 120):
    """Shorten long strings and lists so log entries stay readable."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[: limit - 1] + "…"
    if isinstance(value, list):
        items = [_short(v, limit) for v in value[:5]]
        return items + [f"…+{len(value) - 5} more"] if len(value) > 5 else items
    if isinstance(value, dict):
        return {k: _short(v, limit) for k, v in value.items()}
    return value


def summarize(content: object) -> str:
    """One-line summary of a tool result for the audit trail."""
    if isinstance(content, SearchResults):
        ids = [p.product_id for p in content.products[:5]]
        more = f" +{len(content.products) - 5}" if len(content.products) > 5 else ""
        return f"total_matches={content.total_matches}, returned={len(content.products)}: {ids}{more}"
    if isinstance(content, ProductDetails):
        stock = " ".join(f"{s.size}={s.quantity}" for s in content.stock_by_size)
        return f"{content.product_id} ${content.price:.2f} | {stock}"
    if isinstance(content, StockCheck):
        asked = f"{content.requested_size}={content.requested_size_quantity} ({content.requested_size_status}) | " if content.requested_size else ""
        return f"{content.product_id} ${content.price:.2f} | {asked}in stock: {','.join(content.sizes_in_stock) or 'none'}"
    if isinstance(content, Alternatives):
        alts = [f"{a.product_id}({a.size_quantity if a.size_quantity is not None else a.total_stock})" for a in content.alternatives]
        return f"for {content.original_product_id} size {content.size}: {alts}"
    if isinstance(content, ChatReply):
        page = f", page_search={content.page_search.title!r}" if content.page_search else ""
        return f"reply {len(content.message)} chars, product_ids={content.product_ids}{page}"
    text = content.model_dump_json() if isinstance(content, BaseModel) else str(content)
    return _short(text, 200)


def append_audit_entry(entry: AuditEntry) -> None:
    AUDIT_FILE.parent.mkdir(exist_ok=True)
    with open(LOCK_FILE, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            rows = json.loads(AUDIT_FILE.read_text()) if AUDIT_FILE.exists() else []
        except json.JSONDecodeError:
            # Never overwrite a file we can't parse; keep it and start a new one beside it.
            AUDIT_FILE.rename(AUDIT_FILE.with_suffix(f".corrupt-{uuid.uuid4().hex[:6]}.json"))
            rows = []
        rows.append(entry.model_dump())
        tmp = AUDIT_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
        tmp.replace(AUDIT_FILE)  # atomic swap


class AuditRecorder:
    """Turns one chat turn's agent loop into AuditEntry rows, appended as the loop runs.

    A model response is written once its tool calls have results (when the next
    request carries them), when the run ends, or when it fails.
    """

    def __init__(self, customer: str, page: str | None, user_message: str, model: str):
        self.run_id = uuid.uuid4().hex[:12]
        self.base = dict(customer=customer, page=page, user_message=_short(user_message, 200), model=model)
        self.iteration = 0
        self.pending: ModelResponse | None = None

    def start_response(self, response: ModelResponse) -> None:
        self.pending = response

    def on_request(self, request: ModelRequest) -> None:
        """A new request carries the results of the previous response's tool calls."""
        results: dict[str, AuditToolCall] = {}
        output_retry = False
        for part in request.parts:
            if isinstance(part, ToolReturnPart):
                results[part.tool_call_id] = AuditToolCall(
                    tool_name=part.tool_name, args={}, status="ok", result_summary=summarize(part.content)
                )
            elif isinstance(part, RetryPromptPart) and part.tool_call_id:
                message = part.content if isinstance(part.content, str) else "argument validation failed"
                results[part.tool_call_id] = AuditToolCall(
                    tool_name=part.tool_name or "?", args={}, status="retry", result_summary=_short(message, 200)
                )
                output_retry = output_retry or part.tool_name == "final_result"
        self.finish_response(results, "output_retry" if output_retry else "tool_calls")

    def finish_response(
        self,
        results: dict[str, AuditToolCall] | None = None,
        stop_reason: StopReason = "tool_calls",
        final_output: object = None,
        detail: str | None = None,
    ) -> None:
        if self.pending is None:
            return
        response, self.pending = self.pending, None
        self.iteration += 1
        results = results or {}
        calls = []
        for part in response.parts:
            if not isinstance(part, ToolCallPart):
                continue
            call = results.get(part.tool_call_id)
            if call is None:
                if final_output is not None:
                    call = AuditToolCall(tool_name=part.tool_name, args={}, status="ok", result_summary=summarize(final_output))
                else:
                    status = "pending" if stop_reason == "tool_calls" else "error"
                    call = AuditToolCall(tool_name=part.tool_name, args={}, status=status, result_summary=detail or stop_reason)
            calls.append(call.model_copy(update={"tool_name": part.tool_name, "args": _short(part.args_as_dict())}))
        append_audit_entry(
            AuditEntry(
                run_id=self.run_id,
                iteration=self.iteration,
                timestamp=response.timestamp.astimezone(timezone.utc).isoformat(),
                **{**self.base, "model": response.model_name or self.base["model"]},
                tool_calls=calls,
                stop_reason=stop_reason,
                detail=detail,
                provider_finish_reason=response.finish_reason,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            )
        )

    def stop(self, stop_reason: StopReason, detail: str | None = None) -> None:
        """End the turn early: flush any pending response, or log a standalone entry."""
        if self.pending is not None:
            self.finish_response(stop_reason=stop_reason, detail=detail)
            return
        append_audit_entry(
            AuditEntry(
                run_id=self.run_id,
                iteration=0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                **self.base,
                stop_reason=stop_reason,
                detail=detail,
            )
        )

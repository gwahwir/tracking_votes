"""Bulk re-score seats against the latest seat_agent prompt + schema.

Reads constituency codes from historical_results (2022 baseline), dispatches
seat_agent tasks in parallel (concurrency=3), polls each to completion, and
prints a per-seat status line + final summary.

Unlike calibrate_seat_agent.py, this script does NOT delete existing predictions
— it overwrites in place via the seat_agent's `store` node.

Usage:
    python scripts/rescore_seats.py [--url http://localhost:8000] [--seat-type dun] [--concurrency 3] [--limit N]

Examples:
    python scripts/rescore_seats.py                          # all 56 DUN seats
    python scripts/rescore_seats.py --seat-type parlimen     # 26 Parlimen seats
    python scripts/rescore_seats.py --seat-type all          # both
    python scripts/rescore_seats.py --limit 5                # first 5 (smoke test)
"""

import argparse
import asyncio
import json
import sys
import time
from typing import Optional

import httpx

DEFAULT_URL = "http://localhost:8000"
POLL_INTERVAL = 3
POLL_ATTEMPTS = 100  # up to 5 min per seat


async def _load_seat_codes(client: httpx.AsyncClient, base_url: str, seat_type: str) -> list[str]:
    """Fetch constituency codes from historical_results (2022)."""
    types = ["dun", "parlimen"] if seat_type == "all" else [seat_type]
    codes: list[str] = []
    for t in types:
        resp = await client.get(f"{base_url}/historical?seat_type={t}&year=2022")
        if resp.status_code != 200:
            print(f"ERROR: could not load {t} historical: {resp.status_code}", file=sys.stderr)
            sys.exit(1)
        codes.extend(r["constituency_code"] for r in resp.json())
    return sorted(set(codes))


async def _rescore_one(
    client: httpx.AsyncClient,
    base_url: str,
    code: str,
    sem: asyncio.Semaphore,
    counter: dict,
    total: int,
) -> dict:
    """Dispatch + poll a single seat. Returns a status dict."""
    async with sem:
        result = {"code": code, "status": "unknown", "leading_party": None, "confidence": None, "elapsed_s": None}
        t0 = time.monotonic()
        try:
            resp = await client.post(
                f"{base_url}/agents/seat_agent/tasks",
                json={
                    "message": json.dumps({"constituency_code": code}),
                    "metadata": {"constituency_code": code},
                },
            )
            if resp.status_code not in (200, 202):
                result["status"] = f"dispatch_failed_{resp.status_code}"
                _log_progress(counter, total, code, result)
                return result

            task = resp.json()
            if task.get("deduplicated"):
                result["status"] = "deduplicated"
                _log_progress(counter, total, code, result)
                return result

            task_id = task["task_id"]
            final_state = None
            for _ in range(POLL_ATTEMPTS):
                await asyncio.sleep(POLL_INTERVAL)
                state_resp = await client.get(f"{base_url}/tasks/{task_id}")
                if state_resp.status_code == 200:
                    task_state = state_resp.json()
                    if task_state["state"] in ("completed", "failed"):
                        final_state = task_state["state"]
                        break

            if final_state != "completed":
                result["status"] = f"timeout_{final_state}"
                _log_progress(counter, total, code, result)
                return result

            pred_resp = await client.get(f"{base_url}/seat-predictions/{code}")
            if pred_resp.status_code == 200:
                pred = pred_resp.json()
                result["status"] = "ok"
                result["leading_party"] = pred.get("leading_party")
                result["confidence"] = pred.get("confidence")
            else:
                result["status"] = "no_prediction"

        except Exception as exc:
            result["status"] = f"error_{type(exc).__name__}"

        result["elapsed_s"] = round(time.monotonic() - t0, 1)
        _log_progress(counter, total, code, result)
        return result


def _log_progress(counter: dict, total: int, code: str, result: dict) -> None:
    counter["done"] += 1
    party = result.get("leading_party") or "—"
    conf = result.get("confidence")
    conf_str = f"{conf:>3}" if conf is not None else " — "
    elapsed = result.get("elapsed_s")
    elapsed_str = f"{elapsed:>5.1f}s" if elapsed is not None else "      "
    print(f"[{counter['done']:>3}/{total}] {code:<8} {result['status']:<20} {party:<5} {conf_str}  {elapsed_str}")


async def main(base_url: str, seat_type: str, concurrency: int, limit: Optional[int]) -> None:
    async with httpx.AsyncClient(timeout=60.0) as client:
        codes = await _load_seat_codes(client, base_url, seat_type)
        if limit:
            codes = codes[:limit]
        if not codes:
            print("ERROR: no seats found.", file=sys.stderr)
            sys.exit(1)

        print(f"Re-scoring {len(codes)} seat(s) with concurrency={concurrency}.")
        print(f"{'#':>5} {'code':<8} {'status':<20} {'pty':<5} {'conf':<4} {'time':>6}")
        print("-" * 60)

        sem = asyncio.Semaphore(concurrency)
        counter = {"done": 0}
        t0 = time.monotonic()

        results = await asyncio.gather(
            *(_rescore_one(client, base_url, code, sem, counter, len(codes)) for code in codes)
        )

        elapsed = time.monotonic() - t0
        ok = [r for r in results if r["status"] == "ok"]
        dedup = [r for r in results if r["status"] == "deduplicated"]
        failed = [r for r in results if r["status"] not in ("ok", "deduplicated")]

        print("-" * 60)
        print(f"Total: {len(results)} | ok: {len(ok)} | deduplicated: {len(dedup)} | failed: {len(failed)}")
        print(f"Wall time: {elapsed:.1f}s")
        if ok:
            confs = [r["confidence"] for r in ok if r["confidence"] is not None]
            if confs:
                print(f"Mean confidence (ok): {sum(confs) / len(confs):.1f}")
        if failed:
            print("\nFailed seats:")
            for r in failed:
                print(f"  {r['code']:<8} {r['status']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bulk re-score seats")
    parser.add_argument("--url", default=DEFAULT_URL, help="Control plane URL")
    parser.add_argument("--seat-type", choices=["dun", "parlimen", "all"], default="dun")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--limit", type=int, default=None, help="Score only the first N seats (for testing)")
    args = parser.parse_args()
    asyncio.run(main(args.url, args.seat_type, args.concurrency, args.limit))

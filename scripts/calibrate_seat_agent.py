"""Calibration script: backtest seat_agent predictions against 2022 results.

Usage:
    python scripts/calibrate_seat_agent.py [--url http://localhost:8000]

Requires:
    - PostgreSQL running with historical_results populated (Phase A)
    - Control plane + seat_agent running (docker-compose up)
"""

import argparse
import asyncio
import json
import sys

import httpx

DEFAULT_URL = "http://localhost:8000"
POLL_INTERVAL = 2
POLL_ATTEMPTS = 30


async def main(control_plane_url: str) -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Load 2022 actual results
        resp = await client.get(f"{control_plane_url}/historical?seat_type=dun&year=2022")
        if resp.status_code != 200:
            print(f"ERROR: Could not load historical results: {resp.status_code} {resp.text}", file=sys.stderr)
            sys.exit(1)

        actual_results = {r["constituency_code"]: r for r in resp.json()}
        if not actual_results:
            print("ERROR: No 2022 DUN results found. Run Phase A data ingestion first.", file=sys.stderr)
            sys.exit(1)

        print(f"Loaded {len(actual_results)} constituencies. Starting calibration...\n")

        correct = 0
        total = 0
        results = []

        for code, actual in actual_results.items():
            # Dispatch seat_agent task
            resp = await client.post(
                f"{control_plane_url}/agents/seat_agent/tasks",
                json={
                    "message": json.dumps({"constituency_code": code}),
                    "metadata": {"constituency_code": code},
                },
            )
            if resp.status_code not in (200, 202):
                print(f"SKIP {code}: dispatch failed ({resp.status_code})")
                continue

            task = resp.json()
            task_id = task["task_id"]

            # Poll for completion
            final_state = None
            for _ in range(POLL_ATTEMPTS):
                await asyncio.sleep(POLL_INTERVAL)
                state_resp = await client.get(f"{control_plane_url}/tasks/{task_id}")
                if state_resp.status_code == 200:
                    task_state = state_resp.json()
                    if task_state["state"] in ("completed", "failed"):
                        final_state = task_state["state"]
                        break

            if final_state != "completed":
                print(f"SKIP {code}: task did not complete (state={final_state})")
                continue

            # Fetch prediction
            pred_resp = await client.get(f"{control_plane_url}/seat-predictions/{code}")
            if pred_resp.status_code != 200:
                print(f"SKIP {code}: no prediction found")
                continue

            prediction = pred_resp.json()
            predicted_party = prediction.get("leading_party")
            actual_party = actual.get("winner_coalition")
            match = predicted_party == actual_party

            if match:
                correct += 1
            total += 1

            confidence = prediction.get("confidence", 0)
            results.append({
                "code": code,
                "seat_name": actual.get("seat_name", code),
                "predicted": predicted_party,
                "actual": actual_party,
                "confidence": confidence,
                "correct": match,
            })
            print(f"{'OK  ' if match else 'MISS'} {code:<12} predicted={predicted_party:<4} actual={actual_party:<4} confidence={confidence}")

        print(f"\n{'='*50}")
        print(f"CALIBRATION RESULTS")
        print(f"{'='*50}")
        if total > 0:
            print(f"Accuracy:        {correct}/{total} ({100*correct/total:.1f}%)")
            confidences = [r["confidence"] for r in results if r["confidence"]]
            if confidences:
                print(f"Mean confidence: {sum(confidences)/len(confidences):.1f}")
            correct_conf = [r["confidence"] for r in results if r["correct"] and r["confidence"]]
            wrong_conf = [r["confidence"] for r in results if not r["correct"] and r["confidence"]]
            if correct_conf:
                print(f"Avg confidence (correct): {sum(correct_conf)/len(correct_conf):.1f}")
            if wrong_conf:
                print(f"Avg confidence (wrong):   {sum(wrong_conf)/len(wrong_conf):.1f}")
        else:
            print("No results collected.")

        # Save results
        output_path = "data/calibration_results.json"
        try:
            with open(output_path, "w") as f:
                json.dump({"summary": {"correct": correct, "total": total}, "results": results}, f, indent=2)
            print(f"\nResults saved to {output_path}")
        except Exception as exc:
            print(f"WARNING: Could not save results: {exc}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest seat_agent against 2022 results")
    parser.add_argument("--url", default=DEFAULT_URL, help="Control plane URL")
    args = parser.parse_args()
    asyncio.run(main(args.url))

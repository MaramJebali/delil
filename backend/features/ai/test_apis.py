"""
List + test all LLM models on Groq and Mistral.
Run: python -m features.ai.test_apis
"""

import os
import time
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

PROMPT = "Reply in 3 words or less: 'API works'"

# Models to skip (not useful for chat or unsupported)
SKIP_KEYWORDS = ["whisper", "tts", "guard", "embed", "moderation", "vision-only"]


def list_models(client, provider: str) -> list[str]:
    """Fetch available model IDs from a provider."""
    print(f"\n{'='*70}")
    print(f"  📋 {provider.upper()} — available models")
    print(f"{'='*70}")

    try:
        models = client.models.list()
        ids = sorted([m.id for m in models.data])
        print(f"  Found {len(ids)} models:\n")
        for mid in ids:
            print(f"    • {mid}")
        return ids
    except Exception as e:
        print(f"  ❌ Failed to list: {e}")
        return []


def test_model(client, provider: str, model_id: str) -> dict:
    """Test a single model with a chat completion."""
    start = time.time()
    try:
        r = client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": PROMPT}],
            max_tokens=30,
            temperature=0,
        )
        latency = int((time.time() - start) * 1000)
        reply = (r.choices[0].message.content or "").strip() or "(empty)"
        return {"provider": provider, "model": model_id, "ok": True,
                "reply": reply, "latency_ms": latency}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return {"provider": provider, "model": model_id, "ok": False,
                "error": str(e)[:150], "latency_ms": latency}


def should_test(model_id: str) -> bool:
    """Filter out models that aren't chat-capable."""
    low = model_id.lower()
    return not any(k in low for k in SKIP_KEYWORDS)


def process_provider(name: str, base_url: str, api_key: str):
    print(f"\n\n{'#'*70}")
    print(f"#  {name.upper()}")
    print(f"{'#'*70}")

    if not api_key or api_key.startswith(("paste", "REPLACE", "your_")):
        print(f"  ⚠️  No API key set for {name} — skipping")
        return []

    client = OpenAI(base_url=base_url, api_key=api_key)

    # 1. List
    models = list_models(client, name)
    if not models:
        return []

    # 2. Filter + test
    to_test = [m for m in models if should_test(m)]
    print(f"\n{'='*70}")
    print(f"  🧪 {name.upper()} — testing {len(to_test)} chat models")
    print(f"{'='*70}")

    results = []
    for m in to_test:
        print(f"\n  → {m}")
        r = test_model(client, name, m)
        results.append(r)
        if r["ok"]:
            print(f"     ✅ {r['latency_ms']}ms — {r['reply'][:60]}")
        else:
            print(f"     ❌ {r['latency_ms']}ms — {r['error'][:100]}")

    return results


def main():
    groq_key = os.getenv("GROQ_API_KEY", "")
    mistral_key = os.getenv("MISTRAL_API_KEY", "")

    print(f"\n🔑 GROQ_API_KEY:    {'✅ set' if groq_key else '❌ missing'}")
    print(f"🔑 MISTRAL_API_KEY: {'✅ set' if mistral_key else '❌ missing'}")

    all_results = []
    all_results += process_provider(
        "groq", "https://api.groq.com/openai/v1", groq_key
    )
    all_results += process_provider(
        "mistral", "https://api.mistral.ai/v1", mistral_key
    )

    # ---- Final Summary ----
    print(f"\n\n{'='*70}")
    print("  ✅ FINAL SUMMARY")
    print(f"{'='*70}")

    ok = [r for r in all_results if r["ok"]]
    fail = [r for r in all_results if not r["ok"]]

    print(f"\n  Working: {len(ok)} / {len(all_results)}\n")
    print(f"  {'STATUS':<8} {'PROVIDER':<10} {'MODEL':<45} {'LATENCY':<10}")
    print(f"  {'-'*75}")
    for r in all_results:
        status = "✅ OK" if r["ok"] else "❌ FAIL"
        print(f"  {status:<8} {r['provider']:<10} {r['model']:<45} {r['latency_ms']}ms")

    print(f"\n  🎯 Recommended primary:   {ok[0]['provider']}/{ok[0]['model']}" if ok else "")
    if len(ok) > 1:
        print(f"  🎯 Recommended fast:      {ok[-1]['provider']}/{ok[-1]['model']}")

    # Save results
    import json
    with open("llm_test_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n  📄 Results saved to: llm_test_results.json")


if __name__ == "__main__":
    main()
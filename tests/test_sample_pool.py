"""The sample-question pool stays inside the curated set, and the shuffle
draws stratified samples from it only. Read-only over the frozen gold set."""
import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
GOLD = {g["id"]: g for g in json.loads((ROOT / "evaluation/gold_set/aeroops_goldset_v1_frozen.json").read_text(encoding="utf-8"))}
JURY = {x["id"]: x for x in json.loads((ROOT / "evaluation/jury_scoring/aggregated_jury_scores.json").read_text(encoding="utf-8"))["per_item"]}

JURY_WRONG = {"AF05", "CD04", "CD08", "DA04", "DA06", "MH08"}
ACCEPTED_MISSES = {"FH03", "MH01", "CD03", "AF01", "AF04"}
EXCLUDED = JURY_WRONG | ACCEPTED_MISSES  # 11 items


def _pool():
    text = (ROOT / "static/sample_pool.js").read_text(encoding="utf-8")
    return json.loads(text[text.index("["): text.rindex("]") + 1])


def test_jury_wrong_list_is_current():
    assert {i for i, x in JURY.items() if not x["graphrag"]["correct"]} == JURY_WRONG


def test_pool_size_and_no_excluded_item():
    pool = _pool()
    ids = [q["id"] for q in pool]
    assert len(ids) == len(set(ids)) == 30
    assert not (set(ids) & EXCLUDED)


def test_pool_questions_are_verbatim_gold_and_jury_correct():
    for q in _pool():
        assert q["question"] == GOLD[q["id"]]["question"]
        assert q["category"] == GOLD[q["id"]]["category"]
        assert JURY[q["id"]]["graphrag"]["correct"]


def test_every_category_present():
    assert {q["category"] for q in _pool()} == {g["category"] for g in GOLD.values()}


def test_generated_file_is_current():
    import build_sample_pool
    assert [q["id"] for q in build_sample_pool.build()[1]] == [q["id"] for q in _pool()]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_shuffle_is_stratified_and_stays_in_pool():
    script = """
    global.window = {}; require('./static/sample_pool.js'); const pool = window.AEROOPS_SAMPLE_POOL;
    const { drawSamples } = require('./static/sample_shuffle.js');
    let s = 12345; const rng = () => (s = (s * 1664525 + 1013904223) % 4294967296) / 4294967296;
    const ids = new Set(pool.map(q => q.id)); const seen = new Set(); let prev = [], out = {draws: 0, bad: []};
    for (let n = 0; n < 5000; n++) {
      const d = drawSamples(pool, prev, rng); out.draws++;
      if (d.length !== 4) out.bad.push('size');
      if (new Set(d.map(q => q.category)).size !== 4) out.bad.push('categories');
      if (d.some(q => !ids.has(q.id))) out.bad.push('outside pool');
      if (d.some(q => prev.includes(q.id))) out.bad.push('repeat of previous draw');
      d.forEach(q => seen.add(q.id)); prev = d.map(q => q.id);
    }
    out.coverage = seen.size; console.log(JSON.stringify(out));
    """
    # window is not defined under node: sample_pool.js assigns to it, shuffle attaches to globalThis
    r = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout.strip().splitlines()[-1])
    assert out["draws"] == 5000 and out["bad"] == []
    assert out["coverage"] == 30  # every pooled question is reachable

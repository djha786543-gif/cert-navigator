"""
Phase 6 – End-to-End Test Pipeline

Runs the full Career Portal flow without a live server:
  1. Parse the sample resume (JSON)
  2. Verify normalised profile schema
  3. Get job recommendations (mock data)
  4. Verify job ranking and match scoring
  5. Get tiered certification recommendations
  6. Verify Gold Standard cert catalog depth (domains, labs, questions)
  7. Generate 5-year career plan
  8. Verify all plan fields and role progression

Run with:
    python -m pytest src/test_scripts/test_pipeline.py -v
or directly:
    python src/test_scripts/test_pipeline.py
"""
import json
import sys
from pathlib import Path

# ── Ensure project root is on path ────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.engine.resume_parser       import parse_resume_file
from src.backend.engine.job_recommendation  import recommend_jobs, get_trending_roles
from src.backend.engine.certification_engine import (
    get_recommendations, get_cert_detail, get_study_pack, get_progress,
)
from src.backend.engine.career_plan         import generate_career_plan

# ── Test helpers ───────────────────────────────────────────────────────────────
_PASSED = []
_FAILED = []

def check(name: str, condition: bool, detail: str = ""):
    if condition:
        _PASSED.append(name)
        print(f"  ✅  {name}")
    else:
        _FAILED.append(name)
        print(f"  ❌  {name}" + (f" — {detail}" if detail else ""))


# ════════════════════════════════════════════════════════════════════════════
# PHASE 1 – Resume Parser
# ════════════════════════════════════════════════════════════════════════════

def test_resume_parser():
    print("\n── Phase 1: Resume Parser ──────────────────────────────────────────")
    resume_path = PROJECT_ROOT / "data" / "sample_resume.json"
    profile = parse_resume_file(str(resume_path))

    check("Profile is a dict",            isinstance(profile, dict))
    check("name is present",              bool(profile.get("name")))
    check("current_role is present",      bool(profile.get("current_role")))
    check("target_role is present",       bool(profile.get("target_role")))
    check("skills list is non-empty",     len(profile.get("skills", [])) > 0)
    check("certifications list present",  isinstance(profile.get("certifications"), list))
    check("experience_years is numeric",  isinstance(profile.get("experience_years"), (int, float, type(None))))

    # Verify specific content from DJ's profile
    check("DJ's name detected",           "Deobrat" in (profile.get("name") or ""),
          f"got '{profile.get('name')}'")
    check("CISA certification present",   any(
        "CISA" in (c.get("name","") if isinstance(c,dict) else str(c))
        for c in profile.get("certifications", [])
    ))
    check("SOX skill detected",           any("SOX" in s for s in profile.get("skills", [])))
    return profile


# ════════════════════════════════════════════════════════════════════════════
# PHASE 2 – Job Recommendation Engine
# ════════════════════════════════════════════════════════════════════════════

def test_job_engine(profile):
    print("\n── Phase 2: Job Recommendation Engine ─────────────────────────────")
    jobs = recommend_jobs(profile, max_results=10)

    check("Returns a list",           isinstance(jobs, list))
    check("Returns at least 3 jobs",  len(jobs) >= 3,            f"got {len(jobs)}")
    check("First job has match_score", "match_score" in jobs[0])
    check("Jobs sorted by score",     all(
        jobs[i]["match_score"] >= jobs[i+1]["match_score"]
        for i in range(len(jobs)-1)
    ))
    check("First job score > 0",      jobs[0]["match_score"] > 0, f"score={jobs[0]['match_score']}")
    check("Jobs have required fields", all(
        all(f in j for f in ["id","title","company","location","description"])
        for j in jobs
    ))
    check("skills_matched is populated", any(len(j.get("skills_matched",[])) > 0 for j in jobs))

    trending = get_trending_roles()
    check("Trending roles returned",   len(trending) >= 5)
    check("Trending has growth field", all("growth" in r for r in trending))

    print(f"     Top match: '{jobs[0]['title']}' at {jobs[0]['company']} — {jobs[0]['match_score']}% match")
    return jobs


# ════════════════════════════════════════════════════════════════════════════
# PHASE 3 – Certification Engine (Gold Standard)
# ════════════════════════════════════════════════════════════════════════════

def test_certification_engine(profile):
    print("\n── Phase 3: Certification Engine (Gold Standard) ───────────────────")

    recs = get_recommendations(profile)
    check("Recommendations has all tiers",  all(k in recs for k in ["immediate","midterm","longterm"]))
    check("Immediate certs present",        len(recs.get("immediate", [])) > 0)
    check("CISA in already_held",           "cisa" in recs.get("already_held", []),
          f"held={recs.get('already_held')}")

    # Test individual cert detail — AIGP
    aigp = get_cert_detail("aigp")
    check("AIGP: name present",             bool(aigp.get("name")))
    check("AIGP: 5 domains",               len(aigp.get("domains", [])) == 5,
          f"got {len(aigp.get('domains',[]))}")
    check("AIGP: domain weights sum to 100", sum(d["weight_pct"] for d in aigp["domains"]) == 100)
    check("AIGP: each domain has topics",   all(len(d.get("topics",[])) >= 4 for d in aigp["domains"]))
    check("AIGP: each domain has tools",    all(len(d.get("tools",[])) >= 2 for d in aigp["domains"]))
    check("AIGP: exam info complete",       all(k in aigp.get("exam",{}) for k in ["questions","cost_usd_member","passing_score","duration_minutes"]))
    check("AIGP: has official resources",   len(aigp.get("study_resources",{}).get("official",[])) >= 2)
    check("AIGP: has free resources",       len(aigp.get("study_resources",{}).get("free",[])) >= 3)
    check("AIGP: has practice questions",   len(aigp.get("practice_questions",[])) >= 3)
    check("AIGP: questions have explanations", all(
        bool(q.get("explanation"))
        for q in aigp.get("practice_questions", [])
    ))
    check("AIGP: has labs",                 len(aigp.get("labs",[])) >= 1)
    check("AIGP: labs have steps",          all(
        len(lab.get("steps",[])) >= 5
        for lab in aigp.get("labs", [])
    ))

    # Test study pack
    pack = get_study_pack("ccsp")
    check("CCSP study pack complete",       all(k in pack for k in ["domains","labs","questions","resources","exam_info"]))
    check("CCSP: 6 domains",               len(pack["domains"]) == 6, f"got {len(pack['domains'])}")
    check("CCSP: all domains have weight",  all("weight_pct" in d for d in pack["domains"]))
    check("CCSP domain weights sum to 100", sum(d["weight_pct"] for d in pack["domains"]) == 100)

    # Progress tracking
    mock_progress = {
        "aigp": {"aigp-d1": 90, "aigp-d2": 60, "aigp-d3": 40, "aigp-d4": 75, "aigp-d5": 50}
    }
    progress = get_progress(profile, mock_progress)
    check("Progress tracker returns aigp",  "aigp" in progress)
    check("Progress has overall_pct",       "overall_pct" in progress.get("aigp", {}))
    check("Progress has domain breakdown",  len(progress["aigp"].get("domains",[])) > 0)
    check("Progress has study_focus",       bool(progress["aigp"].get("study_focus")))

    print(f"     AIGP overall progress: {progress['aigp']['overall_pct']}%")
    print(f"     Recommended focus: {progress['aigp']['study_focus']}")
    return recs


# ════════════════════════════════════════════════════════════════════════════
# PHASE 4 – Career Plan
# ════════════════════════════════════════════════════════════════════════════

def test_career_plan(profile):
    print("\n── Phase 4: Career Plan Engine ─────────────────────────────────────")
    plan = generate_career_plan(profile)

    check("Plan has 5 years",                len(plan.get("years",[])) == 5)
    check("Plan has user_name",              bool(plan.get("user_name")))
    check("Plan has current_role",           bool(plan.get("current_role")))
    check("Plan has target_role",            bool(plan.get("target_role")))
    check("Plan has five_year_summary",      bool(plan.get("five_year_summary")))
    check("Summary has salary_uplift",       bool(plan["five_year_summary"].get("salary_uplift_estimate")))
    check("Year 1 phase is 'Establish'",     plan["years"][0]["phase"] == "Establish")
    check("Year 5 phase is 'Transform'",     plan["years"][4]["phase"] == "Transform")
    check("All years have milestones",       all(len(y.get("key_milestones",[])) > 0 for y in plan["years"]))
    check("All years have action items",     all(len(y.get("action_items",[])) > 0 for y in plan["years"]))
    check("All years have salary range",     all("salary_range" in y for y in plan["years"]))
    check("Salary range min < max",          all(
        y["salary_range"]["min"] < y["salary_range"]["max"]
        for y in plan["years"]
    ))
    check("Year 1 includes AIGP cert",       "AIGP" in (plan["years"][0].get("certifications_to_earn") or []))

    summary = plan["five_year_summary"]
    uplift  = summary["salary_uplift_estimate"]
    print(f"     Current: ${uplift['start_min']:,}–${uplift['start_max']:,}")
    print(f"     Year 5:  ${uplift['end_min']:,}–${uplift['end_max']:,}  (+{uplift['pct_increase']}%)")
    print(f"     Path:    {plan['current_role']} → {summary['end_role']}")
    return plan


# ════════════════════════════════════════════════════════════════════════════
# Runner
# ════════════════════════════════════════════════════════════════════════════

def run_all():
    print("\n" + "=" * 65)
    print("  Career Navigator - Full E2E Test Pipeline")
    print("=" * 65)

    try:
        profile = test_resume_parser()
        test_job_engine(profile)
        test_certification_engine(profile)
        test_career_plan(profile)
    except Exception as exc:
        print(f"\n💥 Test run aborted with exception: {exc}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    # ── Summary ──
    total  = len(_PASSED) + len(_FAILED)
    print("\n" + "=" * 65)
    print(f"  Results: {len(_PASSED)}/{total} passed  |  {len(_FAILED)} failed")
    print("=" * 65)

    if _FAILED:
        print("\nFailed checks:")
        for f in _FAILED:
            print(f"  ✗ {f}")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed — Career Portal pipeline is fully operational!")


if __name__ == "__main__":
    run_all()


# ── pytest compatibility ───────────────────────────────────────────────────────
def test_phase1_resume_parser():
    profile = test_resume_parser()
    assert profile and profile.get("name")

def test_phase2_job_engine():
    profile = test_resume_parser()
    jobs    = test_job_engine(profile)
    assert jobs and jobs[0]["match_score"] > 0

def test_phase3_cert_engine():
    profile = test_resume_parser()
    recs    = test_certification_engine(profile)
    assert recs.get("immediate")

def test_phase4_career_plan():
    profile = test_resume_parser()
    plan    = test_career_plan(profile)
    assert len(plan["years"]) == 5

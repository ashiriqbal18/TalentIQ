# TalentIQ — Integrated CT-351 Expert System

The existing Flask/SQLite TalentIQ website and dynamic Job Requirements Builder are
integrated with the finite Horn-rule forward/backward proof mechanics from
`KRR_Group9_CCP/job_skill_engine.py` (retained as
`reasoning/original_job_skill_engine.py`).

## Windows installation (PowerShell)

Use Python **3.11+**. In this folder:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000 and sign up (first run), or sign in with your
original data if you preserved `instance/talentiq.db`.

**Do not run `db.drop_all()` or delete your current database.** When replacing
an existing local project, **backup `instance/talentiq.db` first**, copy the
new source/template/static files into the old project, and keep your existing
`instance/talentiq.db`. The ZIP excludes users' private SQLite contents and
backups by design. `db.create_all()` creates new missing tables; it does not
upgrade incompatible existing columns (a migration would be needed in that case).

## Website workflow

1. Log in and open **My Profile**. Enter real or synthetic classroom data:
   skills + proficiency, education, active certifications, dated work history.
2. Use **Post a Job**, then **My Job Posts → Manage Requirements**.
   Add mandatory/preferred skills, exact qualification names, and certificates.
3. Open **Job Details → Check My Eligibility**.
4. Read status, requirement coverage, forward chaining derivation rounds, and
   goal-driven backward proof trace.
5. Open **Knowledge Explorer** for frame/semantic/logic overview.

## Logical interpretation

- Original engine is preserved as a standalone reference, not wired directly
  to the user interface because it assumes one degree, integer years, and
  pre-defined mock candidates/roles.
- The dynamic adapter translates current SQLite models into grounded facts.
  Horn clauses derive `requirement_met` and `experience_met`, then `eligible`.
- Positive evidence is self-declared; it is **not independent credential verification**.
- Required proficiency levels are ordered Beginner < Intermediate < Advanced.
  A level not provided is unknown, not an asserted positive match.
- Qualification/certificate matching is exact after whitespace/case normalization;
  no guessed equivalence, e.g. `BS CS` and `BS Computer Science` are different.
- Expired candidate certificates are ignored. Overlapping dated employment
  intervals are merged before experience-year comparison.
- Mandatory conditions block proof. Preferred ones affect the information
  summary only, not the final eligibility rule.
- `Eligible`: all mandatory requirements + minimum years proven, with at least
  one configured structured requirement.
- `Not Eligible`: an explicitly reported proficiency or experience value is
  below a mandatory threshold (other missing requirements may remain unknown).
- `Insufficient Information`: eligibility not proved but no explicit
  below-threshold condition, or the job has no configured requirements.
- These are **demonstration knowledge-base assessments, not hiring decisions**.

## Test

```powershell
python -m pytest -q tests/test_dynamic_reasoning.py
```

The original standalone engine's own unit tests passed in the source review
(26 tests); its implementation is preserved under `reasoning/`.

## Modules

- `app.py`, `models.py`: existing Flask authentication / profile / jobs
- `requirements_models.py`, `requirements_routes.py`: dynamic job requirements
- `reasoning/original_job_skill_engine.py`: audited original CT-351 implementation
- `reasoning/engine.py`: finite forward fixed-point + grounded backward proof
- `reasoning/adapter.py`: live candidate/job fact extraction and decision logic
- `reasoning/routes.py`: protected Flask endpoints / report pages
- `templates/eligibility_result.html`: professional proof UI
- `templates/knowledge_explorer.html`: KR concepts, logic specification
- `docs/`: original semantic and frame DOT diagrams

## What is still intentionally not claimed

The formal FOL and Description Logic axioms are **documented representations**,
not a complete general-purpose theorem prover or OWL reasoner. A production
system would also require admin-verified credentials, richer qualification
ontology, profile-data editing, and deeper privacy/access controls.

The project was syntax-checked and pure reasoning tests were run in the
packaging environment. Complete Flask HTTP integration testing must be run
on your local Windows installation where Flask dependencies are installed.

## Edit existing jobs and candidate profile records

This version adds `editing_routes.py` and `templates/edit_profile_record.html`.

- **My Job Posts → Edit Job** edits the existing job in place, preserving its ID, posted requirements, active/inactive status and owner.
- **My Profile → Edit** next to any Skill, Education, Work Experience, or Certification record updates that record in place.
- **Personal Information** has its existing Save Changes form; **Job Preferences** has its existing Save Preferences form.
- All edit endpoints require login and check the logged-in user's ownership. Forms include CSRF tokens.
- Shared skill/degree/certification catalog entries are *not* modified globally when a user edits their personal record.
- No database schema migrations are required. Keep a backup of your `instance` SQLite DB before replacing source files.

After extracting, install dependencies from requirements.txt and run `python app.py`.
Test using a posted job and at least one saved candidate skill. The edit screens require the original project's installed Flask dependencies; source syntax and template compilation were checked in the integration environment, not a full browser/database runtime test.


## Live-data release

- **Knowledge Explorer** now fetches current signed-in candidate profile and a selected accessible job, renders database-backed frame values, factual graph nodes/edges and grounded assertions. The job selector is derived from actual jobs. An absent credential creates no possession edge.
- Export the actual diagram using `Knowledge Explorer → Export live DOT` or `/knowledge-explorer/graph.dot?job_id=<id>`.
- Homepage fake eligibility/sample candidate illustration was removed. No demonstration candidate records are shipped.
- Domain vocabulary and validation constants have been centralized in `domain_config.py` and exposed to templates. Fixed ontology axioms and explanatory labels are specifications, not database instance data.
- No private user database, passwords, backup DB, or local virtual environment is bundled. **Keep your own `instance/talentiq.db` unchanged** when upgrading; back it up first.
- The historical `.dot` diagrams in `docs/` remain *conceptual*, not database-derived. Current FOL/DL blocks explain the ontology; they do not claim to execute a general theorem prover.
- Remaining language strings, styling, page structure, and legitimate inference definitions are intentionally static. Dynamic means domain records and conclusions come from real saved data, not that every UI word is stored in SQLite.

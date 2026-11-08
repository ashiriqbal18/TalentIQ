# TalentIQ live-data release — November 2026

## What's data-driven now

- Knowledge Explorer requires a signed-in user and loads their linked Candidate profile.
- Its selected job menu is populated from active or user-owned jobs, and requirements are queried by that job ID.
- Candidate/Job Frames show saved skills, proficiencies, qualifications, certifications, dated employment and job requirements.
- Semantic Network nodes/relations are created from those actual records only. Missing profile evidence never creates a `has-*` relationship. The conceptual ontology can be viewed separately in the fixed FOL/DL definitions.
- Live grounded assertions and the actual eligibility decision are shown for the same selected job.
- `/knowledge-explorer/graph.dot?job_id=<job-id>` exports a Graphviz DOT graph built from live facts, not a static demo file.
- Homepage no longer shows an imaginary successful eligibility result.
- Work types, proficiency levels, education levels, job requirement types and maximum requirement count have been centralized in `domain_config.py`. These are domain rules, not sample records.
- Retained automated reasoning tests plus new live-graph tests: `pytest -q tests`.

## Keep your existing data safe

This archive excludes the `instance/` database files, backups, Windows virtual environment and compiled bytecode. **Back up your original project and preserve `instance/talentiq.db`**. Merge the new source/template/static files into the old project. Do not replace, reset or delete your database. No migration is required for these changes.

## Boundaries and testing

- Fixed UI labels, default empty-state messages, ontology definitions and validation choices are intentionally static; personal/job instance values are not fabricated.
- The FOL/DL section is an explanatory formal model, not a full FOL or Description Logic theorem prover.
- Dynamic knowledge graph is built with SVG and deterministic layout; it does not need JavaScript or outside graph APIs. For many requirements, the chart grows vertically.
- 17 unit tests passed and Jinja templates parsed. Full Flask browser integration was **not executed** here because Flask/Flask-SQLAlchemy are unavailable in the execution environment. Run `pip install -r requirements.txt` and `python app.py` locally to verify.
- To enable the local debugger intentionally, set `FLASK_DEBUG=1`. Default runner disables debug.

## Recommended local acceptance test

1. Keep your existing DB and log in.
2. Update your profile with a skill at Beginner level; create/select a job requiring Advanced and a degree not listed in your profile.
3. Visit `/knowledge-explorer?job_id=<actual id>` and confirm the real skill displays, the degree exists only as a `requires-education` edge, and no fake `has-education` edge appears.
4. Compare `/jobs/<id>/eligibility`; forward/backward traces and result should correspond to the selected job.
5. Edit skills/requirements and reload the explorer. Graph should change without modifying any HTML.

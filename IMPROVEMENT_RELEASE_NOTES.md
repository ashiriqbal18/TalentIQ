# TalentIQ: Knowledge Representation and Proof Presentation Upgrade

Built on the previously delivered TalentIQ_CT351_Dynamic_Project source.

## Updated

1. Live Semantic Network now displays saved candidate name / selected job title, alongside the record-derived entity nodes and relationships.
2. Node count includes the candidate and job endpoints. Relationship count is calculated from actual evidence and requirement edges, not a fixed value.
3. Graph nodes show live profile facets and required level/importance. The details remain in SVG hover titles as well.
4. Grounded assertions include HasSkillLevel, RequiresSkillLevel, RequirementImportance, and RecordedExperienceYears (only if employment intervals are recorded).
5. Duplicate requirement name removed from the unmet mandatory summary.
6. Backward Chaining display now includes a full mandatory-condition *evidence audit*, separate from the original short-circuit proof trace. This does not falsely claim the inference engine explored all proof branches.
7. Unit tests extended for dynamic relation counts, proficiency facts and missing qualification behavior.

## Safety and compatibility

- No SQLite DB bundled; preserve your own instance/talentiq.db.
- No changes to the Horn-rule conclusions, decision policy, model schema or login.
- Conceptual FOL/DL definitions remain fixed as formal vocabulary, not fake live user data.
- Run `pip install -r requirements.txt` then `python app.py` in your existing virtual environment.
- Check `/knowledge-explorer?job_id=1` (or another accessible ID) and `/jobs/1/eligibility`.
- Use Ctrl+Shift+R to reload CSS.

"""Build knowledge representations exclusively from authorized SQLite records.
No example candidate, job, qualification, or inference is inserted.
"""
from datetime import date
from .adapter import assess, experience_years, normalize


def build_live_knowledge(candidate, job, requirements):
    skills = list(candidate.skills) if candidate else []
    degrees = list(candidate.qualifications) if candidate else []
    certs = list(candidate.certifications) if candidate else []
    experiences = list(candidate.experiences) if candidate else []
    profile = {
        "skills": [(x.skill.name, x.proficiency_level) for x in skills if x.skill],
        "education": [(x.qualification.name, x.institution) for x in degrees if x.qualification],
        "certifications": [(x.certification.name,
                            "Expired" if x.expiry_date and x.expiry_date < date.today() else "Current/expiry not recorded")
                           for x in certs if x.certification],
        "experiences": [(x.job_title, x.company) for x in experiences],
        "experience_years": experience_years(experiences),
    }
    # Each (category, name) is a distinct domain individual; consolidate shared facts.
    evidence = {}
    for name, level in profile['skills']:
        evidence[('skill', normalize(name))] = (name, 'Skill', level)
    for name, institution in profile['education']:
        evidence[('education', normalize(name))] = (name, 'Education', institution or 'Institution not specified')
    for name, expiry in profile['certifications']:
        evidence[('certification', normalize(name))] = (name, 'Certification', expiry)
    needs = {}
    for req in requirements:
        needs[(req.category, normalize(req.name))] = req
    keys = sorted(set(evidence) | set(needs), key=lambda k: (k[0], k[1]))
    # Geometry is presentation configuration only. Every graph individual and
    # relationship below must originate from a profile or requirement row.
    graph = []
    for index, key in enumerate(keys):
        item = evidence.get(key)
        need = needs.get(key)
        name = (need.name if need else item[0])
        graph.append({
            'id': index + 1, 'x': 530, 'y': 178 + index * 87,
            'name': name, 'category': key[0].title(),
            'has': bool(item), 'required': bool(need),
            'evidence_detail': item[2] if item else None,
            'candidate_level': item[2] if item and key[0] == 'skill' else None,
            'required_level': need.level if need and key[0] == 'skill' else None,
            'importance': need.importance if need else None,
            'requirement_detail': (
                (need.level or 'Any recorded level') + ' · ' + need.importance.title()
                if need and need.category == 'skill' else
                need.importance.title() if need else None
            ),
        })
    analysis = assess(candidate, job, requirements) if candidate and job else None
    statements = []
    if candidate:
        statements.append(('Candidate', str(candidate.id)))
        for x in graph:
            if x['has']:
                statements.append(('Has' + x['category'], str(candidate.id), x['name']))
                if x['candidate_level']:
                    statements.append(('HasSkillLevel', str(candidate.id), x['name'], x['candidate_level']))
        if profile['experience_years'] is not None:
            statements.append(('RecordedExperienceYears', str(candidate.id), f"{profile['experience_years']:.2f}"))
    if job:
        statements.append(('Job', str(job.id)))
        statements.append(('MinimumExperience', str(job.id), str(job.min_experience)))
        for x in graph:
            if x['required']:
                statements.append(('Requires' + x['category'], str(job.id), x['name']))
                if x['required_level']:
                    statements.append(('RequiresSkillLevel', str(job.id), x['name'], x['required_level']))
                if x['importance']:
                    statements.append(('RequirementImportance', str(job.id), x['category'], x['name'], x['importance']))
    entity_count = len(graph) + int(bool(candidate)) + int(bool(job))
    relationship_count = sum(int(n['has']) + int(n['required']) for n in graph)
    return dict(profile=profile, graph=graph, entity_count=entity_count, relationship_count=relationship_count, graph_height=max(300, 235 + 87*len(graph)),
                analysis=analysis, statements=statements, requirements=requirements)

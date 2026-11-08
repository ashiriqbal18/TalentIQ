from domain_config import PROFICIENCY_LEVELS
"""Convert live TalentIQ SQLAlchemy records to Horn facts.

Important semantics: an absent profile value is UNKNOWN, not proven false.
Only exact, normalized named credentials match (no guessed equivalences).
"""
from datetime import date
from .original_job_skill_engine import Rule
from .engine import infer

LEVELS = {level.casefold(): index for index, level in enumerate(PROFICIENCY_LEVELS, 1)}


def normalize(value):
    return ' '.join((value or '').casefold().split())


def experience_years(records, today=None):
    """Union recorded employment intervals to avoid double counting overlaps."""
    today = today or date.today()
    periods = []
    for rec in records:
        start = rec.start_date
        end = today if rec.is_current else rec.end_date
        if start is None or end is None or end < start:
            continue
        periods.append((start.toordinal(), min(end, today).toordinal()))
    if not periods:
        return None
    periods.sort()
    merged = []
    for start, end in periods:
        if merged and start <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return sum(b - a + 1 for a, b in merged) / 365.2425


def assess(candidate, job, requirements, today=None):
    today = today or date.today()
    identifier = str(job.id)
    person = str(candidate.id)
    facts = {('candidate', person), ('job', identifier)}
    rules = []
    checks = []
    mandatory_atoms = []
    preferences = []
    evidence_explanations = {}

    # User-entered skills are declared evidence, not independently verified.
    owned_skills = {}
    for entry in candidate.skills:
        if entry.skill:
            owned_skills[normalize(entry.skill.name)] = LEVELS.get(
                normalize(entry.proficiency_level), 0)

    owned_degrees = {normalize(item.qualification.name) for item in candidate.qualifications
                     if item.qualification}
    owned_certs = {normalize(item.certification.name) for item in candidate.certifications
                   if item.certification and (
                       item.expiry_date is None or item.expiry_date >= today)}

    for requirement in requirements:
        category = requirement.category
        name = requirement.name
        key = normalize(name)
        priority = requirement.importance == 'mandatory'
        label = {'skill': 'Skill', 'education': 'Education',
                 'certification': 'Certification'}.get(category, category)
        idx = str(requirement.id)
        evidence_atom = ('evidence', person, identifier, idx)
        passed_atom = ('requirement_met', person, identifier, idx)
        met = False
        explicitly_below = False
        detail = ''
        failure_reason = ''
        if category == 'skill':
            minimum = LEVELS.get(normalize(requirement.level), 0)
            observed = owned_skills.get(key)
            met = observed is not None and observed >= minimum and observed > 0
            explicitly_below = observed is not None and observed > 0 and observed < minimum
            detail = 'Required level: ' + (requirement.level or 'Any recorded level')
            if observed is not None:
                detail += '; your level: ' + next((k.title() for k,v in LEVELS.items() if v == observed), 'Unspecified')
            if explicitly_below:
                failure_reason = f'{name}: candidate level {next(k.title() for k,v in LEVELS.items() if v == observed)} is below required {requirement.level}'
            elif observed is None:
                failure_reason = f'{name}: skill not declared in profile; proficiency unknown'
            elif not met:
                failure_reason = f'{name}: recorded proficiency is unrecognized; cannot prove required level'
        elif category == 'education':
            met = key in owned_degrees
            detail = 'Exact named qualification match (case-insensitive)'
            if not met:
                failure_reason = f'{name}: no exactly matching qualification recorded in profile (unknown, not absent)' 
        elif category == 'certification':
            met = key in owned_certs
            detail = 'Exact certificate name; expired certificates excluded'
            if not met:
                expired = any(normalize(item.certification.name) == key and item.expiry_date is not None and item.expiry_date < today for item in candidate.certifications if item.certification)
                failure_reason = (f'{name}: recorded certification expired' if expired else f'{name}: no current matching certification recorded (unknown, not absent)')
        if met:
            facts.add(evidence_atom)
        else:
            evidence_explanations[evidence_atom] = failure_reason or f'{name}: supporting evidence not recorded'
        rules.append(Rule('R_' + idx + '_' + category,
                          passed_atom, (evidence_atom,)))
        check = {'id': idx, 'category': label, 'name': name,
                 'importance': 'Mandatory' if priority else 'Preferred',
                 'met': met, 'explicitly_below': explicitly_below,
                 'detail': detail, 'reason': failure_reason, 'rule': 'R_' + idx + '_' + category}
        checks.append(check)
        if priority:
            mandatory_atoms.append(passed_atom)
        else:
            preferences.append(check)

    # No requirements configured is not evidence of eligibility.
    years = experience_years(candidate.experiences, today)
    minimum_years = float(job.min_experience or 0)
    experience_known = years is not None
    # Jobs requiring zero experience do not need an employment history.
    experience_met = minimum_years <= 0 or (years is not None and years + 1e-8 >= minimum_years)
    if experience_met:
        facts.add(('experience_evidence', person, identifier))
    else:
        evidence_explanations[('experience_evidence', person, identifier)] = (
            f'Experience: {years:.2f} recorded years below required {minimum_years:g} years'
            if years is not None else
            f'Experience: {minimum_years:g} years required, no dated employment history recorded (unknown)')
    experience_atom = ('experience_met', person, identifier)
    rules.append(Rule('R_experience_threshold', experience_atom,
                      (('experience_evidence', person, identifier),)))
    mandatory_atoms.append(experience_atom)
    checks.append({'id': 'experience', 'category': 'Experience',
                   'name': f'{minimum_years:g} years minimum',
                   'importance': 'Mandatory', 'met': experience_met,
                   'explicitly_below': experience_known and not experience_met,
                   'detail': f'Recorded non-overlapping years: {years:.2f}' if years is not None else 'No dated employment history supplied',
                   'reason': evidence_explanations.get(('experience_evidence', person, identifier), ''),
                   'rule': 'R_experience_threshold'})

    goal = ('eligible', person, identifier)
    rules.append(Rule('R_eligibility_all_mandatory', goal,
                      tuple([('candidate', person), ('job', identifier)] + mandatory_atoms)))
    result = infer(facts, rules, goal, evidence_explanations=evidence_explanations)
    if not requirements:
        status = 'Insufficient Information'
        note = 'This job has no configured structured requirements yet.'
    elif result.forward_proved:
        status = 'Eligible'
        note = 'All declared mandatory requirements are supported by entered profile evidence.'
    elif any(c['explicitly_below'] and c['importance'] == 'Mandatory' for c in checks):
        status = 'Not Eligible'
        note = 'At least one mandatory threshold is explicitly below the requirement; other missing evidence may remain unknown.'
    else:
        status = 'Insufficient Information'
        note = 'At least one mandatory requirement cannot be proven from the profile.'
    unmet_mandatory = [c for c in checks if c['importance'] == 'Mandatory' and not c['met']]
    preferred_total = len(preferences)
    preferred_met = sum(c['met'] for c in preferences)
    return {'status': status, 'note': note, 'checks': checks,
            'unmet_mandatory': unmet_mandatory,
            'mandatory_met': sum(c['met'] for c in checks if c['importance']=='Mandatory'),
            'mandatory_total': sum(c['importance']=='Mandatory' for c in checks),
            'preferred_met': preferred_met, 'preferred_total': preferred_total,
            'result': result, 'base_facts': sorted(facts), 'experience_years': years}

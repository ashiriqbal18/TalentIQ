import sys
from pathlib import Path
from datetime import date
from types import SimpleNamespace as NS
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reasoning.adapter import assess, experience_years


def skill(name, level):
    return NS(skill=NS(name=name), proficiency_level=level)

def degree(name):
    return NS(qualification=NS(name=name))

def cert(name, expiry_date=None):
    return NS(certification=NS(name=name), expiry_date=expiry_date)

def exp(start, end=None, current=False):
    return NS(start_date=start, end_date=end, is_current=current)

def candidate(skills=(), qualifications=(), certificates=(), experience=()):
    return NS(id=1, skills=list(skills), qualifications=list(qualifications),
              certifications=list(certificates), experiences=list(experience))

def job(years=0):
    return NS(id=8, min_experience=years)

def req(id, category, name, level=None, importance='mandatory'):
    return NS(id=id, category=category, name=name, level=level, importance=importance)


def test_all_mandatory_and_preferred_ignored_for_blocking():
    p = candidate([skill('C#', 'Advanced'),skill('SQL','Intermediate')],
                  [degree('BS Computer Science')],[],
                  [exp(date(2020,1,1),date(2024,1,1))])
    r = [req(1,'skill','C#','Advanced'),req(2,'skill','sql','Intermediate'),
         req(3,'education','BS Computer Science'),
         req(4,'certification','Azure',importance='preferred')]
    a=assess(p,job(3),r,date(2026,11,8))
    assert a['status']=='Eligible'
    assert a['result'].forward_proved and a['result'].backward_proved
    assert a['preferred_met']==0 and a['mandatory_met']==4
    assert len(a['result'].rounds)>=2


def test_missing_profile_skill_is_unknown_not_false():
    a=assess(candidate(),job(),[req(1,'skill','C#','Advanced')])
    assert a['status']=='Insufficient Information'
    assert a['result'].forward_proved is False
    assert a['result'].backward_proved is False


def test_proven_lower_skill_is_not_eligible():
    a=assess(candidate([skill('C#','Beginner')]),job(),[req(1,'skill','C#','Advanced')])
    assert a['status']=='Not Eligible'


def test_undated_experience_ambiguous():
    a=assess(candidate(),job(2),[req(1,'skill','C#')])
    assert a['status']=='Insufficient Information'


def test_explicit_experience_shortfall():
    a=assess(candidate(experience=[exp(date(2025,1,1),date(2025,6,1))]),
             job(3),[req(1,'skill','C#')])
    assert a['status']=='Not Eligible'


def test_expired_cert_excluded():
    a=assess(candidate(certificates=[cert('Azure',date(2020,1,1))]),job(),
             [req(1,'certification','Azure')],date(2026,1,1))
    assert a['status']=='Insufficient Information'


def test_multiple_degrees_supported():
    a=assess(candidate(qualifications=[degree('BS AI'),degree('BS CS')]),
             job(),[req(1,'education','bs cs')])
    assert a['status']=='Eligible'


def test_overlapping_experience_union():
    periods=[exp(date(2020,1,1),date(2021,1,1)),exp(date(2020,6,1),date(2022,1,1))]
    years=experience_years(periods,date(2026,1,1))
    assert 1.99 < years < 2.01


def test_no_requirements_is_incomplete():
    a=assess(candidate(),job(),[])
    assert a['status']=='Insufficient Information'


def test_backward_trace_shows_proficiency_mismatch():
    a=assess(candidate([skill('Python','Beginner')]),job(),[req(20,'skill','Python','Advanced')])
    trace='\n'.join(a['result'].backward_trace)
    assert 'candidate level Beginner is below required Advanced' in trace
    assert a['status']=='Not Eligible'
    assert len(a['unmet_mandatory']) == 1

def test_backward_trace_shows_missing_qualification():
    a=assess(candidate(),job(),[req(21,'education','Computer Science')])
    assert 'no exactly matching qualification recorded' in '\n'.join(a['result'].backward_trace)
    assert a['status']=='Insufficient Information'

def test_all_unmet_conditions_in_summary():
    a=assess(candidate([skill('Python','Beginner')]),job(),[req(20,'skill','Python','Advanced'),req(21,'education','Computer Science')])
    assert len(a['unmet_mandatory']) == 2
    assert all(c['reason'] for c in a['unmet_mandatory'])

def test_expired_certificate_is_diagnosed():
    a=assess(candidate(certificates=[cert('Azure',date(2020,1,1))]),job(),[req(22,'certification','Azure')],date(2026,1,1))
    assert 'recorded certification expired' in '\n'.join(a['result'].backward_trace)

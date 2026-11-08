"""Live graph tests use disposable in-memory record doubles, never bundled demo profiles."""
from datetime import date
from types import SimpleNamespace as Obj
from reasoning.live_knowledge import build_live_knowledge


def user(skill_records=(), qualifications=(), certificates=()):
    return Obj(id=45,skills=list(skill_records),qualifications=list(qualifications),
               certifications=list(certificates),experiences=[])


def job():
    return Obj(id=72, min_experience=0)


def skill(name, proficiency):
    return Obj(skill=Obj(name=name),proficiency_level=proficiency)


def requirement(id, category, name, level=None, importance='mandatory'):
    return Obj(id=id,category=category,name=name,level=level,importance=importance)


def test_missing_evidence_never_claimed_owned():
    live=build_live_knowledge(user([skill('Python','Beginner')]), job(),
        [requirement(1,'skill','Python','Advanced'),
         requirement(2,'education','Computer Science')])
    python=next(x for x in live['graph'] if x['name']=='Python')
    degree=next(x for x in live['graph'] if x['name']=='Computer Science')
    assert python['has'] and python['required']
    assert not degree['has'] and degree['required']
    assert live['analysis']['status']=='Not Eligible'
    assert all(not (x[0]=='HasEducation' and x[2]=='Computer Science') for x in live['statements'])


def test_empty_records_produce_no_fake_individuals():
    live=build_live_knowledge(None,None,[])
    assert not live['graph'] and not live['statements'] and live['analysis'] is None


def test_profile_without_job_shows_only_ownership_edges():
    live=build_live_knowledge(user([skill('C++','Intermediate')]),None,[])
    assert len(live['graph'])==1 and live['graph'][0]['has']
    assert not live['graph'][0]['required']
    assert live['statements']==[('Candidate','45'),('HasSkill','45','C++'),('HasSkillLevel','45','C++','Intermediate')]


def test_actual_certification_and_degree_only():
    c=user(qualifications=[Obj(qualification=Obj(name='BS CS'),institution='Uni')],
           certificates=[Obj(certification=Obj(name='AWS'),expiry_date=date(2020,1,1))])
    live=build_live_knowledge(c,job(),[requirement(10,'certification','Azure')])
    assert {x['name'] for x in live['graph']}=={'BS CS','AWS','Azure'}
    assert not next(x for x in live['graph'] if x['name']=='Azure')['has']


def test_graph_counts_and_grounded_proficiency_facts():
    live=build_live_knowledge(user([skill('Python','Beginner')]),job(),[
        requirement(1,'skill','Python','Advanced'),
        requirement(2,'education','Computer Science')])
    assert live['entity_count'] == 4  # candidate, job, Python, Computer Science
    assert live['relationship_count'] == 3  # has Python, requires Python, requires CS
    assert ('HasSkillLevel','45','Python','Beginner') in live['statements']
    assert ('RequiresSkillLevel','72','Python','Advanced') in live['statements']
    assert ('RequirementImportance','72','Skill','Python','mandatory') in live['statements']
    assert ('RequirementImportance','72','Education','Computer Science','mandatory') in live['statements']
    assert not any(fact[0]=='HasEducation' for fact in live['statements'])

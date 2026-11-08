"""CT-351 Group 9 | Intelligent Job Role & Skill Matching Reasoning System.

Positive, finite, function-free Horn rules; forward least-fixed-point chaining;
ground backward proofs. A trusted numerical preprocessing step derives
experience_meets(C,R) using validated integer years >= minimum years.

All people, roles and hiring policies are SYNTHETIC classroom examples.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Sequence

Fact = tuple[str, ...]
Bindings = dict[str, str]
ARITY = {
    'candidate': 1, 'job_role': 1, 'skill': 1, 'degree_type': 1, 'cert_type': 1,
    'verified': 1, 'open_role': 1, 'has_skill': 2, 'has_degree': 2,
    'has_cert': 2, 'experience_years': 2, 'minimum_years': 2,
    'requires_skill': 2, 'requires_cert': 2, 'accepts_degree': 2,
}


@dataclass(frozen=True)
class Rule:
    name: str
    head: Fact
    body: tuple[Fact, ...]


@dataclass(frozen=True)
class Derivation:
    conclusion: Fact
    rule: str
    premises: tuple[Fact, ...]


def fmt(f: Fact) -> str:
    return f'{f[0]}({", ".join(f[1:])})'


def var(x: str) -> bool:
    return x.startswith('?')


def ground(f: Fact) -> bool:
    return not any(var(x) for x in f)


def subst(f: Fact, b: Bindings) -> Fact:
    return tuple(b.get(x, x) for x in f)


def unify(pattern: Fact, fact: Fact, bound: Bindings) -> Bindings | None:
    if len(pattern) != len(fact) or pattern[0] != fact[0]:
        return None
    output = dict(bound)
    for a, z in zip(pattern[1:], fact[1:]):
        if var(a):
            if a in output and output[a] != z:
                return None
            output[a] = z
        elif a != z:
            return None
    return output


def match_body(body: Sequence[Fact], known: frozenset[Fact]):
    states: list[tuple[Bindings, tuple[Fact, ...]]] = [({}, ())]
    index: dict[str, list[Fact]] = {}
    for f in sorted(known):
        index.setdefault(f[0], []).append(f)
    for atom in body:
        next_states = []
        for theta, supports in states:
            for fact in index.get(atom[0], []):
                b = unify(atom, fact, theta)
                if b is not None:
                    next_states.append((b, supports + (fact,)))
        states = next_states
        if not states:
            break
    return states


class KnowledgeError(ValueError):
    pass


def validate(data: Iterable[Fact]) -> None:
    facts = set(data)
    for f in facts:
        if not f or f[0] not in ARITY or len(f) != ARITY[f[0]] + 1:
            raise KnowledgeError(f'Unknown or malformed fact: {f!r}')
    entities = {k: {f[1] for f in facts if f[0] == k}
                for k in ('candidate', 'job_role', 'skill', 'degree_type', 'cert_type')}
    if not entities['candidate'] or not entities['job_role']:
        raise KnowledgeError('Knowledge base needs at least one candidate and one job role.')
    if len(set().union(*entities.values())) != sum(map(len, entities.values())):
        raise KnowledgeError('Typed entity identifiers must be disjoint across entity classes.')
    reqs = {
        'verified': ('candidate',), 'open_role': ('job_role',),
        'has_skill': ('candidate', 'skill'), 'has_degree': ('candidate', 'degree_type'),
        'has_cert': ('candidate', 'cert_type'),
        'experience_years': ('candidate',), 'minimum_years': ('job_role',),
        'requires_skill': ('job_role', 'skill'),
        'requires_cert': ('job_role', 'cert_type'),
        'accepts_degree': ('job_role', 'degree_type'),
    }
    for f in facts:
        for i, sort in enumerate(reqs.get(f[0], ())):
            if f[i + 1] not in entities[sort]:
                raise KnowledgeError(f'Unknown {sort} in {fmt(f)}')
        if f[0] in ('experience_years', 'minimum_years'):
            if not f[2].isdigit() or not 0 <= int(f[2]) <= 50:
                raise KnowledgeError(f'Years must be an integer from 0 to 50: {fmt(f)}')
    for candidate in entities['candidate']:
        for pred in ('has_degree', 'experience_years'):
            count = sum(f[0] == pred and f[1] == candidate for f in facts)
            if count != 1:
                raise KnowledgeError(f'Candidate {candidate} must have exactly one {pred} fact (found {count}).')
    for role in entities['job_role']:
        count = sum(f[0] == 'minimum_years' and f[1] == role for f in facts)
        if count != 1:
            raise KnowledgeError(f'Job role {role} must have exactly one minimum_years fact.')
        if not any(f[0] == 'accepts_degree' and f[1] == role for f in facts):
            raise KnowledgeError(f'Job role {role} must accept at least one degree.')


def numeric_evidence(data: frozenset[Fact]) -> frozenset[Fact]:
    """Built-in comparison is NOT misrepresented as a pure Horn deduction."""
    cy = {f[1]: int(f[2]) for f in data if f[0] == 'experience_years'}
    ry = {f[1]: int(f[2]) for f in data if f[0] == 'minimum_years'}
    return frozenset(('experience_meets', c, r) for c, years in cy.items()
                     for r, minimum in ry.items() if years >= minimum)


def compile_rules(data: frozenset[Fact]) -> tuple[Rule, ...]:
    roles = sorted(f[1] for f in data if f[0] == 'job_role')
    rules: list[Rule] = [
        Rule('H1_skill_evidence', ('skill_evidenced', '?c', '?s'), (('has_skill', '?c', '?s'),)),
        Rule('H2_cert_evidence', ('cert_evidenced', '?c', '?t'), (('has_cert', '?c', '?t'),)),
    ]
    for role, degree in sorted((f[1], f[2]) for f in data if f[0] == 'accepts_degree'):
        rules.append(Rule(f'H3_degree_{role}_{degree}', ('degree_accepted', '?c', role),
                          (('has_degree', '?c', degree),)))
    for role in roles:
        skills = sorted(f[2] for f in data if f[0] == 'requires_skill' and f[1] == role)
        certs = sorted(f[2] for f in data if f[0] == 'requires_cert' and f[1] == role)
        body: tuple[Fact, ...] = (('candidate', '?c'),) + tuple(
            ('skill_evidenced', '?c', s) for s in skills) + tuple(
            ('cert_evidenced', '?c', t) for t in certs)
        rules.append(Rule('H4_requirements_' + role, ('requirements_met', '?c', role), body))
        rules.append(Rule('H5_eligible_' + role, ('eligible', '?c', role), (
            ('candidate', '?c'), ('job_role', role), ('verified', '?c'),
            ('open_role', role), ('degree_accepted', '?c', role),
            ('experience_meets', '?c', role), ('requirements_met', '?c', role))))
    rules.append(Rule('H6_recommend', ('recommended', '?c', '?r'), (('eligible', '?c', '?r'),)))
    for rule in rules:
        headvars = {x for x in rule.head if var(x)}
        bodyvars = {x for atom in rule.body for x in atom if var(x)}
        if not headvars.issubset(bodyvars):
            raise KnowledgeError(f'Unsafe Horn rule: {rule.name}')
    return tuple(rules)


class JobSkillKB:
    def __init__(self, source: Iterable[Fact]):
        self.base = frozenset(source)
        validate(self.base)
        self.calculated = numeric_evidence(self.base)
        self.extensional = self.base | self.calculated
        self.rules = compile_rules(self.base)
        self.inferred = frozenset(self.extensional)
        self.rounds: tuple[tuple[Derivation, ...], ...] = ()

    def forward_chain(self) -> frozenset[Fact]:
        known = set(self.extensional)
        rounds = []
        while True:
            staged: dict[Fact, Derivation] = {}
            snapshot = frozenset(known)
            for rule in self.rules:
                for theta, premises in match_body(rule.body, snapshot):
                    fact = subst(rule.head, theta)
                    if not ground(fact):
                        raise AssertionError(f'Non-ground conclusion {fact}')
                    if fact not in known and fact not in staged:
                        staged[fact] = Derivation(fact, rule.name, premises)
            if not staged:
                break
            batch = tuple(staged[k] for k in sorted(staged))
            rounds.append(batch)
            known.update(staged)
        self.inferred = frozenset(known)
        self.rounds = tuple(rounds)
        return self.inferred

    def backward_prove(self, goal: Fact) -> tuple[bool, tuple[str, ...]]:
        if not ground(goal):
            raise ValueError('Backward proof requires a ground query.')
        log = []
        def rec(atom: Fact, depth: int, trail: tuple[Fact, ...]) -> bool:
            p = '  ' * depth
            if atom in self.extensional:
                kind = 'CALCULATED' if atom in self.calculated else 'FACT'
                log.append(f'{p}{kind}  {fmt(atom)}')
                return True
            if atom in trail:
                log.append(f'{p}CYCLE  {fmt(atom)}'); return False
            options = []
            for rule in self.rules:
                theta = unify(rule.head, atom, {})
                if theta is not None: options.append((rule, theta))
            if not options:
                log.append(f'{p}FAIL  {fmt(atom)} (no matching fact or rule)'); return False
            for rule, theta in options:
                log.append(f'{p}TRY  {fmt(atom)} <= {rule.name}')
                premises = [subst(a, theta) for a in rule.body]
                if not all(ground(s) for s in premises):
                    raise AssertionError('Internal error: proof subgoal contains free variables')
                if all(rec(s, depth + 1, trail + (atom,)) for s in premises):
                    log.append(f'{p}PROVED  {fmt(atom)}'); return True
                log.append(f'{p}RULE FAIL  {rule.name}')
            log.append(f'{p}NOT PROVED  {fmt(atom)}')
            return False
        return rec(goal, 0, ()), tuple(log)

    def diagnose(self, candidate: str, role: str) -> tuple[str, ...]:
        facts = self.base
        problems = []
        for atom, desc in [
            (('candidate', candidate), 'candidate record missing'),
            (('job_role', role), 'job role missing'),
            (('verified', candidate), 'candidate verification not recorded'),
            (('open_role', role), 'job role not marked open'),
            (('degree_accepted', candidate, role), 'no accepted degree evidenced'),
            (('experience_meets', candidate, role), 'insufficient or unrecorded experience'),
        ]:
            if atom not in self.inferred:
                problems.append(desc)
        for s in sorted(f[2] for f in facts if f[0] == 'requires_skill' and f[1] == role):
            if ('has_skill', candidate, s) not in facts:
                problems.append('required skill not evidenced: ' + s)
        for cert in sorted(f[2] for f in facts if f[0] == 'requires_cert' and f[1] == role):
            if ('has_cert', candidate, cert) not in facts:
                problems.append('required certification not evidenced: ' + cert)
        return tuple(problems) if problems else ('all modeled conditions supported',)

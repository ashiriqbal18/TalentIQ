"""Finite, positive Horn-clause inference adapted from the original CT-351 engine.

No hidden ML score: ground facts + explicit rules, a least-fixed-point forward
closure, and a separate goal-driven backward proof with human-readable trace.
"""
from dataclasses import dataclass
from .original_job_skill_engine import Rule, Derivation, match_body, subst, ground, unify, fmt


@dataclass
class InferenceResult:
    known: frozenset
    rounds: tuple
    forward_proved: bool
    backward_proved: bool
    backward_trace: tuple
    goal: tuple
    rules: tuple


def infer(facts, rules, goal, evidence_explanations=None):
    evidence_explanations = evidence_explanations or {}
    source = frozenset(facts)
    rules = tuple(rules)
    known = set(source)
    rounds = []
    while True:
        new = {}
        for rule in rules:
            for binding, premises in match_body(rule.body, frozenset(known)):
                conclusion = subst(rule.head, binding)
                if not ground(conclusion):
                    raise ValueError('Unsafe Horn clause: ' + rule.name)
                if conclusion not in known and conclusion not in new:
                    new[conclusion] = Derivation(conclusion, rule.name, premises)
        if not new:
            break
        batch = tuple(new[k] for k in sorted(new))
        rounds.append(batch)
        known.update(new)

    log = []
    def prove(atom, depth=0, ancestors=()):
        pad = '  ' * depth
        if atom in source:
            log.append(pad + 'FACT ' + fmt(atom))
            return True
        if atom in ancestors:
            log.append(pad + 'CYCLE ' + fmt(atom))
            return False
        relevant = [(r, unify(r.head, atom, {})) for r in rules]
        relevant = [(r, b) for r, b in relevant if b is not None]
        if not relevant:
            detail = evidence_explanations.get(atom, 'No matching evidence is recorded (unknown, not proven false)')
            log.append(pad + 'NOT PROVED ' + fmt(atom) + ' — ' + detail)
            return False
        for rule, bindings in relevant:
            log.append(pad + 'TRY ' + fmt(atom) + ' <= ' + rule.name)
            children = [subst(x, bindings) for x in rule.body]
            if not all(ground(x) for x in children):
                raise ValueError('Non-ground backward subgoal in ' + rule.name)
            if all(prove(child, depth+1, ancestors+(atom,)) for child in children):
                log.append(pad + 'PROVED ' + fmt(atom))
                return True
            log.append(pad + 'RULE FAILED ' + rule.name)
        log.append(pad + 'NOT PROVED ' + fmt(atom))
        return False

    backward = prove(goal)
    forward = goal in known
    if backward != forward:
        raise AssertionError('Forward and backward inference disagree')
    return InferenceResult(frozenset(known), tuple(rounds), forward,
                           backward, tuple(log), goal, rules)

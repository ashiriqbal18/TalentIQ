
/*
   TALENTIQ CT-351
   JOB ELIGIBILITY EXPERT SYSTEM

   Single-file SWI-Prolog implementation.

   Based on:
   - reasoning/adapter.py
   - reasoning/engine.py

   No sample candidate or job facts are hardcoded.

   Real facts are loaded separately using:

   ?- load_facts('talentiq_facts.pl').

   Main queries:

   ?- eligibility(1, 1, Status).
   ?- eligible(1, 1).
   ?- forward_trace(1, 1, Rounds).
   ?- backward_trace(1, 1, Trace).
   ?- mandatory_audit(1, 1, Checks).
   ?- explain(1, 1).
*/


% ============================================================
% 1. LIBRARIES
% ============================================================

:- use_module(library(lists)).
:- use_module(library(date)).


% ============================================================
% 2. DYNAMIC KNOWLEDGE BASE
% ============================================================

:- dynamic candidate/1.
:- dynamic job/1.
:- dynamic candidate_skill/3.
:- dynamic candidate_qualification/2.
:- dynamic candidate_certification/3.
:- dynamic candidate_experience_years/2.
:- dynamic job_min_experience/2.
:- dynamic requirement/6.
:- dynamic as_of_date/3.


% ============================================================
% 3. LOAD DATABASE FACTS
% ============================================================

load_facts(Path) :-

    exists_file(Path),

    retractall(candidate(_)),
    retractall(job(_)),

    retractall(candidate_skill(_, _, _)),

    retractall(candidate_qualification(_, _)),

    retractall(candidate_certification(_, _, _)),

    retractall(candidate_experience_years(_, _)),

    retractall(job_min_experience(_, _)),

    retractall(requirement(_, _, _, _, _, _)),

    retractall(as_of_date(_, _, _)),

    consult(Path).


% ============================================================
% 4. NAME NORMALIZATION
% ============================================================

% Match names without case differences and extra whitespace.

normalized(Input, Norm) :-

    (
        atom(Input)
        ->
        atom_string(Input, S)

        ;

        string(Input)
        ->
        S = Input
    ),

    normalize_space(string(Trim), S),

    string_lower(Trim, Norm).


same_name(A, B) :-

    normalized(A, N),

    normalized(B, N).


% ============================================================
% 5. SKILL PROFICIENCY LEVELS
% ============================================================

% Python domain configuration:
%
% Beginner     = 1
% Intermediate = 2
% Advanced     = 3
%
% Unrecognized level = 0

level_rank(Level, Rank) :-

    normalized(Level, Normalized),

    (
        memberchk(
            Normalized-Rank,
            [
                "beginner"-1,
                "intermediate"-2,
                "advanced"-3
            ]
        )

        -> true

        ; Rank = 0
    ).


% ============================================================
% 6. CANDIDATE SKILL MATCHING
% ============================================================

% Python adapter stores the LAST matching skill level.
% It does not select the highest duplicate proficiency.

last_skill_rank(C, Name, Rank) :-

    findall(
        R,

        (
            candidate_skill(C, Actual, Level),

            same_name(Actual, Name),

            level_rank(Level, R)
        ),

        Ranks
    ),

    Ranks \= [],

    last(Ranks, Rank).


% Requirement satisfied.

skill_check(
    C,
    Name,
    RequiredLevel,
    met,
    sufficient_skill_level
) :-

    last_skill_rank(C, Name, Observed),

    level_rank(RequiredLevel, Minimum),

    Observed > 0,

    Observed >= Minimum,

    !.


% Explicit proficiency failure.

skill_check(
    C,
    Name,
    RequiredLevel,
    failed,
    below_required_skill_level(Observed, Minimum)
) :-

    last_skill_rank(C, Name, Observed),

    level_rank(RequiredLevel, Minimum),

    Observed > 0,

    Observed < Minimum,

    !.


% Unrecognized recorded proficiency.

skill_check(
    C,
    Name,
    _,
    unknown,
    unrecognized_recorded_skill_level
) :-

    last_skill_rank(C, Name, 0),

    !.


% Skill evidence missing.

skill_check(
    _,
    _,
    _,
    unknown,
    skill_not_declared_or_unknown
).


% ============================================================
% 7. EDUCATION MATCHING
% ============================================================

education_check(
    C,
    Name,
    met,
    qualification_recorded
) :-

    candidate_qualification(C, Actual),

    same_name(Actual, Name),

    !.


education_check(
    _,
    _,
    unknown,
    qualification_not_recorded
).


% ============================================================
% 8. CERTIFICATION VALIDATION
% ============================================================

% Optional fixed assessment date for reproducible tests.

assessment_date(Y, M, D) :-

    as_of_date(Y, M, D),

    !.


% Otherwise use local current date.

assessment_date(Y, M, D) :-

    get_time(Time),

    stamp_date_time(
        Time,
        date(Y, M, D, _, _, _, _, _, _),
        local
    ).


% No expiry date means no expiry recorded.

expiry_valid(none) :-

    !.


% Certification is valid through its expiry date.

expiry_valid(date(Y, M, D)) :-

    assessment_date(TY, TM, TD),

    (
        Y > TY

        ;

        Y =:= TY,
        M > TM

        ;

        Y =:= TY,
        M =:= TM,
        D >= TD
    ).


certification_check(
    C,
    Name,
    met,
    current_certification_recorded
) :-

    candidate_certification(C, Actual, Expiry),

    same_name(Actual, Name),

    expiry_valid(Expiry),

    !.


certification_check(
    C,
    Name,
    unknown,
    recorded_certification_expired
) :-

    candidate_certification(C, Actual, Expiry),

    same_name(Actual, Name),

    \+ expiry_valid(Expiry),

    !.


certification_check(
    _,
    _,
    unknown,
    no_current_matching_certificate_recorded
).


% ============================================================
% 9. EXPERIENCE VALIDATION
% ============================================================

% Match Python's default of zero years if the job
% minimum is missing or zero.

minimum_experience(J, Minimum) :-

    (
        job_min_experience(J, Value),

        number(Value)

        ->

        Minimum is max(0, Value)

        ;

        Minimum = 0
    ).


% Zero experience threshold is always satisfied.

experience_check(
    _,
    J,
    met,
    zero_year_threshold
) :-

    minimum_experience(J, Minimum),

    Minimum =< 0,

    !.


% Sufficient work experience.

experience_check(
    C,
    J,
    met,
    sufficient_recorded_experience
) :-

    minimum_experience(J, Minimum),

    candidate_experience_years(C, Years),

    number(Years),

    Years + 1.0e-8 >= Minimum,

    !.


% Explicit experience threshold failure.

experience_check(
    C,
    J,
    failed,
    insufficient_recorded_experience(Years, Minimum)
) :-

    minimum_experience(J, Minimum),

    candidate_experience_years(C, Years),

    number(Years),

    Years + 1.0e-8 < Minimum,

    !.


% Missing experience evidence.

experience_check(
    _,
    _,
    unknown,
    no_dated_employment_recorded
).


% ============================================================
% 10. REQUIREMENT EVALUATION
% ============================================================

% SKILL

check(C, J, R, Status, Reason) :-

    candidate(C),

    job(J),

    requirement(
        J, R, skill, Name, Level, _
    ),

    skill_check(
        C, Name, Level, Status, Reason
    ).


% EDUCATION

check(C, J, R, Status, Reason) :-

    candidate(C),

    job(J),

    requirement(
        J, R, education, Name, _, _
    ),

    education_check(
        C, Name, Status, Reason
    ).


% CERTIFICATION

check(C, J, R, Status, Reason) :-

    candidate(C),

    job(J),

    requirement(
        J, R, certification, Name, _, _
    ),

    certification_check(
        C, Name, Status, Reason
    ).


% ============================================================
% 11. MANDATORY AND PREFERRED REQUIREMENTS
% ============================================================

mandatory_requirement(J, R) :-

    requirement(
        J, R, _, _, _, mandatory
    ).


preferred_requirement(J, R) :-

    requirement(
        J, R, _, _, _, preferred
    ).


% ============================================================
% 12. HORN CLAUSE CONCLUSIONS
% ============================================================

requirement_met(C, J, R) :-

    check(C, J, R, met, _).


experience_met(C, J) :-

    candidate(C),

    job(J),

    experience_check(C, J, met, _).


% All mandatory requirements must be satisfied.

all_mandatory_met(C, J) :-

    forall(
        mandatory_requirement(J, R),

        requirement_met(C, J, R)
    ).


% ============================================================
% 13. ELIGIBILITY RULE
% ============================================================

eligible(C, J) :-

    candidate(C),

    job(J),

    experience_met(C, J),

    all_mandatory_met(C, J).


% ============================================================
% 14. THREE-VALUED ELIGIBILITY DECISION
% ============================================================

% PRIORITY 1:
% No configured requirements = Insufficient Information.

eligibility(
    C,
    J,
    'Insufficient Information'
) :-

    candidate(C),

    job(J),

    \+ requirement(J, _, _, _, _, _),

    !.


% PRIORITY 2:
% All mandatory conditions met = Eligible.

eligibility(C, J, 'Eligible') :-

    eligible(C, J),

    !.


% PRIORITY 3:
% Explicit mandatory threshold failure = Not Eligible.

eligibility(C, J, 'Not Eligible') :-

    candidate(C),

    job(J),

    (
        experience_check(C, J, failed, _)

        ;

        mandatory_requirement(J, R),

        check(C, J, R, failed, _)
    ),

    !.


% PRIORITY 4:
% Missing evidence = Insufficient Information.

eligibility(
    C,
    J,
    'Insufficient Information'
) :-

    candidate(C),

    job(J).


% ============================================================
% 15. INITIAL KNOWLEDGE BASE
% ============================================================

base_fact(C, J, candidate(C)) :-

    candidate(C),

    job(J).


base_fact(C, J, job(J)) :-

    candidate(C),

    job(J).


base_fact(C, J, evidence(C, J, R)) :-

    requirement(J, R, _, _, _, _),

    check(C, J, R, met, _).


base_fact(
    C,
    J,
    experience_evidence(C, J)
) :-

    experience_check(C, J, met, _).


% ============================================================
% 16. GENERATED HORN RULES
% ============================================================

% Requirement inference.

horn_rule(
    C,
    J,
    rule_requirement(R),
    requirement_met(C, J, R),
    [evidence(C, J, R)]
) :-

    requirement(J, R, Category, _, _, _),

    memberchk(
        Category,
        [skill, education, certification]
    ).


% Experience inference.

horn_rule(
    C,
    J,
    'R_experience_threshold',
    experience_met(C, J),
    [experience_evidence(C, J)]
) :-

    candidate(C),

    job(J).


% Final eligibility inference.

horn_rule(
    C,
    J,
    'R_eligibility_all_mandatory',
    eligible(C, J),
    Body
) :-

    candidate(C),

    job(J),

    findall(
        requirement_met(C, J, R),

        mandatory_requirement(J, R),

        Required
    ),

    append(
        [candidate(C), job(J) | Required],
        [experience_met(C, J)],
        Body
    ).


% ============================================================
% 17. FORWARD CHAINING
% ============================================================

% Start with known facts.

forward_trace(C, J, Rounds) :-

    candidate(C),

    job(J),

    findall(
        Fact,
        base_fact(C, J, Fact),
        Facts
    ),

    sort(Facts, Initial),

    fc_rounds(
        C,
        J,
        Initial,
        Rounds,
        _
    ).


% Apply rules repeatedly until no new facts appear.

fc_rounds(C, J, Known, Rounds, Closure) :-

    findall(
        Head-fired(Rule, Head, Body),

        (
            horn_rule(C, J, Rule, Head, Body),

            \+ memberchk(Head, Known),

            forall(
                member(Premise, Body),
                memberchk(Premise, Known)
            )
        ),

        Pairs
    ),

    keysort(Pairs, Sorted),

    unique_heads(Sorted, New),

    (
        New = []

        ->

        Rounds = [],
        Closure = Known

        ;

        findall(
            Head,
            member(fired(_, Head, _), New),
            Added
        ),

        append(Known, Added, Temporary),

        sort(Temporary, Next),

        Rounds = [New | Later],

        fc_rounds(
            C,
            J,
            Next,
            Later,
            Closure
        )
    ).


% Prevent duplicated conclusions.

unique_heads([], []).


unique_heads(
    [Head-Derivation | Rest],
    [Derivation | Remaining]
) :-

    skip_head(Rest, Head, Tail),

    unique_heads(Tail, Remaining).


skip_head(
    [Head-_ | Rest],
    Head,
    Tail
) :-

    !,

    skip_head(Rest, Head, Tail).


skip_head(Rest, _, Rest).


% Check whether Forward Chaining proves eligibility.

forward_proved(C, J) :-

    forward_trace(C, J, _),

    findall(
        Fact,
        base_fact(C, J, Fact),
        Facts
    ),

    sort(Facts, Initial),

    fc_rounds(
        C,
        J,
        Initial,
        _,
        Closure
    ),

    memberchk(
        eligible(C, J),
        Closure
    ).


% ============================================================
% 18. BACKWARD CHAINING
% ============================================================

% Start with the eligibility goal.

backward_trace(C, J, Trace) :-

    candidate(C),

    job(J),

    bc_prove(
        C,
        J,
        eligible(C, J),
        [],
        _,
        Trace
    ).


backward_proved(C, J) :-

    candidate(C),

    job(J),

    bc_prove(
        C,
        J,
        eligible(C, J),
        [],
        true,
        _
    ).


% Recursive proof search.

bc_prove(
    C,
    J,
    Goal,
    Ancestors,
    Success,
    Trace
) :-

    (
        base_fact(C, J, Goal)

        ->

        Success = true,
        Trace = [fact(Goal)]

        ;

        memberchk(Goal, Ancestors)

        ->

        Success = false,
        Trace = [cycle(Goal)]

        ;

        findall(
            Rule-Body,

            horn_rule(C, J, Rule, Goal, Body),

            Rules
        ),

        (
            Rules = []

            ->

            Success = false,
            Trace = [not_proved(Goal)]

            ;

            bc_rules(
                C,
                J,
                Goal,
                Rules,
                [Goal | Ancestors],
                Success,
                Trace
            )
        )
    ).


% Find a suitable rule.

bc_rules(
    _, _, Goal, [], _,
    false,
    [not_proved(Goal)]
).


bc_rules(
    C,
    J,
    Goal,
    [Rule-Body | Rest],
    Ancestors,
    Success,
    Trace
) :-

    bc_premises(
        C,
        J,
        Body,
        Ancestors,
        This,
        Children
    ),

    (
        This == true

        ->

        Success = true,

        append(
            [try(Goal, Rule) | Children],
            [proved(Goal)],
            Trace
        )

        ;

        bc_rules(
            C,
            J,
            Goal,
            Rest,
            Ancestors,
            Success,
            Other
        ),

        append(
            [try(Goal, Rule) | Children],
            [rule_failed(Rule) | Other],
            Trace
        )
    ).


% Verify premises one by one.

bc_premises(_, _, [], _, true, []).


bc_premises(
    C,
    J,
    [Goal | Rest],
    Ancestors,
    Success,
    Trace
) :-

    bc_prove(
        C,
        J,
        Goal,
        Ancestors,
        First,
        FirstTrace
    ),

    (
        First == true

        ->

        bc_premises(
            C,
            J,
            Rest,
            Ancestors,
            Success,
            Later
        ),

        append(
            FirstTrace,
            Later,
            Trace
        )

        ;

        Success = false,
        Trace = FirstTrace
    ).


% ============================================================
% 19. COMPLETE MANDATORY REQUIREMENT AUDIT
% ============================================================

mandatory_audit(C, J, Checks) :-

    candidate(C),

    job(J),

    findall(
        requirement(R, Status, Reason),

        (
            mandatory_requirement(J, R),

            check(C, J, R, Status, Reason)
        ),

        Checks
    ).


% ============================================================
% 20. EXPLAINABLE ELIGIBILITY REPORT
% ============================================================

explain(C, J) :-

    (
        candidate(C),
        job(J)

        ->

        eligibility(C, J, Status),

        format(
            '~nTALENTIQ | Candidate ~w | Job ~w | ~w~n',
            [C, J, Status]
        ),

        format(
            '~nREQUIREMENT CHECKS~n',
            []
        ),

        forall(
            requirement(
                J,
                R,
                Category,
                Name,
                Level,
                Importance
            ),

            (
                check(C, J, R, Result, Reason),

                format(
                    '~w | ~w | ~w | ~w | ~w | ~w | ~q~n',

                    [
                        R,
                        Category,
                        Name,
                        Level,
                        Importance,
                        Result,
                        Reason
                    ]
                )
            )
        ),

        experience_check(
            C,
            J,
            ExpStatus,
            ExpReason
        ),

        format(
            'Experience: ~w (~q)~n',
            [ExpStatus, ExpReason]
        ),

        forward_trace(C, J, Rounds),

        format(
            '~nFORWARD CHAINING~n',
            []
        ),

        forall(
            nth1(N, Rounds, Steps),

            format(
                'Round ~w: ~q~n',
                [N, Steps]
            )
        ),

        backward_trace(C, J, Trace),

        format(
            '~nBACKWARD CHAINING~n',
            []
        ),

        forall(
            member(Event, Trace),

            writeln(Event)
        )

        ;

        writeln(
            'Candidate/job not found in loaded facts'
        )
    ).

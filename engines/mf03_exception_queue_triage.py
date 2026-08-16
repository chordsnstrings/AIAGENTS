"""MF3 -- exception-queue triage.

Every business runs on queues nobody has time to read.  Alert feeds, submission
inboxes, transaction monitors, sensor streams, forums, bank feeds, aged-record
lists: each one arrives faster than a person can work it, and each one contains,
somewhere in the volume, the handful of items that actually needed somebody.
This family is the layer that reads the queue so the owner does not have to.
Its product is never the queue -- it is the short list at the end of it, plus a
defensible account of everything that was kept off that list.

Two failure modes define the family and they pull in opposite directions.  Miss
something real and the queue has quietly failed at the one job it had; surface
everything and the recipient learns within a week to ignore the queue, which is
the same failure arriving more slowly.  So the plan here does its filtering in a
fixed order -- take the item in, collapse duplicates without discarding
occurrences, enrich it with the context a person would otherwise go and fetch,
grade it against rules that existed before the item arrived, and only then
decide whether a human sees it.  Suppression is the privileged act, so it is the
one that must cite the rule that permitted it: an item that leaves the queue
unseen and unlogged is the defect this engine exists to prevent.

The third standing rule is the whole of this family rather than a caveat on it.
Half these units watch for fraud, sanctions hits, conflicts, exam integrity,
ratio breaches and conduct signals, and in every case the catalogue says the
same thing in the workbook's own words: flags, never clears.  So the unit names
what fired, attaches the evidence, applies only the protective control the
policy already prescribes, and hands the packet to the named human with the
decision field empty.  It never states what the signal means about a person, a
cause or an intent.

Config carries the rest.  Signal sources, dedupe windows, thresholds, severity
bands, suppression rules and the routing table all resolve from the vertical
overlay and the active country pack, which is how one engine carries a
sanctioned-party hit, a bottleneck alert, a moderation queue and an unclassified
bank line without knowing which it is holding.
"""

from __future__ import annotations

from typing import Any, ClassVar, Mapping

from adw.models import (
    Artifact,
    Capability,
    ConfigKey,
    Guardrail,
    Step,
    StepKind,
)
from engines.base import Engine, Profile, artifact, register, step

# --------------------------------------------------------------------------- #
# family configuration
# --------------------------------------------------------------------------- #

#: Read by every unit of the family.  Between them these six keys are the whole
#: filter: what is watched, how items collapse, how they are graded, what may be
#: held back, how loud each grade is and who receives it.  Change them and the
#: same code triages a sensor stream or a submissions inbox.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="exception_signal_sources",
        description=(
            "Queues, feeds, systems and inboxes this unit watches, with the "
            "polling interval and the field that carries each item's timestamp."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="triage_rules",
        description=(
            "The deterministic rules that classify an item: the condition each "
            "one tests, the category it assigns and the rule id it is cited by."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="severity_matrix",
        description=(
            "Severity bands, and for each band the response clock, the recipient "
            "and the out-of-hours behaviour it demands."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="suppression_rules",
        description=(
            "The only conditions under which an item may be held back from a "
            "human, and the evidence each one requires before it applies."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="routing_table",
        description=(
            "Which desk, role or queue receives each category and severity, the "
            "default desk for anything unmatched, and the on-call fallback."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="dedupe_window",
        description=(
            "The key items are collapsed on and the window over which repeats "
            "join an existing entry rather than opening a new one."
        ),
        resolved_by="vertical",
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The eleven queue shapes actually present in the catalogue, most specific
#: first.  Tokens are read against worker, system agent, trigger, function and
#: expected output, so they are chosen as nouns of the shape -- "runbook",
#: "demurrage", "proctoring" -- rather than the verbs ("flagged", "triaged",
#: "surfaced") that every unit in the family shares.  Order carries real weight
#: twice: the conduct-risk tokens must claim "never clears" units before any
#: milder profile sees them, and the legality profile must claim the crew
#: scheduling exception agent before the anomaly profile's "exception agent".
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="conduct_risk_flag",
        summary=(
            "A financial-crime, conduct or integrity signal packaged as evidence "
            "for a named compliance human, with the prescribed control applied "
            "and no conclusion attached."
        ),
        match=(
            "fraud",
            "aml",
            "source-of-funds",
            "sanction",
            "restricted-list",
            "siu",
            "surveillance",
            "conflict",
            "transaction-monitoring",
            "stolen card",
            "verification challenge",
            "proctoring",
            "never clears",
            "never concludes",
            "never accuses",
            "hard hold",
            "hard block",
        ),
        steps=(
            step(
                "apply_prescribed_control",
                "Apply the prescribed control and build the referral packet",
                StepKind.ACT,
                (
                    "Apply exactly the control the policy names for this signal -- the "
                    "hold, the block, the freeze, the pause -- and nothing beyond it, "
                    "citing the clause that required it. Build the referral packet "
                    "around it: the signals that fired, the typology they match, the "
                    "subject's history, the control now in force and a decision field "
                    "left empty for the named reviewer. A control you applied is lifted "
                    "by that reviewer and never by you, and the packet reports what the "
                    "evidence shows, never what it implies about the person."
                ),
                produces=("referral_packet", "control_record"),
            ),
        ),
        artifacts=(
            artifact(
                "referral_packet",
                "Referral packet",
                (
                    "The evidence handed to the named compliance role: each signal with "
                    "its source and time, the typology and threshold it matched, the "
                    "subject's prior items and outcomes, and an unfilled decision field."
                ),
                "bundle",
            ),
            artifact(
                "control_record",
                "Protective control record",
                (
                    "Every hold, block, freeze or pause applied, with the policy clause "
                    "that required it, the time it went on, its expiry and the named "
                    "person who may lift it."
                ),
            ),
        ),
        tools=("watchlist_screening", "case_referral", "hold_control"),
        config_keys=(
            ConfigKey(
                key="risk_typologies",
                description=(
                    "The typologies, patterns and thresholds that raise a flag in "
                    "this market, with the rule id each one is cited by."
                ),
                required=True,
            ),
            ConfigKey(
                key="protective_controls",
                description=(
                    "Which control the policy prescribes at each flag type, how long "
                    "it stands and which named role may lift it."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="referral_route",
                description=(
                    "The compliance desk, investigations unit or statutory report "
                    "route each flag type is referred to, and its deadline."
                ),
                required=True,
            ),
        ),
        kpis=(
            "flags referred with a complete evidence packet",
            "prescribed controls applied inside the policy window",
            "referrals returned by the reviewer for missing evidence",
        ),
        channels=("compliance_desk",),
    ),
    Profile(
        name="legality_breach_watch",
        summary=(
            "Rosters, ratios and duty hours run forward against statutory limits "
            "so the breach is flagged in the hours before it would land."
        ),
        match=(
            "legality",
            "roster",
            "staffing ratio",
            "ratio breach",
            "crew",
            "out of hours",
            "duty hour",
        ),
        steps=(
            step(
                "project_the_breach",
                "Run the plan forward against the statutory limit",
                StepKind.ASSESS,
                (
                    "Project the roster, the bookings and the hours already worked "
                    "forward across the configured lookahead and mark the exact hour at "
                    "which each limit would be crossed. Name the limit, the value it "
                    "would reach and the people or sessions affected. A breach reported "
                    "after it happened is a record; this unit exists to produce the "
                    "warning that arrives while the plan can still be changed."
                ),
                produces=("breach_forecast",),
            ),
        ),
        artifacts=(
            artifact(
                "breach_forecast",
                "Projected breach list",
                (
                    "Each projected breach with the limit it crosses, the rule the "
                    "limit comes from, the projected value, the hour it lands, who is "
                    "affected and the options that would avert it."
                ),
                "report",
            ),
        ),
        tools=("roster_system", "limit_calculator"),
        config_keys=(
            ConfigKey(
                key="statutory_limits",
                description=(
                    "Ratios, duty hours, rest periods and qualification requirements "
                    "that bind this market, from the active country pack."
                ),
                required=True,
            ),
            ConfigKey(
                key="lookahead_window",
                description=(
                    "How far forward the projection runs and how early a projected "
                    "breach is surfaced to the planner."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "breaches flagged before the hour they would land",
            "sessions and shifts run inside the statutory limit",
        ),
    ),
    Profile(
        name="policy_rule_check",
        summary=(
            "An item tested clause by clause against a written rule book, with "
            "every breach quoted, cited and left for a person to resolve."
        ),
        match=(
            "advertising and claims",
            "marketing checked",
            "fair-housing",
            "pre-publish",
            "tenancy",
            "suitability",
            "no advice",
            "advice request",
            "guideline",
            "authority-matrix",
            "without authority",
            "localization",
            "locale",
            "compliance reviewer",
            "compliance officer",
            "compliance gatekeeper",
        ),
        steps=(
            step(
                "test_against_the_rule_book",
                "Test the item clause by clause",
                StepKind.ASSESS,
                (
                    "Walk the rule book in force and record a result against every "
                    "clause, quoting the exact wording of the item that triggered each "
                    "flag and citing the clause reference beside it. A clause you cannot "
                    "test is itself a flag rather than a silent pass. Where the rule book "
                    "reserves the subject for a licensed person, the finding is that it "
                    "must be routed to that person -- you record the requirement and "
                    "never supply the answer in their place."
                ),
                produces=("clause_findings",),
            ),
        ),
        artifacts=(
            artifact(
                "clause_findings",
                "Clause-by-clause findings",
                (
                    "Every clause tested with its reference and version, the wording "
                    "that triggered each flag, the severity of the flag and a compliant "
                    "alternative drafted for the human to accept or reject."
                ),
                "report",
            ),
        ),
        tools=("rule_book_lookup", "claim_checker"),
        config_keys=(
            ConfigKey(
                key="rule_book",
                description=(
                    "The regulator, client or house rule set this item is tested "
                    "against, with its version and effective date."
                ),
                required=True,
            ),
            ConfigKey(
                key="blocking_clauses",
                description=(
                    "Which clauses stop an item outright, which are advisory, and "
                    "which named role clears each kind."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "items checked before they left the business",
            "flagged clauses carrying a citation and a suggested alternative",
            "items released against a flag that a human later reversed",
        ),
    ),
    Profile(
        name="content_moderation",
        summary=(
            "User-generated content screened against the community policy, with "
            "actions taken through the customer's own connected accounts."
        ),
        match=(
            "moderator",
            "moderation",
            "on-policy",
            "ugc",
            "forum",
            "comment section",
            "policy enforcement",
            "player content",
            "screened",
        ),
        steps=(
            step(
                "apply_policy_action",
                "Take the action the policy names, on the customer's own account",
                StepKind.ACT,
                (
                    "Take only the action the moderation policy attaches to the category "
                    "that fired -- hide, hold for review, warn, restrict, escalate -- and "
                    "take it through the customer's own connected community grant, never "
                    "from an account the platform owns. Snapshot the content before "
                    "acting and attach the clause and the appeal route to the entry: an "
                    "action without a snapshot cannot be reviewed, and anything the "
                    "policy does not name goes to the owner as a judgement call."
                ),
                produces=("action_log",),
            ),
        ),
        artifacts=(
            artifact(
                "action_log",
                "Moderation action log",
                (
                    "Every action taken with the policy clause behind it, the content "
                    "snapshot as it stood, the account it was taken from, the author "
                    "notified and the appeal route offered."
                ),
                "log",
            ),
        ),
        tools=("community_platform_client", "content_snapshot"),
        config_keys=(
            ConfigKey(
                key="moderation_policy",
                description=(
                    "Categories of content, the action each one takes, the strike "
                    "counts and the threshold at which a case goes to the owner."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="connected_accounts",
                description=(
                    "OAuth grants for the customer's own community surfaces. Every "
                    "moderation action is taken under one of these; the platform "
                    "never acts from an account it owns."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "policy actions carrying a clause and a snapshot",
            "actions overturned on appeal",
            "time from report to action on the community surface",
        ),
        channels=("community_platforms",),
    ),
    Profile(
        name="suggestion_queue",
        summary=(
            "Work prepared to the point of a single tap: the suggested action, "
            "its evidence and its alternatives, waiting on a human decision."
        ),
        match=(
            "approval queue",
            "approve/edit",
            "suggests codes",
            "code suggestions",
            "human coder",
            "classification queue",
            "suggested classification",
            "suggested match",
            "unclassified",
        ),
        steps=(
            step(
                "prepare_the_one_tap_decision",
                "Prepare the decision so it costs one tap",
                StepKind.DRAFT,
                (
                    "Put the suggested action in front of the reviewer already filled "
                    "in, with the history or reference set it was matched against, the "
                    "confidence behind it and the ranked alternatives beneath it, so the "
                    "decision is a tap rather than a research task. The suggestion is a "
                    "draft and stays one: nothing leaves this queue on your authority, "
                    "and an item the reviewer edits teaches the match for next time."
                ),
                produces=("decision_queue_item",),
            ),
        ),
        artifacts=(
            artifact(
                "decision_queue_item",
                "Prepared decision",
                (
                    "The drafted action with the evidence and source that produced it, "
                    "its confidence, the ranked alternatives, the reviewer's recorded "
                    "choice and any edit they made to it."
                ),
            ),
        ),
        tools=("suggestion_ranker", "history_matcher"),
        config_keys=(
            ConfigKey(
                key="suggestion_sources",
                description=(
                    "The history, code set, chart of accounts or reference data a "
                    "suggestion is matched against, and its version."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="queue_service_level",
                description=(
                    "How long an item may wait for a human tap, who is reminded when "
                    "it does not come, and what the item does meanwhile."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "suggestions accepted without an edit",
            "items waiting past the queue service level",
            "actions taken without a recorded human tap",
        ),
    ),
    Profile(
        name="alert_runbook_triage",
        summary=(
            "Technical alerts and tickets deduped, matched to a known runbook and "
            "either run to completion or routed with everything gathered."
        ),
        match=(
            "runbook",
            "ticket triage",
            "soc ",
            "phishing",
            "dedupe",
            "predictive-maintenance",
            "sensor alert",
            "work order",
            "ocpp",
            "uptime",
            "fault",
            "out of order",
            "tagged out",
            "service-desk",
        ),
        steps=(
            step(
                "run_the_known_runbook",
                "Run the runbook, or stop and route",
                StepKind.ACT,
                (
                    "Where the item matches a known condition exactly, execute that "
                    "runbook's fixed steps in order and record each one with what it "
                    "returned. Where it matches nothing, or where any step returns "
                    "something the runbook does not cover, stop there and route the item "
                    "with every observation attached. Where the fix needs hands or parts, "
                    "raise the work order with the asset, the fault code, the access "
                    "window and the parts it will need. A half-run runbook is routed, "
                    "never improvised past the point the runbook stops."
                ),
                produces=("runbook_run", "work_order_request"),
            ),
        ),
        artifacts=(
            artifact(
                "runbook_run",
                "Runbook run record",
                (
                    "The runbook matched, each step executed with its result and "
                    "timestamp, the point at which the run stopped and the reason it "
                    "stopped there."
                ),
                "log",
            ),
            artifact(
                "work_order_request",
                "Work order or dispatch request",
                (
                    "The drafted work order: asset, location, fault code, severity, "
                    "access window, parts required and the schedule slot it is asking "
                    "for."
                ),
            ),
        ),
        tools=("runbook_library", "asset_register", "work_order_system"),
        config_keys=(
            ConfigKey(
                key="runbook_library",
                description=(
                    "Known conditions that have a fixed runbook, the steps each one "
                    "runs and the signature that identifies a match."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="dispatch_thresholds",
                description=(
                    "Which fault codes and severities become a work order or a site "
                    "visit rather than a remote step, and the response window each "
                    "carries."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "items closed by runbook without reaching a person",
            "routed items arriving with full context attached",
            "repeat alerts on an asset already recorded as fixed",
        ),
    ),
    Profile(
        name="service_incident_bridge",
        summary=(
            "A customer-facing system down: fixed checks run and reported as "
            "observations, a temporary workaround issued, the fix tracked."
        ),
        match=(
            "diagnostics",
            "workaround",
            "sso",
            "deliverability",
            "spf",
            "blocklist",
            "sending paused",
            "integration breaks",
        ),
        steps=(
            step(
                "issue_the_workaround",
                "Run the fixed checks and get the customer working again",
                StepKind.ACT,
                (
                    "Run the check list the configuration names for this failure class "
                    "and record what each check returned -- reachable or not, record "
                    "present or absent, token valid or expired -- as observations with "
                    "their timestamps, not as a verdict about the cause. Apply the "
                    "protective step the policy allows where one is named, issue the "
                    "temporary workaround the customer may use meanwhile, tell them "
                    "plainly that it is temporary, and hold the item open against the "
                    "permanent fix and the commercial risk the outage created."
                ),
                produces=("diagnostic_record", "workaround_notice"),
            ),
        ),
        artifacts=(
            artifact(
                "diagnostic_record",
                "Check results record",
                (
                    "Each configured check with what it returned and when, the "
                    "protective step applied if any, and the observations passed to "
                    "whoever owns the permanent fix."
                ),
                "log",
            ),
            artifact(
                "workaround_notice",
                "Workaround notice",
                (
                    "What the customer can do meanwhile, what it does not cover, how "
                    "long it stands, and the renewal, contract or reputation risk the "
                    "outage has been flagged against."
                ),
                "message",
            ),
        ),
        tools=("diagnostic_probe", "status_page", "ticket_system"),
        config_keys=(
            ConfigKey(
                key="diagnostic_checks",
                description=(
                    "The fixed check list per failure class, what each check reads and "
                    "which result counts as an observation worth routing."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="workaround_policy",
                description=(
                    "Which temporary access, route or pause may be issued, for how "
                    "long, who is told and what must never be issued without a person."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "time from report to a workaround in the customer's hands",
            "items held open until the permanent fix landed",
            "commercial risk flagged at the time of the incident",
        ),
        channels=("customer_portal",),
    ),
    Profile(
        name="anomaly_exception_watch",
        summary=(
            "A number out of band against its baseline, sized and dated for the "
            "planner who owns the decision about it."
        ),
        match=(
            "anomal",
            "forecast",
            "bottleneck",
            "spike",
            "pickup",
            "address error",
            "exception agent",
        ),
        steps=(
            step(
                "compare_to_the_baseline",
                "Size the gap against the baseline",
                StepKind.ASSESS,
                (
                    "Set the current figure against the baseline the configuration names "
                    "-- the plan, the forecast, the same week last year, the trailing "
                    "band -- and state the direction and size of the gap, the window it "
                    "opened in and which inputs moved. Carry it forward: what this costs "
                    "or breaks if nothing changes is the sentence that makes a planner "
                    "act. You size the exception; the planner decides what to do about it."
                ),
                produces=("variance_report",),
            ),
        ),
        artifacts=(
            artifact(
                "variance_report",
                "Variance report",
                (
                    "The metric, its baseline and the band around it, the gap with its "
                    "direction and size, the window it opened in, the inputs that moved "
                    "and the downstream effect if nothing changes."
                ),
                "report",
            ),
        ),
        tools=("metric_store", "baseline_model"),
        config_keys=(
            ConfigKey(
                key="baseline_definition",
                description=(
                    "What each watched metric is compared against and how its normal "
                    "band is computed, per metric and per season."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="exception_thresholds",
                description=(
                    "The deviation at which a metric becomes an exception, and the "
                    "band above which it goes out immediately rather than in a digest."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "exceptions surfaced before the planner noticed them",
            "exceptions carrying a quantified downstream effect",
            "surfaced exceptions the planner marked as noise",
        ),
    ),
    Profile(
        name="disruption_cascade",
        summary=(
            "A broken commitment traced to every record downstream of it, with "
            "alternatives sourced and the affected told before they ask."
        ),
        match=(
            "cascade",
            "blast radius",
            "late delivery",
            "milestone",
            "delay",
            "rolled from sailing",
            "rebooking",
            "rebooked",
            "demurrage",
            "cold-chain",
            "alternative routing",
            "withdraws",
            "damaged",
            "86'd",
            "alternates",
            "downstream",
            "eta chain",
            "placements",
        ),
        steps=(
            step(
                "compute_the_blast_radius",
                "Trace everything downstream of the break",
                StepKind.ASSESS,
                (
                    "Follow the broken commitment through the dependency map to every "
                    "record that rests on it -- jobs, bookings, shipments, sessions, "
                    "students, containers, menus -- and list each one with the effect on "
                    "it and the penalty or cost clause it triggers. The list is computed "
                    "from the records rather than estimated: the affected party you miss "
                    "is the one who hears about it from somebody else."
                ),
                produces=("impact_list",),
            ),
            step(
                "source_the_alternative",
                "Re-plan against the approved alternatives",
                StepKind.ACT,
                (
                    "Work the approved alternates, substitutes and reroutes in the order "
                    "configuration ranks them, re-plan the affected records against what "
                    "is actually available, and hold the new dates and quantities against "
                    "the original so the difference stays visible. Where a switch needs "
                    "authority the unit does not hold, the re-plan is prepared as an "
                    "option with its cost beside it and the owner picks."
                ),
                produces=("replan_record",),
            ),
        ),
        artifacts=(
            artifact(
                "impact_list",
                "Impact list",
                (
                    "Every downstream record touched by the break, with the party it "
                    "belongs to, the effect on it, the value at risk and the penalty or "
                    "service clause it triggers."
                ),
                "report",
            ),
            artifact(
                "replan_record",
                "Re-plan and alternatives record",
                (
                    "The alternates worked with what each returned, the revised dates, "
                    "routes or quantities against the original, the cost difference and "
                    "the options left for the owner to pick between."
                ),
            ),
        ),
        tools=("dependency_map", "supplier_directory", "bulk_notifier"),
        config_keys=(
            ConfigKey(
                key="cascade_map",
                description=(
                    "Which records depend on which commitment, and how many hops "
                    "downstream the trace runs for this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="alternate_sources",
                description=(
                    "Approved alternates, substitutes and reroutes in preference "
                    "order, with the authority each one needs before it is used."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "affected parties told before they asked",
            "affected records re-planned in the same cycle as the break",
            "exposure quantified per affected record",
        ),
    ),
    Profile(
        name="stale_record_sweep",
        summary=(
            "Open records swept on their age rule so every one of them ends in a "
            "chase or a close-out, and none ages out unseen."
        ),
        match=(
            "stale",
            "hygiene",
            "ages out",
            "aged record",
            "unaccepted",
            "close-or-chase",
        ),
        steps=(
            step(
                "sweep_by_age",
                "Sweep the open records against their age rule",
                StepKind.ACT,
                (
                    "Run every open record against the age threshold for its type and "
                    "stage on the configured cycle, and give each aged record one of the "
                    "two endings the rule allows: a chase drafted to whoever owes the "
                    "next move, or a close-out proposed with its reason and its value. "
                    "Nothing ages out in silence -- a record that has had neither goes "
                    "onto the sweep report by name, with the day it was last touched."
                ),
                produces=("hygiene_report",),
            ),
        ),
        artifacts=(
            artifact(
                "hygiene_report",
                "Hygiene sweep report",
                (
                    "Every aged record with its type, age, owner, value, the day it was "
                    "last touched, the ending proposed for it and what actually happened "
                    "to it this cycle."
                ),
                "report",
            ),
        ),
        tools=("record_sweeper", "pipeline_lookup"),
        config_keys=(
            ConfigKey(
                key="age_thresholds",
                description=(
                    "The age at which each record type and stage becomes stale, and "
                    "the value band that changes the threshold."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="close_or_chase_policy",
                description=(
                    "Which stale records may be proposed for close-out, which must be "
                    "chased, how many chases run and who signs a close-out off."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "aged records given a chase or a close-out on the day they aged",
            "records still ageing past threshold at end of cycle",
            "value recovered from records the sweep re-opened",
        ),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: inbound items sorted, checked for completeness and handed to the
    # desk that owns them, with nothing left unrouted at the end of a cycle.
    Profile(
        name="queue_router",
        summary=(
            "Inbound items sorted, completeness-checked and handed to the desk "
            "that owns them, with nothing left sitting unrouted."
        ),
        match=(),
        steps=(
            step(
                "route_to_the_desk",
                "Hand the item to the desk that owns it",
                StepKind.ACT,
                (
                    "Match the item to the desk the routing table names for its type, "
                    "value band and market, attach the completeness check so the desk "
                    "can see what is missing before it opens anything, and hand it over "
                    "with its clock already running. An item that matches no desk goes "
                    "to the default desk and appears on the report as unrouted; it is "
                    "never held back while you work out where it belongs."
                ),
                produces=("desk_assignment",),
            ),
        ),
        artifacts=(
            artifact(
                "desk_assignment",
                "Desk assignment",
                (
                    "The desk chosen, the rule that chose it, the completeness check "
                    "with whatever is missing named, the clock started and any "
                    "subsequent reassignment with its reason."
                ),
            ),
        ),
        tools=("desk_directory", "completeness_checker"),
        config_keys=(
            ConfigKey(
                key="desk_directory",
                description=(
                    "Which desk, role or team owns each item type and value band, and "
                    "the default desk for anything unmatched."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="intake_completeness",
                description=(
                    "The fields and documents an item must carry before a desk will "
                    "accept it, per item type."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "items routed to the right desk first time",
            "items returned by a desk as misrouted",
            "items still unrouted at the end of a cycle",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class ExceptionQueueTriageEngine(Engine):
    """Carries every unit whose work is a queue read on somebody else's behalf.

    The engine holds one skeleton -- take the item in, collapse and enrich it,
    grade it against written rules, decide whether it surfaces, write the packet,
    place it and tell the recipient -- and eleven profiles that say what kind of
    queue it is.  Nothing in the code knows whether the item is a sanctions hit,
    a bottleneck or a stale quote; the sources, thresholds, severity bands and
    routing all arrive as configuration.
    """

    id: ClassVar[str] = "MF3"
    family: ClassVar[str] = "Exception-queue triage"
    what_it_does: ClassVar[str] = (
        "Watches a queue and surfaces only what needs a human"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.QUEUE_TRIAGE,
        Capability.WATCH_SIGNAL,
        Capability.SCORE,
        Capability.RECONCILE,
        Capability.RUN_PROTOCOL,
        Capability.DISPATCH,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "exception_queue",
        "signal_monitor",
        "dedupe_index",
        "enrichment_lookup",
        "triage_scorer",
        "routing_table",
        "message_sender",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "owner_dashboard",
        "email",
        "messaging",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "share of queue volume closed without reaching a person",
        "suppressed items a human later re-opened",
        "time from signal to the item being in front of the right person",
        "surfaced items breaching their response clock",
        "duplicate entries in the surfaced queue",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "exception_queue"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Observe, gather, assess, decide, draft, act, notify.

        The order is the discipline.  Duplicates collapse before anything is
        graded, so the same event cannot be counted three times; grading happens
        against written rules before the surface-or-suppress decision, so the
        decision cites a rule instead of an impression; and the recipient is told
        last, after the item is actually on the queue with an owner and a clock,
        so no alert ever points at something that is not there.
        """
        return (
            step(
                "take_the_item_in",
                "Read the queue",
                StepKind.OBSERVE,
                (
                    "Poll every configured source from its last position and take in "
                    "each new item with its raw signal, its source system and the time "
                    "it actually occurred rather than the time you saw it. An item you "
                    "read is an item you now own: nothing is skimmed past."
                ),
                produces=("queue_item",),
            ),
            step(
                "collapse_and_enrich",
                "Collapse duplicates and attach the context",
                StepKind.GATHER,
                (
                    "Join repeats onto one entry on the configured key and window, "
                    "keeping every occurrence and the count rather than discarding the "
                    "extras. Then attach what the recipient would otherwise go and fetch: "
                    "the record it concerns, the party behind it, the history of this "
                    "subject and what happened the last times this fired."
                ),
                produces=("evidence_pack", "queue_item"),
            ),
            step(
                "grade_against_the_rules",
                "Grade it against the written rules",
                StepKind.ASSESS,
                (
                    "Score the item against the triage rules and the severity matrix, "
                    "and record the rule id, the values it read and the band it produced. "
                    "A severity you cannot trace back to a named rule is a guess; guesses "
                    "are graded at the default band and never quietly downgraded."
                ),
                produces=("triage_grade",),
            ),
            step(
                "surface_or_hold_back",
                "Decide what a person actually needs to see",
                StepKind.DECIDE,
                (
                    "Hold an item back only where the suppression rules positively "
                    "permit it and the evidence they require is present, and log that "
                    "item with the rule that allowed it. Everything else surfaces, and "
                    "anything ambiguous surfaces: the queue's licence to filter rests "
                    "entirely on the held-back list being auditable."
                ),
                produces=("suppression_log",),
            ),
            step(
                "write_the_packet",
                "Write it so one read is enough",
                StepKind.DRAFT,
                (
                    "Compose the item for the person receiving it: what fired, why it "
                    "matters here, the evidence with its sources, the options open and "
                    "the single thing you are asking them to decide. Write what the "
                    "signal shows and stop there -- what it means about a person, a "
                    "cause or an intent is theirs to conclude, not yours to suggest."
                ),
                produces=("exception_brief",),
            ),
            step(
                "place_it_on_the_queue",
                "Place the item with an owner and a clock",
                StepKind.ACT,
                (
                    "Write the item to the queue with its grade, the desk the routing "
                    "table names for it, a named owner and the response clock its band "
                    "demands. An item on the queue without an owner and a clock is an "
                    "item nobody has agreed to look at."
                ),
                produces=("routing_record", "queue_item"),
            ),
            step(
                "tell_the_recipient",
                "Tell the person whose problem it is",
                StepKind.NOTIFY,
                (
                    "Send at the volume the severity band sets -- immediately to the "
                    "named contact, or in the digest -- using the out-of-hours contact "
                    "where the band demands one. When a cycle produces nothing that "
                    "needs a person, the digest says so explicitly: a quiet queue is a "
                    "finding, not an absence of one."
                ),
                produces=("queue_digest",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "queue_item",
                "Queue item",
                (
                    "The exception itself: source system, raw signal, first-seen and "
                    "occurred times, dedupe key, occurrence count, current state, owner "
                    "and response clock."
                ),
            ),
            artifact(
                "evidence_pack",
                "Evidence pack",
                (
                    "The context attached to the item so the recipient decides without "
                    "opening another system: the record it concerns, the party, the "
                    "history of this subject and prior items with their outcomes."
                ),
                "bundle",
            ),
            artifact(
                "triage_grade",
                "Triage grade",
                (
                    "The category and severity assigned, the rule id that produced "
                    "them, the values that rule read and the response clock the band "
                    "carries."
                ),
            ),
            artifact(
                "suppression_log",
                "Suppression log",
                (
                    "Every item held back from a person, with the suppression rule that "
                    "permitted it, the evidence that rule required and the sample later "
                    "re-tested against it."
                ),
                "log",
            ),
            artifact(
                "exception_brief",
                "Exception brief",
                (
                    "The surfaced item written for one read: what fired, why it matters, "
                    "the evidence with sources, the options and the single decision "
                    "being asked for."
                ),
                "document",
            ),
            artifact(
                "routing_record",
                "Routing record",
                (
                    "Where the item went and why: the desk, the rule that chose it, the "
                    "named owner, the time it was placed and every reassignment since."
                ),
            ),
            artifact(
                "queue_digest",
                "Queue digest",
                (
                    "The cycle's summary: what surfaced, what is still open against its "
                    "clock, what breached, what volume was held back and under which "
                    "rules -- including the cycle where nothing needed a person."
                ),
                "report",
            ),
            # Produced by the interlock step compose() prepends to every
            # safety-critical unit.  Declared here because three units of this
            # family are diamonds and an undeclared artefact fails the audit.
            artifact(
                "interlock_log",
                "Interlock log",
                (
                    "The fixed protocol steps executed on recognition, in order, each "
                    "with its timestamp and result, up to the point the unit stopped at "
                    "the human gate."
                ),
                "log",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"What counts as an exception in {vertical['name'].lower()}, how loud "
                f"each grade is and which desk receives it come from the vertical "
                f"overlay and the routing table -- read both rather than inferring "
                f"what is urgent here."
            )
        else:
            where = (
                "This queue runs across every vertical on the platform, so what counts "
                "as an exception, and how loud it is, is whatever the overlay in front "
                "of you supplies."
            )
        return (
            "HOW YOU WORK. You stand between a queue nobody has time to read and a "
            "person whose attention is the scarcest thing in the business, so your "
            "product is the short list -- and a defensible account of everything you "
            "kept off it. Take each item in, join the repeats onto one entry without "
            "losing a single occurrence, and attach the context the recipient would "
            "otherwise go and fetch: the record it concerns, the party behind it, what "
            "happened the last three times this fired. Grade it only against rules "
            "that were written down before the item arrived, and name the rule and the "
            "values that fired it, because a severity you cannot trace to a rule is a "
            "guess and a guess goes out at the default band rather than being quietly "
            "downgraded. Hold something back only where the suppression rules "
            "positively permit it, log it with the rule that allowed it, and surface "
            "anything ambiguous -- your licence to filter rests entirely on the "
            "held-back list being auditable. What surfaces goes out as a packet a "
            "person can act on in one read: what fired, the evidence, the options, the "
            "one decision you are asking for, an owner and a clock. You report what "
            "the signal shows and never what it means about a person, a cause or an "
            f"intent; the flag is yours and the conclusion is theirs. "
            f"{self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-NO-SILENT-SUPPRESSION",
                rule=(
                    "Nothing leaves the queue unseen without a rule that permitted "
                    "it. Filtering is licensed by the held-back list, not assumed."
                ),
                check=(
                    "Every item not surfaced has a suppression_log entry naming the "
                    "suppression_rules clause and the evidence it required; an item "
                    "with no matching clause is surfaced instead."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-GRADE-CITES-A-RULE",
                rule=(
                    "Every severity and category is produced by a named rule, not by "
                    "an impression of how serious the item looks."
                ),
                check=(
                    "triage_grade carries a rule id from triage_rules and the input "
                    "values it read; an item that matches no rule is graded at the "
                    "default band of severity_matrix and surfaced."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-FLAG-NOT-VERDICT",
                rule=(
                    "The unit states what fired and what the evidence shows. It never "
                    "states what that means about a person, a cause or an intent."
                ),
                check=(
                    "The outbound packet contains no conclusion, accusation or "
                    "root-cause statement, and its decision field is empty until the "
                    "named human fills it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-DEDUPE-KEEPS-THE-COUNT",
                rule=(
                    "Collapsing duplicates joins occurrences to one entry; it never "
                    "discards them to make the queue look shorter."
                ),
                check=(
                    "Each merged entry retains every source event and its occurrence "
                    "count, and the merge key and window are the ones dedupe_window "
                    "configures."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-OWNER-AND-CLOCK",
                rule=(
                    "Every surfaced item carries a named owner and a response clock, "
                    "and an item that ages past its clock escalates rather than sits."
                ),
                check=(
                    "No item is placed without an owner and a clock from "
                    "severity_matrix; breaches appear in queue_digest and re-route to "
                    "the escalation contact."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CONTROL-NOT-LIFTED",
                rule=(
                    "A hold, block, freeze or pause the unit applied is lifted by the "
                    "named human. The unit applies the prescribed control and stops."
                ),
                check=(
                    "control_record shows the clause that required each control and "
                    "the role that may lift it; no plan step releases a control the "
                    "unit itself applied."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-FILTER-MEASURED",
                rule=(
                    "Noise reduction is measured rather than assumed: what the queue "
                    "held back is sampled against what humans later re-opened."
                ),
                check=(
                    "Each cycle re-tests a sample of suppressed items against reopened "
                    "and escalated ones, and reports the miss rate in queue_digest."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "The live queue and everything already open on it, with its clocks",
            "Watched signal sources and the last position read from each",
            "Triage rules, severity bands and suppression rules in force, with versions",
            "History of this subject: prior items, prior outcomes, prior suppressions",
            "Routing table, named owners and who is on call out of hours",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming what kind of queue this profile is reading.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer can override.
        """
        return _PROFILE_MISSION_LINES.get(profile.name, _PROFILE_MISSION_LINES["queue_router"])


#: Mission prose per profile.  Each names the queue, the artefact that proves the
#: work and the exact point at which the unit stops and a person takes over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "conduct_risk_flag": (
        "This queue carries conduct and financial-crime signals: match the item to "
        "the typology that fired, apply only the control the policy already "
        "prescribes, assemble the referral packet with every signal, its source and "
        "the subject's history, and hand it to the named compliance role with the "
        "decision field empty -- you flag and you never conclude, and you never lift "
        "a control you put on."
    ),
    "legality_breach_watch": (
        "This queue is a statutory limit being approached: run the roster, the "
        "bookings and the hours already worked forward to the hour the limit would "
        "be crossed, name the limit and the people affected, and put the warning in "
        "front of the planner while the plan can still be changed."
    ),
    "policy_rule_check": (
        "This queue is items measured against a written rule book: test every clause, "
        "quote the wording that triggered each flag, cite the clause beside it, draft "
        "the compliant alternative, and route anything the rule book reserves for a "
        "licensed person to that person instead of answering it."
    ),
    "content_moderation": (
        "This queue is what other people posted: screen it against the community "
        "policy, take only the action the policy attaches to the category that fired, "
        "act through the customer's own connected accounts and never a platform "
        "account, and keep a snapshot and an appeal route against every action."
    ),
    "suggestion_queue": (
        "This queue is work prepared to the point of a single tap: put the suggested "
        "action in front of the reviewer already filled in, with its evidence and its "
        "ranked alternatives, and let nothing leave on your authority -- the tap is "
        "the decision and the edit is the correction you learn from."
    ),
    "alert_runbook_triage": (
        "This queue is technical alerts and tickets: dedupe and enrich before anyone "
        "sees them, run the runbook to the letter where the condition is known, raise "
        "the work order where the fix needs hands, and stop and route with everything "
        "gathered the moment the item stops matching a runbook."
    ),
    "service_incident_bridge": (
        "This queue is a customer-facing system down: run the fixed checks and report "
        "what each returned as an observation rather than a cause, get a temporary "
        "workaround into the customer's hands and say plainly that it is temporary, "
        "and hold the item open against the permanent fix and the commercial risk."
    ),
    "anomaly_exception_watch": (
        "This queue is numbers out of band: set the figure against the baseline "
        "configuration names, size and date the gap, say what it costs or breaks if "
        "nothing changes, and hand it to the planner whose call it is -- an exception "
        "without a quantified consequence gets ignored, and deserves to be."
    ),
    "disruption_cascade": (
        "This queue is a broken commitment: trace it through the dependency map to "
        "every record downstream, compute the impact and the exposure per record "
        "rather than estimating it, work the approved alternates in order, and tell "
        "the affected parties before they find out from somebody else."
    ),
    "stale_record_sweep": (
        "This queue is everything that has stopped moving: sweep the open records "
        "against their age rule every cycle and give each aged one a chase or a "
        "proposed close-out with its reason, so nothing ages out unseen and the "
        "report names whatever had neither."
    ),
    "queue_router": (
        "This queue is inbound work that belongs to somebody else: sort each item to "
        "the desk the routing table names, attach the completeness check so the desk "
        "sees what is missing before it opens anything, and send an unmatched item to "
        "the default desk marked unrouted rather than holding it while you decide."
    ),
}


__all__ = ["ExceptionQueueTriageEngine"]

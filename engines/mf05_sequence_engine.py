"""MF5 -- Sequence engine.

Fifty-four units that all do the same structural thing: something happens, and
then a *planned series of touches* runs over hours, days or months until the
subject converts, replies, opts out or the ladder is exhausted.  A quote that
was never answered, a basket left full, a cancellation that was just requested,
a donor who has not given in eighteen months, a supplier who missed a delivery
date, a patient three days out of theatre -- one mechanism, sixteen shapes.

What makes this family distinctive is not the sending.  It is the *stopping*.
Anything can fire a message on a timer; the discipline is knowing when a
sequence must not fire at all: because the person already replied, already
bought, already opted out, is already inside another journey, or is being
touched at two in the morning in their own timezone.  The base plan therefore
does not begin with a message.  It begins with enrolment, eligibility and a
committed touch plan whose exit conditions are written down *before* the first
touch goes out, and it ends with a named terminal outcome per subject.  A
journey that simply goes quiet has failed, however good the copy was.

Vertical difference lands almost entirely in configuration: how many touches,
how far apart, on which rail, in what tone, with what offer attached, and what
counts as an exit.  The cadence for a lapsed gym member and a lapsed donor are
the same three numbers with different values.

Three failure modes drive the guardrails below.  The first is the sequence that
keeps sending after the answer arrived -- the single fastest way to turn a warm
list cold.  The second is the invented incentive: a save offer, a discount or a
reward that no one approved, conjured because the contact hesitated.  The third
is the ladder that walks past its own threshold and suspends, restricts or
writes off on its own authority, when the last rung was always meant to be a
person.
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
# profile mission notes
# --------------------------------------------------------------------------- #

#: One sentence per profile, woven into the mission body.  Kept out of
#: :class:`Profile` because the dataclass is frozen and shared by all fourteen
#: engines; the discipline a shape demands is MF5's business, not the base's.
_PROFILE_NOTES: Mapping[str, str] = {
    "arrears_ladder": (
        "The ladder is a fixed, evidenced series of notices with a threshold at "
        "the end: you run every rung in order and stop there, because pausing a "
        "service, writing off a balance or starting a formal process is the "
        "owner's move and never yours"
    ),
    "no_response_ladder": (
        "Silence is the signal you are working: you widen the channel at each "
        "rung, evidence every attempt including the ones that reached nobody, "
        "and apply the documented closure rule at the end of the ladder rather "
        "than chasing somebody forever"
    ),
    "review_capture": (
        "You ask once, at the moment the work has actually landed and the "
        "feeling is real, and the score decides the route -- an unhappy answer "
        "goes privately to a person and never towards a public surface"
    ),
    "referral_and_reward": (
        "You ask only people who have already told you they are happy, you hand "
        "them a tracked link rather than a vague favour, and you issue a reward "
        "only against a conversion the ledger can evidence"
    ),
    "abandonment_recovery": (
        "You are working in minutes rather than days: pick the session up "
        "exactly where it stopped, offer the same thing back rather than making "
        "them start again, and take a reason when the answer is still no"
    ),
    "cancel_intercept": (
        "Somebody is leaving right now, so you slow the moment down -- hear the "
        "reason, offer only what the approved save ladder actually contains, and "
        "let them go cleanly and quickly when they mean it"
    ),
    "lapse_winback": (
        "These people already stopped, so you segment on recency, frequency and "
        "value before you write anything, touch each segment on its own cadence, "
        "and hold to one campaign window per contact"
    ),
    "broadcast_campaign": (
        "You send to a list the business owns, from the mailbox the business "
        "owns, and the whole send waits at the gate until a person releases it "
        "-- one careless broadcast costs more list than a year of careful ones "
        "builds"
    ),
    "cultivation_ladder": (
        "These are the few relationships worth a named cadence: you keep the "
        "history straight, time each ask to something that actually happened, "
        "and never let the ask outrun the relationship"
    ),
    "offer_to_decision": (
        "An open offer with no decision date decays, so you run a finite, dated "
        "ladder to a yes or a no and record which -- a no closed cleanly is a "
        "better outcome than a maybe left hanging"
    ),
    "onboarding_journey": (
        "The journey is a dated checklist that starts before day one and ends at "
        "the last checkpoint: every task carries an owner and a date, and a "
        "missed checkpoint escalates rather than quietly slips"
    ),
    "upsell_and_rebook": (
        "The window is short and it opens the instant the value lands, so you "
        "make one relevant offer priced from the published book and take the yes "
        "there and then rather than promising to follow up later"
    ),
    "checkin_cadence": (
        "The schedule comes from the protocol rather than from convenience: you "
        "ask what the protocol asks, log every answer including the silences, "
        "and route anything that reads as a red flag to the named person "
        "immediately"
    ),
    "proactive_update": (
        "You send on the cadence whether or not there is news, because the whole "
        "point is that nobody has to ring and ask -- when there is nothing to "
        "report you say so plainly instead of padding"
    ),
    "remediation_chase": (
        "You are chasing a counterparty against a dated commitment, so every "
        "chase names the outstanding item, the date it was due and the evidence "
        "that would close it"
    ),
    "multi_touch_sequence": (
        "You run the touches the configured cadence names, in order, each with "
        "its own stop condition, and you close the journey with a named outcome "
        "rather than letting it fade out"
    ),
}


def _record_text(record: Mapping[str, Any]) -> str:
    """Lowercased text of the workbook cells that describe a unit."""
    return " ".join(
        str(part or "").lower()
        for part in (
            record.get("worker"),
            record.get("system_agent"),
            record.get("trigger"),
            record.get("function"),
            record.get("expected_output"),
        )
    )


#: Language that means the ladder ends in an action nobody automated should
#: take on its own: suspension, restriction, write-off, formal process.
_THRESHOLD_MARKERS = (
    "threshold",
    "restriction",
    "suspension",
    "service-pause",
    "pause rule",
    "pause flag",
    "closure",
    "formal notice",
    "legal",
    "arrears",
    "collections",
    "dunning",
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class SequenceEngine(Engine):
    """Carries every MF5 unit: enrol a subject, run the touches, stop on time."""

    id: ClassVar[str] = "MF5"
    family: ClassVar[str] = "Sequence engine"
    what_it_does: ClassVar[str] = (
        "Multi-touch follow-up, save, reactivation and referral journeys"
    )

    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.SEQUENCE,
        Capability.CLOCK,
        Capability.CASE_STATE,
        Capability.CONVERSE,
        Capability.PUBLISH,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "journey_scheduler",
        "contact_record",
        "consent_register",
        "suppression_check",
        "message_composer",
        "outbound_channel",
        "outcome_attribution",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "email",
        "messaging",
        "voice",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "sequence_completion_rate",
        "reply_rate",
        "conversion_rate",
        "opt_out_rate",
        "attributed_revenue",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = (
        ConfigKey(
            key="sequence_cadence",
            description=(
                "The ladder for this journey type: how many touches, the interval "
                "between each, and the channel each one uses."
            ),
            resolved_by="vertical",
            required=True,
        ),
        ConfigKey(
            key="stop_conditions",
            description=(
                "What ends a journey early -- reply, conversion, opt-out, "
                "complaint, bereavement or vulnerability flag -- and which of "
                "them also suppress future journeys."
            ),
            resolved_by="owner",
            required=True,
        ),
        ConfigKey(
            key="frequency_caps",
            description=(
                "Maximum automated touches one contact may receive per window, "
                "counted across every journey rather than within this one."
            ),
            resolved_by="owner",
            required=True,
        ),
        ConfigKey(
            key="contactable_hours",
            description=(
                "Hours, days and dates on which an automated touch may be sent in "
                "this market, read in the recipient's own timezone."
            ),
            required=True,
        ),
        ConfigKey(
            key="consent_basis",
            description=(
                "The lawful basis and consent record this market requires before "
                "an outbound touch, per channel, with the opt-out wording."
            ),
            required=True,
        ),
        ConfigKey(
            key="suppression_list",
            description=(
                "Contacts no journey may touch, with the reason and the date the "
                "suppression was applied."
            ),
            resolved_by="owner",
            required=True,
        ),
        ConfigKey(
            key="offer_set",
            description=(
                "The incentives, discounts and rewards this journey may put in "
                "writing, with the value and expiry of each. The unit picks from "
                "this list and never composes a new one."
            ),
            resolved_by="owner",
            required=True,
        ),
    )
    state_object: ClassVar[str] = "journey_record"

    # -- profiles ----------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        """Sixteen shapes, ordered specific before general.

        Order does real work here, because MF5 vocabulary overlaps heavily.
        Almost every shape says "sequence", half of them say "retention", and
        three different mechanisms say "lapse".  Where two shapes share a word,
        the one whose mechanism actually runs the unit is listed first: the
        cancel intercept before the win-back, because "save/win-back agent" is a
        cancel desk; the cultivation ladder before the win-back, because
        "cultivation and lapse prevention" is a giving programme; the broadcast
        campaign before the decision close, because a "term-break retention
        campaigner" is a cohort send, not an enrolment ladder.
        """
        return (
            # Money owed.  First because a dunning ladder is a regulated,
            # evidenced sequence whose last rung is somebody else's decision, and
            # nothing about it may be softened by a friendlier profile matching
            # earlier.
            Profile(
                name="arrears_ladder",
                summary=(
                    "Money owed, chased on an evidenced ladder of notices that "
                    "stops at the threshold where a person decides."
                ),
                match=(
                    "dunning",
                    "arrears",
                    "collections",
                    "late payment",
                    "statutory-interest",
                    "interest letters",
                    "payment bounced",
                    "retry ladder",
                ),
                steps=(
                    step(
                        "aging_position",
                        "Establish the position and the rung",
                        StepKind.ASSESS,
                        "Read the balance, its age, what has already been sent and any "
                        "arrangement already in place, and identify which rung of the "
                        "ladder is next. The rung comes from the aging policy, not from "
                        "how the last conversation felt.",
                        produces=("ladder_position",),
                    ),
                    step(
                        "notice_draft",
                        "Draft the notice this rung requires",
                        StepKind.DRAFT,
                        "Use the notice wording the country pack prescribes for this rung, "
                        "with the balance, the period it covers, the payment routes "
                        "available in this market and any statutory interest or fee the "
                        "wording carries. Tone escalates with the rung; the figures never "
                        "move.",
                        produces=("notice_pack",),
                    ),
                    step(
                        "threshold_handover",
                        "Assemble the threshold pack and stop",
                        StepKind.GATE,
                        "Where the ladder reaches its final rung, assemble the pack -- the "
                        "full notice history, delivery evidence, every contact attempt and "
                        "the current balance -- and put it in front of the named person. "
                        "Pausing the service, restricting the account or starting a formal "
                        "process is their decision to take, and the journey stops here "
                        "until they take it.",
                        produces=("threshold_pack",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "ladder_position",
                        "Ladder position",
                        "Balance, age, rung reached, the notices already delivered and the "
                        "date the next rung falls due.",
                    ),
                    artifact(
                        "notice_pack",
                        "Notice pack",
                        "Each notice as issued, in the prescribed wording, with its "
                        "delivery evidence.",
                        fmt="document",
                    ),
                    artifact(
                        "threshold_pack",
                        "Threshold pack",
                        "Everything the person deciding at the threshold needs: history, "
                        "evidence, balance and the options open to them.",
                    ),
                ),
                tools=("ledger_lookup", "notice_templates", "payment_link"),
                config_keys=(
                    ConfigKey(
                        key="aging_ladder",
                        description=(
                            "Days past due at which each rung fires, and the wording, tone "
                            "and fee that rung carries."
                        ),
                        required=True,
                    ),
                    ConfigKey(
                        key="threshold_rule",
                        description=(
                            "The point at which the ladder stops and a person decides on "
                            "pause, restriction or formal process."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="arrangement_options",
                        description=(
                            "Payment arrangements that may be offered without a person, if "
                            "any, and the terms of each."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=("cure_rate", "days_to_cure", "ladder_evidence_completeness"),
            ),
            # Nobody is answering.  Distinct from every other shape because the
            # subject is not deciding slowly -- they are unreachable, and the
            # work is widening the channel and evidencing the attempt.
            Profile(
                name="no_response_ladder",
                summary=(
                    "A contact who has gone quiet or unreachable, traced across "
                    "channels on an evidenced ladder with a documented end."
                ),
                match=(
                    "no-show",
                    "non-response",
                    "unreachable",
                    "goes silent",
                    "bouncing",
                    "re-verification",
                    "access failure",
                    "trace ladder",
                    "pipeline advanced",
                ),
                steps=(
                    step(
                        "channel_trace",
                        "Widen the channel each rung",
                        StepKind.ACT,
                        "Work down the alternate contact routes the record holds -- second "
                        "number, alternate address, guardian, agent, registered contact -- "
                        "one rung at a time, and mark each route dead or alive as you go. "
                        "A bounced or dead route is a finding to record, not a step to "
                        "repeat.",
                        produces=("trace_log",),
                    ),
                    step(
                        "hold_state",
                        "Hold the underlying work in a stated position",
                        StepKind.ACT,
                        "Freeze the case, slot, claim or project in the position the policy "
                        "names while the trace runs -- release what can be released, state "
                        "what is being held and why, and keep the position visible to "
                        "whoever picks it up next.",
                        produces=("hold_position",),
                    ),
                    step(
                        "closure_rule",
                        "Apply the documented end of the ladder",
                        StepKind.GATE,
                        "When the ladder is exhausted, apply the documented rule for this "
                        "case type and put anything it does not cover -- closure, "
                        "restriction, write-off -- in front of the named person with the "
                        "full trace attached.",
                        produces=("closure_recommendation",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "trace_log",
                        "Trace log",
                        "Every route tried, the channel, the timestamp and whether it "
                        "reached anybody.",
                        fmt="log",
                    ),
                    artifact(
                        "hold_position",
                        "Hold position",
                        "What was released, what is being held, under which rule, and who "
                        "can lift it.",
                    ),
                    artifact(
                        "closure_recommendation",
                        "Closure recommendation",
                        "The rule the ladder ended on, the evidence behind it and the "
                        "decision being put to a person.",
                    ),
                ),
                tools=("contact_route_lookup", "address_verification", "case_state_write"),
                config_keys=(
                    ConfigKey(
                        key="trace_ladder",
                        description=(
                            "Contact routes to try, in order, with the wait between each "
                            "and the evidence each attempt must leave."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="closure_rules",
                        description=(
                            "What happens when the trace is exhausted, by case type, and "
                            "which outcomes need a person."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                ),
                kpis=("reconnect_rate", "routes_tried_per_case", "days_to_closure"),
                channels=("email", "messaging", "voice", "post"),
            ),
            # Ask for the review.  Early, because the score gate is the whole
            # mechanism and it must not be reached by a generic follow-up shape.
            Profile(
                name="review_capture",
                summary=(
                    "A timed post-completion ask, score-gated: happy answers to "
                    "the public surfaces, unhappy ones privately to a person."
                ),
                match=(
                    "review",
                    "testimonial",
                    "nps",
                    "promoter",
                    "detractor",
                    "ugc",
                ),
                steps=(
                    step(
                        "score_gate",
                        "Take the score before the ask",
                        StepKind.ASSESS,
                        "Ask the rating question first and read the answer against the "
                        "configured gate. The gate decides the route; you never ask for a "
                        "public review from somebody who has not yet said they were happy.",
                        produces=("feedback_score",),
                    ),
                    step(
                        "route_by_score",
                        "Send the happy out and the unhappy in",
                        StepKind.DECIDE,
                        "Above the gate, offer the public surfaces the country pack names "
                        "for this market with a direct link. Below it, open a private "
                        "recovery case for the named owner and send no public request at "
                        "all -- the recovery is worth more than the star would have been.",
                        produces=("review_request",),
                    ),
                    step(
                        "harvest_content",
                        "Collect what came back and place it",
                        StepKind.ACT,
                        "Collect the reviews, ratings, photos and written testimonials that "
                        "arrived, record the consent that came with each, and pass those "
                        "cleared for reuse to the site or profile that displays them.",
                        produces=("collected_feedback",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "feedback_score",
                        "Feedback score",
                        "The score as given, the question that produced it and the gate it "
                        "fell on.",
                    ),
                    artifact(
                        "review_request",
                        "Review request",
                        "Who was asked, when, on which surface, and what the timing was "
                        "measured from.",
                    ),
                    artifact(
                        "collected_feedback",
                        "Collected feedback",
                        "Reviews, ratings, testimonials and media received, each with its "
                        "source, date and consent state.",
                    ),
                ),
                tools=("review_surface_links", "consent_capture", "recovery_case_open"),
                config_keys=(
                    ConfigKey(
                        key="review_surfaces",
                        description=(
                            "The review and rating surfaces that matter in this market, in "
                            "priority order."
                        ),
                        required=True,
                    ),
                    ConfigKey(
                        key="score_gate",
                        description=(
                            "The score at or above which a public ask is offered, and the "
                            "route below it."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="ask_timing",
                        description=(
                            "How long after completion the ask goes out, by service type."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                ),
                kpis=("review_yield_rate", "public_ask_precision", "detractor_recovery_rate"),
            ),
            # Referral and reward: an ask with a tracked link on one side and a
            # ledger on the other.  The ledger is what stops rewards leaking.
            Profile(
                name="referral_and_reward",
                summary=(
                    "A post-satisfaction referral ask with tracked links, and a "
                    "two-sided reward ledger that pays only against evidence."
                ),
                match=("referral", "reward", "ambassador"),
                steps=(
                    step(
                        "advocate_check",
                        "Confirm they are actually happy first",
                        StepKind.ASSESS,
                        "Check the satisfaction signal -- a score, a completed job, a "
                        "positive reply -- before any ask goes out. An ask sent to somebody "
                        "with an open complaint costs the relationship and the referral.",
                    ),
                    step(
                        "issue_link",
                        "Issue the tracked link",
                        StepKind.ACT,
                        "Generate a link tied to this advocate and this offer, put it in "
                        "front of them with the reward stated plainly on both sides, and "
                        "record which link went to whom.",
                        produces=("referral_link",),
                    ),
                    step(
                        "reconcile_rewards",
                        "Reconcile conversions and issue what was earned",
                        StepKind.ACT,
                        "Match arrivals back to the link that sent them, hold each against "
                        "the qualifying rule, and issue the reward the offer set names once "
                        "the conversion is evidenced. An unevidenced conversion is a "
                        "question for a person, not a payout.",
                        produces=("reward_ledger",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "referral_link",
                        "Tracked referral link",
                        "The link issued, the advocate it belongs to, the offer attached "
                        "and its expiry.",
                    ),
                    artifact(
                        "reward_ledger",
                        "Two-sided reward ledger",
                        "Referrals made, arrivals matched, conversions evidenced, rewards "
                        "issued and redeemed, with revenue attributed to each.",
                    ),
                ),
                tools=("link_tracker", "reward_ledger_write", "partner_directory"),
                config_keys=(
                    ConfigKey(
                        key="referral_offer",
                        description=(
                            "What each side receives, when it vests and how long the offer "
                            "stands."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="qualifying_conversion",
                        description=(
                            "What counts as a converted referral -- enquiry, booking, "
                            "completed job, paid invoice."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="attribution_window",
                        description=(
                            "How long after a click or introduction an outcome still counts "
                            "as referred."
                        ),
                        resolved_by="owner",
                    ),
                ),
                kpis=("referral_ask_rate", "referral_conversion_rate", "reward_leakage_rate"),
            ),
            # Something was left half-finished in the last few minutes.  Its own
            # shape because the clock is minutes and the right message is the
            # thing they already had, handed straight back.
            Profile(
                name="abandonment_recovery",
                summary=(
                    "An in-flight session, basket or half-finished booking picked "
                    "up where it stopped, in minutes rather than days."
                ),
                match=(
                    "abandonment",
                    "cart",
                    "basket",
                    "incomplete booking",
                    "exit-intent saves",
                ),
                steps=(
                    step(
                        "capture_state",
                        "Capture exactly what was left behind",
                        StepKind.GATHER,
                        "Snapshot the session as it stood: the items, the slot, the form "
                        "fields already filled, the step it stopped on and the last thing "
                        "the person looked at.",
                        produces=("abandoned_state",),
                    ),
                    step(
                        "resume_offer",
                        "Hand the same thing straight back",
                        StepKind.ACT,
                        "Send a resume link that reopens the session exactly as it was, "
                        "inside the recovery window, with the price and availability "
                        "re-checked rather than assumed. Do not make somebody start again "
                        "to buy what they had already chosen.",
                        produces=("recovered_session",),
                    ),
                    step(
                        "capture_reason",
                        "Take the reason when the answer is still no",
                        StepKind.GATHER,
                        "Where the session is not resumed, ask one short question about why "
                        "and record the answer against the reason codes. A captured reason "
                        "is the second-best outcome and the only one that improves the "
                        "funnel.",
                        produces=("abandon_reason",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "abandoned_state",
                        "Abandoned session state",
                        "Items, slot, fields, step reached and timestamp at the moment it "
                        "stopped.",
                    ),
                    artifact(
                        "recovered_session",
                        "Recovered session",
                        "The resume link issued, whether it was used, and what was booked "
                        "or bought as a result.",
                    ),
                    artifact(
                        "abandon_reason",
                        "Reason for leaving",
                        "The stated reason against the configured reason codes, with the "
                        "step it was abandoned on.",
                    ),
                ),
                tools=("session_snapshot", "resume_link", "inventory_lookup"),
                config_keys=(
                    ConfigKey(
                        key="recovery_window",
                        description=(
                            "How soon after abandonment the first touch fires, and how long "
                            "the resume link stays valid."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="reason_codes",
                        description="The reason codes an abandoned session is coded against.",
                        resolved_by="vertical",
                    ),
                ),
                kpis=("recovery_rate", "minutes_to_first_touch", "reason_capture_rate"),
            ),
            # Somebody is leaving now.  Ahead of win-back because "save /
            # win-back agent" and "retention agent" are cancel desks, and the
            # save ladder is a very different object from a reactivation cadence.
            Profile(
                name="cancel_intercept",
                summary=(
                    "An active cancellation or defection risk, intercepted with "
                    "the approved save ladder and a clean exit if they mean it."
                ),
                match=(
                    "cancel",
                    "save sequence",
                    "saves desk",
                    "save/win-back",
                    "at-risk",
                    "solicits",
                    "offboarding",
                ),
                steps=(
                    step(
                        "leaving_reason",
                        "Hear the reason before offering anything",
                        StepKind.GATHER,
                        "Ask why, in one question, and code the answer. Price, service, "
                        "moving away and no-longer-needed are four different conversations, "
                        "and three of them cannot be fixed with a discount.",
                        produces=("churn_reason",),
                    ),
                    step(
                        "save_offer",
                        "Offer only what the ladder holds",
                        StepKind.DRAFT,
                        "Pick the save offer the ladder assigns to this reason and this "
                        "value band and put it in writing with its terms and expiry. "
                        "Anything beyond the ladder goes to the named person as a request, "
                        "never out of the door as an improvisation.",
                        produces=("save_offer",),
                    ),
                    step(
                        "clean_exit",
                        "Let them go properly when they mean it",
                        StepKind.ACT,
                        "Where the answer is still no, complete the exit the policy "
                        "describes -- final dates, balances, returns, data -- take the "
                        "offboarding feedback, and schedule the win-back for the interval "
                        "the cadence names. A leaver held up at the door does not come back.",
                        produces=("exit_record",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "churn_reason",
                        "Reason for leaving",
                        "The stated reason coded against the churn reason set, with the "
                        "value band and tenure of the account.",
                    ),
                    artifact(
                        "save_offer",
                        "Save offer",
                        "The offer made, the rung of the ladder it came from, its terms and "
                        "expiry, and whether it was taken.",
                    ),
                    artifact(
                        "exit_record",
                        "Exit record",
                        "Final dates, balances, what was returned or closed, the "
                        "offboarding answers and the win-back date scheduled.",
                    ),
                ),
                tools=("subscription_state", "offer_ladder_lookup", "case_state_write"),
                config_keys=(
                    ConfigKey(
                        key="save_ladder",
                        description=(
                            "Which save offer may be made for which churn reason and value "
                            "band, and the rung above which a person decides."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="churn_reason_set",
                        description="The reason codes a cancellation is coded against.",
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="exit_policy",
                        description=(
                            "Notice periods, final billing, returns and data handling on "
                            "exit in this market."
                        ),
                        required=True,
                    ),
                ),
                kpis=("save_rate", "save_offer_cost", "exit_completion_rate"),
            ),
            # Ahead of win-back: "cultivation and lapse prevention" is a giving
            # programme, not a reactivation campaign, and the two ask in very
            # different registers.
            Profile(
                name="cultivation_ladder",
                summary=(
                    "The few high-value or high-affinity relationships worth a "
                    "named cadence: cultivated, tracked and asked in proportion."
                ),
                match=(
                    "cultivat",
                    "giving",
                    "donor",
                    "alumni",
                    "vip",
                    "superfan",
                    "fan crm",
                    "fan-club",
                    "high-value player",
                ),
                steps=(
                    step(
                        "identify_cohort",
                        "Identify who belongs in the cohort",
                        StepKind.ASSESS,
                        "Score the base on the configured signals -- lifetime value, "
                        "frequency, recency, engagement, affiliation -- and keep the reason "
                        "each person entered or left the cohort. Membership is earned by "
                        "the signal, not by who is memorable.",
                        produces=("cohort_list",),
                    ),
                    step(
                        "relationship_ladder",
                        "Time the ask to something that happened",
                        StepKind.DRAFT,
                        "Draft each touch against the relationship history: what they last "
                        "gave, played, attended or bought, what it funded or produced, and "
                        "what is being asked now. Thanks and news come between asks, not "
                        "after the ask has already worn the relationship out.",
                        produces=("cultivation_plan",),
                    ),
                    step(
                        "steward_outcome",
                        "Acknowledge, then record what it was worth",
                        StepKind.ACT,
                        "Acknowledge every response inside the configured window, record the "
                        "value and the touch it followed, and hand anything above the "
                        "personal-attention threshold to the named person rather than "
                        "answering it with a template.",
                        produces=("stewardship_log",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "cohort_list",
                        "Cohort list",
                        "Who is in the cohort, the signals that placed them there and the "
                        "date they entered or left it.",
                    ),
                    artifact(
                        "cultivation_plan",
                        "Cultivation plan",
                        "The touch ladder per person: what is sent, when, and what it "
                        "references from the relationship history.",
                    ),
                    artifact(
                        "stewardship_log",
                        "Stewardship log",
                        "Every response, acknowledgement, gift or renewal with its value "
                        "and the touch it followed.",
                        fmt="log",
                    ),
                ),
                tools=("segment_builder", "relationship_history", "value_ledger"),
                config_keys=(
                    ConfigKey(
                        key="cohort_criteria",
                        description=(
                            "Signals and thresholds that place somebody in the cultivated "
                            "cohort, and what removes them."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="ask_ladder",
                        description=(
                            "How often an ask may be made, at what level, and how many "
                            "non-ask touches sit between them."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="personal_attention_threshold",
                        description=(
                            "The value above which a named person, not a journey, holds the "
                            "relationship."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=("cohort_retention_rate", "ask_response_rate", "value_per_member"),
            ),
            # People who already stopped.  Segmentation is the mechanism: the
            # cadence and the offer both follow from recency, frequency, value.
            Profile(
                name="lapse_winback",
                summary=(
                    "Lapsed, dormant and about-to-lapse contacts segmented on "
                    "recency, frequency and value, then reactivated on cadence."
                ),
                match=(
                    "win-back",
                    "winback",
                    "reactivat",
                    "lapsed",
                    "lapse",
                    "rfm",
                    "renewal",
                    "dormant",
                ),
                steps=(
                    step(
                        "segment_base",
                        "Segment before writing anything",
                        StepKind.ASSESS,
                        "Split the base on recency, frequency and value and size each "
                        "segment. A single message to everybody who ever stopped is not a "
                        "campaign; it is a list being spent.",
                        produces=("segment_set",),
                    ),
                    step(
                        "segment_offer",
                        "Match the cadence and the offer to the segment",
                        StepKind.DRAFT,
                        "Give each segment the touch count, interval and offer the "
                        "configuration assigns it, referencing what they last had rather "
                        "than a generic welcome-back. Every figure comes from the published "
                        "price book or the approved offer set.",
                        produces=("winback_campaign",),
                    ),
                    step(
                        "reactivation_report",
                        "Report who came back and what they were worth",
                        StepKind.NOTIFY,
                        "Report the reactivated list by segment with the revenue attributed "
                        "inside the attribution window, and the segments that did not "
                        "respond, so the next run starts from evidence.",
                        produces=("reactivation_report",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "segment_set",
                        "Segment set",
                        "Each segment with its rule, its size and the cadence and offer "
                        "assigned to it.",
                    ),
                    artifact(
                        "winback_campaign",
                        "Win-back campaign",
                        "The touches issued per segment, with the offer attached to each "
                        "and its expiry.",
                    ),
                    artifact(
                        "reactivation_report",
                        "Reactivation report",
                        "Who returned, from which segment, after which touch, and the "
                        "revenue attributed to each.",
                    ),
                ),
                tools=("segment_builder", "transaction_history", "outcome_attribution"),
                config_keys=(
                    ConfigKey(
                        key="lapse_definition",
                        description=(
                            "How long without activity counts as lapsed for this trade, and "
                            "how far ahead of a renewal date the pre-lapse touch fires."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="segment_model",
                        description=(
                            "Recency, frequency and value bands, and the cadence and offer "
                            "each band receives."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="attribution_window",
                        description=(
                            "How long after a touch a return still counts as reactivated by "
                            "this journey."
                        ),
                        resolved_by="owner",
                    ),
                ),
                kpis=("reactivation_rate", "revenue_per_reactivation", "segment_coverage"),
            ),
            # A send to a list rather than a journey per person.  Its own shape
            # because the owned-channel rule and the approval gate bite hardest
            # here: one bad broadcast burns the asset the business owns.
            Profile(
                name="broadcast_campaign",
                summary=(
                    "A cohort or seasonal campaign to the business's own list, "
                    "sent from the business's own mailbox after approval."
                ),
                match=(
                    "campaign agent",
                    "campaigner",
                    "email marketer",
                    "seasonal",
                    "owned list",
                    "mailbox",
                ),
                steps=(
                    step(
                        "list_hygiene",
                        "Build the audience and clean it",
                        StepKind.ASSESS,
                        "Build the audience from the owned list, remove suppressions, "
                        "opt-outs, bounces and anybody already inside another journey this "
                        "window, and state the audience size before anything is drafted.",
                        produces=("audience_list",),
                    ),
                    step(
                        "campaign_draft",
                        "Draft the campaign against the calendar",
                        StepKind.DRAFT,
                        "Draft subject, body and offer against the seasonal calendar in the "
                        "active country pack, with every figure taken from the published "
                        "price book and the opt-out wording this market requires.",
                        produces=("campaign_draft",),
                    ),
                    step(
                        "release_gate",
                        "Hold the whole send at the gate",
                        StepKind.GATE,
                        "Put the draft, the audience count and the offer in front of the "
                        "owner and wait. Nothing leaves until a person has released it, and "
                        "it leaves from the mailbox in the customer's own grant.",
                    ),
                    step(
                        "campaign_report",
                        "Report what the send actually did",
                        StepKind.NOTIFY,
                        "Report deliveries, opens, replies, opt-outs and the bookings or "
                        "orders attributed inside the window, so the next campaign is "
                        "chosen on evidence rather than on habit.",
                        produces=("campaign_report",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "audience_list",
                        "Audience list",
                        "The segment sent to, its size, and every exclusion applied with "
                        "the reason.",
                    ),
                    artifact(
                        "campaign_draft",
                        "Campaign draft",
                        "Subject, body, offer and opt-out wording as put to the owner for "
                        "release.",
                        fmt="document",
                    ),
                    artifact(
                        "campaign_report",
                        "Campaign report",
                        "Deliveries, opens, replies, opt-outs and attributed bookings or "
                        "orders for this send.",
                    ),
                ),
                tools=("list_builder", "campaign_composer", "approval_queue"),
                config_keys=(
                    ConfigKey(
                        key="seasonal_calendar",
                        description=(
                            "Dates and seasons that carry commercial weight in this market, "
                            "from the active country pack."
                        ),
                        required=True,
                    ),
                    ConfigKey(
                        key="campaign_approval",
                        description=(
                            "Who releases a send, and the audience size above which a "
                            "second pair of eyes is required."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="send_limits",
                        description=(
                            "Maximum campaign sends per contact per period, and the minimum "
                            "gap between campaigns."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                ),
                kpis=("delivery_rate", "open_rate", "unsubscribe_rate", "campaign_attributed_revenue"),
                channels=("email", "messaging"),
            ),
            # An open offer being walked to a dated decision.  Ahead of the
            # generic shapes because "closer", "taster" and "melt" all describe
            # the same finite ladder ending in a recorded yes or no.
            Profile(
                name="offer_to_decision",
                summary=(
                    "An open quote, trial or place walked to a dated decision "
                    "point and closed as a yes or a recorded no."
                ),
                match=(
                    "unaccepted",
                    "cold enquir",
                    "trial-to",
                    "taster",
                    "decision point",
                    "closer",
                    "melt",
                    "yield",
                    "enrol",
                    "enroll",
                ),
                steps=(
                    step(
                        "open_offer",
                        "Read the offer as it stands",
                        StepKind.GATHER,
                        "Pull the open quote, trial or place: what was offered, on what "
                        "terms, when it expires and what the person has already asked. The "
                        "next touch answers their last question, not a generic script.",
                        produces=("open_offer",),
                    ),
                    step(
                        "objection_pass",
                        "Answer the objection the touch surfaced",
                        StepKind.DRAFT,
                        "Where a reason for hesitating comes back, answer it from the "
                        "published terms, price book and the vertical's own proof, and "
                        "record the objection so the pattern is visible. What you cannot "
                        "answer from a source goes to a person with the thread attached.",
                        produces=("objection_log",),
                    ),
                    step(
                        "decision_close",
                        "Close it as a yes or a no by the date",
                        StepKind.DECIDE,
                        "On the decision date, record the outcome plainly -- accepted, "
                        "declined with a reason, or lapsed -- and where it is a yes, put the "
                        "next concrete step in place: the booking, the enrolment, the signed "
                        "agreement. An offer left open past its date is closed as lapsed, "
                        "not chased again.",
                        produces=("decision_record",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "open_offer",
                        "Open offer",
                        "What was offered, its terms, its expiry and the state it is in "
                        "today.",
                    ),
                    artifact(
                        "objection_log",
                        "Objection log",
                        "Every reason for hesitating, the answer given and the source it "
                        "came from.",
                        fmt="log",
                    ),
                    artifact(
                        "decision_record",
                        "Decision record",
                        "Accepted, declined or lapsed, the date, the reason and the next "
                        "step put in place.",
                    ),
                ),
                tools=("quote_lookup", "enrolment_write", "calendar_write"),
                config_keys=(
                    ConfigKey(
                        key="decision_deadline",
                        description=(
                            "How long an offer or trial stands before the decision point, "
                            "by offer type."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="objection_library",
                        description=(
                            "Sourced answers to the common objections in this trade, with "
                            "the document each is drawn from."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="touch_count",
                        description=(
                            "How many touches this ladder runs before it closes as lapsed."
                        ),
                        resolved_by="owner",
                        default=4,
                    ),
                ),
                kpis=("close_rate", "touches_to_decision", "open_offer_ageing"),
            ),
            # A dated checklist across other people's systems, starting before
            # day one.  The journey is the timeline; the tasks have owners.
            Profile(
                name="onboarding_journey",
                summary=(
                    "A dated onboarding timeline -- before day one to the last "
                    "checkpoint -- with an owner and a due date on every task."
                ),
                match=(
                    "onboarding",
                    "new hire",
                    "day one",
                    "activation milestone",
                    "day-30",
                    "day-90",
                    "day minus",
                ),
                steps=(
                    step(
                        "timeline_build",
                        "Lay the timeline out from the start date",
                        StepKind.DECIDE,
                        "Anchor every task to the start date -- the ones that must land "
                        "before it and the checkpoints that follow it -- and give each an "
                        "owner, a due date and a definition of done.",
                        produces=("onboarding_timeline",),
                    ),
                    step(
                        "task_chase",
                        "Chase each task to done",
                        StepKind.ACT,
                        "Raise each task with its owner ahead of its due date, chase what is "
                        "outstanding, and record what is complete against the evidence that "
                        "proves it -- the contract returned, the access granted, the kit "
                        "ordered, the training assigned.",
                        produces=("task_state",),
                    ),
                    step(
                        "checkpoint_review",
                        "Run the checkpoints and escalate the misses",
                        StepKind.NOTIFY,
                        "Run each checkpoint on its date, record the answers, and escalate "
                        "anything still outstanding to the named owner. A missed checkpoint "
                        "is raised, never rolled forward quietly.",
                        produces=("checkpoint_log",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "onboarding_timeline",
                        "Onboarding timeline",
                        "Every task anchored to the start date, with owner, due date and "
                        "definition of done.",
                    ),
                    artifact(
                        "task_state",
                        "Task state",
                        "Each task with its state, its evidence and who completed it.",
                    ),
                    artifact(
                        "checkpoint_log",
                        "Checkpoint log",
                        "Each checkpoint, when it ran, what came back and what was "
                        "escalated.",
                        fmt="log",
                    ),
                ),
                tools=("task_tracker", "access_request", "training_assignment"),
                config_keys=(
                    ConfigKey(
                        key="onboarding_plan",
                        description=(
                            "Tasks and checkpoints by role or account type, with the offset "
                            "from the start date for each."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="task_owners",
                        description="Which role owns each onboarding task, with a fallback.",
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="activation_milestones",
                        description=(
                            "What counts as activated for this account type, and by when."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                ),
                kpis=("day_one_readiness", "milestone_hit_rate", "checkpoint_completion_rate"),
            ),
            # The moment right after the value landed.  Short window, one offer,
            # priced from the book.  Ahead of the check-in shape because a hotel
            # upsell mentions check-in and is not a check-in at all.
            Profile(
                name="upsell_and_rebook",
                summary=(
                    "The moment after the value lands: one relevant add-on, "
                    "package or next booking, taken there and then."
                ),
                match=(
                    "upsell",
                    "up-sell",
                    "add-on",
                    "rebook",
                    "next appointment",
                    "membership",
                    "package",
                    "bundle",
                ),
                steps=(
                    step(
                        "offer_fit",
                        "Pick the one offer that actually fits",
                        StepKind.ASSESS,
                        "Read what they just had, what the record says they use and what "
                        "the eligibility rules allow, and pick the single most relevant "
                        "add-on, package or interval. A list of five offers converts worse "
                        "than the right one.",
                        produces=("offer_selection",),
                    ),
                    step(
                        "present_offer",
                        "Put it in front of them at the moment",
                        StepKind.ACT,
                        "Present the offer inside the window the configuration names -- at "
                        "checkout, at delivery, at the end of the visit -- priced from the "
                        "published price book, with what it includes stated plainly.",
                        produces=("offer_made",),
                    ),
                    step(
                        "take_the_yes",
                        "Take the yes while it is a yes",
                        StepKind.ACT,
                        "Where the answer is yes, complete it on the spot: hold the slot, "
                        "add the line, start the plan, take the deposit the policy requires. "
                        "Record the uptake and the value either way.",
                        produces=("uptake_record",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "offer_selection",
                        "Offer selection",
                        "The offer chosen, the signals that chose it and the eligibility "
                        "rule that allowed it.",
                    ),
                    artifact(
                        "offer_made",
                        "Offer made",
                        "What was offered, when, at what price and from which price-book "
                        "row.",
                    ),
                    artifact(
                        "uptake_record",
                        "Uptake record",
                        "Accepted or declined, the value taken, and the booking, package or "
                        "balance created.",
                    ),
                ),
                tools=("catalogue_lookup", "price_book_lookup", "calendar_write", "payment_link"),
                config_keys=(
                    ConfigKey(
                        key="upsell_matrix",
                        description=(
                            "Which add-on, package or interval follows which service, and "
                            "who is eligible for it."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="offer_window",
                        description=(
                            "When the offer may be made relative to the service, and how "
                            "long it stands."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="rebook_intervals",
                        description=(
                            "The standard interval to the next visit or service, by service "
                            "type."
                        ),
                        resolved_by="vertical",
                    ),
                ),
                kpis=("attach_rate", "rebook_rate", "revenue_per_visit"),
            ),
            # Scheduled check-ins that expect an answer, run to a protocol.  The
            # red flag is the reason this shape exists: an answer that reads
            # badly must reach a person the same day, not the weekly report.
            Profile(
                name="checkin_cadence",
                summary=(
                    "Protocol-timed check-ins after a service, treatment or "
                    "milestone, with every answer logged and red flags routed."
                ),
                match=(
                    "check-ins",
                    "check-in agent",
                    "aftercare",
                    "post-op",
                    "discharge",
                    "pastoral",
                    "member care",
                    "follow-ups sequenced",
                    "completion",
                    "nudg",
                    "recovery check",
                ),
                steps=(
                    step(
                        "protocol_schedule",
                        "Take the schedule from the protocol",
                        StepKind.ASSESS,
                        "Read the protocol for this treatment, course or programme and "
                        "schedule each check-in at the interval it names. The interval is "
                        "clinical, pastoral or pedagogical configuration; it is never "
                        "adjusted for convenience.",
                        produces=("checkin_schedule",),
                    ),
                    step(
                        "ask_protocol_questions",
                        "Ask what the protocol asks",
                        StepKind.GATHER,
                        "Put the protocol's own questions, in the contact's language, and "
                        "record the answers verbatim alongside the coded response. Do not "
                        "add questions, and do not interpret the answers.",
                        produces=("checkin_response",),
                    ),
                    step(
                        "flag_red_answers",
                        "Route anything that reads as a red flag",
                        StepKind.NOTIFY,
                        "Compare each answer to the escalation criteria and send anything "
                        "that meets one -- or any answer at all that did not come back -- to "
                        "the named person straight away, with the response attached. You "
                        "flag and route; the judgement is theirs.",
                        produces=("escalation_flag",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "checkin_schedule",
                        "Check-in schedule",
                        "Each check-in with the protocol interval it came from and the date "
                        "it falls due.",
                    ),
                    artifact(
                        "checkin_response",
                        "Check-in response",
                        "The questions asked, the answers as given, and the non-responses, "
                        "each with its timestamp.",
                    ),
                    artifact(
                        "escalation_flag",
                        "Escalation flag",
                        "The answer that met a criterion, the criterion it met, who it went "
                        "to and when they picked it up.",
                    ),
                ),
                tools=("protocol_lookup", "escalation_queue", "case_state_write"),
                config_keys=(
                    ConfigKey(
                        key="checkin_protocol",
                        description=(
                            "Intervals and questions per treatment, course or programme, "
                            "and who owns the protocol."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="escalation_criteria",
                        description=(
                            "Answers and non-answers that must reach a named person, and "
                            "how quickly."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                ),
                kpis=("checkin_completion_rate", "response_rate", "minutes_to_escalation"),
            ),
            # A standing promise to keep somebody informed, kept whether or not
            # there is news.  It is the absence of the update that costs, so the
            # cadence is the product.
            Profile(
                name="proactive_update",
                summary=(
                    "A standing update cadence to a stakeholder that kills the "
                    "any-news call, sent whether or not there is news."
                ),
                match=(
                    "update cadence",
                    "proactive update",
                    "any-news",
                    "daily parent",
                    "diary",
                    "meals, naps",
                ),
                steps=(
                    step(
                        "gather_period",
                        "Gather what happened in the period",
                        StepKind.GATHER,
                        "Collect the facts the update covers -- activity, progress, "
                        "viewings, meals, naps, photos, numbers -- from the systems that "
                        "hold them, with the consent state on anything involving an image.",
                        produces=("update_inputs",),
                    ),
                    step(
                        "compose_update",
                        "Write it in the format they expect",
                        StepKind.DRAFT,
                        "Write the update to the agreed format and length. Where nothing "
                        "happened, say that plainly with what happens next and when -- a "
                        "padded update trains people to stop reading.",
                        produces=("update_note",),
                    ),
                    step(
                        "send_on_cadence",
                        "Send on the day, every time",
                        StepKind.ACT,
                        "Send on the cadence agreed with the recipient, from the customer's "
                        "own channel, and record the delivery. A cadence kept nine times in "
                        "ten is not a cadence.",
                        produces=("update_log",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "update_inputs",
                        "Update inputs",
                        "The facts gathered for this period, each with the system it came "
                        "from and its consent state.",
                    ),
                    artifact(
                        "update_note",
                        "Update",
                        "The update as sent, in the agreed format, for the period it "
                        "covers.",
                        fmt="document",
                    ),
                    artifact(
                        "update_log",
                        "Update log",
                        "Every update sent, its period, its recipient and its delivery "
                        "state.",
                        fmt="log",
                    ),
                ),
                tools=("activity_feed", "media_consent_check", "document_composer"),
                config_keys=(
                    ConfigKey(
                        key="update_cadence",
                        description=(
                            "How often each stakeholder type is updated, on which day, and "
                            "in which format."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="update_content",
                        description=(
                            "What each update must contain, and what may never appear in "
                            "one."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                    ConfigKey(
                        key="media_consent",
                        description=(
                            "Consent required before an image of a person is included, and "
                            "who holds it."
                        ),
                        required=True,
                    ),
                ),
                kpis=("cadence_adherence", "inbound_status_calls", "update_open_rate"),
            ),
            # Chasing a counterparty against a dated commitment.  Different from
            # a silent contact: they are reachable, the work is not done, and the
            # chase must name the item and the evidence that closes it.
            Profile(
                name="remediation_chase",
                summary=(
                    "A counterparty chased against a dated commitment until the "
                    "outstanding item is evidenced as closed."
                ),
                match=(
                    "otif",
                    "remediation",
                    "patch chaser",
                    "patch/vuln",
                    "supplier chaser",
                    "chased against",
                ),
                steps=(
                    step(
                        "outstanding_list",
                        "List what is outstanding, by date",
                        StepKind.ASSESS,
                        "Compare the commitment -- the purchase order, the patch baseline, "
                        "the remediation plan -- against the current state and list every "
                        "item still open with the date it was due and how late it is.",
                        produces=("outstanding_register",),
                    ),
                    step(
                        "chase_item",
                        "Chase the item, not the relationship",
                        StepKind.ACT,
                        "Send each chase naming the specific item, its due date, its age and "
                        "the evidence that would close it, to the contact the counterparty "
                        "named. Escalate up the configured contact ladder as the age bands "
                        "pass.",
                        produces=("chase_log",),
                    ),
                    step(
                        "performance_report",
                        "Report performance against the commitment",
                        StepKind.NOTIFY,
                        "Report on time and in full against the commitment by counterparty "
                        "and period, with the items still open and their age, so the "
                        "commercial conversation happens on numbers.",
                        produces=("performance_report",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "outstanding_register",
                        "Outstanding register",
                        "Every open item with its owner, due date, age band and the "
                        "evidence needed to close it.",
                    ),
                    artifact(
                        "chase_log",
                        "Chase log",
                        "Each chase sent, to whom, at which escalation level, and what came "
                        "back.",
                        fmt="log",
                    ),
                    artifact(
                        "performance_report",
                        "Performance report",
                        "On-time and in-full performance by counterparty and period, with "
                        "the ageing of what is still open.",
                    ),
                ),
                tools=("commitment_register", "estate_inventory", "escalation_queue"),
                config_keys=(
                    ConfigKey(
                        key="commitment_source",
                        description=(
                            "The order, baseline or plan that defines what was promised and "
                            "when."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="chase_escalation",
                        description=(
                            "Age bands and the contact level each one escalates to at the "
                            "counterparty."
                        ),
                        resolved_by="owner",
                        required=True,
                    ),
                    ConfigKey(
                        key="closure_evidence",
                        description=(
                            "What proves an item closed, by item type, and who may accept "
                            "it."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                ),
                kpis=("on_time_in_full_rate", "mean_days_open", "chase_to_closure_ratio"),
            ),
            # Fallback: a plain multi-touch ladder fired by an event.  Anything
            # whose whole job is "run these touches after this happened, then
            # close it with an outcome" lands here.
            Profile(
                name="multi_touch_sequence",
                summary=(
                    "A plain event-triggered ladder: the configured touches, in "
                    "order, closed with a named outcome."
                ),
                steps=(
                    step(
                        "sequence_state",
                        "Hold the state the touches act on",
                        StepKind.GATHER,
                        "Assemble the facts this ladder turns on -- what happened, what is "
                        "held, what was agreed, who else is waiting -- so each touch says "
                        "something true rather than something generic.",
                        produces=("sequence_state",),
                    ),
                    step(
                        "parallel_actions",
                        "Do the operational moves the event forces",
                        StepKind.ACT,
                        "Carry out the moves the trigger requires alongside the messaging -- "
                        "release what the terms release, contact the parties next in line, "
                        "return the item to its queue -- and record each one against the "
                        "rule that required it.",
                        produces=("action_log",),
                    ),
                    step(
                        "named_outcome",
                        "Close it with an outcome somebody can read",
                        StepKind.NOTIFY,
                        "Report the outcome of the ladder to the owner in one line each: "
                        "what was recovered, released or lost, and what is still open. A "
                        "ladder that ends in silence has not ended.",
                        produces=("action_log",),
                    ),
                ),
                artifacts=(
                    artifact(
                        "sequence_state",
                        "Sequence state",
                        "The facts the ladder acts on, as they stood when it was triggered.",
                    ),
                    artifact(
                        "action_log",
                        "Action log",
                        "Every operational move made alongside the touches, with the rule "
                        "that required it.",
                        fmt="log",
                    ),
                ),
                tools=("case_state_write", "task_tracker"),
                config_keys=(
                    ConfigKey(
                        key="trigger_actions",
                        description=(
                            "The operational moves this trigger forces beyond the messaging, "
                            "and the rule behind each."
                        ),
                        resolved_by="vertical",
                        required=True,
                    ),
                ),
                kpis=("ladder_completion_rate", "outcome_capture_rate"),
            ),
        )

    # -- plan --------------------------------------------------------------
    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Enrol, qualify, schedule, compose, send, close.

        Steps five to seven are the body of a loop: they run once per touch, and
        the plan describes one pass through it.  The two steps in front of them
        are the ones that make this family safe -- a journey is committed, with
        its exits written down, before a single message is composed.  Profile
        steps are appended after these and carry the shape-specific work.
        """
        return (
            step(
                "enrol",
                "Enrol the subject in the journey",
                StepKind.OBSERVE,
                "Take the trigger event, identify the subject it concerns and open or "
                "reuse their journey record. Where they are already inside a journey, "
                "note which one: two ladders running at the same contact is the "
                "commonest way a warm list is spent.",
                produces=("journey_record",),
            ),
            step(
                "eligibility",
                "Check they may be contacted at all",
                StepKind.GATHER,
                "Read the consent record, the suppression list, the opt-out state and the "
                "reachable channels for this contact, and gather the facts the copy will "
                "need. Consent is checked against the basis this market requires, per "
                "channel, and a missing basis is a stop rather than a risk taken.",
                produces=("consent_state",),
            ),
            step(
                "cadence",
                "Pick the cadence this subject earns",
                StepKind.ASSESS,
                "Place the subject in the segment or band the configuration defines and "
                "read off the cadence it carries: how many touches, how far apart, on "
                "which channel, with which offer attached. The cadence comes from "
                "configuration, never from how promising this particular contact feels.",
            ),
            step(
                "schedule",
                "Commit the touch plan with its exits",
                StepKind.DECIDE,
                "Write the plan down before anything is sent: each touch with its date, "
                "channel and purpose, the contactable hours it must fall inside, the "
                "frequency cap it counts against, and the exit conditions that end the "
                "journey early. A ladder with no last rung is not a plan.",
                produces=("touch_plan",),
            ),
            step(
                "compose",
                "Draft the next touch",
                StepKind.DRAFT,
                "Draft the due touch in the contact's language: one ask, referring to "
                "what actually happened to them, with any figure taken from the published "
                "price book and any incentive taken from the approved offer set. Later "
                "touches shorten; they do not get louder.",
            ),
            step(
                "send",
                "Re-check the exits, then send",
                StepKind.ACT,
                "Immediately before the touch fires, re-read the exit conditions, the "
                "suppression list and the frequency cap -- state changes between "
                "scheduling and sending, and that gap is where the unwanted message "
                "lives. Then send it from the customer's own connected account inside "
                "contactable hours and log the delivery.",
                produces=("touch_log",),
            ),
            step(
                "close",
                "Close each journey with a named outcome",
                StepKind.NOTIFY,
                "Record what came back and close the journey with a named terminal "
                "outcome -- converted, declined, opted out, unreachable or exhausted -- "
                "then report the outcomes to the owner on the configured cadence. A "
                "journey that simply stops being touched has no outcome and cannot be "
                "improved.",
                produces=("sequence_outcome",),
            ),
        )

    # -- artefacts ---------------------------------------------------------
    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "journey_record",
                "Journey record",
                "One record per subject per journey: which ladder they are on, which "
                "touch is next, when it is due and which exit condition is watching.",
            ),
            artifact(
                "touch_plan",
                "Touch plan",
                "The committed ladder: every touch with its date, channel, purpose and "
                "the exit conditions attached to it.",
            ),
            artifact(
                "touch_log",
                "Touch log",
                "Every touch attempted with channel, timestamp, sending account, "
                "delivery state and whatever came back.",
                fmt="log",
            ),
            artifact(
                "consent_state",
                "Consent and suppression state",
                "The consent basis, opt-out state and suppression flags as they stood at "
                "the moment of each send, not at enrolment.",
            ),
            artifact(
                "sequence_outcome",
                "Sequence outcome",
                "The terminal outcome per subject with its reason, the touch it followed "
                "and any value attributed inside the window.",
            ),
        )

    # -- inputs ------------------------------------------------------------
    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "The subject's record: history, value, tenure and current state",
            "Consent, opt-out and suppression state per channel",
            "Journeys this contact is already enrolled in, and their next due dates",
            "Cadence, stop conditions and frequency caps for this journey type",
            "Approved offer set and the published price book",
        )

    # -- mission -----------------------------------------------------------
    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        """How a sequence unit works, and where the discipline actually bites.

        Varies by profile and vertical, because the shapes genuinely differ: a
        dunning ladder and a post-op check-in share a skeleton and share almost
        nothing else about tone, timing or who owns the last rung.
        """
        lines = [
            "HOW YOU WORK. You run journeys, not messages. A trigger enrols a subject, "
            "and before anything is composed you commit a touch plan: how many touches, "
            "how far apart, on which rail, and -- written down first -- the conditions "
            "that end the journey early. Every number in that plan comes from "
            "configuration. None of it comes from how promising this particular contact "
            "feels today.",
            "Stopping is the skill. Immediately before each touch fires you re-read the "
            "exits, the suppression list, the opt-out state and the frequency cap, "
            "because state changes between scheduling and sending and that gap is "
            "exactly where the unwanted message lives. A reply, a conversion or an "
            "opt-out ends the ladder at once. Contactable hours are read in the "
            "recipient's timezone from the active pack, and a contact already inside "
            "another journey is not touched twice.",
            "Every figure you put in writing comes from the published price book, and "
            "every incentive from the approved offer set -- you choose from that list, "
            "you never invent a sweetener because somebody hesitated. Each journey ends "
            "in a named outcome: converted, declined, opted out, unreachable or "
            f"exhausted. {_PROFILE_NOTES[profile.name].rstrip('.')}.",
        ]

        vertical = record.get("vertical") or {}
        if vertical:
            lines.append(
                f"You are running {vertical['name'].lower()} journeys, so the intervals, "
                "the terminology, the offer set and the statutory dates come from the "
                "vertical overlay and the country pack. A cadence that is right in one "
                "trade is an intrusion in the next; read it, do not assume it."
            )

        if record["type"].startswith("playbook"):
            lines.append(
                "You are a playbook: one event fires you, you run the ladder once for the "
                "subject it concerns, and you close it. You do not adopt the contact or "
                "keep touching them after the ladder ends -- that belongs to the agent "
                "that owns the relationship."
            )

        return "\n\n".join(lines)

    # -- guardrails --------------------------------------------------------
    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        """MF5's own failure modes, each with something a reviewer can check."""
        guardrails = [
            Guardrail(
                id="GR-MF5-STOP-ON-RESPONSE",
                rule=(
                    "A reply, a conversion, an opt-out or a complaint ends the journey "
                    "immediately. Nothing is sent after the answer has arrived."
                ),
                check=(
                    "Every touch_log entry carries the exit check that ran immediately "
                    "before it, with its timestamp; a touch sent after an exit condition "
                    "was met is an error, counted and surfaced, not a near miss."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF5-CONSENT-AT-SEND",
                rule=(
                    "Consent, opt-out and suppression are evaluated at the moment of "
                    "sending, not at the moment of enrolling."
                ),
                check=(
                    "consent_state records the basis, opt-out state and suppression flags "
                    "as read at send time; a touch with no send-time consent record "
                    "cannot leave the queue."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF5-FINITE-LADDER",
                rule=(
                    "Every journey has a last touch and a named terminal outcome. No "
                    "ladder runs open-ended, and none ends in silence."
                ),
                check=(
                    "touch_plan declares the touch count before the first send, and every "
                    "closed journey_record carries one of the configured terminal "
                    "outcomes with its reason."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF5-ONE-LADDER-PER-CONTACT",
                rule=(
                    "Frequency caps count across every journey, not within one. A contact "
                    "already being touched is not enrolled again in the same window."
                ),
                check=(
                    "Enrolment queries the contact's open journeys and the cap is applied "
                    "to the total; the touch that would breach it is deferred or dropped "
                    "with the reason recorded."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF5-OFFERS-FROM-THE-SET",
                rule=(
                    "Incentives, discounts, save offers and rewards come from the "
                    "approved offer set. The unit never composes a new one to close a "
                    "hesitant contact."
                ),
                check=(
                    "Every incentive in an outbound touch resolves to a row in offer_set "
                    "with its value and expiry; anything outside the set is held at the "
                    "gate for the owner."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF5-CONTACTABLE-HOURS",
                rule=(
                    "No automated touch is sent outside the contactable hours and dates "
                    "the active country pack defines, read in the recipient's timezone."
                ),
                check=(
                    "Each scheduled touch carries the local send window it was checked "
                    "against; a touch falling outside it is deferred to the next window "
                    "rather than sent early."
                ),
                source="mechanism_family",
            ),
        ]

        # Ladders that end in a suspension, restriction, write-off or formal
        # process are the family's sharpest edge: the mechanism is designed to
        # walk towards a consequence, so the last rung needs its own check.
        haystack = _record_text(record)
        if any(marker in haystack for marker in _THRESHOLD_MARKERS):
            guardrails.append(
                Guardrail(
                    id="GR-MF5-THRESHOLD-IS-A-GATE",
                    rule=(
                        "The unit runs the ladder up to the threshold and stops. Pausing "
                        "a service, restricting an account, closing a case or starting a "
                        "formal or legal process is always a person's decision."
                    ),
                    check=(
                        "The final rung produces a pack for the named person and no "
                        "state change; any step that would suspend, restrict, close or "
                        "write off is preceded by a blocking gate and its recorded "
                        "outcome."
                    ),
                    source="mechanism_family",
                )
            )

        # Revenue-critical journeys are judged on the clock as well as the copy:
        # a save or recovery touch that arrives after the decision was made is
        # indistinguishable from no touch at all.
        if record["flags"]["revenue_critical"]:
            guardrails.append(
                Guardrail(
                    id="GR-MF5-FIRST-TOUCH-CLOCK",
                    rule=(
                        "The first touch of a save or recovery journey goes out inside "
                        "the configured window, measured from the trigger event."
                    ),
                    check=(
                        "journey_record carries the trigger timestamp and the first-touch "
                        "timestamp; breaches are counted against the unit and surfaced on "
                        "the owner's digest rather than averaged away."
                    ),
                    source="mechanism_family",
                )
            )
        return tuple(guardrails)

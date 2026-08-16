"""MF8 -- reconciliation.

Two systems both claim to know what happened, and they disagree.  A calendar and
three booking platforms; an invoice ledger and a bank feed; a payout statement
and the analytics it was supposedly calculated from; a timesheet and the job
data behind it; a settlement file and the trades it was meant to carry.  This
family is the layer that puts the two sides next to each other, pairs what pairs,
and turns everything left over into a worked list with an owner and a clock.  The
matched majority is never the product.  The product is the residue -- and a
defensible account of how the residue got to zero.

The discipline is in what the family refuses to do with a difference.  A
reconciliation that absorbs an awkward delta into a rounding line, a suspense
account or a plug has not reconciled anything; it has hidden the one item that
was trying to tell somebody something.  So every pairing here cites the rule and
the tolerance that made it, every unmatched item becomes a break rather than a
shrug, and a break survives re-running the match: only a posted correction or a
named person closes one.  "Exception list worked to zero" is an accounting
statement, and this family treats it as one -- opening breaks reconciled to
closing breaks, each closure carrying its reference.

The third standing rule lands squarely on the interesting half of the work.  The
unit computes the delta and gathers the evidence; it does not conclude why the
delta exists, who caused it or what it should cost.  It posts only the
corrections the write-back authority already permits, inside the ceiling that
authority sets, and everything else goes over as a pack with the decision field
empty -- to the accountant on the client-money break, the adjudicator on the
timesheet variance, the trustee on the restricted fund, the owner on the
financing offer.  Where the unit does file a claim against a counterparty, it
states the contract clause and the computed figure and stops there.

Config carries the rest.  Which systems hold the two sides, the cut-off each is
read at, the keys and tolerances that pair a record, the taxonomy a break falls
into, the ageing bands, the escalation ladder and the value ceiling on a
self-service correction all resolve from the vertical overlay and the active
country pack.  That is how one engine carries a channel manager, a payroll
exception resolver, a T+1 trade break and a retailer deduction without knowing
which of them it is holding.
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

#: Read by every unit of the family.  Between them these seven keys are the whole
#: reconciliation: what the two sides are, when each is cut, what counts as a
#: pair, what a leftover is called, how long it may sit, what the unit may fix on
#: its own authority and when the position is due.  Change them and the same code
#: matches a rota against a booking platform or a settlement file against a
#: trade blotter.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="reconciliation_sources",
        description=(
            "The systems that carry each side of the match, how each one is read, "
            "the cut-off it is taken at and the control total it reports for the "
            "period before any transformation."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="match_rules",
        description=(
            "The ordered rules that pair a record on one side with a record on "
            "the other: the keys each rule compares, the tolerance it allows and "
            "the rule id every pairing is cited by."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="break_taxonomy",
        description=(
            "The categories an unmatched or mismatched item can take, and for "
            "each one the owner it goes to, the remedy the policy already permits "
            "and the clock it runs against."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="tolerance_and_rounding",
        description=(
            "Differences that may be absorbed without raising a break -- rounding, "
            "currency conversion, known timing offsets -- and the ceiling above "
            "which nothing may be absorbed at all."
        ),
        required=True,
    ),
    ConfigKey(
        key="reconciliation_cycle",
        description=(
            "How often the match runs, the period each run covers, the cut-off it "
            "takes both sides at and the deadline the closing position is due by."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="write_back_authority",
        description=(
            "Which corrections the unit may post on its own authority, the value "
            "ceiling on each, and which are reserved for a named person however "
            "obvious they look."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="ageing_bands",
        description=(
            "The age bands open breaks are reported in, and the point in each band "
            "at which a break escalates rather than continuing to sit."
        ),
        resolved_by="owner",
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The ten reconciliation shapes actually present in the catalogue, most specific
#: first.  Tokens are nouns of the shape -- "roaming", "reweigh", "otif",
#: "timesheet" -- rather than the verbs every unit here shares ("matched",
#: "reconciled", "chased"), which would swallow the family whole.  Order carries
#: weight in three places: the money-side profiles must claim their units before
#: the identity profile's merge language sees "duplicate payment"; the settlement
#: profile must claim the payout-anomaly units before the claim profile's dispute
#: language reaches them; and the restricted-funds profile must claim a
#: client-money break before the generic ledger fallback does.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="availability_channel_sync",
        summary=(
            "One authoritative calendar, menu or rate sheet pushed out to every "
            "connected platform, with the platform that disagrees blocked from "
            "selling rather than left to double-sell."
        ),
        match=(
            "availability sync",
            "channel manager",
            "platform sync",
            "delivery platform",
            "aggregator",
            "double-book",
            "double book",
            "double-sell",
            "double sell",
            "menus and hours",
            "rates and availability",
            "calendar and platform",
            "synced calendar",
            "synchronisation",
            "synchronization",
        ),
        steps=(
            step(
                "write_back_to_every_platform",
                "Push the authoritative state to every connected platform",
                StepKind.ACT,
                (
                    "Take the value the authoritative source holds and posts it to every "
                    "connected platform, through the customer's own account for that "
                    "platform and never through an account the operator holds on their "
                    "behalf. Read each platform's acknowledgement back and treat silence "
                    "as failure: where a write is rejected or unconfirmed, hold that "
                    "platform's inventory back until it confirms. A platform still "
                    "selling against yesterday's state is the double-booking this unit "
                    "exists to prevent."
                ),
                produces=("channel_state", "overbooking_guard"),
            ),
        ),
        artifacts=(
            artifact(
                "channel_state",
                "Per-platform state",
                (
                    "For each connected platform: what it currently holds, what the "
                    "authoritative source holds, the delta, the write attempted, the "
                    "acknowledgement returned and the time the change took effect."
                ),
            ),
            artifact(
                "overbooking_guard",
                "Inventory holdback record",
                (
                    "Every holdback applied because a platform could not be written to "
                    "or would not confirm: what was withheld, from which platform, from "
                    "when, and the confirmation that released it."
                ),
                "log",
            ),
        ),
        tools=("channel_connector", "availability_ledger", "platform_write_api"),
        config_keys=(
            ConfigKey(
                key="connected_platforms",
                description=(
                    "The platforms this business sells through, which fields each "
                    "one accepts, the write cadence and rate limit for each, and "
                    "which of them may also push a change back."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="authoritative_source",
                description=(
                    "Which system holds the truth for each field, so a conflict "
                    "resolves by rule rather than by whichever write landed last."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="oversell_buffer",
                description=(
                    "The margin held back per platform to absorb propagation lag, "
                    "and the confirmation required before it is released."
                ),
                resolved_by="vertical",
            ),
        ),
        kpis=(
            "double-bookings and double-sells that reached a customer",
            "time from a change to it being live on every connected platform",
            "platform writes rejected and retried through to confirmation",
        ),
        channels=("connected_platforms",),
    ),
    Profile(
        name="receivables_financing_match",
        summary=(
            "Invoices on the receivables rail matched against the offers funding "
            "providers publish, every offer presented with its full cost, and the "
            "choice left entirely with the owner."
        ),
        match=(
            "financing",
            "receivable",
            "factoring",
            "invoicing rail",
            "offers presented",
        ),
        steps=(
            step(
                "set_the_offers_side_by_side",
                "Match the receivable to every offer it qualifies for",
                StepKind.ASSESS,
                (
                    "Read the receivables position, test each invoice against the "
                    "eligibility rules of every configured provider, and set the offers "
                    "that come back side by side on the same basis: the amount advanced, "
                    "the total cost of the capital, the recourse, the term and the "
                    "deadline the offer expires on. Show the referral commission the "
                    "business earns beside each one, because an offer whose incentive is "
                    "hidden is not an offer the owner can weigh. You present; the owner "
                    "chooses, and no offer is taken up on your say-so."
                ),
                produces=("offer_comparison",),
            ),
            step(
                "track_the_commission_to_receipt",
                "Track every referral through to the commission received",
                StepKind.ACT,
                (
                    "Record each referral against the invoice that produced it and "
                    "reconcile the commission actually received against the rate the "
                    "provider agreed, chasing the difference like any other break. A "
                    "referral that was made and never paid for is an unreconciled "
                    "receivable of its own."
                ),
                produces=("commission_ledger",),
            ),
        ),
        artifacts=(
            artifact(
                "offer_comparison",
                "Offer comparison",
                (
                    "Every offer the invoice qualified for on one basis: amount, total "
                    "cost of capital, recourse, term, expiry and the referral commission "
                    "attached, with the eligibility rule each provider applied."
                ),
                "document",
            ),
            artifact(
                "commission_ledger",
                "Commission ledger",
                (
                    "Each referral with the invoice behind it, the offer taken up, the "
                    "commission due under the provider agreement, the commission "
                    "received and the difference still being chased."
                ),
            ),
        ),
        tools=("receivables_ledger", "financing_marketplace", "offer_comparator"),
        config_keys=(
            ConfigKey(
                key="financing_providers",
                description=(
                    "Funding providers available in this market, the products each "
                    "offers, its eligibility rules and the commission agreed."
                ),
                required=True,
            ),
            ConfigKey(
                key="referral_disclosure",
                description=(
                    "The disclosure that must be shown to the customer alongside a "
                    "referred offer in this market, and when it must be shown."
                ),
                required=True,
            ),
        ),
        kpis=(
            "eligible invoices matched to at least one live offer",
            "offers presented with the total cost of capital stated",
            "commission received reconciled against commission due",
        ),
    ),
    Profile(
        name="record_identity_merge",
        summary=(
            "The same person or company recognised across channels, merged only "
            "above the confidence line, with history unified and every merge "
            "reversible."
        ),
        match=(
            "dedupe",
            "deduplicated",
            "identity resolution",
            "duplicate customer record",
            "merge queue",
            "merged record",
            "field drift",
            "inconsistent entry",
            "normaliz",
            "normalis",
            "rfm",
            "golden record",
            "history unified",
        ),
        steps=(
            step(
                "score_the_identity_match",
                "Cluster the candidates and score every pair",
                StepKind.ASSESS,
                (
                    "Cluster records on the configured identity keys and score each "
                    "candidate pair against them, recording which keys agreed, which "
                    "conflicted and the confidence that came out. Two people who share a "
                    "surname and a postcode are a candidate, not a match; the score is "
                    "the whole of the argument and it is written down."
                ),
                produces=("merge_candidate_set",),
            ),
            step(
                "merge_only_above_the_line",
                "Merge above the line, queue everything below it",
                StepKind.ACT,
                (
                    "Merge only pairs scoring above the configured confidence line. Keep "
                    "every source record and carry every history item -- bookings, "
                    "invoices, messages, consents -- onto the survivor, and keep the "
                    "merge reversible for the configured window. Anything below the line "
                    "waits in the queue for a person: an incorrect merge destroys two "
                    "records at once and is far more expensive than the duplicate it was "
                    "trying to remove."
                ),
                produces=("merge_log",),
            ),
        ),
        artifacts=(
            artifact(
                "merge_candidate_set",
                "Merge candidate set",
                (
                    "Every candidate pair with the identity keys that agreed, the keys "
                    "that conflicted, the confidence score and the side of the line it "
                    "fell on."
                ),
            ),
            artifact(
                "merge_log",
                "Merge log",
                (
                    "Each merge performed or queued: the surviving record, the records "
                    "folded into it, the history items carried across, the confidence, "
                    "the actor and the window in which it can still be reversed."
                ),
                "log",
            ),
            artifact(
                "normalisation_rules",
                "Field normalisation rules",
                (
                    "The rules in force for each drifting field, the corrections that "
                    "taught each rule, and the error rate on that field before and after "
                    "the rule was added."
                ),
            ),
        ),
        tools=("identity_resolver", "match_scorer", "merge_ledger", "field_normaliser"),
        config_keys=(
            ConfigKey(
                key="identity_keys",
                description=(
                    "The fields that identify a party in this market and how each is "
                    "compared -- exact, fuzzy, phonetic or normalised first."
                ),
                required=True,
            ),
            ConfigKey(
                key="merge_confidence_threshold",
                description=(
                    "The score above which a merge proceeds unattended, and the band "
                    "below it that always goes to a person."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="merge_reversal_window",
                description=(
                    "How long a merge stays reversible and what has to be retained "
                    "for it to be undone cleanly."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "duplicate rate in the live record set",
            "merges a human later reversed",
            "field values failing the normalisation rules",
        ),
    ),
    Profile(
        name="pay_variance_resolution",
        summary=(
            "Pay and time rebuilt line by line from the source records, so the "
            "variance is explained with evidence before it hardens into a "
            "grievance -- and any correction beyond the rules is adjudicated."
        ),
        match=(
            "payroll",
            "timesheet",
            "payday",
            "pay is wrong",
            "pay explanation",
            "grievance",
            "hours worked",
            "wage",
        ),
        steps=(
            step(
                "rebuild_the_pay_line",
                "Rebuild every line from the record behind it",
                StepKind.ASSESS,
                (
                    "Rebuild the period line by line from source: hours from the job, "
                    "rota and system data; the rate from the contract in force on the "
                    "day; each addition and each deduction from the rule that produced "
                    "it. Put the expected line beside the paid line and show the record "
                    "behind every difference. A person asking why their pay is wrong is "
                    "owed the arithmetic, not an assurance."
                ),
                produces=("line_by_line_explanation", "variance_pack"),
            ),
            step(
                "hand_the_correction_over",
                "Hand any correction beyond the rules to the adjudicator",
                StepKind.GATE,
                (
                    "Where the variance resolves by a rule -- a missing shift found in "
                    "the job data, a rate the contract already sets -- write the "
                    "correction up and put it through the payroll cut-off. Where it does "
                    "not, the pack goes to the named adjudicator with the evidence and "
                    "an empty decision field, and you wait. Judging between a worker's "
                    "account and the system's is not arithmetic and it is not yours."
                ),
                produces=("variance_pack",),
            ),
        ),
        artifacts=(
            artifact(
                "line_by_line_explanation",
                "Line-by-line explanation",
                (
                    "The period rebuilt for the person receiving it: every line, the "
                    "record it came from, the rule that produced it, the expected value, "
                    "the paid value and the difference."
                ),
                "document",
            ),
            artifact(
                "variance_pack",
                "Variance pack",
                (
                    "The variance assembled for adjudication: the two accounts side by "
                    "side, the corroborating job, rota and system evidence, the value at "
                    "stake, the payroll deadline and an unfilled decision field."
                ),
                "bundle",
            ),
        ),
        tools=("payroll_system", "time_records", "rota_system", "rate_card"),
        config_keys=(
            ConfigKey(
                key="pay_rules",
                description=(
                    "Rates, premiums, statutory additions and deductions that apply "
                    "in this market, and the order they are calculated in."
                ),
                required=True,
            ),
            ConfigKey(
                key="payroll_calendar",
                description=(
                    "Pay periods, the cut-off a correction must land before and the "
                    "route for anything that misses it."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="time_evidence_sources",
                description=(
                    "Which systems corroborate worked time -- job records, dispatch, "
                    "access control, location data -- and the weight each carries."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "variances resolved before the payroll cut-off",
            "pay queries answered with a line-by-line explanation at first reply",
            "queries that escalated into a formal grievance",
        ),
    ),
    Profile(
        name="payables_match_control",
        summary=(
            "Supplier invoices and expense claims tested against the order, the "
            "receipt and the policy, with duplicates and mismatches held before "
            "the payment run reaches them."
        ),
        match=(
            "supplier invoice",
            "three-way",
            "three way match",
            "match po",
            "purchase order",
            "expense claim",
            "receipt matched",
            "out-of-policy",
            "blocked before payment",
            "accounts payable",
        ),
        steps=(
            step(
                "run_the_three_way_match",
                "Test the invoice against the order and the receipt",
                StepKind.ASSESS,
                (
                    "Match the invoice to the order it cites and to the evidence that "
                    "the goods or the service actually arrived, and state the delta "
                    "on its own line for quantity, for unit price and for terms. Test each "
                    "expense line against the policy clause that governs it and mark it "
                    "in-policy or out-of-policy against that clause. A single blended "
                    "difference tells nobody which control failed."
                ),
                produces=("three_way_match", "policy_check"),
            ),
            step(
                "hold_it_before_the_money_moves",
                "Hold the payment before the run picks it up",
                StepKind.ACT,
                (
                    "Put a hold on any invoice that duplicates one already in the ledger "
                    "or that fails the match outside tolerance, and do it before the "
                    "payment run reaches it -- money recovered after it has left is a "
                    "different and much longer job. Name the duplicate key or the failing "
                    "control on the hold, and leave the hold in place until the named "
                    "person releases it; you never release your own hold."
                ),
                produces=("payment_hold",),
            ),
        ),
        artifacts=(
            artifact(
                "three_way_match",
                "Three-way match result",
                (
                    "Invoice against order against receipt, with the delta stated "
                    "on its own line for quantity, unit price and terms, and the tolerance "
                    "each was tested against."
                ),
            ),
            artifact(
                "policy_check",
                "Policy check",
                (
                    "Each claim or invoice line against the policy clause it was tested "
                    "against, marked in-policy or out-of-policy, with the receipt or "
                    "supporting document attached."
                ),
            ),
            artifact(
                "payment_hold",
                "Payment hold record",
                (
                    "Every hold placed before the payment run: the invoice, the "
                    "duplicate key or failing control that caused it, the value stopped, "
                    "the time it went on and the named person who may release it."
                ),
                "log",
            ),
        ),
        tools=("purchase_ledger", "order_system", "receipt_capture", "payment_hold"),
        config_keys=(
            ConfigKey(
                key="match_tolerances",
                description=(
                    "The quantity, price and terms variance tolerated on a supplier "
                    "invoice before the match fails, by supplier or category."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="expense_policy",
                description=(
                    "The expense policy in force: categories, limits, receipt "
                    "requirements and the clause each line is tested against."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="duplicate_invoice_keys",
                description=(
                    "The fields whose repetition marks an invoice as a probable "
                    "duplicate, and the window over which repetition counts."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="payment_run_calendar",
                description=(
                    "When payment runs execute, so a hold lands ahead of one rather "
                    "than behind it."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "duplicate invoices held before the payment run",
            "invoices matched without a human touch",
            "value released outside the configured tolerance",
        ),
    ),
    Profile(
        name="restricted_funds_break",
        summary=(
            "Money that is not the business's own, checked against the restriction "
            "that binds it and surfaced on the statutory same-day clock with the "
            "notice drafted and the resolution reserved."
        ),
        match=(
            "client money",
            "client account",
            "restricted fund",
            "trust account",
            "ring-fenced",
            "ringfenced",
            "trustee",
            "accounts rules",
            "misallocation",
            "designated fund",
            "escrow",
        ),
        steps=(
            step(
                "test_against_the_restriction",
                "Test every movement against the restriction that binds it",
                StepKind.ASSESS,
                (
                    "Test each movement against the restriction attached to the money: "
                    "whose it is, which fund or client ledger it belongs to, and what it "
                    "may be applied to. Name the restriction, the rule reference and the "
                    "amount for every breach found, and distinguish a shortfall from a "
                    "misapplication -- they carry different obligations and different "
                    "clocks."
                ),
                produces=("restriction_check",),
            ),
            step(
                "serve_the_notice_inside_the_clock",
                "Serve the notice inside the statutory window",
                StepKind.NOTIFY,
                (
                    "Put the exception in front of the named officer inside the window "
                    "the rules impose, with the ledger extract attached and the notice "
                    "already drafted for their signature. Whether the breach is "
                    "notifiable, how it is corrected and what is said to the regulator "
                    "are theirs; your obligation ends at a complete, timely, evidenced "
                    "hand-over -- and a break you surfaced late is a breach of its own."
                ),
                produces=("statutory_notice",),
            ),
        ),
        artifacts=(
            artifact(
                "restriction_check",
                "Restriction check",
                (
                    "Every movement tested against the restriction that binds it, with "
                    "the rule reference, the fund or client ledger, the amount and "
                    "whether it is a shortfall or a misapplication."
                ),
            ),
            artifact(
                "statutory_notice",
                "Drafted notice",
                (
                    "The notice prepared for the named officer: what was found, the "
                    "ledger extract that evidences it, the rule engaged, the window it "
                    "must be answered in and an unsigned decision block."
                ),
                "document",
            ),
        ),
        tools=("client_ledger", "restriction_register", "notice_drafter"),
        config_keys=(
            ConfigKey(
                key="client_money_rules",
                description=(
                    "The rules governing money held for another party in this market, "
                    "including the reconciliation frequency they mandate."
                ),
                required=True,
            ),
            ConfigKey(
                key="same_day_clock",
                description=(
                    "The window in which a break must be surfaced and to whom, and "
                    "the out-of-hours route when it opens outside working hours."
                ),
                required=True,
            ),
            ConfigKey(
                key="notifiable_breach_route",
                description=(
                    "Which breaches are reportable in this market, to which body and "
                    "inside what deadline."
                ),
                required=True,
            ),
        ),
        kpis=(
            "breaks surfaced inside the same-day window",
            "notices served with the ledger extract attached",
            "breaks that reached a reporting deadline unworked",
        ),
    ),
    Profile(
        name="settlement_break_closure",
        summary=(
            "A break between what a counterparty settled and what the business "
            "expected, isolated to the file, batch or trade that carries it and "
            "chased up the ladder against the settlement clock."
        ),
        match=(
            "settlement break",
            "settlement file",
            "settlement clock",
            "settlements clerk",
            "settlement reconcil",
            "roaming",
            "emsp",
            "royalt",
            "payout anomaly",
            "payouts matched",
            "platform payout",
            "trade break",
            "affirmation",
            "counterparty",
            "commission reconcil",
            "commission statement",
            "enrolments matched",
            "chased to settlement",
            "merchants notified",
        ),
        steps=(
            step(
                "isolate_the_break",
                "Isolate the break and size who it touches",
                StepKind.ASSESS,
                (
                    "Narrow the break from the total down to the file, batch, line or "
                    "trade that actually carries it, and name every counterparty, "
                    "merchant or account touched by it with the value each one is "
                    "exposed to. Compare against the counterparty's own statement rather "
                    "than your expectation of it: the two documents are the reconciliation, "
                    "and a break stated as a lump sum cannot be chased by anybody."
                ),
                produces=("break_isolation",),
            ),
            step(
                "work_the_escalation_ladder",
                "Work the ladder against the settlement clock",
                StepKind.ACT,
                (
                    "Re-run or re-submit whatever the scheme's own rules already permit "
                    "to be re-submitted, then chase the counterparty up the configured "
                    "ladder with the settlement deadline in front of you, logging each "
                    "rung with the time, the contact and the response. Tell the affected "
                    "parties what is broken and what happens next before they find out "
                    "from their own statement; silence during a settlement break costs "
                    "more than the break."
                ),
                produces=("escalation_ladder_log", "counterparty_dispute"),
            ),
        ),
        artifacts=(
            artifact(
                "break_isolation",
                "Break isolation",
                (
                    "The break narrowed to the file, batch, line or trade carrying it, "
                    "with every counterparty, merchant or account affected, the value "
                    "each is exposed to and the settlement deadline in play."
                ),
            ),
            artifact(
                "escalation_ladder_log",
                "Escalation ladder log",
                (
                    "Each rung worked: the time, the contact, what was asked, what came "
                    "back, and the deadline the rung was measured against."
                ),
                "log",
            ),
            artifact(
                "counterparty_dispute",
                "Counterparty claim",
                (
                    "The claim raised with the counterparty: what was expected, what "
                    "arrived, the evidence for the difference, the value claimed and the "
                    "reference the counterparty assigned it."
                ),
                "document",
            ),
        ),
        tools=(
            "settlement_ledger",
            "counterparty_portal",
            "file_replay",
            "dispute_filing",
        ),
        config_keys=(
            ConfigKey(
                key="settlement_calendar",
                description=(
                    "Settlement cycles, cut-offs and the deadline each break must be "
                    "closed by in this market."
                ),
                required=True,
            ),
            ConfigKey(
                key="counterparty_registry",
                description=(
                    "Counterparties, schemes and platforms settled with, each with "
                    "its statement format, contact route and dispute window."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="escalation_ladder",
                description=(
                    "The rungs a chase climbs per counterparty, the wait at each and "
                    "the point at which it leaves the desk."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "breaks closed inside the settlement window",
            "value ageing past the settlement clock",
            "affected parties told before they raised it themselves",
        ),
        channels=("counterparty_portal",),
    ),
    Profile(
        name="claim_recovery_pack",
        summary=(
            "A charge somebody else raised, tested line by line against the "
            "contract and the operating evidence, with the valid part conceded and "
            "the invalid part disputed inside the counterparty's window."
        ),
        match=(
            "deduction",
            "chargeback",
            "otif",
            "reweigh",
            "reclass",
            "traffic fine",
            "toll notice",
            "fine received",
            "payment dispute",
            "reserve release",
            "eligibility comput",
            "rebill",
            "appeal",
            "recovered cash",
            "evidence pack",
            "carrier evidence",
            "shipment evidence",
            "loss history",
        ),
        steps=(
            step(
                "compute_valid_against_invalid",
                "Compute the valid part against the invalid part",
                StepKind.ASSESS,
                (
                    "Pull the evidence the contract itself names -- proof of delivery, "
                    "weights and dimensions, route and telematics records, utilisation "
                    "data, shipment and appointment records -- and test the charge line "
                    "by line against the clause each line rests on. Concede the part that "
                    "is valid as plainly as you contest the part that is not; a claim "
                    "that disputes everything is discounted wholesale by the party "
                    "reading it. Where the charge attributes to a person, vehicle or cost "
                    "centre, attribute it from the operating data and state the evidence "
                    "the attribution rests on."
                ),
                produces=("validity_computation",),
            ),
            step(
                "file_inside_their_window",
                "File the claim inside the counterparty's window",
                StepKind.ACT,
                (
                    "Draft the dispute, appeal or release request in the counterparty's "
                    "own format with every exhibit attached and the amount stated, and "
                    "file it inside their window where the policy already permits filing. "
                    "Where the policy reserves that call -- an appeal on the record, a "
                    "release of held funds, a rebill against a person -- it stays a draft "
                    "against the gate with the deadline shown, because a reserved decision "
                    "presented late is a decision taken by default."
                ),
                produces=("claim_filing", "recovery_ledger"),
            ),
        ),
        artifacts=(
            artifact(
                "validity_computation",
                "Validity computation",
                (
                    "The charge line by line: the contract clause each line was tested "
                    "against, the evidence pulled for it, the part computed valid, the "
                    "part computed invalid and the attribution where one applies."
                ),
            ),
            artifact(
                "claim_filing",
                "Claim filing",
                (
                    "The dispute, appeal or release request as filed or drafted: the "
                    "counterparty's format, the exhibits attached, the amount claimed, "
                    "the window it must land in and the reference returned."
                ),
                "document",
            ),
            artifact(
                "recovery_ledger",
                "Recovery ledger",
                (
                    "Every claim raised with its value, its state, the deadline it must "
                    "be filed by, the outcome and the cash actually recovered against it."
                ),
            ),
        ),
        tools=("evidence_store", "contract_terms", "claim_portal", "recovery_ledger"),
        config_keys=(
            ConfigKey(
                key="contract_terms",
                description=(
                    "The commercial terms a charge is tested against: service levels, "
                    "tolerances, liability, the evidence each clause requires and the "
                    "window a claim must be raised in."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="evidence_sources",
                description=(
                    "Which operating systems supply proof for each charge type, and "
                    "how long each retains it."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="attribution_rules",
                description=(
                    "How a charge is attributed to a person, vehicle, site or cost "
                    "centre from the operating data, and what evidence attribution "
                    "requires before anything is rebilled."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "claims filed inside the counterparty's window",
            "share of disputed value actually recovered",
            "charges attributed to the right party first time",
        ),
    ),
    Profile(
        name="asset_return_reconciliation",
        summary=(
            "What went out counted back against what came in, item by item, with "
            "retrieval booked for what is locatable and the contract's own rate "
            "billed for what is not."
        ),
        match=(
            "inventory-out",
            "inventory back",
            "equipment left",
            "retrieval",
            "loss billed",
            "reconciled inventory",
            "stock count",
            "asset register",
            "kit return",
        ),
        steps=(
            step(
                "count_it_back",
                "Count what returned against what went out",
                StepKind.ASSESS,
                (
                    "Reconcile the return against the issue list item by item, and mark "
                    "everything missing, damaged or unaccounted for with where it was "
                    "last seen, who signed for it and which job it went out on. A total "
                    "that balances at case level while an item inside it is missing is "
                    "not a reconciliation."
                ),
                produces=("asset_reconciliation",),
            ),
            step(
                "book_retrieval_and_bill_the_loss",
                "Book the retrieval, bill the loss at the contract rate",
                StepKind.ACT,
                (
                    "Where the item is locatable, book the retrieval into the round that "
                    "suits it and tell the holder when someone is coming. Where it is "
                    "not, raise the charge the contract already sets, at the rate written "
                    "in it -- never a figure you compose -- and show the reconciliation "
                    "line the charge rests on."
                ),
                produces=("retrieval_booking", "loss_charge"),
            ),
        ),
        artifacts=(
            artifact(
                "asset_reconciliation",
                "Asset reconciliation",
                (
                    "The issue list against the return, item by item, with each missing "
                    "or damaged item, where it was last seen, who signed for it and the "
                    "job it went out on."
                ),
            ),
            artifact(
                "retrieval_booking",
                "Retrieval booking",
                (
                    "The collection arranged for each locatable item: the site, the "
                    "window, the assignee and the confirmation given to the holder."
                ),
            ),
            artifact(
                "loss_charge",
                "Loss charge",
                (
                    "Each item charged for, the contract clause and rate the charge "
                    "rests on, the reconciliation line evidencing the loss and the "
                    "document the charge was raised on."
                ),
            ),
        ),
        tools=("asset_register", "issue_and_return_log", "scheduler", "billing"),
        config_keys=(
            ConfigKey(
                key="asset_register",
                description=(
                    "The items tracked out and back, their identifiers, their value "
                    "and the person accountable for each."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="loss_charge_schedule",
                description=(
                    "The contract rate charged for each class of lost or damaged "
                    "item, and the grace period before a charge is raised."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "items reconciled back inside the return window",
            "losses billed at the contract rate",
            "assets written off as unaccounted for",
        ),
    ),
    Profile(
        name="ledger_match_exception",
        summary=(
            "The family's plain shape: what was billed matched against what "
            "actually moved, the residual allocated or chased, and the exception "
            "list worked down to zero with every closure referenced."
        ),
        steps=(
            step(
                "allocate_and_chase_the_residual",
                "Allocate what arrived, leave the residual visible",
                StepKind.ACT,
                (
                    "Allocate what actually arrived against the right invoice and the "
                    "right line under the allocation rules, and leave the residual "
                    "standing as its own item rather than smoothing it away. Where money "
                    "is short, send the statement and start the chase on the configured "
                    "ladder; where money is over, raise the credit or the refund the "
                    "policy already permits at that value and queue anything above it. "
                    "The customer is told either way, because a balance they do not "
                    "recognise is the next dispute."
                ),
                produces=("allocation_record", "statement"),
            ),
        ),
        artifacts=(
            artifact(
                "allocation_record",
                "Allocation record",
                (
                    "What arrived, the invoice and line it was allocated against, the "
                    "allocation rule applied, the residual left standing and the credit "
                    "or refund raised where there was an excess."
                ),
            ),
            artifact(
                "statement",
                "Statement and balance chase",
                (
                    "The statement sent, the balance outstanding on it, the chase step "
                    "it belongs to on the ladder and the delivery result."
                ),
                "document",
            ),
        ),
        tools=("accounting_ledger", "bank_feed", "invoice_ledger", "statement_builder"),
        config_keys=(
            ConfigKey(
                key="allocation_rules",
                description=(
                    "How an incoming amount is applied across invoices and lines -- "
                    "oldest first, by reference, part-payment handling -- and what "
                    "happens to an unmatched residual."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="chase_ladder",
                description=(
                    "The steps, intervals and tone of a balance chase in this market, "
                    "and the point at which it stops being an automated one."
                ),
                required=True,
            ),
            ConfigKey(
                key="write_off_threshold",
                description=(
                    "The residual below which a difference may be written off, who "
                    "may do it and what has to be recorded when it is."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "exception list worked to zero by the cycle deadline",
            "value left unallocated at the close of each cycle",
            "residuals written off rather than resolved",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class ReconciliationEngine(Engine):
    """Carries every unit whose product is the residue between two records.

    One skeleton -- take both sides at the same cut-off, normalise them, pair
    what the rules pair, classify and own what is left, write the pack, post
    only what authority permits and report the position -- and ten profiles that
    say what the two sides are.  Nothing in the code knows whether it is holding
    a calendar against three booking platforms or a settlement file against a
    trade blotter; the sources, keys, tolerances, taxonomy and ladders all
    arrive as configuration.
    """

    id: ClassVar[str] = "MF8"
    family: ClassVar[str] = "Reconciliation"
    what_it_does: ClassVar[str] = (
        "Matches records across systems and works the exceptions"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.RECONCILE,
        Capability.WATCH_SIGNAL,
        Capability.SCORE,
        Capability.QUEUE_TRIAGE,
        Capability.CASE_STATE,
        Capability.COLLECT_DOCUMENTS,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "source_extractor",
        "ledger_reader",
        "match_engine",
        "tolerance_calculator",
        "break_register",
        "adjustment_poster",
        "report_builder",
        "message_sender",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "owner_dashboard",
        "finance_desk",
        "email",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "share of items matched without a human touch",
        "open breaks past their ageing band",
        "value left unreconciled at the close of each cycle",
        "adjustments posted that a human later reversed",
        "cycles whose closing position was reported by its deadline",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    #: The register is the family's memory.  A break belongs to it, not to the
    #: run that found it, which is what lets a break survive re-running the match.
    state_object: ClassVar[str] = "break_register"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Take both sides, normalise, match, classify, draft, correct, report.

        The order is the control.  Both sides are read before anything is
        compared, so neither can be quietly re-fetched to suit the other; the
        normalisation that makes them comparable happens in the open, with the
        raw value retained, so a pairing can be reproduced by someone who does
        not trust it; and the write-back sits after the pack is drafted rather
        than before, so what the unit fixed on its own authority is always
        visible beside what it did not.
        """
        return (
            step(
                "take_both_sides",
                "Take both sides at the same cut-off",
                StepKind.OBSERVE,
                (
                    "Read each side of the match from its own system of record at the "
                    "cut-off the cycle configures, and capture the control total that "
                    "source reports for the period before you touch anything. Record the "
                    "system, the extraction time and the range covered for each side. "
                    "Two sides that resolve to the same source are not a reconciliation, "
                    "and a run that cannot state its control totals cannot prove it saw "
                    "everything."
                ),
                produces=("reconciliation_run",),
            ),
            step(
                "normalise_onto_one_shape",
                "Normalise both sides onto one comparable shape",
                StepKind.GATHER,
                (
                    "Map both sides onto the common key set -- amount, currency, date, "
                    "reference, party, quantity -- applying only the transformations the "
                    "configuration names: rounding, currency conversion, known timing "
                    "offsets. Keep the raw value beside every derived one and record the "
                    "transformation that produced it. Anything you had to change to make "
                    "the two sides comparable is part of the evidence, not a private "
                    "convenience."
                ),
                produces=("source_extract",),
            ),
            step(
                "pair_what_the_rules_pair",
                "Run the match rules in order and cite every pair",
                StepKind.ASSESS,
                (
                    "Run the match rules in the order they are written, exact keys before "
                    "tolerance-based ones, and record for every pair the rule id, the "
                    "keys compared and the residual difference left over. One record "
                    "pairs with one counterpart. Whatever fails to pair, pairs twice or "
                    "pairs outside tolerance is a break -- never a difference absorbed "
                    "into a rounding line to make the totals agree."
                ),
                produces=("matched_set", "break_register"),
            ),
            step(
                "classify_and_own_each_break",
                "Give every break a category, an owner and a clock",
                StepKind.DECIDE,
                (
                    "Put each break into a category from the taxonomy and take from that "
                    "category its owner, the remedy the policy already permits and the "
                    "clock it runs against. Carry forward the breaks still open from "
                    "previous cycles with their original first-seen date, so age is "
                    "measured from when the difference appeared and not from today. A "
                    "break that matches no category is not thereby resolved: it goes to "
                    "the default owner and stays open."
                ),
                produces=("break_register",),
            ),
            step(
                "write_the_break_pack",
                "Write each break so one read is enough",
                StepKind.DRAFT,
                (
                    "For each break that needs a person, set the two sides beside each "
                    "other with the delta, the evidence behind both, what has changed "
                    "since it was first seen, the candidate explanations as observations "
                    "with the evidence for each, the remedy the policy permits and the "
                    "single decision you are asking for. Say what the records show and "
                    "stop: why the difference happened, whose mistake it was and what it "
                    "should cost belong to the person reading the pack."
                ),
                produces=("break_pack",),
            ),
            step(
                "post_only_what_authority_permits",
                "Post the corrections you are authorised to post",
                StepKind.ACT,
                (
                    "Post each correction the write-back authority already permits, "
                    "inside its value ceiling, as an entry that references the break it "
                    "closes and the authority clause that allowed it, keeping the before "
                    "and after values. Everything above the ceiling, and everything the "
                    "authority reserves, stays open with its pack queued. A tidy ledger "
                    "you were not authorised to tidy is worse than an untidy one."
                ),
                produces=("adjustment_log",),
            ),
            step(
                "report_the_position",
                "Report the closing position and what is still open",
                StepKind.NOTIFY,
                (
                    "Report the cycle: value and count matched, breaks opened, breaks "
                    "closed with the reference that closed each, what remains open by "
                    "ageing band and the value at risk in each. Reconcile opening breaks "
                    "to closing breaks so the movement is provable. A list reported at "
                    "zero has to show how it got there; a clean cycle is a finding, and "
                    "it is stated as one."
                ),
                produces=("reconciliation_report",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "reconciliation_run",
                "Reconciliation run",
                (
                    "The run itself: period, cut-off, each source with its system, "
                    "extraction time and reported control total, and the matched, broken "
                    "and unreconciled totals it closed on."
                ),
            ),
            artifact(
                "source_extract",
                "Normalised source extract",
                (
                    "Each side mapped onto the common key set, with the raw value kept "
                    "beside every derived one and the transformation that produced it, so "
                    "any pairing can be reproduced by someone who does not trust it."
                ),
            ),
            artifact(
                "matched_set",
                "Matched set",
                (
                    "Every pairing made: the two records, the rule id and tolerance that "
                    "paired them, the keys compared and the residual difference left "
                    "over."
                ),
            ),
            artifact(
                "break_register",
                "Break register",
                (
                    "The live list of open breaks carried across cycles: which side each "
                    "sits on, its category, value, first-seen date, age, owner, clock and "
                    "current state."
                ),
            ),
            artifact(
                "break_pack",
                "Break pack",
                (
                    "One break written for a decision: both sides side by side, the "
                    "delta, the evidence, movement since first seen, candidate "
                    "explanations as observations, the permitted remedy and an unfilled "
                    "decision field."
                ),
                "bundle",
            ),
            artifact(
                "adjustment_log",
                "Adjustment log",
                (
                    "Every correction the unit made on its own authority: the entry "
                    "raised, the break it closes, the authority clause that permitted it, "
                    "the before and after values and the actor."
                ),
                "log",
            ),
            artifact(
                "reconciliation_report",
                "Reconciliation report",
                (
                    "The closing position: matched value and count, breaks opened and "
                    "closed with their closing references, what remains open by ageing "
                    "band, value at risk, and opening breaks reconciled to closing "
                    "breaks."
                ),
                "report",
            ),
            # No unit of this family is currently a diamond, but compose() would
            # prepend an interlock step the moment the workbook flagged one, and
            # an artefact a step produces without declaring fails the audit.
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
                f"What the two sides are in {vertical['name'].lower()}, how quickly a "
                f"break has to be closed and what a difference of that size means come "
                f"from the vertical overlay and the active country pack -- read both "
                f"rather than assuming the cycle you know."
            )
        else:
            where = (
                "This match runs across every vertical on the platform, so the sources, "
                "the tolerances and the clock a break runs against are whatever the "
                "overlay in front of you supplies."
            )
        return (
            "HOW YOU WORK. Two systems both claim to know what happened and they "
            "disagree; your work is the disagreement, not the part that already "
            "agrees. Take each side from its own system of record at the same "
            "cut-off, keep the control total each one reports, and normalise both onto "
            "one shape in the open -- raw value beside every derived one -- because a "
            "pairing nobody can reproduce is not a match. Run the match rules in the "
            "order they are written, cite the rule and the residual on every pair, and "
            "treat everything left over as a break: nothing is absorbed into a "
            "rounding line, a suspense account or a plug to make two totals agree. "
            "Give each break a category, an owner, an age measured from the day the "
            "difference appeared and a clock, and carry it across cycles until a "
            "posted correction or a named person closes it -- re-running the match "
            "closes nothing. Post only the corrections your authority already permits, "
            "inside its ceiling, and hand the rest over as a pack: both sides side by "
            "side, the delta, the evidence, the candidate explanations as observations "
            "and the one decision you are asking for. You state what differs and what "
            "the records show; why it differs, who is at fault and what it should cost "
            "are not yours to conclude. And when you report the list at zero, the "
            "report shows how it got there -- opening breaks, new, corrected, decided, "
            f"written off, each closure carrying its reference. "
            f"{self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-NO-PLUG-FIGURE",
                rule=(
                    "A difference is never absorbed to make two sides agree. Nothing "
                    "is written to a suspense, rounding or balancing line to close a "
                    "break."
                ),
                check=(
                    "Every entry in adjustment_log names the record it corrects and "
                    "the write_back_authority clause that permitted it; no entry "
                    "balances to a plug, a suspense account or an unnamed difference."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-BOTH-SIDES-FROM-SOURCE",
                rule=(
                    "Each side of the match comes from its own system of record at "
                    "the same cut-off. A ledger is never reconciled against a copy of "
                    "itself."
                ),
                check=(
                    "source_extract names each side's system, extraction time, period "
                    "and reported control total; a run whose sides resolve to one "
                    "source fails rather than reporting a clean match."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MATCH-CITES-A-RULE",
                rule=(
                    "Every pairing names the rule and the tolerance that made it. A "
                    "match nobody else can reproduce is not a match."
                ),
                check=(
                    "Each matched_set row carries a rule id from match_rules, the keys "
                    "compared and the residual; pairs made outside those rules are "
                    "listed as breaks instead."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NO-DOUBLE-COUNT",
                rule=(
                    "One record pairs with one counterpart. The same payment, invoice, "
                    "shipment or slot is never matched or sold twice."
                ),
                check=(
                    "matched_set holds a single pairing per record on each side; a "
                    "record appearing in two pairings raises a break rather than "
                    "closing both."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-BREAK-SURVIVES-THE-CYCLE",
                rule=(
                    "A break stays open until it is worked. Re-running the match "
                    "closes nothing; only a posted correction or a human decision "
                    "does."
                ),
                check=(
                    "Every break_register entry keeps its first-seen date and its age "
                    "across cycles, and a break absent from the current extract is "
                    "reported as still open rather than dropped."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CORRECTION-INSIDE-AUTHORITY",
                rule=(
                    "The unit posts only the corrections write_back_authority already "
                    "permits, inside its value ceiling. Everything else is queued as a "
                    "brief, however obvious the fix looks."
                ),
                check=(
                    "Each adjustment_log entry cites its authority clause and shows a "
                    "value under that clause's ceiling; anything above it appears in "
                    "break_pack with an empty decision field."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CAUSE-IS-AN-OBSERVATION",
                rule=(
                    "The unit reports what the two sides hold and what differs. It "
                    "never states why the difference happened or attributes fault."
                ),
                check=(
                    "break_pack lists candidate explanations as observations with the "
                    "evidence for each; where a claim is filed it states the contract "
                    "clause and the computed figure, never a finding about a party."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-ZERO-IS-EVIDENCED",
                rule=(
                    "A list reported at zero is a claim that has to be evidenced. "
                    "Every closure names what closed it."
                ),
                check=(
                    "reconciliation_report reconciles opening breaks to closing breaks "
                    "-- new, corrected, decided, written off -- and each closure "
                    "carries its adjustment or gate reference."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "Both sides of the match, each read from its own system of record at the configured cut-off",
            "The control total each source reports for the period, before any transformation",
            "The break register as it stood at the close of the last cycle, with ages and owners",
            "Match rules, tolerances and the break taxonomy in force, with their versions",
            "Contract, policy and scheme terms deciding what a difference means and who carries it",
            "Every correction posted since the last run, with the authority it was posted under",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming what the two sides are for this profile.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer can override.
        """
        return _PROFILE_MISSION_LINES.get(
            profile.name, _PROFILE_MISSION_LINES["ledger_match_exception"]
        )


#: Mission prose per profile.  Each names the two sides, the artefact that proves
#: the work and the exact point at which the unit stops and a person takes over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "availability_channel_sync": (
        "Here the two sides are one authoritative calendar, menu or rate sheet and "
        "every platform selling against it: read what each platform actually holds "
        "rather than what you last sent it, push the correct state out through the "
        "customer's own account on each platform, and where a platform will not "
        "confirm, hold its inventory back rather than let it sell what is no longer "
        "there."
    ),
    "receivables_financing_match": (
        "Here the two sides are the invoices on the rail and the offers providers "
        "will actually fund them at: set every offer on the same basis with its full "
        "cost and its referral commission visible, reconcile the commission received "
        "against the commission due, and leave the choice of offer entirely with the "
        "owner -- you compare, you never recommend."
    ),
    "record_identity_merge": (
        "Here the two sides are the same party arriving twice under different "
        "spellings: score every candidate pair on the identity keys and write the "
        "score down, merge only above the confidence line while carrying every "
        "history item onto the survivor and keeping the merge reversible, and send "
        "everything below the line to a person, because a wrong merge destroys two "
        "records at once."
    ),
    "pay_variance_resolution": (
        "Here the two sides are what somebody was paid and what the job, rota and "
        "system records say they were owed: rebuild the period line by line from "
        "source, show the record behind every difference before the person has to ask "
        "twice, put rule-based corrections through ahead of the payroll cut-off, and "
        "hand anything that needs judgement between two accounts to the named "
        "adjudicator."
    ),
    "payables_match_control": (
        "Here the two sides are what a supplier or a colleague has claimed and what "
        "the order, the receipt and the policy support: state the delta on its own line for "
        "quantity, price and terms, mark each expense line against the clause it was "
        "tested against, and get the hold on a duplicate or a failed match in place "
        "before the payment run reaches it -- you place the hold and never release "
        "your own."
    ),
    "restricted_funds_break": (
        "Here the money is not the business's own, so the two sides are the ledger and "
        "the restriction that binds it: test whose money it is and what it may be "
        "applied to, distinguish a shortfall from a misapplication, and get the exception "
        "in front of the named officer inside the same-day window with the extract "
        "attached and the notice drafted -- correction, reporting and resolution are "
        "theirs."
    ),
    "settlement_break_closure": (
        "Here the two sides are a counterparty's statement or file and what the "
        "business expected to settle: isolate the break down to the file, batch, line "
        "or trade that carries it, name every merchant, account or counterparty "
        "exposed, re-submit only what the scheme's rules already allow, and climb the "
        "escalation ladder against the settlement clock while telling the affected "
        "parties before their own statement does."
    ),
    "claim_recovery_pack": (
        "Here the two sides are a charge somebody else raised and the operating "
        "evidence your contract says decides it: pull the proof the clause names, "
        "compute the valid part as plainly as the invalid part, attribute the charge "
        "from data rather than assumption, and file inside their window -- holding "
        "anything the policy reserves as a draft against the gate with the deadline "
        "showing."
    ),
    "asset_return_reconciliation": (
        "Here the two sides are what went out on the job and what came back: count it "
        "back item by item against the issue list rather than at case level, book the "
        "retrieval for whatever is locatable, and bill anything that is not at the "
        "rate the contract already sets and never at a figure you compose."
    ),
    "ledger_match_exception": (
        "Here the two sides are what was billed and what actually moved: allocate what "
        "arrived against the right invoice and line, leave the residual standing as "
        "its own item instead of smoothing it away, send the statement and start the "
        "chase where money is short or raise the permitted credit where it is over, "
        "and work the exception list down to a zero you can evidence line by line."
    ),
}

"""MF4 -- the clock and calendar engine.

Most families are started by a person: someone calls, a queue fills, a review
appears.  This family is started by a date.  Nobody asks for a recall to go out,
nobody remembers that the notice period on a contract closes in nine days, and
nobody notices the certificate that expired last Tuesday until an inspector
does.  The work exists whether or not anyone thinks of it, which is precisely
why it is the work that gets missed.

So the engine is a clock.  Every unit here holds a register of dated
obligations, each one derived from an anchor in the record and a rule in
configuration -- six months since the last visit, ninety days before the licence
lapses, twenty-one days after the invoice, the statutory period counted in
working days from service.  Each obligation runs down a ladder of rungs at
configured lead times, each rung with its own channel and recipient, and the
last rung fires early enough that the thing can still be done.  The register is
swept on a schedule rather than on demand, and a sweep that finds nothing due is
a reported result rather than silence.

Two failure modes define the family.  The first is the date that passed while
nobody was looking; the second is the date that was marked done because a
message went out about it.  Both are answered the same way: nothing closes on
elapsed time, an obligation is discharged by filed evidence -- the booking
reference, the receipt, the returned confirmation, the issued certificate -- and
anything still open when its date passes goes onto the exception list with a
named owner the same day.

The third standing rule bites hardest at the moment a date forces a choice.
Renew or exit, elect or default, enforce or waive, restrict or let the shift go
ahead: the unit states the date, the rule that sets it and the consequence the
instrument already documents, and it assembles that into a brief early enough to
be a decision rather than an emergency.  The choice itself is a person's.
Everything market-shaped -- the intervals, the statutory periods, the working
calendar, the notice forms -- resolves from the vertical overlay and the active
country pack, so the same engine runs a vaccination recall, a covenant diary and
a receivables ladder without knowing which it is holding.
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

#: Read by every unit of the family.  A date is never a literal in this engine:
#: it is an anchor plus a rule plus a calendar, and all three are configuration.
#: Swap the rule set and the same code runs a boiler service recall, a hearing
#: reminder or a filing diary without a line changing.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="date_rules",
        description=(
            "How each dated obligation this unit holds is derived: the anchor "
            "event it counts from, the interval or term, and whether the period "
            "runs in calendar or working days."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="lead_time_ladder",
        description=(
            "The rungs in front of each due date: how far ahead each one fires, "
            "on which channel, to whom, and which rung stops being a reminder and "
            "becomes an escalation."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="working_calendar",
        description=(
            "Working days, public holidays, weekend convention, time zone and "
            "quiet hours for this market. Every due date and every send is "
            "adjusted against it before it is set."
        ),
        required=True,
    ),
    ConfigKey(
        key="statutory_date_sets",
        description=(
            "Statutory, filing and seasonal date sets for this market, from the "
            "active country pack, with the counting convention each one uses."
        ),
        required=True,
    ),
    ConfigKey(
        key="suppression_rules",
        description=(
            "When a due date must not generate contact: already satisfied, "
            "already booked, opted out, in dispute, bereaved or dormant -- plus "
            "frequency caps and the quiet hours no rung may cross."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="completion_rules",
        description=(
            "What proves a dated obligation was met -- booking reference, "
            "receipt, returned confirmation, filed certificate -- so nothing is "
            "ever closed by time having passed."
        ),
        resolved_by="vertical",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The thirteen date shapes actually present in the catalogue, most specific
#: first.  Match tokens are read against worker, system agent, trigger, function
#: and expected output, and they name the *kind of date* rather than the verbs
#: ("reminder", "chased", "tracked", "diarized") that the whole family shares --
#: those would match everything and separate nothing.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="outage_eta_notice",
        summary=(
            "A disruption already under way, pushed to everyone it touches with "
            "a time attached, and corrected the moment the time moves."
        ),
        match=(
            "outage",
            "etr agent",
            "eta notifier",
            "eta messages",
            "arrival window",
            "restore time",
            "notifications by area",
            "area notifications",
        ),
        steps=(
            step(
                "refresh_the_window",
                "Push a corrected window before the old one expires",
                StepKind.NOTIFY,
                (
                    "Re-read the estimate on the configured interval and push a "
                    "corrected window as soon as it moves past the change threshold. "
                    "A window that quietly runs out is worse than never having given "
                    "one, so the correction goes out ahead of the time it replaces, "
                    "to the same recipients, with the reason it changed."
                ),
                produces=("window_update_log",),
            ),
        ),
        artifacts=(
            artifact(
                "window_update_log",
                "Window update log",
                (
                    "Every window issued for this event: the source estimate behind "
                    "it, the area or customer set it reached, the channel, and when "
                    "and why it was superseded."
                ),
                "log",
            ),
        ),
        tools=("dispatch_feed", "area_resolver", "bulk_notifier"),
        config_keys=(
            ConfigKey(
                key="affected_party_resolution",
                description=(
                    "How an event is resolved to the people it affects -- by route, "
                    "area, site, asset or job -- and the contact list each produces."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="estimate_refresh_policy",
                description=(
                    "How often the arrival or restoration estimate is re-read, and "
                    "the change threshold at which a corrected window must be sent."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "corrected windows sent before the previous window expired",
            "inbound where-is-it contacts per event",
        ),
        channels=("sms", "push_notification", "voice"),
    ),
    Profile(
        name="notice_confirmation",
        summary=(
            "A dated notice whose deadline belongs to the recipient, chased "
            "until the confirmation comes back rather than until it is sent."
        ),
        match=(
            "election",
            "capital call",
            "udi",
            "recall notif",
            "recall notices",
            "notices issued",
            "confirmations chased",
            "default-consequence",
        ),
        steps=(
            step(
                "reconcile_confirmations",
                "Reconcile notices issued against confirmations returned",
                StepKind.ASSESS,
                (
                    "Set every notice issued against every response received, list "
                    "the recipients still silent and chase each on the rung their "
                    "silence has reached. State the position that applies if nothing "
                    "comes back exactly as the instrument sets it -- the register is "
                    "closed by a confirmation, never by the deadline arriving."
                ),
                produces=("confirmation_register",),
            ),
        ),
        artifacts=(
            artifact(
                "confirmation_register",
                "Notice and confirmation register",
                (
                    "Every recipient with the date the notice was served, the form "
                    "and channel it was served in, proof of delivery, the response "
                    "received or still outstanding, and the documented default "
                    "position if the deadline passes in silence."
                ),
                "register",
            ),
        ),
        tools=("holder_register", "notice_issuer", "response_tracker"),
        config_keys=(
            ConfigKey(
                key="notice_service_rules",
                description=(
                    "How a notice of this kind must be served in this market: form, "
                    "channel, minimum period, and what counts as proof of delivery."
                ),
                required=True,
            ),
            ConfigKey(
                key="default_consequence_matrix",
                description=(
                    "What happens to a recipient who does not respond by the "
                    "deadline, per notice or election type, as the instrument "
                    "already documents it."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "notices served inside the required period with delivery proof",
            "recipients who confirmed rather than defaulting by silence",
        ),
        channels=("postal_mail", "email"),
    ),
    Profile(
        name="visit_reminder",
        summary=(
            "A booked commitment reminded down a ladder until it is confirmed, "
            "with the way to move it in every message."
        ),
        match=(
            "no-show",
            "reschedule",
            "72h",
            "reminders with confirm",
            "failure-to-appear",
            "court date",
            "hearing",
            "pre-op",
            "theatre time",
        ),
        steps=(
            step(
                "reconcile_attendance",
                "Reconcile who attended against who was reminded",
                StepKind.ASSESS,
                (
                    "After the appointed time, match attendance against the rungs "
                    "that fired, file the outcome on the record and put a slot freed "
                    "by a no-show back in front of the booking desk the same day. A "
                    "reminder ladder that is never measured against attendance is "
                    "decoration."
                ),
                produces=("attendance_reconciliation",),
            ),
        ),
        artifacts=(
            artifact(
                "attendance_reconciliation",
                "Attendance reconciliation",
                (
                    "Each booked commitment with the rungs sent, the confirmation or "
                    "reschedule received, whether the party attended, the preparation "
                    "items outstanding at the time, and the slot released when they "
                    "did not attend."
                ),
                "report",
            ),
        ),
        tools=("booking_system", "slot_release", "attendance_log"),
        config_keys=(
            ConfigKey(
                key="confirmation_policy",
                description=(
                    "What counts as a confirmation, how long an unconfirmed booking "
                    "is held before the slot is offered elsewhere, and who is told."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="preparation_requirements",
                description=(
                    "What must be complete before the appointment can go ahead -- "
                    "forms, consent, documents, deposit, preparation instructions -- "
                    "and the rung at which each gap is chased."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "bookings confirmed before the appointed time",
            "no-show rate against reminded bookings",
            "preparation gaps closed before the appointment",
        ),
        channels=("sms", "voice"),
    ),
    Profile(
        name="interval_recall",
        summary=(
            "A due date generated from what was last done, worked until it "
            "becomes a booking rather than a message."
        ),
        match=(
            "recall",
            "reactivator",
            "rebook",
            "grooming",
            "vaccinat",
            "vaccine",
            "replenish",
            "reorder",
            "warranty callback",
            "aftercare",
            "snag follow",
            "service interval",
            "interval engine",
            "interval-based",
            "usage cycle",
            "maintenance clock",
            "treatment-type",
        ),
        steps=(
            step(
                "work_the_recall_list",
                "Carry the recall through to a booking",
                StepKind.ACT,
                (
                    "Put real slots inside the reminder itself so the reply is a "
                    "booking rather than a conversation, and keep the record on the "
                    "list until a booking exists, the attempt policy is exhausted or "
                    "the person opts out. A recall that ends in a delivered message "
                    "has not worked; a recall ends in a diary entry."
                ),
                produces=("recall_list",),
            ),
        ),
        artifacts=(
            artifact(
                "recall_list",
                "Recall list",
                (
                    "Everyone due or overdue on their interval with the date of the "
                    "last service, the interval that applies and where it came from, "
                    "the rungs already sent, the booking made, and the opt-outs and "
                    "suppressions excluded with their reason."
                ),
                "register",
            ),
        ),
        tools=("service_history", "booking_system", "slot_finder"),
        config_keys=(
            ConfigKey(
                key="recall_intervals",
                description=(
                    "The interval per service, treatment, product or asset type, the "
                    "anchor it runs from, and the tolerance either side of the due "
                    "date within which a booking still counts as on interval."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="recall_attempt_policy",
                description=(
                    "How many rungs a recall runs, over what period, on which "
                    "channels, and when a record moves to dormant instead of being "
                    "chased again."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "recalls that ended in a booking",
            "records overdue by more than one full interval",
        ),
    ),
    Profile(
        name="membership_cycle",
        summary=(
            "A recurring plan with a renewal date, a pause allowance and a "
            "balance -- none of which may lapse without the member knowing."
        ),
        match=(
            "membership",
            "memberships",
            "loyalty",
            "gift card",
            "season ticket",
            "freeze",
            "member cycles",
        ),
        steps=(
            step(
                "sweep_plan_state",
                "Sweep every plan against its cycle",
                StepKind.ASSESS,
                (
                    "Re-run each plan against its term: what renews this cycle, what "
                    "is frozen and when the freeze ends, what balance or entitlement "
                    "expires alongside it, and what has failed to collect. A plan "
                    "that lapses in silence is a customer nobody decided to lose."
                ),
                produces=("plan_state_register",),
            ),
        ),
        artifacts=(
            artifact(
                "plan_state_register",
                "Plan state register",
                (
                    "Every plan with its term, renewal date, freeze window and "
                    "remaining allowance, the entitlement or points balance and its "
                    "expiry, the collection state behind it and the notice already "
                    "sent."
                ),
                "register",
            ),
        ),
        tools=("subscription_ledger", "entitlement_store", "booking_system"),
        config_keys=(
            ConfigKey(
                key="plan_terms",
                description=(
                    "Term, notice, price band, freeze allowance and cancellation "
                    "rules per plan, and what happens to an unused balance when the "
                    "term rolls."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="freeze_rules",
                description=(
                    "How long a plan may be paused, how often, what it costs and "
                    "what the member keeps while it is frozen."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "renewals processed before the term expired",
            "plans lapsed without a prior notice on file",
            "balances expiring unused after a warning was sent",
        ),
    ),
    Profile(
        name="renewal_notice_clock",
        summary=(
            "An agreement whose notice date falls before its renewal date, "
            "surfaced while the choice is still open."
        ),
        match=(
            "notice-period",
            "notice date",
            "notice dates",
            "auto-renewal",
            "renew-or-exit",
            "break clause",
            "lease event",
            "tenancy",
            "retainer",
            "policy renewal",
            "renewals worked",
            "renewals opened",
            "ahead of expiry",
            "before lapse",
            "renewal outreach",
        ),
        steps=(
            step(
                "assemble_the_renewal_brief",
                "Put the renewal decision in front of the owner in time",
                StepKind.DRAFT,
                (
                    "Before the notice date, assemble what the decision needs: term "
                    "and notice dates, what was used against what was paid, the price "
                    "movement, the comparables or alternatives on file, and what "
                    "follows from each of renew, renegotiate and exit. Deliver it at "
                    "the configured lead time -- a pack that arrives after the notice "
                    "window has closed is a report on a decision already made for you."
                ),
                produces=("renewal_brief",),
            ),
        ),
        artifacts=(
            artifact(
                "renewal_brief",
                "Renewal brief",
                (
                    "The renew-or-exit pack: term and notice dates with the clause "
                    "they come from, usage and cost across the term, price movement, "
                    "alternatives on file, and the documented consequence of each "
                    "option including doing nothing."
                ),
                "document",
            ),
        ),
        tools=("contract_store", "usage_report", "comparables_lookup"),
        config_keys=(
            ConfigKey(
                key="notice_periods",
                description=(
                    "The notice period each agreement type requires, how it is "
                    "counted, and the form the notice itself must take."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="renewal_decision_lead_time",
                description=(
                    "How far before the notice date the decision pack reaches the "
                    "owner, and who decides at each value band."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "renewal decisions taken before the notice date",
            "agreements that rolled by default rather than by decision",
        ),
    ),
    Profile(
        name="credential_validity",
        summary=(
            "A document whose expiry restricts what its holder may do -- "
            "tracked to the renewal, and to the restriction if it lapses."
        ),
        match=(
            "credential",
            "privilege",
            "practitioner",
            "induction",
            "per contractor",
            "contractor cert",
            "certification",
            "work-restriction",
            "restriction flag",
            "work-authorization",
            "visa",
            "passport",
            "validity",
            "ages out",
            "eligibility",
            "expiries chased",
            "expiry tracker",
            "hard-stop",
            "hard stop",
        ),
        steps=(
            step(
                "apply_the_restriction",
                "Raise the restriction the moment the document lapses",
                StepKind.ACT,
                (
                    "When a document passes its expiry, raise the restriction the "
                    "policy already attaches to it -- the flag on the record, the "
                    "removal from the assignable list, the block on the site pass -- "
                    "tell the named holder and supervisor, and hold it in place until "
                    "the renewed document is on file and verified against its issuer. "
                    "The restriction is a fact of the configuration, not a judgement "
                    "about the person."
                ),
                produces=("restriction_record",),
            ),
        ),
        artifacts=(
            artifact(
                "restriction_record",
                "Restriction record",
                (
                    "Each credential past its date with the restriction applied and "
                    "when, who was told, the renewal in progress, and the verified "
                    "document that lifted it."
                ),
                "register",
            ),
        ),
        tools=("credential_register", "document_store", "roster_system"),
        config_keys=(
            ConfigKey(
                key="credential_types",
                description=(
                    "Every credential, permission or status document this business "
                    "must hold for its people, suppliers and clients, with its "
                    "validity period, its issuer and the evidence that proves it."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="lapse_restrictions",
                description=(
                    "What a holder may not do once a document has lapsed, who "
                    "enforces it, who must be told, and the hard cut-off beyond "
                    "which no discretion exists."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "credentials renewed before their expiry date",
            "restricted activity attempted on a lapsed credential",
        ),
    ),
    Profile(
        name="licence_certificate_diary",
        summary=(
            "Recurring tests, inspections, certificates and permits, booked far "
            "enough ahead that a failure can still be remedied."
        ),
        match=(
            "licence",
            "certificate",
            "test due",
            "test-due",
            "tests booked",
            "inspection",
            "type-approval",
            "homologation",
            "roadworth",
            "compliance calendar",
            "compliance diary",
        ),
        steps=(
            step(
                "book_and_file",
                "Book the test early and file the certificate on issue",
                StepKind.ACT,
                (
                    "Book the test, inspection or assessment with enough margin that "
                    "a failed first attempt still leaves time to remedy and re-test, "
                    "hold the contractor slot against the expiry date, and file the "
                    "certificate against the asset the moment it is issued with its "
                    "next expiry already derived. An expired certificate on an asset "
                    "still in use is the failure this profile exists to prevent."
                ),
                produces=("certificate_file",),
            ),
        ),
        artifacts=(
            artifact(
                "certificate_file",
                "Certificate file",
                (
                    "Each asset, site or activity with its current certificate, the "
                    "issuing body, issue and expiry dates, the document itself, any "
                    "remedial actions it required and the next booking already in "
                    "the diary."
                ),
                "document",
            ),
        ),
        tools=("asset_register", "contractor_booking", "document_store"),
        config_keys=(
            ConfigKey(
                key="certificate_regimes",
                description=(
                    "Which tests, inspections and certificates apply to each asset "
                    "class in this market, how often they fall due and who is "
                    "competent to issue them."
                ),
                required=True,
            ),
            ConfigKey(
                key="remediation_lead_time",
                description=(
                    "How far ahead of expiry each test is booked so a failure can be "
                    "remedied and re-tested before the certificate runs out."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "certificates renewed before expiry",
            "assets in use on an expired certificate",
        ),
        channels=("postal_mail",),
    ),
    Profile(
        name="deadline_docket",
        summary=(
            "A deadline somebody else sets, docketed the day the matter opens "
            "and run down an alert ladder to the person who must act."
        ),
        match=(
            "docket",
            "limitation",
            "statute deadline",
            "ladder",
            "deadline calendar",
            "scholarship",
            "deadlines collide",
            "deposit-deadline",
            "foi",
            "dormant",
            "dormancy",
            "scheme deadline",
            "statutory window",
            "forfeit",
        ),
        steps=(
            step(
                "verify_the_docket",
                "Re-derive every docketed date and check it still holds",
                StepKind.ASSESS,
                (
                    "Recompute each docketed date from its anchor and its rule, "
                    "re-check it against the current calendar and against anything "
                    "that has changed in the underlying matter, and confirm each one "
                    "still has a named owner with the preparatory work sequenced "
                    "backwards from it. A date nobody owns is a date nobody meets."
                ),
                produces=("docket_entry",),
            ),
        ),
        artifacts=(
            artifact(
                "docket_entry",
                "Docket entry",
                (
                    "Each deadline with the rule or authority that sets it, the "
                    "anchor date and the calculation shown, the rungs already fired, "
                    "the work sequenced backwards from it and the named owner of "
                    "each piece."
                ),
                "register",
            ),
        ),
        tools=("docket_register", "deadline_calculator", "matter_lookup"),
        config_keys=(
            ConfigKey(
                key="deadline_rules",
                description=(
                    "How each deadline type is calculated in this market: the anchor "
                    "event, the period, whether it runs in calendar or working days, "
                    "and how it moves when it lands on a non-working day."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="deadline_escalation_owners",
                description=(
                    "Who is alerted at each rung as the date approaches, up to the "
                    "point at which a missed date itself becomes a reportable event."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "deadlines docketed on the day the matter opened",
            "deadlines met with the required work filed inside the window",
        ),
        channels=("postal_mail",),
    ),
    Profile(
        name="filing_calendar",
        summary=(
            "Periodic returns to a named office: assembled from source data, "
            "signed by whoever must sign, filed on the date, receipt kept."
        ),
        match=(
            "filing",
            "tax calendar",
            "per office",
            "trademark",
            "patent",
            "reclaim",
            "gift-aid",
        ),
        steps=(
            step(
                "assemble_the_return",
                "Assemble the return and hold it for signature",
                StepKind.DRAFT,
                (
                    "Build the return in the form the office requires, with every "
                    "figure traced back to the source system it came from and every "
                    "missing item listed against whoever holds it. Hold the pack for "
                    "the signature the filing requires; you prepare and you submit "
                    "what has been signed, and you never decide what the return "
                    "should say."
                ),
                produces=("filing_pack",),
            ),
        ),
        artifacts=(
            artifact(
                "filing_pack",
                "Filing pack",
                (
                    "The return with each figure traced to its source, the schedules "
                    "and attachments the office requires, the outstanding items with "
                    "their holders, the signature obtained and the submission receipt "
                    "once filed."
                ),
                "document",
            ),
        ),
        tools=("filing_portal", "source_ledger", "document_store"),
        config_keys=(
            ConfigKey(
                key="filing_obligations",
                description=(
                    "Which returns this business owes in this market, to which "
                    "office, on what frequency, in what form and by when."
                ),
                required=True,
            ),
            ConfigKey(
                key="filing_signature_roles",
                description=(
                    "Who must sign each return before it is submitted, the lead time "
                    "they need, and the substitute when they are unavailable."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "returns filed before their date with a receipt on file",
            "returns filed late or amended after submission",
        ),
        channels=("postal_mail",),
    ),
    Profile(
        name="receivables_dunning",
        summary=(
            "Money owed on a clock: staged reminders, a link that works, a "
            "receipt, and an aging list nobody has to assemble by hand."
        ),
        match=(
            "invoic",
            "receivable",
            "aging",
            "arrears",
            "rent collector",
            "rent and service-charge",
            "fee cycles",
            "fee reminder",
            "term fee",
            "payment collector",
            "payment links",
            "retries",
            "receipts",
            "split payers",
            "payment failed",
            "grace-period",
            "premium finance",
            "cover-lapse",
            "demurrage",
            "detention",
            "free-time",
            "storage-fee",
            "fee-accrual",
            "cash collected",
            "deposit-and-confirm",
        ),
        steps=(
            step(
                "age_and_escalate",
                "Re-age the ledger and move each balance to its rung",
                StepKind.ASSESS,
                (
                    "Re-age every open balance each run, move it to the rung its age "
                    "and the arrears policy dictate, and show any charge that has "
                    "accrued with the clause in the terms that produced it. At the "
                    "end of the ladder the account goes to the owner with its full "
                    "contact and payment history attached, rather than any further "
                    "step being taken on your own authority."
                ),
                produces=("aging_report",),
            ),
        ),
        artifacts=(
            artifact(
                "aging_report",
                "Aging report",
                (
                    "Every open balance by age band with the rung it has reached, "
                    "the promises made and kept, payments and part-payments "
                    "received, charges accrued under the terms with their clause, "
                    "and the accounts now at the end of the ladder."
                ),
                "report",
            ),
        ),
        tools=("ledger_lookup", "payment_link_issuer", "receipt_issuer"),
        config_keys=(
            ConfigKey(
                key="arrears_policy",
                description=(
                    "The dunning rungs, the charge or interest the terms allow at "
                    "each, the grace period, and the point at which access or "
                    "service is affected."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="payment_plan_rules",
                description=(
                    "Instalment arrangements the unit may offer without asking, the "
                    "ratios and splits it may apply, and the hardship cases that go "
                    "to a person instead."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "balances collected before the final rung",
            "days sales outstanding against the payment term",
            "accounts escalated with a complete contact history attached",
        ),
    ),
    Profile(
        name="campaign_calendar",
        summary=(
            "Dated moments planned out to a horizon, queued for the owner ahead "
            "of their lead time, published only from the customer's accounts."
        ),
        match=(
            "seasonal",
            "campaign calendar",
            "promotions",
            "occasion",
            "birthday",
            "anniversar",
            "liveops",
            "event calendar",
            "content calendar",
            "content scheduler",
            "cross-platform",
        ),
        steps=(
            step(
                "queue_the_slots",
                "Build the calendar and queue each slot for the owner",
                StepKind.ACT,
                (
                    "Plan out to the configured horizon, one slot per dated moment "
                    "with its asset, audience and offer attached, and put each slot "
                    "in front of the owner ahead of its own lead time. A slot the "
                    "owner has released publishes on its date from the customer's own "
                    "connected accounts; nothing goes out from a platform account, "
                    "and nothing goes out that a person has not released."
                ),
                produces=("slot_calendar",),
            ),
        ),
        artifacts=(
            artifact(
                "slot_calendar",
                "Slot calendar",
                (
                    "The dated plan: every slot with its date, the moment or season "
                    "it belongs to, the asset and offer attached, its release state "
                    "and the account it went out from."
                ),
                "calendar",
            ),
        ),
        tools=("content_calendar", "asset_library", "scheduler"),
        config_keys=(
            ConfigKey(
                key="seasonal_calendar",
                description=(
                    "Dated moments that matter in this market -- seasons, holidays, "
                    "observances and trading peaks -- from the active country pack."
                ),
                required=True,
            ),
            ConfigKey(
                key="campaign_lead_times",
                description=(
                    "How far ahead of each moment the plan, the assets and the "
                    "owner's release are needed, per channel."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "slots released before their lead time expired",
            "dated moments covered against the market calendar",
        ),
        channels=("social", "email"),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: a commitment somebody made on a date, carried until the evidence
    # that discharges it is on file.
    Profile(
        name="dated_obligation",
        summary=(
            "A commitment with a date on it, held against the clause that "
            "created it and closed only by the evidence that discharges it."
        ),
        match=(),
        steps=(
            step(
                "sweep_the_obligations",
                "Sweep the register against today",
                StepKind.ASSESS,
                (
                    "Run the register against the run date: what falls due next, what "
                    "is overdue, what has been discharged with evidence and what has "
                    "quietly lost its owner. Every entry carries the clause or "
                    "instrument that created it, so the chase quotes the source rather "
                    "than asserting the requirement."
                ),
                produces=("obligation_register",),
            ),
        ),
        artifacts=(
            artifact(
                "obligation_register",
                "Obligation register",
                (
                    "Every dated commitment with the clause or instrument that "
                    "created it, the party who owes it, the date it falls due, the "
                    "evidence that will discharge it and its state today."
                ),
                "register",
            ),
        ),
        tools=("obligation_register", "contract_store", "document_store"),
        config_keys=(
            ConfigKey(
                key="obligation_sources",
                description=(
                    "Where dated commitments are extracted from for this business -- "
                    "agreements, instruments, permits, schedules, awards -- and who "
                    "owns each type once extracted."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="obligation_review_cycle",
                description=(
                    "How often the register is re-derived from its source documents, "
                    "and who receives the overdue and unowned lists."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "obligations discharged with evidence on or before their date",
            "obligations sitting in the register without a named owner",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class ClockCalendarEngine(Engine):
    """Carries every unit whose work is generated by a date rather than a person.

    One skeleton -- read the clock, assemble the dates and their records, place
    each on its ladder, choose the rung or the gate, draft, act, and raise what
    is at risk -- and thirteen profiles that say what kind of date is being
    held.  Nothing in the code knows whether the date is a vaccination interval,
    a notice period or a statutory filing: the anchor, the rule, the ladder and
    the working calendar all arrive as configuration.
    """

    id: ClassVar[str] = "MF4"
    family: ClassVar[str] = "Clock & calendar engine"
    what_it_does: ClassVar[str] = (
        "Renewal, recall, statutory, covenant, AR and reminder dates"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.CLOCK,
        Capability.SCHEDULE,
        Capability.SEQUENCE,
        Capability.WATCH_SIGNAL,
        Capability.RECONCILE,
        Capability.COLLECT_DOCUMENTS,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "diary_store",
        "clock_scheduler",
        "calendar_service",
        "message_sender",
        "booking_system",
        "document_store",
        "task_queue",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "email",
        "messaging",
        "calendar_invite",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "dates actioned inside their lead-time window",
        "obligations that passed their date unseen",
        "rungs delivered against rungs scheduled",
        "dates closed on filed evidence rather than on elapsed time",
        "decisions handed over before the date forced them",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "date_register"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Read the clock, derive, position, choose, draft, act, raise.

        The order carries the discipline.  Dates are re-derived from their
        anchors before anything is judged overdue, the record behind a date is
        loaded before a message is written about it, and the exception list goes
        out last -- after the run has happened -- so it describes what is
        actually still at risk rather than what was at risk before the sweep.
        """
        return (
            step(
                "read_the_clock",
                "Read the clock and pull what is in the window",
                StepKind.OBSERVE,
                (
                    "Fix the run date against the market's working calendar, time "
                    "zone and holidays, then pull every dated obligation whose "
                    "lead-time window is now open together with everything already "
                    "past its date and not yet discharged. The sweep runs on its "
                    "schedule whether or not anything is due; an empty window is a "
                    "result you report, not a run that did not happen."
                ),
                produces=("due_window_list",),
            ),
            step(
                "assemble_the_dates",
                "Re-derive each date and load what sits behind it",
                StepKind.GATHER,
                (
                    "Recompute each due date from its anchor and the configured rule "
                    "rather than trusting the number stored last time, and load the "
                    "record it belongs to: the agreement, treatment, asset, invoice, "
                    "credential or matter, the contact and consent state of everyone "
                    "a rung would reach, and any evidence already filed against it."
                ),
                produces=("date_register",),
            ),
            step(
                "place_on_the_ladder",
                "Place every date on its ladder",
                StepKind.ASSESS,
                (
                    "Work out, for each date, how far it is from due in the calendar "
                    "that governs it, which rung that distance selects, whether the "
                    "obligation is already satisfied, suppressed, opted out or in "
                    "dispute, and whether the remaining time is still enough for the "
                    "thing to be done. Show the arithmetic: a date you cannot "
                    "derive is a date you may not act on."
                ),
                produces=("date_register",),
            ),
            step(
                "choose_the_rung",
                "Choose the rung, the escalation or the gate",
                StepKind.DECIDE,
                (
                    "For each date, pick what the ladder says: fire the next rung, "
                    "hold because a suppression applies, or stop because the date "
                    "forces a judgement -- renew or exit, elect or default, enforce "
                    "or waive, restrict or let it run. Where it is a judgement, the "
                    "gate is the answer and it is raised now, with time still on the "
                    "clock, rather than reported after the date has gone."
                ),
            ),
            step(
                "draft_the_notice",
                "Draft the rung and, where needed, the brief",
                StepKind.DRAFT,
                (
                    "Write the rung in the recipient's language and channel: what is "
                    "due, the date it is due, what happens if it is missed as the "
                    "rule or the terms already document it, and the one action that "
                    "discharges it with a way to take it. Where a person must "
                    "decide, draft the brief alongside -- the options, what each "
                    "costs, the deadline on the decision itself."
                ),
                produces=("advance_notice", "decision_brief"),
            ),
            step(
                "act_and_rearm",
                "Send, book, file, and re-arm the clock",
                StepKind.ACT,
                (
                    "Send the rung from the customer's own connected accounts inside "
                    "the configured quiet hours, take the action the date exists for "
                    "where it is within your authority -- the booking, the payment "
                    "link, the submission, the restriction -- record the evidence "
                    "that discharges the obligation, and set the next due date from "
                    "the rule rather than from today. An obligation is never marked "
                    "met because a message about it went out."
                ),
                produces=("ladder_log", "completion_evidence"),
            ),
            step(
                "raise_what_is_at_risk",
                "Raise everything still at risk to a named owner",
                StepKind.NOTIFY,
                (
                    "Send the exception list on its own cadence: what is overdue, "
                    "what is undeliverable, what is unowned, what will be missed at "
                    "the present rate and what needs a decision, each with the name "
                    "of the person it now sits with. Send it whether or not anything "
                    "went wrong, because the absence of an exception list reads "
                    "exactly like a run that never happened."
                ),
                produces=("exception_report",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "date_register",
                "Date register",
                (
                    "The clock itself: every dated obligation with its anchor, the "
                    "rule and calendar that produced the due date, the ladder it runs "
                    "on, its owner and its current state."
                ),
                "register",
            ),
            artifact(
                "due_window_list",
                "Due window list",
                (
                    "What this run picked up: everything inside its lead-time window "
                    "and everything already past its date, ranked by days to or past "
                    "due, with the rung each has reached."
                ),
                "report",
            ),
            artifact(
                "advance_notice",
                "Advance notice",
                (
                    "The rung as it was sent: what is due, when, the consequence the "
                    "rule or the terms document, the action that discharges it, in "
                    "the recipient's language and channel."
                ),
                "message",
            ),
            artifact(
                "ladder_log",
                "Ladder log",
                (
                    "Every rung fired for every obligation with its channel, "
                    "recipient, timestamp, delivery status and the response it drew, "
                    "plus every rung suppressed and the rule that suppressed it."
                ),
                "log",
            ),
            artifact(
                "completion_evidence",
                "Completion evidence",
                (
                    "What proves the obligation was met: the booking reference, "
                    "receipt, returned confirmation, filed certificate or submission "
                    "receipt, filed against the date it discharges."
                ),
            ),
            artifact(
                "exception_report",
                "Exception report",
                (
                    "Dates overdue, undeliverable, unowned or heading for a miss, "
                    "each with the reason, the time remaining and the named person "
                    "it now sits with."
                ),
                "report",
            ),
            artifact(
                "decision_brief",
                "Decision brief",
                (
                    "The pack handed over when a date forces a judgement: the "
                    "options, what each costs, the evidence behind them, the deadline "
                    "on the decision and what happens if it is not taken."
                ),
                "document",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"The intervals, terms and statutory periods for "
                f"{vertical['name'].lower()} come from the vertical overlay and the "
                f"active country pack -- never from the last time this was done by "
                f"hand."
            )
        else:
            where = (
                "This clock runs in every vertical on the platform, so the "
                "intervals, terms and statutory periods are whatever the overlay and "
                "the country pack in front of you supply."
            )
        return (
            "HOW YOU WORK. Your work is generated by dates, not by anyone asking "
            "for it, so nothing reaches you as a request and everything reaches you "
            "as a due date. Every date you hold is derived -- an anchor in the "
            "record, a rule in configuration, a working calendar to count in -- and "
            "you re-derive it rather than trusting the number you stored last time, "
            "because a date you cannot show the arithmetic for is one you may not "
            "act on. You run a ladder rather than a reminder: rungs at configured "
            "lead times, each with its channel and its recipient, the last one early "
            "enough that the thing can still be done, and every rung tested against "
            "the suppression rules before it goes out so nobody is chased for "
            "something they have already settled. You sweep on your schedule whether "
            "or not anything is due, and you report the empty sweep, because the "
            "failure this family exists to prevent is a date that passed while "
            "nobody was looking. Nothing closes because time went by: an obligation "
            "is discharged by filed evidence -- the booking, the receipt, the "
            "returned confirmation, the certificate -- and anything still open when "
            "its date passes goes on the exception list the same day with a named "
            "owner. You state the date, the rule that sets it and the consequence "
            "the terms already document; the decision the date forces belongs to a "
            "person, and your job is to put it in front of them while it is still a "
            f"decision. {self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-DATE-IS-DERIVED",
                rule=(
                    "Every due date is derived from an anchor in the record and a "
                    "rule in configuration. No date is typed in, remembered or "
                    "inferred from a previous message."
                ),
                check=(
                    "Each date_register entry carries its anchor date, the source "
                    "field or document it came from and the date_rules id that "
                    "produced it; an entry missing any of the three cannot fire a "
                    "rung."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CALENDAR-ADJUSTED",
                rule=(
                    "Dates and sends are counted in the market's working calendar "
                    "and time zone, not in raw days, and a rung never lands after "
                    "the date it is warning about."
                ),
                check=(
                    "Every due date records the working_calendar version used and "
                    "the holiday or weekend adjustment applied; every scheduled rung "
                    "resolves to a send time inside quiet hours and before the due "
                    "date."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NO-SILENT-LAPSE",
                rule=(
                    "No date passes unaccounted for. Every obligation whose date has "
                    "gone is either discharged with evidence or on the exception "
                    "list with a named owner."
                ),
                check=(
                    "At the end of each run, every date_register entry past its due "
                    "date maps to either a completion_evidence record or an "
                    "exception_report line naming the person it now sits with."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-EVIDENCE-NOT-ELAPSED",
                rule=(
                    "An obligation is closed by the evidence that discharges it, "
                    "never by time passing and never by a reminder having been sent."
                ),
                check=(
                    "A close is refused unless an artefact satisfying "
                    "completion_rules is attached; delivery of a rung updates the "
                    "ladder_log only and never the obligation's state."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-SUPPRESSION-HONOURED",
                rule=(
                    "A due date that is already satisfied, opted out, in dispute or "
                    "suppressed generates no contact, and no ladder exceeds the "
                    "configured frequency cap."
                ),
                check=(
                    "Every rung is tested against suppression_rules and the contact "
                    "and consent state before sending, and each suppression is "
                    "written to the ladder_log with the rule that caused it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-DEADLINE-IMMOVABLE",
                rule=(
                    "The unit never moves, waives, extends or restarts a statutory "
                    "or contractual date. It sets and re-arms its own reminders and "
                    "nothing else."
                ),
                check=(
                    "Dates sourced from statutory_date_sets or from an agreement are "
                    "written once and read thereafter; any change carries an actor, "
                    "a reason and the authority that granted it, and raises a gate."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CONSEQUENCE-CITED",
                rule=(
                    "A notice states the date, the rule that sets it and the "
                    "documented consequence of missing it. It never tells the "
                    "recipient which way to decide."
                ),
                check=(
                    "Every consequence sentence in an advance_notice cites the "
                    "clause, rule or statute reference it came from, and any choice "
                    "the date forces appears in the decision_brief as options rather "
                    "than as a recommendation."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-RUN-IS-VISIBLE",
                rule=(
                    "A sweep that finds nothing still reports. Silence from this "
                    "unit is indistinguishable from a unit that has stopped running."
                ),
                check=(
                    "Each scheduled sweep writes a run record with the window "
                    "covered, the counts examined, actioned and suppressed, and "
                    "delivers the exception_report even when it is empty."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "Date register for this business with every obligation and its due date",
            "Anchor records the dates derive from: agreements, services, assets, "
            "invoices, credentials",
            "Working calendar, public holidays, time zone and quiet hours for this "
            "market",
            "Contact and consent state for every party a rung would reach",
            "Evidence already filed against dates that have passed",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming the kind of date this profile is holding.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer may override.
        """
        return _PROFILE_MISSION_LINES.get(
            profile.name, _PROFILE_MISSION_LINES["dated_obligation"]
        )


#: Mission prose per profile.  Each names the kind of date, what discharges it
#: and the exact point at which the unit stops and a person takes over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "outage_eta_notice": (
        "Your date is a time you have promised somebody: resolve the event to "
        "everyone it affects, give them a window rather than an apology, re-read "
        "the estimate on its interval and push the correction before the window "
        "you gave them runs out -- and describe the disruption without ever "
        "attributing a cause that has not been established."
    ),
    "notice_confirmation": (
        "Your date belongs to the recipient rather than to you: serve the notice "
        "in the form and period the instrument requires, keep proof of delivery, "
        "chase every holder who has not answered, and state the default position "
        "that applies in silence exactly as the instrument sets it -- the register "
        "closes on confirmations returned, not on notices sent."
    ),
    "visit_reminder": (
        "Your date is a commitment somebody has already made: remind down the "
        "ladder with the way to confirm and the way to move it in every message, "
        "chase the preparation the appointment depends on, and reconcile "
        "attendance afterwards so the slot a no-show freed goes back to the "
        "booking desk the same day."
    ),
    "interval_recall": (
        "Your date is generated by what was last done: hold the interval, its "
        "anchor and its tolerance, put real slots inside the reminder so the reply "
        "is a booking, and keep working the list until there is a booking, the "
        "attempts are exhausted or the person opts out -- a delivered message is "
        "not an outcome."
    ),
    "membership_cycle": (
        "Your date is a recurring term: carry each plan through renewal, freeze "
        "and expiry together, warn before a balance or entitlement lapses with it, "
        "and never let a plan end in silence -- a member who discovers the lapse "
        "themselves has already left."
    ),
    "renewal_notice_clock": (
        "Your date is the notice date rather than the renewal date, and it is the "
        "one that decides the outcome: work backwards from it, assemble what was "
        "used against what was paid and what the alternatives are, and deliver the "
        "pack early enough that renewing, renegotiating and exiting are all still "
        "available."
    ),
    "credential_validity": (
        "Your date is a document's expiry and it restricts what its holder may do: "
        "chase the renewal down the ladder, apply the restriction the policy "
        "attaches the moment the date passes, tell the holder and the supervisor, "
        "and hold the restriction until the renewed document is on file and "
        "verified against its issuer."
    ),
    "licence_certificate_diary": (
        "Your date is a certificate's expiry on an asset that stays in use: book "
        "the test with enough margin that a failure can still be remedied and "
        "re-tested, hold the slot, file the certificate against the asset the "
        "moment it is issued, and derive the next expiry from it rather than from "
        "the day it was filed."
    ),
    "deadline_docket": (
        "Your date is set by somebody else and missing it is the loss: docket it "
        "the day the matter that creates it exists, show the calculation and the "
        "authority behind it, sequence the preparatory work backwards from it, and "
        "run the alert ladder to a named owner rather than to a queue."
    ),
    "filing_calendar": (
        "Your date is a return owed to a named office: assemble it from the source "
        "systems with every figure traceable, list what is missing and who holds "
        "it, hold the pack for the signature the filing requires, submit only what "
        "has been signed and keep the receipt as the evidence the date is "
        "discharged."
    ),
    "receivables_dunning": (
        "Your date is a payment term: age the ledger, work the rungs the arrears "
        "policy sets, put a working link and a receipt on every touch, quote only "
        "figures the ledger and the published terms already contain, and hand "
        "hardship, write-off and enforcement to the owner with the full history "
        "attached."
    ),
    "campaign_calendar": (
        "Your dates are the moments the market already has -- seasons, holidays, "
        "occasions, releases: plan out to the horizon, attach an asset and an offer "
        "to each slot, put every slot in front of the owner ahead of its lead time, "
        "and publish only from the customer's own connected accounts once a person "
        "has released it."
    ),
    "dated_obligation": (
        "Your date is a commitment somebody made in writing: extract it with the "
        "clause that created it, give it an owner and a discharge test, chase it "
        "with the source quoted rather than asserted, and close it only on the "
        "evidence -- an obligation nobody owns is one nobody meets."
    ),
}

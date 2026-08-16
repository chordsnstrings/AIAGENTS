"""MF10 -- the capacity and scheduling engine.

What these businesses sell only exists at a time.  An hour of a stylist's chair,
a bay with a ramp in it, a bed, a seat in Tuesday's class, a crew's morning, a
table at eight: none of it can be stored, and an hour that passes unsold is not
inventory carried forward, it is revenue that never existed.  That is why this
family is the one owners feel first.  Every other family produces work; this one
decides whether the work can physically happen, and it is judged on two numbers
that pull against each other -- how little capacity stands idle, and how few
commitments are broken to fill it.

So the engine holds a ledger rather than a calendar.  Every bookable resource
appears in it with the windows it actually works, what is committed against it,
what is on hold, and what is blocked by absence, closure, travel or a job
overrunning; and each of those states carries the time it was last read, because
availability that is minutes old is not availability.  A window is only offerable
once it has survived the whole envelope the work needs -- duration, setup and
clean-down, buffer, the travel legs either side, the skill, licence, equipment
and access it requires -- and nothing is ever promised before it has been held.
The gap between saying a time out loud and writing it down is where every double
booking is made, and closing that gap is most of what this engine does.

Three failure modes shape it.  Capacity committed twice, which the customer
discovers rather than the business.  Capacity that was never really free -- a
cached diary, a resource nobody recognised was on leave, a route that assumed a
van teleports.  And the silent change: a time that moved without the people
standing at the other end of it being told.  The answers are structural rather
than diligent -- a collision-checked write under a hold, a live read at the
moment of commitment, and a broadcast to every party a change touches inside the
notice period the policy sets.

The third standing rule bites hardest when capacity runs short, because then
somebody loses.  You rank the competing demands against the configured priority
policy, you state exactly what would have to move to fit the next one in and what
it costs, and you stop: whose booking is bumped, which customer is disappointed,
whether the tie breaks on value or on need is an owner's judgement, and a
scheduler that quietly displaces people has stopped being a scheduler.
Everything market- and trade-shaped -- what a unit of capacity is, how long the
work takes, who is competent to do it, how far apart two jobs really are, whose
claim is protected -- resolves from the vertical overlay and the active country
pack, so the same engine runs a salon column, an operating-theatre list and a
harvest crew without knowing which it is holding.
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

#: Read by every unit of the family.  Nothing here is a constant in the code: a
#: slot is thirty minutes in one vertical and a three-day window in another, a
#: resource is a chair, a bay, a bed or a combine harvester, and who gets
#: protected when the day will not fit is an owner's policy rather than an
#: algorithm's opinion.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="capacity_model",
        description=(
            "What a unit of capacity is for this business -- a slot, a chair, a "
            "bay, a bed, a seat, a table, a crew-hour, a vehicle-day -- how many "
            "exist per resource and window, and the overbooking allowance, if "
            "any, that may be committed beyond the nominal count."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="booking_rules",
        description=(
            "Per service or job type: duration, setup and clean-down, the buffer "
            "either side, minimum notice, booking horizon, cut-off, and the "
            "cancellation and change windows the published terms allow."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="resource_eligibility",
        description=(
            "Which resources may take which work: the skills, grades, licences, "
            "certifications, languages, equipment and site access each job "
            "requires, and the pairings the business forbids."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="priority_policy",
        description=(
            "How competing demands are ranked when capacity is short -- urgency, "
            "clinical or statutory need, contract, tier, value, order of arrival "
            "-- and the tie-breaks that go to a person instead of being ranked."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="working_calendar",
        description=(
            "Opening hours, shift patterns, public holidays, seasonal closures, "
            "time zone and quiet hours for this market. Every window offered and "
            "every message sent is adjusted against it first."
        ),
        required=True,
    ),
    ConfigKey(
        key="change_notification_rules",
        description=(
            "Who must be told when a committed time moves, how far ahead, on "
            "which channel, and what the published terms owe the affected party "
            "when the business is the one that moved it."
        ),
        resolved_by="owner",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The eleven scheduling shapes actually present in the catalogue, ordered
#: specific before general.  Match tokens name the *shape of the constraint* --
#: an absent person, a broken day, a waiting list, a map, a fixed pool -- rather
#: than the verbs the whole family shares.  "Booked", "slot", "schedule" and
#: "capacity" appear in almost every unit here and would separate nothing.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="cover_scramble",
        summary=(
            "Somebody rostered has not appeared: qualified cover found against "
            "the clock, and the people waiting told before they notice."
        ),
        # Absence language is unmistakable and appears nowhere else in the
        # family, so this profile can safely sit first.
        match=(
            "no-show",
            "calls in sick",
            "teacher absent",
            "cover blast",
            "cover cascade",
            "cover dispatch",
            "cover assigned",
            "cover found",
            "cover sent",
            "backup network",
            "backup interpreter",
            "key crew cancels",
        ),
        steps=(
            step(
                "close_the_cover_loop",
                "Close the loop on the cover attempt",
                StepKind.ASSESS,
                (
                    "Record who was asked, in what order, who accepted, who declined "
                    "and how long the cascade took, and update the reliability record "
                    "of the absent party and of everyone who answered. Where the "
                    "cascade is exhausted and the work is still uncovered, hand it "
                    "over with the ranked list of who would be affected and what the "
                    "published terms owe each of them -- which commitment is dropped "
                    "is not yours to pick."
                ),
                produces=("cover_cascade_log",),
            ),
        ),
        artifacts=(
            artifact(
                "cover_cascade_log",
                "Cover cascade log",
                (
                    "The absence with the time it became known, every person asked "
                    "with their tier, channel and response, the cover accepted and "
                    "when, the parties told and what they were offered, and the work "
                    "left uncovered with its owner."
                ),
                "log",
            ),
        ),
        tools=("standby_pool", "bulk_notifier", "reliability_register"),
        config_keys=(
            ConfigKey(
                key="cover_cascade",
                description=(
                    "The qualified pool per role and site, the order the tiers are "
                    "worked, how long each tier holds before the next is opened, and "
                    "the point at which the work is declared uncoverable."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="absence_compensation_rules",
                description=(
                    "What the published terms owe a customer, member or client when "
                    "a session is covered late, moved or lost: credit, free rebook, "
                    "refund, and who may authorise each."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "minutes from absence detected to cover accepted",
            "sessions lost outright after the cascade was exhausted",
            "affected parties told before they arrived",
        ),
        channels=("sms", "push_notification", "voice"),
    ),
    Profile(
        name="disruption_recovery",
        summary=(
            "A schedule already committed is broken by weather, breakage or "
            "collision: the knock-on recomputed and every displaced party "
            "re-timed."
        ),
        match=(
            "double booking",
            "weather",
            "breakdown",
            "breaks mid-day",
            "tooling failure",
            "disruption",
            "recovery arranged",
            "reroute",
            "rebalanced",
            "cascade recomputed",
            "scramble",
        ),
        steps=(
            step(
                "close_out_the_displaced",
                "Account for every commitment the disruption touched",
                StepKind.ASSESS,
                (
                    "Sweep the displaced list before you finish: each commitment the "
                    "event touched now holds a new confirmed time, an agreed credit "
                    "from the published terms, or a line on the exception list with "
                    "the person it sits with. Write the delay notice alongside it -- "
                    "what happened, when it became known, what moved as a result and "
                    "the consequence the contract already documents -- because a "
                    "disruption nobody recorded on the day cannot be evidenced when "
                    "it is later claimed against."
                ),
                produces=("displacement_register", "disruption_notice"),
            ),
        ),
        artifacts=(
            artifact(
                "displacement_register",
                "Displacement register",
                (
                    "Every commitment the disruption touched with its original time, "
                    "the reason it moved, its new time or its credit, who was told "
                    "and when, and the ones still unplaced with their owner."
                ),
                "register",
            ),
            artifact(
                "disruption_notice",
                "Disruption notice",
                (
                    "The dated record of the event: what occurred, when it became "
                    "known, the work and parties affected, the revised sequence and "
                    "the contractual consequence as the terms already document it."
                ),
                "document",
            ),
        ),
        tools=("dependency_graph", "forecast_feed", "bulk_notifier"),
        config_keys=(
            ConfigKey(
                key="dependency_rules",
                description=(
                    "What depends on what: the lead and lag between stages, the work "
                    "that cannot start until a predecessor is complete, and how far "
                    "a change propagates downstream before it needs a decision."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="disruption_policy",
                description=(
                    "The order in which commitments are protected when capacity "
                    "collapses, the goodwill and compensation the published terms "
                    "permit, and who must be told within what window."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="forecast_thresholds",
                description=(
                    "The weather, traffic and condition feeds used in this market "
                    "and the thresholds at which work is held, moved or re-sequenced "
                    "rather than attempted."
                ),
                required=True,
            ),
        ),
        kpis=(
            "affected parties re-timed before their original window passed",
            "displaced commitments still unplaced at the end of the run",
            "delay notices filed on the day the event occurred",
        ),
        channels=("sms", "voice", "push_notification"),
    ),
    Profile(
        name="waitlist_backfill",
        summary=(
            "Capacity that came free, offered down a waiting list in the order "
            "policy sets, until it is filled or the offer window closes."
        ),
        match=(
            "waitlist",
            "standby",
            "seat-filler",
            "seat inventory",
            "backfill",
            "last-minute",
            "empty slots",
            "cancelled slots",
            "places offered",
            "departures filled",
            "full classes",
        ),
        steps=(
            step(
                "work_the_waiting_list",
                "Offer the opening down the list in order",
                StepKind.ACT,
                (
                    "Offer the opening in the configured order, holding the capacity "
                    "for whoever is being asked so nobody else takes it mid-offer, "
                    "and move down only when the response window closes or the offer "
                    "is declined. Record every offer, decline, timeout and skip "
                    "against the party and the rule that permitted it; if the list "
                    "runs out the capacity returns to open, never to filled."
                ),
                produces=("waitlist_register",),
            ),
        ),
        artifacts=(
            artifact(
                "waitlist_register",
                "Waitlist register",
                (
                    "Everyone waiting with the date they joined, what they are "
                    "waiting for, their stated availability and constraints, their "
                    "position and the rule that sets it, and every offer made with "
                    "its outcome and timestamp."
                ),
                "register",
            ),
        ),
        tools=("waitlist_store", "slot_release", "bulk_notifier"),
        config_keys=(
            ConfigKey(
                key="waitlist_order",
                description=(
                    "What sets position on the list -- join date, tier, clinical or "
                    "statutory priority, sibling or group rules, spend -- and the "
                    "departures from strict order the policy permits, each with the "
                    "reason that justifies it."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="offer_window",
                description=(
                    "How long one party holds an offer before it passes on, how many "
                    "may hold the same opening at once, and the cut-off after which "
                    "an opening is released to general sale instead."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "freed capacity refilled before its start time",
            "offers accepted per opening worked",
            "positions passed over without a recorded rule",
        ),
        channels=("sms", "push_notification"),
    ),
    Profile(
        name="emergency_dispatch",
        summary=(
            "An urgent job graded into a response window at any hour, with an "
            "arrival time committed to and corrected rather than guessed."
        ),
        # Sits ahead of the routing profile because these units are dispatchers
        # too; what separates them is the grade and the clock, not the map.
        match=(
            "severity",
            "24/7",
            "out-of-hours",
            "any hour",
            "tow/recovery",
            "recovery dispatch",
            "emergency",
        ),
        steps=(
            step(
                "hold_the_arrival_window",
                "Commit to a window and correct it before it expires",
                StepKind.NOTIFY,
                (
                    "Give the caller a window rather than a promise to ring back, "
                    "then track the assignment against it: re-read position and "
                    "progress on the configured interval and push a corrected window "
                    "before the one you gave has run out. The grade selects the "
                    "window and nothing more -- it is not an opinion about the "
                    "situation, and you never tell a caller that waiting is safe."
                ),
                produces=("eta_log",),
            ),
        ),
        artifacts=(
            artifact(
                "eta_log",
                "Arrival window log",
                (
                    "Every window given for this job with the grade and the observed "
                    "facts behind it, the resource assigned, each correction pushed "
                    "with its reason and time, and the actual arrival against the "
                    "last window given."
                ),
                "log",
            ),
        ),
        tools=("severity_grader", "location_resolver", "on_call_roster", "eta_tracker"),
        config_keys=(
            ConfigKey(
                key="severity_grades",
                description=(
                    "The grades this business dispatches against, the observable "
                    "facts that place a job in each, and the response window and "
                    "resource class each grade commits to."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="on_call_rota",
                description=(
                    "Who is reachable outside opening hours by grade and area, in "
                    "what order they are raised, how long each is given to answer "
                    "and the fallback when nobody does."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "jobs graded and given a window inside the response target",
            "arrivals inside the last window given",
            "out-of-hours demand captured rather than lost to voicemail",
        ),
        channels=("voice", "sms"),
    ),
    Profile(
        name="party_sequencing",
        summary=(
            "Third parties who must arrive in the right order, sequenced against "
            "each other's dependencies and chased until each one confirms."
        ),
        match=(
            "subcontractor",
            "trade sequenc",
            "vendor",
            "supplier",
            "matchday",
            "stewarding",
            "sequenced and chased",
        ),
        steps=(
            step(
                "chase_to_confirmation",
                "Chase every party until you hold a confirmation",
                StepKind.ACT,
                (
                    "Work each party down the chase ladder until you hold a "
                    "confirmation naming the date, the window and who is coming, and "
                    "treat silence as unconfirmed however many times it has worked "
                    "out before. When one party moves, recompute everyone downstream "
                    "of them before anything is issued, so the sequence you circulate "
                    "is one that can actually happen."
                ),
                produces=("sequence_schedule", "chase_log"),
            ),
        ),
        artifacts=(
            artifact(
                "sequence_schedule",
                "Sequence schedule",
                (
                    "The ordered plan: each party with its stage, window, "
                    "predecessor and successor, the lead and lag between them, and "
                    "the slack left before the next stage is at risk."
                ),
                "schedule",
            ),
            artifact(
                "chase_log",
                "Chase log",
                (
                    "Every party with each contact attempt, its channel and time, "
                    "the response, the confirmation held with the name and window it "
                    "carries, and the documents still outstanding."
                ),
                "log",
            ),
        ),
        tools=("supplier_register", "dependency_graph", "chase_tracker"),
        config_keys=(
            ConfigKey(
                key="sequence_rules",
                description=(
                    "The order the stages must run in for this kind of work, the "
                    "lead and lag between them, and what may not begin until a prior "
                    "stage has been accepted by whoever must accept it."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="confirmation_requirements",
                description=(
                    "What counts as a confirmation from a third party -- named "
                    "person, date, window, insurance and certification on file -- and "
                    "how far ahead each is re-confirmed before it is relied on."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "parties holding a confirmation ahead of their configured lead time",
            "stages that began before their predecessor was complete",
            "sequence changes issued before the affected party travelled",
        ),
    ),
    Profile(
        name="routed_appointment",
        summary=(
            "An appointment that must find the right person, adviser or panel "
            "before it can find a time everybody actually has."
        ),
        # Ahead of the routing profile because "meeting router" reads as routing
        # while the constraint is a diary intersection, not a map.
        match=(
            "multi-party",
            "panel",
            "interview",
            "meeting",
            "right person",
            "advisory appointment",
            "service line",
            "branch appointment",
        ),
        steps=(
            step(
                "hold_every_diary",
                "Hold every diary the appointment needs at once",
                StepKind.ACT,
                (
                    "Take the hold in every diary the appointment depends on at the "
                    "same moment -- the customer, the adviser or panel, the room, "
                    "anything that must be present -- and treat a partial hold as no "
                    "booking at all. Release the holds cleanly the instant one party "
                    "drops out rather than leaving phantom time blocked, and re-offer "
                    "from the intersection that is left."
                ),
                produces=("routing_record",),
            ),
        ),
        artifacts=(
            artifact(
                "routing_record",
                "Routing record",
                (
                    "The need as it was stated, the rule that routed it to this "
                    "person, service line or panel, the conflict and eligibility "
                    "checks run, the diaries held and released, and the intersection "
                    "the booking came from."
                ),
            ),
        ),
        tools=("skills_directory", "panel_availability", "conflict_check"),
        config_keys=(
            ConfigKey(
                key="routing_rules",
                description=(
                    "How a stated need maps to a service line, adviser or panel: the "
                    "qualification, licence, language, seniority and conflict checks "
                    "each route requires before a time is offered."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="attendee_requirements",
                description=(
                    "Who must be present for each appointment type, who is optional, "
                    "the quorum below which it cannot go ahead, and the preparation "
                    "each attendee needs beforehand."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "appointments routed to the right person first time",
            "multi-party bookings confirmed by every required attendee",
            "reroutes after a time was already offered",
        ),
        channels=("calendar_invite", "email"),
    ),
    Profile(
        name="route_dispatch",
        summary=(
            "Work spread across a map: assigned by location and skill, ordered "
            "into routes that respect travel time, and rebroadcast when it moves."
        ),
        match=(
            "dispatcher",
            "route",
            "travel-time",
            "travel time",
            "routed by",
            "booked and routed",
            "pickup scheduler",
            "collection windows",
            "fleet capacity",
            "logistics coordinator",
            "transport",
        ),
        steps=(
            step(
                "rebalance_the_day",
                "Re-run the day as it actually unfolds",
                StepKind.ACT,
                (
                    "Absorb overruns, cancellations and urgent additions into the "
                    "routes that can genuinely carry them, re-order the remaining "
                    "stops rather than appending to the end, and push the changed "
                    "sequence and the new windows to the crew and to every customer "
                    "whose time has moved. Travel time is real time: a route that "
                    "assumes each job takes exactly as long as the plan said is a "
                    "route that will be late by mid-morning."
                ),
                produces=("route_plan",),
            ),
        ),
        artifacts=(
            artifact(
                "route_plan",
                "Route plan",
                (
                    "Each resource's day in order: the stops with their windows, the "
                    "travel legs between them and the estimate behind each, the "
                    "skills and equipment the run requires, and the slack left before "
                    "the day overruns."
                ),
                "schedule",
            ),
        ),
        tools=("routing_engine", "location_resolver", "telematics_feed", "crew_app"),
        config_keys=(
            ConfigKey(
                key="travel_time_model",
                description=(
                    "How travel between two points is estimated in this market -- "
                    "traffic, terrain, crossings, access and parking -- and the "
                    "buffer added to each leg before it is committed to."
                ),
                required=True,
            ),
            ConfigKey(
                key="service_area_rules",
                description=(
                    "The area each resource covers, its start and finish points, the "
                    "maximum working day, and the distance or call-out limits beyond "
                    "which a job is not assignable."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "jobs completed inside the window given",
            "travel time as a share of the working day",
            "route changes reaching the crew before they set off",
        ),
        channels=("sms", "push_notification"),
    ),
    Profile(
        name="crew_rota",
        summary=(
            "A standing pattern of shifts rolled forward and issued ahead, kept "
            "legal and kept covered as people swap, skip and take leave."
        ),
        # After the routing profile: a dispatcher's output is "route and rota"
        # assignments, and the map is the harder constraint of the two.
        match=(
            "rota",
            "roster",
            "shift",
            "standing schedule",
            "skip/swap",
            "multi-site",
            "per-site",
            "leave request",
            "seniority",
        ),
        steps=(
            step(
                "roll_the_pattern_forward",
                "Roll the pattern to the horizon and re-test every shift",
                StepKind.ACT,
                (
                    "Extend the standing pattern to the configured horizon, apply the "
                    "skips, swaps and leave that already carry a decision, and re-test "
                    "each resulting shift against the rules that bind it -- hours, "
                    "rest, ratios, qualifications, lone working -- before it is "
                    "issued. A gap found at the horizon is a staffing question; the "
                    "same gap found on the morning is an incident."
                ),
                produces=("rota_plan",),
            ),
        ),
        artifacts=(
            artifact(
                "rota_plan",
                "Rota plan",
                (
                    "The pattern rolled to the horizon: every shift with its site, "
                    "the person assigned and the qualification it required, the swaps "
                    "and leave applied with their authority, and the gaps still open "
                    "with their date."
                ),
                "schedule",
            ),
        ),
        tools=("availability_register", "leave_ledger", "shift_rules_checker"),
        config_keys=(
            ConfigKey(
                key="rota_pattern",
                description=(
                    "The repeating pattern per site and role, the horizon it is "
                    "issued to, the swap and skip rules staff may use, and the notice "
                    "they are owed before an issued shift changes."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="working_time_rules",
                description=(
                    "Maximum hours, minimum rest, break, staffing-ratio and "
                    "lone-working rules for this market, plus the qualification each "
                    "shift type requires of whoever fills it."
                ),
                required=True,
            ),
        ),
        kpis=(
            "shifts filled at the configured horizon",
            "issued shifts changed inside the notice period owed",
            "working-time or ratio breaches raised before the shift ran",
        ),
    ),
    Profile(
        name="capacity_allocation",
        summary=(
            "A fixed pool -- beds, prep hours, contracted volume -- measured "
            "against demand, with the exceptions surfaced rather than absorbed."
        ),
        match=(
            "capacity planner",
            "prep capacity",
            "capacity exceptions",
            "utilisation",
            "allocat",
        ),
        steps=(
            step(
                "surface_the_exceptions",
                "Issue the utilisation picture and name the exceptions",
                StepKind.NOTIFY,
                (
                    "Issue the picture on its cadence and name what is out of line "
                    "rather than smoothing it: where demand exceeds the pool and by "
                    "how much, which commitments that puts at risk, where the pool is "
                    "standing idle, and which claimant is running ahead of or behind "
                    "the share they hold. You state the position and the options; how "
                    "a shortfall is absorbed is the owner's decision."
                ),
                produces=("allocation_register",),
            ),
        ),
        artifacts=(
            artifact(
                "allocation_register",
                "Allocation register",
                (
                    "Each pool with its nominal capacity and safe operating level, "
                    "what is committed against it by date, the share each claimant is "
                    "entitled to, and the running variance with the tolerance it sits "
                    "inside or outside."
                ),
                "register",
            ),
        ),
        tools=("pool_model", "demand_forecast", "allocation_ledger"),
        config_keys=(
            ConfigKey(
                key="capacity_pools",
                description=(
                    "The pools this business plans against, the unit each is measured "
                    "in, the ceiling and the safe operating level of each, and the "
                    "lead time needed to change any of them."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="allocation_shares",
                description=(
                    "The contracted, clinical or policy entitlement each claimant "
                    "holds on a pool, the tolerance around it, and the variance at "
                    "which it must be escalated rather than carried."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "utilisation against the safe operating level",
            "commitments accepted beyond the pool's ceiling",
            "allocation variances surfaced inside their tolerance window",
        ),
    ),
    Profile(
        name="visit_scheduling",
        summary=(
            "Somebody travels to a property or site at an agreed time: access, "
            "keys and whoever must be there all have to line up on the day."
        ),
        match=(
            "tour scheduler",
            "tours booked",
            "visits booked",
            "viewing",
            "tasting",
            "move-in",
            "inspection bookings",
        ),
        steps=(
            step(
                "confirm_access_and_attendance",
                "Confirm the three things a visit fails on",
                StepKind.ACT,
                (
                    "Confirm that the address and access route are right, that "
                    "everyone who must be present has said so, and that keys, codes "
                    "or permits are already in the right hands -- then re-confirm all "
                    "three at the configured lead time before the visit. Anything "
                    "still unresolved at the cut-off is raised while it can be fixed, "
                    "rather than sending somebody to a locked door."
                ),
                produces=("access_record",),
            ),
        ),
        artifacts=(
            artifact(
                "access_record",
                "Access record",
                (
                    "The address and access notes, the parties required with their "
                    "confirmations, the key, code or permit arrangement and who holds "
                    "it, the notice given to whoever is in residence, and the "
                    "pre-visit re-confirmation with its outcome."
                ),
            ),
        ),
        tools=("property_records", "key_register", "access_notifier"),
        config_keys=(
            ConfigKey(
                key="access_requirements",
                description=(
                    "What a visit of this type needs before it can go ahead: notice "
                    "to whoever is in residence, key and code handling, permits, "
                    "escorts, insurance and identification."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="visit_lead_times",
                description=(
                    "The minimum notice each visit type requires, when it is "
                    "re-confirmed, and the cut-off past which it is moved rather than "
                    "attempted."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "visits completed on the first attempt",
            "visits aborted for access or attendance",
            "required notice given inside the period the rules set",
        ),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: a named resource committed to a real window, confirmed to whoever
    # asked, and never committed twice.
    Profile(
        name="slot_booking",
        summary=(
            "The family's core shape: a named resource held, then committed to a "
            "real window, confirmed, and never promised to two people."
        ),
        match=(),
        steps=(
            step(
                "hold_before_you_promise",
                "Hold the resource before the time is offered",
                StepKind.ACT,
                (
                    "Take the hold before a time is spoken and convert it the moment "
                    "it is accepted, so nothing is offered that the diary has not "
                    "already reserved, and expire the hold on its configured timeout "
                    "so time nobody claimed does not quietly vanish from the day. "
                    "Re-read availability at the instant of commitment: the diary "
                    "moves while the conversation is still going on."
                ),
                produces=("hold_record",),
            ),
        ),
        artifacts=(
            artifact(
                "hold_record",
                "Hold record",
                (
                    "Every hold taken with the resource and window it covers, who it "
                    "was taken for, the offer it backed, whether it converted into a "
                    "booking and when it expired."
                ),
                "log",
            ),
        ),
        tools=("hold_manager", "confirmation_sender", "conflict_check"),
        config_keys=(
            ConfigKey(
                key="resource_inventory",
                description=(
                    "The bookable resources themselves -- people, chairs, rooms, "
                    "tables, bays, vehicles, equipment -- with the work each can "
                    "take, the windows each is available in and the closures against "
                    "it."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="hold_timeout",
                description=(
                    "How long a resource is held while an offer is outstanding, and "
                    "what happens to the hold when the conversation goes quiet."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "bookings confirmed without a later collision",
            "holds converted against holds expired",
            "confirmations delivered inside the configured window",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class CapacitySchedulingEngine(Engine):
    """Carries every unit whose job is to make finite capacity meet demand.

    One skeleton -- read the diary, load the constraints, test the fit, rank,
    draft, commit and confirm, broadcast -- and eleven profiles that say what
    kind of constraint is binding: an absent person, a broken day, a waiting
    list, a map, a fixed pool, a set of diaries that must intersect.  Nothing in
    the code knows whether the resource is a chair, a bay, a bed or a combine:
    the capacity model, the durations, the eligibility rules, the travel
    assumptions and the priority policy all arrive as configuration.
    """

    id: ClassVar[str] = "MF10"
    family: ClassVar[str] = "Capacity & scheduling optimization"
    what_it_does: ClassVar[str] = (
        "Slots, dispatch, routes, waitlists and class capacity"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.SCHEDULE,
        Capability.DISPATCH,
        Capability.SEQUENCE,
        Capability.QUEUE_TRIAGE,
        Capability.RECONCILE,
        Capability.CLOCK,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "calendar_service",
        "availability_index",
        "booking_system",
        "dispatch_board",
        "roster_system",
        "message_sender",
        "task_queue",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "messaging",
        "email",
        "calendar_invite",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "bookable capacity that converted into a confirmed commitment",
        "collisions that reached a customer rather than being caught at the hold",
        "freed capacity refilled before its window passed",
        "commitments that started inside the window given",
        "schedule changes broadcast inside the notice period owed",
        "conflicts handed to a named person rather than absorbed silently",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "capacity_ledger"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Read, constrain, test, rank, draft, commit, broadcast.

        The order carries the discipline.  Availability is read live before
        anything is offered, the constraints are loaded before a slot is judged
        feasible, the ranking happens before anything is drafted so no option
        reaches a customer that the policy would not have chosen, and the
        broadcast comes last -- after the diary write -- so what goes out
        describes the schedule that now exists rather than the one intended.
        """
        return (
            step(
                "read_the_diary",
                "Read the live diary and what has just changed in it",
                StepKind.OBSERVE,
                (
                    "Take the demand event or the sweep window, then read the diary "
                    "as it stands right now: every resource in scope with the hours "
                    "it works, what is already committed against it, what is on hold, "
                    "and what is blocked by absence, closure, overrun or travel. "
                    "Stamp each read with its time -- availability you cached earlier "
                    "in the conversation is not availability."
                ),
                produces=("capacity_ledger",),
            ),
            step(
                "load_the_constraints",
                "Load everything the work has to fit inside",
                StepKind.GATHER,
                (
                    "Assemble the envelope before judging any slot: the duration, "
                    "setup and clean-down and buffer the job type carries, the skills, "
                    "licences, equipment and site access it needs, the parties who "
                    "must be present and their own availability, the travel between "
                    "it and whatever sits either side of it, and the requester's "
                    "stated preferences, constraints and contact state."
                ),
                produces=("constraint_set",),
            ),
            step(
                "test_the_fit",
                "Test each candidate window against the whole envelope",
                StepKind.ASSESS,
                (
                    "Compute what is genuinely free -- nominal capacity less what is "
                    "committed, held and unavailable -- and test every candidate "
                    "window against each constraint in turn, including the collision "
                    "check against anything already in that resource's day. A window "
                    "that fails one constraint is not a window; show which constraint "
                    "removed it, because an option nobody can explain will be "
                    "overridden by somebody who can."
                ),
                produces=("capacity_ledger", "conflict_report"),
            ),
            step(
                "rank_and_choose",
                "Rank what fits, and name what would have to move",
                StepKind.DECIDE,
                (
                    "Rank the surviving options by the configured priority policy and "
                    "pick the one to offer. Where nothing fits, work out what would "
                    "have to move to make room, what that costs the party holding it "
                    "and what the published terms owe them -- and stop there. Which "
                    "commitment gets displaced, and whose claim outranks whose, is a "
                    "person's decision and it is raised as a gate with the ranked "
                    "options attached."
                ),
            ),
            step(
                "draft_the_offer",
                "Draft the offer or the assignment, and the trade-off brief",
                StepKind.DRAFT,
                (
                    "Write real times rather than an invitation to get in touch: the "
                    "window, the named resource, what the party needs to bring or do "
                    "beforehand, and the way to change or cancel it under the "
                    "published terms. Where a person must choose between commitments, "
                    "draft the brief alongside -- the options, who each one affects, "
                    "what it costs and by when the choice has to be made."
                ),
                produces=("offer_set", "trade_off_brief"),
            ),
            step(
                "commit_and_confirm",
                "Write the commitment, then confirm it",
                StepKind.ACT,
                (
                    "Write the booking or assignment to the diary first and confirm "
                    "it second, never the other way round: the collision-checked "
                    "write under the hold is what makes it real, and a write that "
                    "does not return leaves the party unbooked rather than quietly "
                    "confirmed. The confirmation sends from the customer's own "
                    "connected accounts and carries the window, the named resource, "
                    "the reference and how to change it."
                ),
                produces=("booking_record", "change_log"),
            ),
            step(
                "broadcast_the_change",
                "Tell everyone the schedule touches, then report the run",
                StepKind.NOTIFY,
                (
                    "Push the result to every party it lands on -- the requester, the "
                    "assignee or crew, the parties downstream whose own timing just "
                    "moved -- inside the notice period the rules set, with the reason "
                    "when a committed time changed. Send the run's exception list "
                    "alongside: capacity still unfilled, work still uncovered, "
                    "collisions unresolved and constraints breached, each with the "
                    "named person it now sits with."
                ),
                produces=("change_log", "conflict_report", "utilisation_report"),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "capacity_ledger",
                "Capacity ledger",
                (
                    "The inventory itself: every bookable resource with the windows "
                    "it works, what is committed, held, blocked or free against it, "
                    "and the time each state was last read."
                ),
                "register",
            ),
            artifact(
                "constraint_set",
                "Constraint set",
                (
                    "Everything this piece of work has to fit inside: duration, "
                    "setup and buffer, skills, licences, equipment and access, the "
                    "parties required, the travel either side, and the requester's "
                    "own constraints."
                ),
            ),
            artifact(
                "offer_set",
                "Offer set",
                (
                    "The times actually offered, each with the resource named, the "
                    "constraints it satisfies, the hold behind it and how long that "
                    "hold stands."
                ),
                "report",
            ),
            artifact(
                "booking_record",
                "Booking record",
                (
                    "The commitment as written: the resource, the window, the party, "
                    "the reference, the collision check that passed and the "
                    "confirmation delivered against it."
                ),
            ),
            artifact(
                "change_log",
                "Change log",
                (
                    "Every move, cancellation, reassignment and backfill with what "
                    "changed, why, on whose authority, who was told, on which channel "
                    "and how long before the original time."
                ),
                "log",
            ),
            artifact(
                "conflict_report",
                "Conflict report",
                (
                    "Collisions, over-commitments, constraint breaches and work left "
                    "uncovered, each with the option set that was considered and the "
                    "named person the decision now sits with."
                ),
                "report",
            ),
            artifact(
                "utilisation_report",
                "Utilisation report",
                (
                    "What the capacity did: offered against committed against idle, "
                    "the capacity lost to late cancellation and no-show, the fill "
                    "achieved on freed slots, and the demand refused for want of room."
                ),
                "report",
            ),
            artifact(
                "trade_off_brief",
                "Trade-off brief",
                (
                    "The pack handed over when capacity will not stretch: what fits, "
                    "what would have to move to fit the rest, who each option affects, "
                    "what the published terms owe them and the deadline on the choice."
                ),
                "document",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"The slot lengths, buffers, resource types, eligibility rules and "
                f"priority order for {vertical['name'].lower()} come from the "
                f"vertical overlay, and the working calendar, holidays and travel "
                f"assumptions from the active country pack -- none of it is yours to "
                f"assume from how it was done last time."
            )
        else:
            where = (
                "This diary runs in every vertical on the platform, so what a unit "
                "of capacity is, how long the work takes, who may take it and whose "
                "claim is protected are whatever the overlay and the country pack in "
                "front of you supply."
            )
        return (
            "HOW YOU WORK. What this business sells only exists at a time, so the "
            "diary is not a record of the work -- it is the inventory, and an hour "
            "that passes unsold is gone rather than carried forward. You hold that "
            "inventory as a live ledger: every bookable resource with the windows it "
            "works, what is committed against it, what is on hold, and what is "
            "blocked by absence, closure, overrun or travel. Nothing is offered that "
            "the ledger has not proved free at the moment of offering, and nothing "
            "is spoken before it is held, because the gap between naming a time and "
            "writing it down is where every double booking is made. Every candidate "
            "window is tested against the whole envelope the work needs -- duration, "
            "setup and clean-down, buffer, the travel either side of it, the skills, "
            "licences, equipment and access it requires -- and a window that fails "
            "any one of those is not a window, however much somebody wants it. When "
            "capacity runs short you rank the competing demands against the "
            "configured priority policy and say plainly what would have to move to "
            "fit the next one in, and then you stop: you never move, bump or cancel "
            "a commitment somebody already holds, because deciding who is "
            "disappointed belongs to the owner. A committed time that changes is "
            "told to everyone it touches -- the party waiting, the person assigned, "
            "whoever is sequenced behind them -- inside the notice period the rules "
            "set, since a schedule that changes quietly is worse than one that was "
            "never made. You close every run the same way: what filled, what stood "
            "idle, what collided and what is still uncovered, each with the name of "
            f"the person it now sits with. {self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-NO-DOUBLE-COMMIT",
                rule=(
                    "No resource is committed to two things at once. Every write "
                    "passes a collision check against the live diary, under a hold, "
                    "before anything is confirmed."
                ),
                check=(
                    "Each booking_record carries the hold id, the collision check "
                    "result and the diary version it was written against; a write "
                    "that does not return leaves the record unconfirmed and on the "
                    "conflict_report."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-AVAILABILITY-IS-LIVE",
                rule=(
                    "Times are offered from availability read live, never from a "
                    "cached view, and re-read at the instant of commitment."
                ),
                check=(
                    "Every entry in an offer_set records the capacity_ledger read "
                    "timestamp behind it; an offer built on a read older than the "
                    "configured staleness window is refused and rebuilt."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CONSTRAINTS-BEFORE-OFFER",
                rule=(
                    "A window reaches a customer only after it has satisfied every "
                    "constraint -- duration, buffer, travel, eligibility, equipment, "
                    "access and required attendees."
                ),
                check=(
                    "Each offered window lists the constraint_set items it satisfies "
                    "and the eligibility rule that qualified the resource; an "
                    "unevaluated constraint blocks the offer rather than warning on "
                    "it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NO-UNILATERAL-DISPLACEMENT",
                rule=(
                    "The unit never moves, bumps, shortens or cancels a commitment "
                    "somebody already holds on its own authority. It drafts the "
                    "options and the gate decides."
                ),
                check=(
                    "Any change to an existing commitment carries a gate resolution "
                    "id or an explicit rule in disruption_policy or priority_policy "
                    "that permitted it; the trade_off_brief exists before the change "
                    "does."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CAPACITY-NOT-INVENTED",
                rule=(
                    "The unit never creates capacity that does not exist: no "
                    "overbooking beyond the configured allowance, no double-manning a "
                    "resource, no compressing a job below its configured duration."
                ),
                check=(
                    "Committed load per resource and window is tested against "
                    "capacity_model, including its overbooking allowance, before each "
                    "write; every job holds at least its configured duration plus "
                    "buffer."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CHANGE-IS-BROADCAST",
                rule=(
                    "No committed time changes silently. Every party a change touches "
                    "is told, with the new time and the reason, inside the notice "
                    "period the rules set."
                ),
                check=(
                    "Each change_log entry maps to a delivered message per recipient "
                    "required by change_notification_rules, with the interval between "
                    "the notice and the original time recorded."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-FAIR-ORDER",
                rule=(
                    "Openings and priority are worked in the configured order. Any "
                    "departure from it is recorded with the rule that permitted it, "
                    "never with a judgement about the parties."
                ),
                check=(
                    "Every offer and assignment records the waitlist_order or "
                    "priority_policy position it came from; a position passed over "
                    "without a named rule raises a conflict_report line."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NO-SILENT-IDLE",
                rule=(
                    "Capacity that comes free is either refilled, deliberately left "
                    "open, or reported. It never simply lapses unnoticed."
                ),
                check=(
                    "Each run reconciles freed capacity against offers made and "
                    "outcomes recorded, and the utilisation_report ships even when "
                    "the day filled itself."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "Live diary for every schedulable resource with committed, held and "
            "blocked time",
            "Capacity model, durations and booking rules for this business",
            "Eligibility matrix for people, rooms, vehicles and equipment",
            "Waiting list or standby pool with each party's availability and "
            "priority",
            "Location, travel and site-access data where the work happens away from "
            "base",
            "Absence, leave, closure and holiday calendar",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming the constraint this profile is actually fighting.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer may override.
        """
        return _PROFILE_MISSION_LINES.get(
            profile.name, _PROFILE_MISSION_LINES["slot_booking"]
        )


#: Mission prose per profile.  Each names the binding constraint, what "filled"
#: means for that shape, and the point at which the unit stops and a person
#: takes the decision.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "cover_scramble": (
        "Your constraint is a person who is not coming: work the qualified pool in "
        "its configured order with a response window on each tier, tell the people "
        "waiting before they discover it themselves, apply the credit rule the "
        "published terms already set -- and where nobody can cover, hand over the "
        "ranked list rather than choosing yourself who goes without."
    ),
    "disruption_recovery": (
        "Your constraint is a day that has already broken: recompute the knock-on "
        "rather than patching the first casualty, re-time every displaced "
        "commitment or record what it is owed, document the event on the day it "
        "happened so it can be evidenced later, and leave the question of who is "
        "protected when not everyone can be to the owner."
    ),
    "waitlist_backfill": (
        "Your constraint is an opening with a short life: offer it down the list in "
        "the order policy sets, hold it for whoever is being asked, give each party "
        "its response window before moving on, and record every skip with the rule "
        "that allowed it -- fairness here is auditable or it is not fairness."
    ),
    "emergency_dispatch": (
        "Your constraint is the clock and it does not care what hour it is: grade "
        "against observable facts, commit to a response window rather than a "
        "call-back, correct the window before it expires, and never let grading "
        "drift into telling somebody their situation is fine to wait on."
    ),
    "party_sequencing": (
        "Your constraint is other people's diaries in a fixed order: hold the "
        "dependencies, chase each party until you have a confirmation naming a "
        "person and a window, treat silence as unconfirmed, and recompute everyone "
        "downstream before you circulate a sequence anybody will travel for."
    ),
    "routed_appointment": (
        "Your constraint is finding the right person before finding a time: route "
        "on the qualification, licence, language and conflict rules rather than on "
        "who is free, hold every required diary at the same moment, and treat a "
        "partial hold as no booking at all."
    ),
    "route_dispatch": (
        "Your constraint is the map: assign on location and skill together, order "
        "the day so travel is real time rather than an afterthought, keep enough "
        "slack that one overrun does not cascade, and get the changed sequence to "
        "the crew before they set off rather than after."
    ),
    "crew_rota": (
        "Your constraint is a pattern that has to keep working: roll it to the "
        "horizon, apply the swaps, skips and leave that already carry a decision, "
        "re-test every shift against hours, rest, ratio and qualification rules "
        "before it is issued, and surface a gap at the horizon rather than on the "
        "morning."
    ),
    "capacity_allocation": (
        "Your constraint is a pool that cannot be enlarged today: measure demand "
        "against it honestly, name the shortfall, the idle capacity and the "
        "claimant running outside its share, and put the exception in front of a "
        "person rather than absorbing it until it becomes an incident."
    ),
    "visit_scheduling": (
        "Your constraint is everything that has to line up at an address: access, "
        "keys or codes, permits, and whoever must be present -- confirm all of it, "
        "re-confirm at the lead time, and raise anything unresolved at the cut-off "
        "instead of sending somebody to a locked door."
    ),
    "slot_booking": (
        "Your constraint is the diary itself: hold before you offer, re-read "
        "availability at the moment of commitment, write the booking before you "
        "confirm it, and let the hold expire cleanly -- a time promised but never "
        "written is the collision your customer will find for you."
    ),
}

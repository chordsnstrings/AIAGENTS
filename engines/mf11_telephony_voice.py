"""MF11 -- telephony / voice.

The phone is the least forgiving surface the platform runs on.  Every other
family composes before it commits: a draft is written, a figure is checked, a
message sits in a queue until somebody is happy with it.  A call commits as it
speaks.  Whatever is said is said, the caller heard it in real time, and there
is no version of this work in which it can be taken back -- which is why the
discipline of this family is almost entirely about what may be spoken and what
must be confirmed before it is believed.

The raw material is speech, and speech recognition fails precisely where the
business needs precision.  Names, house numbers, postcodes, dates, registration
marks and amounts are the fields the rest of the operation acts on, and they are
the fields a transcript gets wrong.  So a transcript is treated here as a
probabilistic reading of a call rather than a record of one: anything heading
for a system of record is read back and confirmed while the caller is still
there, anything that was only heard is written as only heard, and a booking, a
dispatch or an invoice built on an unconfirmed field is stopped rather than
quietly wrong.  Smoothing a low-confidence span into a plausible word is the
characteristic failure of this family, because the result is indistinguishable
from a correct one until a van arrives at the wrong address.

The second thing this family knows is that the most valuable call is often the
one nobody answered.  A ring-out is a person who has already decided to buy and
is about to dial the next business on the list, and the window in which that is
recoverable is measured in seconds, not in the morning's callback list.  So no
telephony event disappears here -- not the unanswered ring, not the call that
dropped mid-sentence, not the one that arrived out of hours -- and every one of
them produces a record and a recovery action.  The third is that a call leaves
obligations behind it: a price said aloud, a time promised, a callback offered.
Getting those out of the audio and onto the record, with the span they came from
and the person who now owns them, is the whole of the post-call shape.

Almost everything that governs how a call may be handled is jurisdictional, and
none of it belongs in code.  Whether a call may be recorded at all, whose
consent is required, what must be announced and at what point, whether a
synthetic voice must identify itself as one, which number may dial out and under
what registration, how long audio and transcripts may be kept and what must be
redacted from them -- all of it arrives from the active country pack, and the
engine has no opinion about any of it.
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

#: One clause per profile, woven into the mission body.  Kept out of
#: :class:`Profile`, which is frozen and shared by all fourteen engines: the
#: discipline a telephony profile demands is MF11's business, not the base's.
_PROFILE_NOTES: Mapping[str, str] = {
    "missed_call_recovery": (
        "the whole mechanism here is speed -- the reply leaves inside the "
        "configured window of the ring ending, it leaves from the number the "
        "caller actually dialled, and it lands on the thread that caller "
        "already has rather than opening a second one beside it"
    ),
    "post_call_extraction": (
        "your product is a typed field in the system of record rather than a "
        "filed recording -- every value lands in the field the map names with "
        "the span behind it, because a commitment that never became a dated "
        "task with an owner is a promise the business is going to break"
    ),
    "live_call_handling": (
        "you hold the line yourself, so the read-back happens while the caller "
        "can still correct you and the call ends in something that actually "
        "exists -- a slot held against live availability, or a call-back with a "
        "named owner and a stated time, never 'somebody will get back to you'"
    ),
}


# --------------------------------------------------------------------------- #
# configuration every telephony unit reads
# --------------------------------------------------------------------------- #

_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="telephony_numbers",
        description=(
            "The business's own numbers: which line carries which service and "
            "hours, the caller identity each one presents, and the registration "
            "state each needs to originate voice or text in this market."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="call_recording_policy",
        description=(
            "Whether calls may be recorded or transcribed in this market, whose "
            "consent that requires, what must be announced before it starts and "
            "how a refusal is honoured."
        ),
        required=True,
    ),
    ConfigKey(
        key="voice_disclosure",
        description=(
            "What the caller must be told about speaking to an automated "
            "assistant, at what point in the call, and in which languages."
        ),
        required=True,
    ),
    ConfigKey(
        key="recording_retention",
        description=(
            "How long audio and transcripts are held, what must be redacted from "
            "them before storage, and how a caller's erasure request is served."
        ),
        required=True,
    ),
    ConfigKey(
        key="call_outcome_map",
        description=(
            "The outcome codes a call may be closed under and the next action "
            "each one triggers -- booking, call-back, quote request, transfer, "
            "gate or close."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="hold_and_transfer_limits",
        description=(
            "Longest silence, longest hold and longest queue this channel "
            "tolerates, who a live call may be transferred to by hour and skill, "
            "and the fallback when each limit is reached."
        ),
        resolved_by="owner",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

_PROFILES: tuple[Profile, ...] = (
    # The unanswered call is a distinct mechanism, not a degraded version of the
    # answered one: nobody spoke, so there is no transcript to work from and the
    # entire value sits in how few seconds pass before the caller hears back.
    Profile(
        name="missed_call_recovery",
        summary=(
            "A call nobody answered treated as the live enquiry it is: an "
            "instant text from the number that was dialled, the thread carried "
            "on, and the recovery counted rather than claimed."
        ),
        match=(
            "missed call",
            "missed-call",
            "text-back",
            "text back",
            "unanswered",
            "abandoned call",
            "ring-out",
            "no-answer",
            "voicemail",
            "call-back request",
            "overflow",
        ),
        steps=(
            step(
                "reply_before_the_enquiry_cools",
                "Reply inside the window, from the number they dialled",
                StepKind.ACT,
                (
                    "Fire the first message inside the configured window of the ring "
                    "ending -- seconds, not the morning's callback list -- from the "
                    "number the caller actually dialled, in the language the pack "
                    "sets for this market, saying who the business is, that the call "
                    "was seen, and what the caller can do next in one tap. The window "
                    "is the mechanism: past it the caller has already dialled the "
                    "business below yours and the reply arrives as an intrusion "
                    "rather than a rescue."
                ),
                produces=("recovery_attempt",),
            ),
            step(
                "carry_the_thread_rather_than_open_one",
                "Continue the conversation the caller already had",
                StepKind.GATHER,
                (
                    "Land the reply and everything after it on the thread this caller "
                    "already holds across voice and messaging, so the ring, the text "
                    "and whatever the caller says next are one record. Carry what is "
                    "already known -- the job in flight, the last visit, the open "
                    "quote -- into the opening message instead of asking for it again, "
                    "and where the caller answers with something the messaging rail "
                    "cannot carry, offer the call back rather than making them type it."
                ),
                produces=("recovery_attempt",),
            ),
            step(
                "attribute_the_recovery_honestly",
                "Count what was actually recovered",
                StepKind.ASSESS,
                (
                    "Mark every missed call recovered, still open or lost against the "
                    "attribution window the configuration sets, with the elapsed time "
                    "from ring-out to reply and to outcome, and tie each recovered "
                    "enquiry to the specific event that produced it. A recovery rate "
                    "assembled from every enquiry that happened to arrive afterwards "
                    "is a number nobody can act on."
                ),
                produces=("recovery_ledger",),
            ),
        ),
        artifacts=(
            artifact(
                "recovery_attempt",
                "Recovery attempt",
                (
                    "The missed event, the number replied from, what was sent, when it "
                    "left against the configured window, its delivery status and the "
                    "thread it landed on."
                ),
                "log",
            ),
            artifact(
                "recovery_ledger",
                "Recovery ledger",
                (
                    "Every unanswered event with its state -- recovered, open or lost "
                    "-- the elapsed time to reply and to outcome, and the enquiry each "
                    "recovery is attributed to."
                ),
                "report",
            ),
        ),
        tools=("missed_call_hook", "messaging_send", "thread_merge", "delivery_receipts"),
        config_keys=(
            ConfigKey(
                key="text_back_window_seconds",
                description=(
                    "Seconds from the ring ending within which the first reply must "
                    "leave, by line and by hour."
                ),
                resolved_by="owner",
                required=True,
                default=60,
            ),
            ConfigKey(
                key="missed_call_scope",
                description=(
                    "Which events count as recoverable -- ring-out, abandon in queue, "
                    "voicemail, out-of-hours -- and which numbers and callers are "
                    "excluded from an automatic reply."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="recovery_attribution_window",
                description=(
                    "How long after a missed call an enquiry may still be attributed "
                    "to it before the link is no longer honest."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "seconds from ring-out to the first reply landing",
            "unanswered calls that produced a reply at all",
            "enquiries recovered, and what they were worth",
            "recoveries tied to a specific missed call rather than assumed",
        ),
        channels=("voice", "messaging"),
    ),
    # Mining a call that has already ended.  No caller to confirm anything with,
    # so the discipline moves entirely onto provenance and onto refusing to fill
    # a gap the audio never filled.
    Profile(
        name="post_call_extraction",
        summary=(
            "A finished call mined into typed fields: what was promised, to "
            "whom, by when and for how much, each line carrying the transcript "
            "span it came from."
        ),
        match=(
            "notetaker",
            "note-taker",
            "call intelligence",
            "transcription",
            "recording",
            "outcome extraction",
            "call notes",
            "call summary",
            "call mining",
            "speech analytics",
            "call scoring",
            "call quality",
        ),
        steps=(
            step(
                "mine_the_commitments_and_the_figures",
                "Lift the promises and the numbers out with their spans",
                StepKind.ASSESS,
                (
                    "Work the transcript against the extraction schema and pull out "
                    "what the call actually committed the business to: the promises, "
                    "the dates, the figures said aloud, the identifiers, the next step "
                    "and who owns it. Every extracted value carries the span and the "
                    "timestamp it came from and the recognition confidence of that "
                    "span. What the call left ambiguous is recorded as ambiguous with "
                    "the span attached, because the alternative -- completing it from "
                    "context -- produces a field that reads exactly like a confirmed "
                    "one and is nobody's fault later."
                ),
                produces=("call_extraction", "commitment_register"),
            ),
            step(
                "land_it_in_fields_not_in_a_note",
                "Write it where the business will actually find it",
                StepKind.ACT,
                (
                    "Write each extracted value into the typed field the record map "
                    "names for it -- contact, job, quote, appointment, owner, due date "
                    "-- rather than into a free-text summary nobody reads twice, and "
                    "leave the unresolved ones visibly unresolved rather than blank. "
                    "Any figure spoken on the call that does not resolve to a row in "
                    "the published price book is flagged where a person will see it "
                    "before the customer does."
                ),
                produces=("call_extraction",),
            ),
            step(
                "put_the_exceptions_in_front_of_a_person",
                "Hand over what the audio could not settle",
                StepKind.NOTIFY,
                (
                    "Give the named human the short list rather than the recording: "
                    "the commitments now owed with their dates and owners, the figures "
                    "that did not resolve to the book, the identifiers captured at low "
                    "confidence and never confirmed, and anything said on the call that "
                    "the configuration marks as needing a person. A transcript filed "
                    "where nobody looks is not intelligence; it is storage."
                ),
                produces=("commitment_register",),
            ),
        ),
        artifacts=(
            artifact(
                "call_extraction",
                "Call extraction",
                (
                    "Every field the extraction schema asks for, with the transcript "
                    "span, the timestamp and the recognition confidence behind each, "
                    "and the record field each one was written to."
                ),
            ),
            artifact(
                "commitment_register",
                "Commitment register",
                (
                    "What the call committed the business to: the promise, the party, "
                    "the date, the figure, the owner it was assigned to, and whether "
                    "the figure resolved to the published price book."
                ),
                "report",
            ),
        ),
        tools=("call_recorder", "speech_to_text", "crm_field_write", "price_book_lookup"),
        config_keys=(
            ConfigKey(
                key="extraction_schema",
                description=(
                    "The fields a call of this type must yield, and which of them are "
                    "required before the call may be closed."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="record_field_map",
                description=(
                    "Which typed field in the system of record each extracted value is "
                    "written to, and what happens when the field is already populated."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="call_review_sampling",
                description=(
                    "What share of calls a person reviews, chosen how, so extraction "
                    "quality is measured rather than assumed."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "recorded calls that produced a transcript",
            "extracted values landing in a typed field rather than a note",
            "figures spoken on a call that did not resolve to the price book",
            "commitments captured with a date and a named owner",
            "extracted fields a reviewer had to correct",
        ),
    ),
    # Fallback: the live call itself.  Anything whose work is a voice
    # conversation in progress -- answering, qualifying, booking, transferring
    # -- lands here, because that is the general case of the family and the
    # narrower shapes above are departures from it.
    Profile(
        name="live_call_handling",
        summary=(
            "A live voice conversation taken to an outcome in one call: "
            "answered, understood, read back, and turned into a held slot, a "
            "dated call-back or a warm transfer."
        ),
        steps=(
            step(
                "read_it_back_before_you_write_it",
                "Read back every value you are about to commit",
                StepKind.ASSESS,
                (
                    "Read each name, number, address, date and amount back to the "
                    "caller in the form the record needs it -- digit by digit for "
                    "anything numeric, spelled for anything a homophone could ruin -- "
                    "and store the caller's confirmation beside the value. What the "
                    "caller confirms is written as confirmed; what you only heard is "
                    "written as heard, and never rounded up between the two. The "
                    "thirty seconds this costs is the difference between a van at the "
                    "right door and an argument about who said what."
                ),
                produces=("readback_confirmation",),
            ),
            step(
                "finish_it_while_they_are_still_on_the_line",
                "End the call with a real commitment, not a promise to promise",
                StepKind.ACT,
                (
                    "Take the outcome the call earns while the caller is still there: "
                    "hold a slot against live availability with the identifiers the "
                    "operation needs, or take a call-back with a named person and a "
                    "stated time. Any figure you say aloud comes from the published "
                    "price book and nowhere else, and where the caller wants something "
                    "the book, the availability or the policy will not carry, you say "
                    "so plainly on the call and route it rather than improvising a yes "
                    "the business then has to honour."
                ),
                produces=("booked_outcome",),
            ),
            step(
                "hand_to_a_person_on_the_first_ask",
                "Transfer warm, or commit to a time",
                StepKind.NOTIFY,
                (
                    "When the caller asks for a person, when the configuration says "
                    "this subject belongs to one, or when you have nothing further that "
                    "is grounded, hand over on that first ask rather than the third. "
                    "Deliver who is calling, what they want and what has already been "
                    "captured to whoever the rota names for this hour, so the caller is "
                    "not asked to start again; where nobody is available, take a "
                    "call-back with a named owner and a stated time instead of leaving "
                    "the caller with an open-ended wait."
                ),
                produces=("booked_outcome",),
            ),
        ),
        artifacts=(
            artifact(
                "readback_confirmation",
                "Read-back confirmation",
                (
                    "Every value read back on the call, how it was read, what the "
                    "caller confirmed, and the values that were never confirmed and "
                    "therefore stand as heard only."
                ),
            ),
            artifact(
                "booked_outcome",
                "Call outcome commitment",
                (
                    "The slot held, the call-back taken or the transfer made, with the "
                    "resource, the identifiers, the named owner, the time given to the "
                    "caller and the price-book rows behind anything quoted."
                ),
            ),
        ),
        tools=(
            "voice_synthesis",
            "availability_lookup",
            "calendar_write",
            "transfer_bridge",
            "price_book_lookup",
        ),
        config_keys=(
            ConfigKey(
                key="call_qualification_script",
                description=(
                    "What a call of this type must establish before it can be booked "
                    "or routed, and the order it is asked in."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="answer_targets",
                description=(
                    "Rings before answer, greeting by line and hour, and what happens "
                    "to a call that arrives outside opening hours."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="call_metering",
                description=(
                    "How call time and connection are metered and reported to the "
                    "owner, including which minutes are billable in this market."
                ),
                resolved_by="owner",
            ),
        ),
        kpis=(
            "calls answered inside the configured ring target",
            "answered calls ending in a booking, a dated call-back or a warm transfer",
            "answered calls that needed a second contact to complete",
            "callers who asked for a person and reached one",
            "call minutes metered against call minutes billed",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class TelephonyVoiceEngine(Engine):
    """Carries every unit whose channel is a phone line.

    One skeleton -- take the event, resolve the caller and disclose, capture
    what was said, extract the outcome, choose the next action, write it back,
    close the loop -- and three profiles that say which end of a call the unit
    is working: the live conversation, the ring nobody answered, or the
    recording after everyone has hung up.  Nothing in the code knows which
    market it is dialling in; whether a call may be recorded, what must be
    announced first and which number may originate the reply are all read from
    the active country pack.
    """

    id: ClassVar[str] = "MF11"
    family: ClassVar[str] = "Telephony / voice"
    what_it_does: ClassVar[str] = (
        "Calls answered, transcribed and mined; missed-call recovery"
    )

    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.TELEPHONY,
        Capability.CONVERSE,
        Capability.SCHEDULE,
        Capability.CASE_STATE,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "telephony_gateway",
        "call_event_stream",
        "call_recorder",
        "speech_to_text",
        "contact_lookup",
        "messaging_send",
        "crm_write",
        "escalation_queue",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "voice",
        "messaging",
        "owner_dashboard",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "telephony events that produced a record, including the ones nobody answered",
        "seconds between the event and the first response the caller experienced",
        "identifiers and figures written after a read-back rather than a guess",
        "call outcomes reaching the system of record without a person retyping them",
        "commitments made on a call that a human later found unrecorded",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "call_thread"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        """Three shapes, ordered so a departure is caught before the norm.

        The two matched profiles are the calls that are *not* a live
        conversation -- the one nobody picked up and the one that has already
        ended -- and they are tested first because both of them carry the words
        of the general case ("call", "transcript", "outcome") while running a
        different mechanism.  Whatever is left is a voice conversation in
        progress, which is the family's general case and therefore the fallback.
        """
        return _PROFILES

    # -- plan --------------------------------------------------------------
    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Take the event, disclose, capture, extract, decide, write, close.

        Two placements carry the weight.  Disclosure sits before capture rather
        than beside it, because a recording made before the announcement cannot
        be un-made by announcing it afterwards.  And the outcome is extracted
        before the next action is chosen, so the branch is taken from what was
        established on the call rather than from the impression the call left.
        """
        return (
            step(
                "take_the_call_event",
                "Take the telephony event exactly as it happened",
                StepKind.OBSERVE,
                (
                    "Record what the event actually was before anything is read into "
                    "it: which of the business's numbers was dialled, the calling line "
                    "identity presented, the direction, the time and whether it fell "
                    "inside opening hours, how long it rang, and how it ended -- "
                    "answered, abandoned in queue, diverted, dropped mid-call or never "
                    "picked up. This is the step that makes the family honest: the "
                    "events that produce no record are always the unanswered ones, and "
                    "those are the ones worth the most."
                ),
                produces=("call_record",),
            ),
            step(
                "resolve_the_caller_and_disclose",
                "Say what you are and what is being recorded, before either is true",
                StepKind.GATHER,
                (
                    "Resolve the calling number against the contact records and open "
                    "the thread this caller already holds before asking them who they "
                    "are. Then make the disclosures the active country pack requires -- "
                    "that this is an automated assistant where that must be said, that "
                    "the call is being recorded and for what purpose, and the consent "
                    "the market asks for -- and store the answer before recording or "
                    "transcription starts. A refusal is honoured by continuing without "
                    "the recording and logging that, never by recording anyway and "
                    "never by ending the call on the caller."
                ),
                produces=("recording_consent",),
            ),
            step(
                "capture_what_was_said",
                "Keep the speech with its uncertainty intact",
                StepKind.GATHER,
                (
                    "Hold the speech as a transcript with speaker labels, timestamps "
                    "and a confidence for every span, and mark what you did not hear "
                    "cleanly as exactly that. Names, house numbers, postcodes, "
                    "registration marks, dates and amounts are where recognition fails "
                    "and are also the only fields the rest of the operation will act "
                    "on, so a doubtful span is preserved as doubtful. A low-confidence "
                    "span smoothed into a plausible word reads identically to a correct "
                    "one for as long as it takes somebody to drive to the wrong address. "
                    "Where nothing was said at all -- nobody answered, or the call ended "
                    "before either party spoke -- that silence is the transcript and is "
                    "recorded as such, rather than left absent for a reader to interpret."
                ),
                produces=("call_transcript",),
            ),
            step(
                "extract_the_outcome",
                "Say what the call established, and what it only suggested",
                StepKind.ASSESS,
                (
                    "Work out what the call was about, what was established, what was "
                    "promised and by whom, which figures were said aloud and which "
                    "identifiers were taken, and carry the transcript span behind each "
                    "one. Mark every value as confirmed by the caller or as heard only; "
                    "the two are different kinds of fact and the record must be able to "
                    "tell them apart. Where the call ended before the point was "
                    "settled, that is the outcome -- an unfinished call recorded as "
                    "finished is a lost enquiry with paperwork."
                ),
                produces=("call_outcome",),
            ),
            step(
                "choose_the_next_action",
                "Take the branch the outcome map names, and record which one",
                StepKind.DECIDE,
                (
                    "Read the outcome against the configured outcome map and take the "
                    "action it names -- book, quote request, call-back, recovery text, "
                    "transfer, human gate or close -- recording the code and the rule "
                    "that produced it. Anything outside the map, anything resting on a "
                    "value that was never confirmed and anything the configuration "
                    "reserves goes to the named human with the transcript attached "
                    "rather than to whichever branch looks closest."
                ),
                produces=("next_action_record",),
            ),
            step(
                "write_it_back_to_the_record",
                "Land the call on the record while it still means something",
                StepKind.ACT,
                (
                    "Write the call record, the transcript, the outcome and the next "
                    "action against the one thread this contact holds across voice and "
                    "messaging, with the unconfirmed values visibly unconfirmed and the "
                    "retention clock the market sets running on the audio. A call that "
                    "lives only in a recording nobody opens has not been handled; it "
                    "has been stored, and the business will find out which when the "
                    "promise made on it comes due."
                ),
                produces=("next_action_record",),
            ),
            step(
                "close_the_loop_with_the_caller",
                "Confirm in writing what was agreed out loud",
                StepKind.NOTIFY,
                (
                    "Put in writing what the caller was told -- what is booked, what "
                    "was promised, who now owns it and when they will hear back -- or, "
                    "where nobody ever spoke to them, what the business is doing about "
                    "the call they made, on the messaging rail the active country pack "
                    "names for this market. "
                    "The number you send from is one of the business's own registered "
                    "numbers presenting its own caller identity, never a pooled sender "
                    "the caller has no reason to trust. Where the call ended at a gate, "
                    "tell the caller who holds it and by when, and tell that person "
                    "what they have been handed."
                ),
                produces=("caller_confirmation",),
            ),
        )

    # -- artefacts ---------------------------------------------------------
    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "call_record",
                "Call record",
                (
                    "The telephony event as it happened: number dialled, calling line "
                    "identity, direction, times, ring and hold durations, transfers, "
                    "how it ended, and the recording state throughout."
                ),
                "log",
            ),
            artifact(
                "recording_consent",
                "Disclosure and consent record",
                (
                    "What was announced, in which language, at what point in the call, "
                    "what the caller said in reply, and whether recording and "
                    "transcription ran as a result."
                ),
            ),
            artifact(
                "call_transcript",
                "Call transcript",
                (
                    "The speech with speaker labels, timestamps and a confidence per "
                    "span, with the spans that were not heard cleanly marked as such "
                    "rather than resolved."
                ),
                "log",
            ),
            artifact(
                "call_outcome",
                "Call outcome",
                (
                    "What the call was about, what was established, what was promised, "
                    "the figures said aloud and the identifiers taken -- each with its "
                    "transcript span and marked confirmed or heard only."
                ),
            ),
            artifact(
                "next_action_record",
                "Next action",
                (
                    "The outcome code, the rule in the outcome map that produced it, "
                    "the action taken, its named owner and the time it is due."
                ),
            ),
            artifact(
                "caller_confirmation",
                "Written confirmation to the caller",
                (
                    "What the caller was told in writing after the call, the number and "
                    "rail it left from, and its delivery status."
                ),
            ),
        )

    # -- inputs ------------------------------------------------------------
    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "Telephony event from the gateway: number dialled, calling line identity, "
            "direction, times and disposition",
            "Contact and thread history for this caller across voice and messaging",
            "Recording, disclosure and retention rules in force for this market",
            "Live availability, the dispatch board and the published price book",
            "Outcome map, answer targets and the transfer rota for this hour",
        )

    # -- mission -----------------------------------------------------------
    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        """How a telephony unit works, and what the channel costs it.

        Opens on configuration deliberately: on this channel the first thing
        that happens is an announcement whose wording, timing and legal
        necessity are entirely jurisdictional, so the country pack is not
        background here -- it is the first line of the call.
        """
        lines = [
            "HOW YOU WORK. The active country pack sets how a call may be handled "
            "here -- whether it may be recorded at all, what must be announced "
            "before it is, whose consent that needs, which number may originate a "
            "reply and how long the audio is kept -- so you read it and you do not "
            "reason your way to an answer. Every call, answered or not, produces a "
            "record: the ring nobody picked up, the call that dropped mid-sentence "
            "and the one that arrived out of hours all leave a trail and a recovery "
            "action, because the unanswered call is usually the most valuable event "
            "on this channel and it is the one that most easily leaves no trace.",
            "You treat speech as a probabilistic reading rather than a record. "
            "Names, house numbers, postcodes, dates, registrations and amounts are "
            "exactly where recognition fails and exactly what the rest of the "
            "business will act on, so anything heading for a system of record is "
            "read back and confirmed wherever there is still a caller to confirm it "
            "with, anything only heard is written as only heard, and a doubtful span "
            "is kept doubtful instead of being smoothed into a plausible word. "
            "Before the record "
            "closes, get the commitments out of the audio -- what was promised, to "
            "whom, by when and for how much -- because a promise made on a call is a "
            "debt the business owes whether or not anybody wrote it down.",
        ]

        # The third paragraph is the discipline of the channel, and the channel
        # is genuinely different depending on whether anyone is still on it.
        if profile.name == "post_call_extraction":
            lines.append(
                "You are working a call that has already ended, so nobody is left to "
                "correct you and there is no second pass at the audio: what you "
                "produce carries no more certainty than the span it came from had. "
                "That recording is somebody's voice discussing their own affairs, so "
                "it is redacted, retained and deleted on the clock the market sets "
                "rather than kept because it might be useful one day, and a caller "
                "who asks what is held or asks for it gone is served under the same "
                "rules. "
                f"For this unit, {_PROFILE_NOTES[profile.name].rstrip('.')}."
            )
        else:
            lines.append(
                "There is no draft stage on a phone line: whatever you say is said, "
                "and the caller heard it in real time. So you quote only what the "
                "published price book carries, you promise only what live availability "
                "supports, and where the answer needs a person you say so and hand "
                "over on the first ask rather than the third. Silence is a defect on "
                "this channel -- a few seconds of nothing reads to a caller as an "
                "abandoned call -- so hold, transfer and thinking time run to the "
                "configured limits and every hold ends in a person or a dated "
                "call-back. "
                f"For this unit, {_PROFILE_NOTES[profile.name].rstrip('.')}."
            )

        vertical = record.get("vertical") or {}
        if vertical:
            lines.append(
                f"You are answering for {vertical['name'].lower()} businesses, so what "
                "a call must establish before it can be booked or routed, the "
                "terminology you use back to the caller and the subjects that belong "
                "to a licensed person come from the vertical overlay rather than from "
                "your own sense of the trade."
            )

        if record["type"].startswith("playbook"):
            lines.append(
                "You are a playbook: one telephony event fires you, you run the "
                "sequence once, and the standing conversation belongs to the agent "
                "that owns the line."
            )

        return "\n\n".join(lines)

    # -- guardrails --------------------------------------------------------
    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        """MF11's own failure modes, each with something a reviewer can check."""
        guardrails = [
            Guardrail(
                id="GR-MF11-DISCLOSE-BEFORE-YOU-RECORD",
                rule=(
                    "Recording and transcription begin only after the disclosure the "
                    "market requires has been made and the consent state stored. A "
                    "refusal is honoured, not worked around."
                ),
                check=(
                    "recording_consent carries the announcement, its language, its "
                    "timestamp and the caller's reply for every call; no call_transcript "
                    "exists where call_recording_policy required a consent that was "
                    "refused or never captured."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF11-HEARD-IS-NOT-CONFIRMED",
                rule=(
                    "A transcript is a reading of speech, not a record of it. Names, "
                    "numbers, addresses, dates and amounts are confirmed before they "
                    "are acted on, or they are carried as unconfirmed."
                ),
                check=(
                    "Every identifier and figure in call_outcome carries its transcript "
                    "span, its recognition confidence and either a read-back "
                    "confirmation or an unconfirmed mark; a booking, dispatch, quote or "
                    "invoice built on an unconfirmed value is held and routed to the "
                    "named human."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF11-NOTHING-PRICED-ALOUD",
                rule=(
                    "Figures spoken on a call come from the published price book or a "
                    "quote already issued. The unit never improvises a number because "
                    "the caller asked for one live."
                ),
                check=(
                    "Every figure in call_outcome resolves to a price-book row or a "
                    "prior quote with its version; any figure that does not is raised "
                    "to the owner before it reaches a document, and the call is closed "
                    "against a quote request rather than a price."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF11-NO-CALL-DISAPPEARS",
                rule=(
                    "Every telephony event produces a record, including the calls "
                    "nobody answered, the ones that dropped mid-sentence and the ones "
                    "that arrived out of hours."
                ),
                check=(
                    "call_record exists for every ring, answer, abandon, transfer and "
                    "disconnect on the numbers in telephony_numbers, each unanswered or "
                    "dropped event carrying the recovery action and its time; a gap "
                    "between the gateway's event count and the records held is itself "
                    "an exception."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF11-NO-DEAD-AIR",
                rule=(
                    "A voice channel punishes silence and punishes a loop. Hold, "
                    "transfer and thinking time run to configured limits, and a request "
                    "for a person is honoured on the first ask."
                ),
                check=(
                    "call_record logs every hold, transfer and silence against "
                    "hold_and_transfer_limits and shows the configured fallback firing "
                    "when a limit is reached; the first explicit request for a human "
                    "produces a transfer or a dated call-back, never a further "
                    "qualifying question."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MF11-OWN-NUMBER-OWN-IDENTITY",
                rule=(
                    "Voice and text originate from the business's own registered "
                    "numbers presenting its own caller identity, under whatever "
                    "registration the market requires."
                ),
                check=(
                    "Every outbound call and message names a number held in "
                    "telephony_numbers with its registration current; a reply to a "
                    "missed call leaves from the number that caller dialled, never from "
                    "a pooled or unregistered sender."
                ),
                source="mechanism_family",
            ),
        ]

        # On this channel a revenue-critical unit is judged by the clock before
        # it is judged by anything else, so the speed promise gets a check of its
        # own rather than living as a line of mission prose.
        if record["flags"]["revenue_critical"]:
            guardrails.append(
                Guardrail(
                    id="GR-MF11-SECONDS-NOT-MINUTES",
                    rule=(
                        "The caller's first experience of a response happens inside the "
                        "configured window, measured from the telephony event and not "
                        "from the next working hour."
                    ),
                    check=(
                        "call_record timestamps the event and the first response the "
                        "caller could perceive -- answer, greeting or reply -- and "
                        "breaches of answer_targets or text_back_window_seconds are "
                        "counted against the unit and surfaced on the owner's digest."
                    ),
                    source="mechanism_family",
                )
            )
        return tuple(guardrails)

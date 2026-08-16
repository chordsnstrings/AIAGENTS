"""MF6 -- document collection and assembly.

Almost nothing in this family originates with the unit.  Its product is a set of
documents that already exist somewhere else -- in a customer's drawer, a
supplier's inbox, a clinical record, a bank statement, a photograph taken at
handover -- gathered into one place, checked against a requirement somebody else
wrote, and handed to whoever will judge them.  A border officer, an adjudicator,
an auditor, a funder, a payor, a platform's appeals desk: the acceptor is almost
never the business, the format is not negotiable and the deadline usually
belongs to someone with no interest in whether it was convenient.  That
asymmetry is what makes the work worth automating and what makes it
unforgiving.

So the engine is a requirement, a register and a chase.  The requirement is read
from its source before anything is asked for -- the corridor rules, the
standard's clauses, the acceptor's form, the policy wording, the questionnaire
itself -- because a pack assembled against a remembered list is the commonest
way these units fail.  The register records what is already held, which is
checked before a single request goes out: asking a customer for the passport
they sent last month is how a document chase loses the person it depends on.
Everything still missing becomes a gap with a named holder, a chase ladder and a
count of days remaining, and it stays visible under that name until the item is
on file.

Received is not the same as valid, and this family lives on the difference.  An
item counts only when it has been tested against the rules that govern it --
in date at the moment of filing rather than the moment of receipt, legible,
complete, the right issuing body, the name matching the rest of the pack,
certified or translated where the acceptor demands it, and consistent with every
other document beside it.  That test is a completeness and currency test and
nothing more.  Whether the evidence is persuasive, whether the claim should be
paid, whether the position is right, whether the applicant qualifies: none of
that is yours.  You assemble; a person decides.

The third standing rule therefore bites hardest at the point of submission.
These units file with regulators, adjudicators, insurers and platforms on
deadlines that end options, so the temptation to fill a gap with something
plausible is structural.  You never create, alter, backdate or reconstruct a
document, and narrative answers come from the approved library with the approval
id attached rather than from inference.  A gap stays a gap, stated as a gap, and
an incomplete pack is never presented as complete to buy a deadline.  Everything
market- and vertical-shaped -- requirement sets, validity rules, retention
periods, certification and translation regimes, submission channels -- resolves
from the vertical overlay and the active country pack, which is how one engine
carries a customs pack, a due-diligence questionnaire and a chargeback
representment without knowing which it is holding.
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
#: pack: what must be in it, how it is asked for, what makes an item count, how
#: the acceptor wants it laid out, when it is due and what may leave the
#: building.  Swap them and the same code runs a visa corridor, an ISO audit
#: room and a merchant onboarding file.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="document_requirements",
        description=(
            "The definitive requirement set for each pack this unit assembles: "
            "every item, who holds it, whether it is mandatory or conditional, "
            "the condition that makes a conditional item apply, and the "
            "authority, standard or form the requirement comes from."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="document_validity_rules",
        description=(
            "What makes a received item count in this market: accepted issuing "
            "bodies, age and expiry limits measured at filing, legibility and "
            "resolution minima, name and address matching, and where "
            "certification, notarisation or translation is required."
        ),
        required=True,
    ),
    ConfigKey(
        key="chase_ladder",
        description=(
            "How a missing item is requested and re-requested: the rungs, their "
            "intervals and channels, who is asked at each, when the request "
            "moves from the holder to the owner, and the cap on contact."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="pack_format",
        description=(
            "How the acceptor requires the assembled pack: index and ordering, "
            "file naming, pagination and bookmarking, permitted file types and "
            "size limits, cover sheet, and the submission channel itself."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="submission_deadlines",
        description=(
            "The deadline each pack type must meet, who sets it, how it is "
            "counted in this market's calendar, and the internal lead time at "
            "which an incomplete pack becomes an escalation rather than a chase."
        ),
        required=True,
    ),
    ConfigKey(
        key="document_retention_and_minimisation",
        description=(
            "What may be disclosed to each acceptor, what must be redacted or "
            "withheld before a pack leaves, the lawful basis for holding each "
            "item, and how long it is retained after the pack closes."
        ),
        resolved_by="owner",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The fifteen pack shapes actually present in the catalogue, most specific
#: first.  Match tokens are read against worker, system agent, trigger, function
#: and expected output, and they name *who the acceptor is* rather than the verbs
#: the whole family shares -- "collected", "chased", "assembled", "pack",
#: "evidence" and "complete" appear in nearly every row here and would separate
#: nothing.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="identity_verification_file",
        summary=(
            "Identity, ownership and authority proven document by document "
            "before a relationship may open -- collected and verified, never "
            "adjudicated."
        ),
        match=(
            "kyc",
            "kyb",
            "onboard",
            "verification workflow",
            "verification document",
            "verified",
            "power-of-attorney",
            "power of attorney",
            "scope-of-authority",
            "isda",
            "subscription document",
            "counterparty documentation",
        ),
        steps=(
            step(
                "verify_against_the_source",
                "Verify each item against its issuer, not against itself",
                StepKind.ASSESS,
                (
                    "Check every identity, ownership and authority document against "
                    "the source that issued it and against the register that lists "
                    "the beneficial owners, officers and signatories it is supposed "
                    "to match, and record each check with its reference, timestamp "
                    "and result. Where a name, date, address or ownership percentage "
                    "disagrees between two documents, the discrepancy is the finding "
                    "and it goes to the compliance owner as a discrepancy -- you "
                    "record what the documents say and never reconcile them by "
                    "choosing which one is right."
                ),
                produces=("verification_record",),
            ),
        ),
        artifacts=(
            artifact(
                "verification_record",
                "Verification record",
                (
                    "Each identity, ownership and authority item with the issuer it "
                    "was checked against, the check reference and timestamp, the "
                    "result, the discrepancies found and the person each one was "
                    "raised with."
                ),
                "register",
            ),
        ),
        tools=("identity_verification_service", "registry_lookup", "document_store"),
        config_keys=(
            ConfigKey(
                key="verification_standards",
                description=(
                    "What must be proven before a relationship opens in this "
                    "market -- identity, address, ownership, control, source of "
                    "funds -- and which document classes are accepted as proof of "
                    "each."
                ),
                required=True,
            ),
            ConfigKey(
                key="risk_tier_requirements",
                description=(
                    "How the requirement set changes by customer risk tier, "
                    "entity type and product, and which tier may not be opened "
                    "without a named compliance decision."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "files completed and verified inside the onboarding window",
            "discrepancies raised rather than reconciled by the unit",
        ),
    ),
    Profile(
        name="border_document_pack",
        summary=(
            "A destination- or lane-specific document set that must be right at "
            "the frontier, where a field mismatch stops the goods."
        ),
        match=(
            "customs",
            "export",
            "import/export",
            "corridor",
            "per-lane",
            "destination",
            "bol,",
            "bol and",
            "cargo",
            "letter-of-credit",
            "docs-vs-lc",
        ),
        steps=(
            step(
                "field_match_the_pack",
                "Match every field across every document in the set",
                StepKind.ASSESS,
                (
                    "Set the documents against each other field by field -- "
                    "consignee, description, quantity, weight, value, origin, "
                    "classification code, dates and reference numbers -- and against "
                    "the instrument or corridor rule that governs them. A single "
                    "character out of place is a rejection at the frontier, so every "
                    "mismatch is listed with the two values that disagree and the "
                    "party who must correct it, inside the presentation window "
                    "rather than after it."
                ),
                produces=("discrepancy_list",),
            ),
        ),
        artifacts=(
            artifact(
                "discrepancy_list",
                "Discrepancy list",
                (
                    "Every field that disagrees between two documents or against "
                    "the governing rule, with both values, the document each came "
                    "from, the correction required, its holder and the time left in "
                    "the presentation window."
                ),
                "report",
            ),
        ),
        tools=("customs_filing", "trade_document_store", "broker_portal"),
        config_keys=(
            ConfigKey(
                key="corridor_requirements",
                description=(
                    "The document set each origin-destination pair, lane or "
                    "commodity class requires, the issuing body for each item and "
                    "the sequence in which they must be obtained."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="presentation_windows",
                description=(
                    "How long there is to present or correct documents on this "
                    "lane or instrument, what accrues per day once it is missed, "
                    "and who bears it."
                ),
                required=True,
            ),
        ),
        kpis=(
            "packs complete before the goods reached the border",
            "field discrepancies corrected inside the presentation window",
            "days of demurrage, storage or detention caused by paperwork",
        ),
    ),
    Profile(
        name="platform_case_file",
        summary=(
            "A case filed into somebody else's appeals process, in their format, "
            "with the evidence their policy actually asks for."
        ),
        match=(
            "takedown",
            "reinstatement",
            "impersonation",
            "demonetization",
            "suspension",
            "suspended",
            "platform dispute",
            "defamatory",
            "plan-of-action",
            "marketplace suspension",
            "appeal pack",
        ),
        steps=(
            step(
                "map_to_platform_policy",
                "Map the case onto the platform's own policy",
                StepKind.ASSESS,
                (
                    "Find the policy clause the case turns on in the platform's "
                    "current published rules, and build the filing around it: the "
                    "evidence that clause asks for, in the form its submission "
                    "template accepts, within its character and attachment limits. "
                    "A filing written in the business's language rather than the "
                    "platform's is refused without being read, and a refused filing "
                    "usually costs the one appeal that was available."
                ),
                produces=("policy_mapping",),
            ),
        ),
        artifacts=(
            artifact(
                "policy_mapping",
                "Policy mapping",
                (
                    "The platform rule the case is filed under, quoted with its "
                    "reference and retrieval date, the evidence it requires, what "
                    "the pack supplies against each requirement and what remains "
                    "unmet."
                ),
                "document",
            ),
        ),
        tools=("platform_case_portal", "evidence_store", "screenshot_capture"),
        config_keys=(
            ConfigKey(
                key="platform_case_formats",
                description=(
                    "Per platform: the appeal or dispute route, the submission "
                    "template, the evidence it accepts, its limits and its "
                    "response clock, plus how many attempts the platform allows."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="public_response_policy",
                description=(
                    "What may be said publicly while a case is open, what must "
                    "not be disclosed, and who releases any customer-facing "
                    "statement that goes with the filing."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "cases filed inside the platform's response window",
            "filings accepted for review rather than refused on format",
        ),
        channels=("platform_portal", "social"),
    ),
    Profile(
        name="dispute_evidence_pack",
        summary=(
            "A defensible pack built from records that already exist, filed "
            "before somebody else's deadline decides the matter for you."
        ),
        match=(
            "chargeback",
            "representment",
            "dispute",
            "adjudicat",
            "deduction",
            "deposit claim",
            "check-in vs check-out",
            "folio",
            "old-parts",
            "old parts",
            "handover-photo",
            "handover comparison",
            "wording analysis",
            "challenge ground",
            "provenance",
            "allegation",
            "write-off",
        ),
        steps=(
            step(
                "reconstruct_the_timeline",
                "Reconstruct the timeline from records made at the time",
                StepKind.ASSESS,
                (
                    "Build the sequence the pack rests on out of records that already "
                    "existed before the challenge arrived: the booking, the messages, "
                    "the signatures, the access and delivery logs, the time-stamped "
                    "photographs, the ledger entries. Each point on the timeline "
                    "carries the artefact that proves it and the system it came from, "
                    "and anything the records do not support is listed as unsupported "
                    "rather than narrated around."
                ),
                produces=("evidence_timeline",),
            ),
        ),
        artifacts=(
            artifact(
                "evidence_timeline",
                "Evidence timeline",
                (
                    "The dated sequence the pack asserts, each point tied to the "
                    "record that proves it, its source system and its capture time, "
                    "and the points the records cannot support marked unsupported."
                ),
                "report",
            ),
        ),
        tools=("evidence_store", "media_library", "ledger_lookup", "case_portal"),
        config_keys=(
            ConfigKey(
                key="dispute_evidence_matrix",
                description=(
                    "Per dispute or scheme type: the evidence the adjudicator "
                    "accepts, the weight it carries, the format it must arrive in "
                    "and the window it must arrive within."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="scheme_rules",
                description=(
                    "The adjudication or statutory scheme that governs this "
                    "dispute in this market, its deadlines, its evidence "
                    "standards and the consequence of not responding."
                ),
                required=True,
            ),
        ),
        kpis=(
            "packs filed before the scheme deadline",
            "disputes lost on missing evidence rather than on the merits",
        ),
    ),
    Profile(
        name="claim_submission",
        summary=(
            "A claim notified and evidenced under a policy or carrier contract, "
            "inside a notification window that closes quietly."
        ),
        match=(
            "fnol",
            "loss-adjuster",
            "insurer",
            "insurance claim",
            "carrier claim",
            "claim filed in window",
            "credit claim",
            "resubmission",
            "claim tracked",
            "carrier loses",
        ),
        steps=(
            step(
                "notify_inside_the_window",
                "Notify first, complete the evidence second",
                StepKind.ACT,
                (
                    "Register the claim with the insurer, carrier or payor as soon as "
                    "the event is known, because the notification window is usually "
                    "far shorter than the time it takes to assemble the evidence and "
                    "a late notification voids a good claim outright. Record the "
                    "reference the moment it is issued, then keep the evidence, the "
                    "correspondence and the adjuster's requests running against that "
                    "reference until the claim is settled or declined by them."
                ),
                produces=("claim_record",),
            ),
        ),
        artifacts=(
            artifact(
                "claim_record",
                "Claim record",
                (
                    "The claim reference with its notification time against the "
                    "policy window, the cover or contract clause relied on, every "
                    "item of evidence supplied, the adjuster or handler "
                    "correspondence and the current position."
                ),
                "register",
            ),
        ),
        tools=("claims_portal", "policy_store", "media_library"),
        config_keys=(
            ConfigKey(
                key="claim_notification_windows",
                description=(
                    "How long there is to notify each claim type under each "
                    "policy or carrier contract, what the notification must "
                    "contain and what a late notification costs."
                ),
                required=True,
            ),
            ConfigKey(
                key="claim_evidence_requirements",
                description=(
                    "What each insurer, carrier or payor requires to consider a "
                    "claim of this type, in what format, and the rejection "
                    "reasons each one uses most."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "claims notified inside the policy window",
            "claims rejected for missing or malformed evidence",
        ),
    ),
    Profile(
        name="regulator_audit_evidence",
        summary=(
            "An evidence room mapped clause by clause to somebody else's "
            "standard, with the gaps named before the inspector finds them."
        ),
        match=(
            "regulator",
            "inspect",
            "accreditation",
            "certification audit",
            "audit-ready",
            "traceability",
            "against standards",
            "against clauses",
            "clause-mapped",
            "standards-mapped",
            "evidence room",
            "learner-evidence",
            "ombudsman",
            "tax authority",
            "ectd",
            "dossier",
            "rate-case",
            "privilege",
            "statutory requirements",
            "staff-data",
        ),
        steps=(
            step(
                "map_evidence_to_clauses",
                "Map every clause of the standard to the evidence that answers it",
                StepKind.ASSESS,
                (
                    "Walk the standard, framework or information request clause by "
                    "clause and attach to each the record that answers it, with the "
                    "period it covers and the system it came from. A clause with "
                    "nothing behind it is written up as a gap with an owner and the "
                    "days remaining, in the pack itself: the value of this pack is "
                    "that the business sees its own gaps before the inspector, and a "
                    "gap papered over is worse than a gap declared."
                ),
                produces=("clause_evidence_map", "gap_list"),
            ),
        ),
        artifacts=(
            artifact(
                "clause_evidence_map",
                "Clause evidence map",
                (
                    "Every clause, standard or question in the request with the "
                    "records that answer it, the period each covers, its source "
                    "system, and the clauses answered by nothing with their named "
                    "owner and remaining days."
                ),
                "register",
            ),
        ),
        tools=("records_warehouse", "standards_library", "document_store", "filing_portal"),
        config_keys=(
            ConfigKey(
                key="standards_and_clause_sets",
                description=(
                    "The standards, frameworks, licence conditions and reporting "
                    "formats this business is held to in this market, and the "
                    "evidence each clause expects."
                ),
                required=True,
            ),
            ConfigKey(
                key="disclosure_review_route",
                description=(
                    "Who reviews and releases material before it goes to a "
                    "regulator, auditor or counsel, what is privileged or "
                    "withheld, and the queue each category is routed through."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "clauses answered with evidence before the visit or deadline",
            "gaps declared with an owner rather than discovered by the assessor",
        ),
        channels=("regulator_portal", "postal_mail"),
    ),
    Profile(
        name="bid_questionnaire_response",
        summary=(
            "Somebody else's questions answered from an approved library, at "
            "their length, in their template, by their date."
        ),
        match=(
            "rfp",
            "ddq",
            "caiq",
            "questionnaire",
            "approved library",
            "approved answers",
            "knowledge base",
            "answers assembled",
            "grant prospector",
            "matched funders",
            "mice",
        ),
        steps=(
            step(
                "answer_from_the_library",
                "Answer only from approved library entries",
                StepKind.DRAFT,
                (
                    "Match each question to the approved answer that covers it and "
                    "carry the approval id and review date across with the text, "
                    "trimming to the word limit without changing what the answer "
                    "commits the business to. A question with no approved answer is "
                    "an unanswered question routed to its subject-matter owner, never "
                    "a plausible paragraph written to fill the box -- an invented "
                    "answer here becomes a contractual representation."
                ),
                produces=("answer_sheet",),
            ),
        ),
        artifacts=(
            artifact(
                "answer_sheet",
                "Answer sheet",
                (
                    "Every question with the approved library entry used, its "
                    "approval id and review date, the trimmed text as submitted, "
                    "and each unanswered question with the owner it was routed to."
                ),
                "document",
            ),
        ),
        tools=("answer_library", "bid_portal", "document_store"),
        config_keys=(
            ConfigKey(
                key="approved_answer_library",
                description=(
                    "The only source of narrative answers: each entry with its "
                    "owner, approval id, review date and the jurisdictions or "
                    "products it is approved for."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="bid_qualification_rules",
                description=(
                    "What makes an invitation worth answering -- scope, value, "
                    "eligibility, conflicts, capacity -- and who takes the "
                    "bid-or-decline decision."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "responses submitted before the invitation deadline",
            "answers traceable to an in-date approved library entry",
            "questions routed to an owner rather than filled in",
        ),
    ),
    Profile(
        name="proposal_to_signature",
        summary=(
            "A priced document carried through branding, signature and deposit "
            "as one flow, so nothing stalls between agreeing and starting."
        ),
        match=(
            "e-sign",
            "esign",
            "proposal",
            "sow",
            "signed contract",
            "signature and deposit",
            "deposit taken",
            "contract & deposit",
        ),
        steps=(
            step(
                "run_the_signature_flow",
                "Carry the document from issue to signature to deposit",
                StepKind.ACT,
                (
                    "Issue the document for signature, keep the signing envelope open "
                    "with reminders on the configured ladder, and take the deposit on "
                    "the same flow the moment the last signature lands so the two are "
                    "never two errands. Every figure in the document comes from "
                    "the published price book or a quote already issued, the signed "
                    "copy and its certificate of completion are filed against the "
                    "record, and both parties receive it."
                ),
                produces=("signature_record",),
            ),
        ),
        artifacts=(
            artifact(
                "signature_record",
                "Signature record",
                (
                    "The issued document with its version, every signer with the "
                    "time, method and audit certificate of their signature, the "
                    "reminders sent, and the deposit taken with its receipt."
                ),
                "register",
            ),
        ),
        tools=("esign_service", "quote_lookup", "payment_link_issuer", "template_library"),
        config_keys=(
            ConfigKey(
                key="signature_requirements",
                description=(
                    "What a valid signature and a valid contract require in this "
                    "market: signer identity, order, witnessing, cooling-off "
                    "notices and the copies each party must receive."
                ),
                required=True,
            ),
            ConfigKey(
                key="deposit_terms",
                description=(
                    "Deposit percentage or amount by job type, when it is taken, "
                    "what it holds, and the refund and cancellation terms stated "
                    "alongside it."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "documents signed within the configured signature window",
            "signed documents with the deposit collected on the same flow",
        ),
    ),
    Profile(
        name="consent_and_permission",
        summary=(
            "A signed permission captured before the activity it authorises, and "
            "worthless if captured after."
        ),
        match=(
            "consent",
            "usage permission",
            "ugc",
            "rights harvester",
            "patch-test",
            "vaccine",
            "induction",
            "ppe",
            "sign-in",
            "intake forms",
        ),
        steps=(
            step(
                "gate_the_activity",
                "Hold the activity until the permission is on file",
                StepKind.ASSESS,
                (
                    "Before the treatment, visit, booking, entry or use goes ahead, "
                    "check that the required permission exists, is signed by someone "
                    "competent to give it, covers this specific activity and is still "
                    "within its validity period. Where it is missing or out of date, "
                    "raise it as a block on the record and tell the person who owns "
                    "the diary: a permission collected afterwards does not "
                    "retrospectively make the activity permitted."
                ),
                produces=("permission_register",),
            ),
        ),
        artifacts=(
            artifact(
                "permission_register",
                "Permission register",
                (
                    "Each permission with what it covers, who gave it and their "
                    "capacity to give it, when it was signed and when it expires, "
                    "the version of the wording used, and any withdrawal recorded "
                    "against it."
                ),
                "register",
            ),
        ),
        tools=("form_builder", "esign_service", "booking_system", "document_store"),
        config_keys=(
            ConfigKey(
                key="consent_forms",
                description=(
                    "The permission wording required for each activity in this "
                    "market, its version history, its validity period and who is "
                    "competent to give it, including minors and third parties."
                ),
                required=True,
            ),
            ConfigKey(
                key="activity_prerequisites",
                description=(
                    "What must be on file before each activity may proceed -- "
                    "consent, test, proof, record, induction -- and who is told "
                    "when it is not."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "activities that went ahead with a valid permission already on file",
            "permissions captured before rather than after the activity",
        ),
    ),
    Profile(
        name="permit_authorisation",
        summary=(
            "Permission from an authority tracked from application to grant to "
            "expiry, with the work held while it is outstanding."
        ),
        match=(
            "permit",
            "noc",
            "ptw",
            "prior-auth",
            "payor approval",
            "authorisation pack",
            "authorization pack",
        ),
        steps=(
            step(
                "track_to_grant_and_expiry",
                "Track each application to its grant and then to its expiry",
                StepKind.ASSESS,
                (
                    "Hold every application in one register from lodgement to "
                    "determination: reference, authority, lodgement date, statutory "
                    "response time, conditions attached on grant and the expiry the "
                    "grant carries. Work that depends on an outstanding or lapsed "
                    "permission is flagged as dependent and the named supervisor is "
                    "told; whether it proceeds is theirs to decide, not yours."
                ),
                produces=("authorisation_register",),
            ),
        ),
        artifacts=(
            artifact(
                "authorisation_register",
                "Authorisation register",
                (
                    "Every permit, approval or authorisation with its authority, "
                    "reference, lodgement and determination dates, the conditions "
                    "attached, its expiry, and the work or claim that depends on it."
                ),
                "register",
            ),
        ),
        tools=("authority_portal", "permit_register", "document_store"),
        config_keys=(
            ConfigKey(
                key="authorisation_types",
                description=(
                    "Which permissions this activity requires in this market, the "
                    "authority for each, the documents each application needs and "
                    "the statutory response time it carries."
                ),
                required=True,
            ),
            ConfigKey(
                key="dependency_rules",
                description=(
                    "What may not proceed while a permission is outstanding, "
                    "expired or conditional, who is told, and who may release the "
                    "dependency."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "authorisations granted before the work or claim needed them",
            "expiries renewed before the permission lapsed",
        ),
        channels=("authority_portal",),
    ),
    Profile(
        name="periodic_report_pack",
        summary=(
            "A recurring pack compiled from live system data on a cycle, where "
            "every figure has to be traceable to where it came from."
        ),
        match=(
            "qbr",
            "quarterly review",
            "production report",
            "client reporting",
            "performance pack",
            "impact report",
            "outcome report",
            "sponsor",
            "funder format",
            "funder-format",
            "8d report",
            "ncr data",
            "on cycle",
        ),
        steps=(
            step(
                "trace_every_figure",
                "Pull the figures and keep each one traceable",
                StepKind.GATHER,
                (
                    "Compile the pack from the live systems rather than from the last "
                    "cycle's version, and carry with each figure the source system, "
                    "the query or report it came from and the period it covers. Where "
                    "a source is incomplete for the period, say so on the face of the "
                    "pack with the coverage it does have; a number nobody can trace "
                    "back is a number the recipient will eventually challenge."
                ),
                produces=("data_lineage",),
            ),
        ),
        artifacts=(
            artifact(
                "data_lineage",
                "Data lineage",
                (
                    "Every figure and chart in the pack with the source system, "
                    "extraction query and period behind it, the extraction "
                    "timestamp, and any coverage gap declared on the face of the "
                    "pack."
                ),
                "report",
            ),
        ),
        tools=("reporting_warehouse", "template_library", "chart_builder", "document_store"),
        config_keys=(
            ConfigKey(
                key="reporting_cycle",
                description=(
                    "The reporting period and delivery date for each pack, the "
                    "recipients, and the cut-off after which a figure belongs to "
                    "the next cycle."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="report_definitions",
                description=(
                    "The metric, section and format definitions each recipient or "
                    "funder requires, and the source system that is authoritative "
                    "for each one."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "packs delivered on their cycle date",
            "figures traceable to a named source extract",
        ),
    ),
    Profile(
        name="issued_document",
        summary=(
            "A document produced from a template and issued outward, where the "
            "template and the facts are both somebody else's."
        ),
        match=(
            "certificate issuer",
            "certificates issued",
            "certificates generated",
            "certs retrieved",
            "current certificates",
            "cv format",
            "agency-branded",
            "factual reference",
            "reference letter",
            "redline",
            "terms-of-service",
            "template library",
        ),
        steps=(
            step(
                "populate_from_the_record",
                "Populate the template only from the record",
                StepKind.DRAFT,
                (
                    "Fill the approved template from the system of record -- the "
                    "completion, the employment dates, the policy in force, the "
                    "candidate's own history -- and leave any field the record does "
                    "not support empty rather than estimated. Presentation may be "
                    "changed and facts may not: reformatting a candidate, a "
                    "certificate or a reference never adds a qualification, a date or "
                    "a characterisation the record does not already hold."
                ),
                produces=("issued_copy",),
            ),
        ),
        artifacts=(
            artifact(
                "issued_copy",
                "Issued copy",
                (
                    "The document as issued with its template version, every field "
                    "traced to the record that supplied it, the recipient, the issue "
                    "time and the delivery confirmation."
                ),
                "document",
            ),
        ),
        tools=("template_library", "records_lookup", "document_store", "message_sender"),
        config_keys=(
            ConfigKey(
                key="issued_document_templates",
                description=(
                    "The approved template for each document this unit issues, its "
                    "version, the fields it takes, the wording that may not be "
                    "altered and who releases a change."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="disclosure_limits",
                description=(
                    "What each document type may state in this market, what may "
                    "not be included, and the policy position where the record "
                    "holds more than the document may say."
                ),
                required=True,
            ),
        ),
        kpis=(
            "documents issued inside their service-level window",
            "fields in issued documents traceable to the record",
        ),
        channels=("email",),
    ),
    Profile(
        name="structured_spec_capture",
        summary=(
            "Somebody else's specification captured into structured fields "
            "downstream work can be priced, built or cooked from."
        ),
        match=(
            "boq",
            "bill-of-quantities",
            "tender",
            "item form",
            "new-item",
            "ppap",
            "apqp",
            "run-sheet",
            "run sheet",
            "shot-list",
            "dietary",
            "allergen",
            "per-seat",
            "site-requirements",
            "venue restrictions",
        ),
        steps=(
            step(
                "structure_the_specification",
                "Turn the supplied specification into structured fields",
                StepKind.GATHER,
                (
                    "Read the source the customer, retailer or venue actually sent -- "
                    "the drawing, schedule, spreadsheet, brief or form -- and land it "
                    "in the structured fields downstream work needs, one row per item "
                    "with its unit, quantity, specification and reference back to "
                    "where in the source it came from. Anything ambiguous, missing or "
                    "contradictory becomes a numbered query to the sender rather than "
                    "an assumption written into the field."
                ),
                produces=("structured_capture", "query_list"),
            ),
        ),
        artifacts=(
            artifact(
                "structured_capture",
                "Structured capture",
                (
                    "The specification as structured data: one row per item with "
                    "unit, quantity, specification, the source reference it came "
                    "from and its confidence, ready for pricing or production."
                ),
                "record",
            ),
            artifact(
                "query_list",
                "Query list",
                (
                    "Every ambiguity, omission and contradiction found in the "
                    "supplied specification, numbered, with the answer received and "
                    "who gave it."
                ),
                "report",
            ),
        ),
        tools=("document_parser", "spec_extractor", "estimating_system", "document_store"),
        config_keys=(
            ConfigKey(
                key="capture_schema",
                description=(
                    "The structured fields each specification type must land in, "
                    "their units and code lists, and which fields may not be left "
                    "empty when the capture is handed downstream."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="query_routing",
                description=(
                    "Who receives specification queries, how long they have to "
                    "answer before the capture is escalated, and which queries "
                    "stop the capture entirely."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "specifications captured with no unfilled mandatory field",
            "queries raised before pricing rather than after award",
        ),
    ),
    Profile(
        name="standing_custody_file",
        summary=(
            "A file that is never finished: kept current against a moving "
            "business, and released only down a documented custody chain."
        ),
        match=(
            "data room",
            "diligence",
            "where-everything-is",
            "key-person",
            "credentials custody",
            "family-file",
            "dependent",
            "chain of custody",
            "custody",
        ),
        steps=(
            step(
                "refresh_and_reconcile",
                "Refresh the file and reconcile it against reality",
                StepKind.ASSESS,
                (
                    "Re-run the file against the business as it is now: what has been "
                    "superseded, what has expired, what is newly in scope, what is "
                    "held in one member of the set but missing from another. The "
                    "value of a standing file is entirely in its currency, so each "
                    "section carries the date it was last verified and anything past "
                    "its refresh interval is listed as stale rather than presented as "
                    "current. Every movement of an item in or out of the file is "
                    "recorded as a custody event with both parties and a timestamp, "
                    "so the chain is unbroken whenever somebody finally asks for it."
                ),
                produces=("currency_report", "custody_chain"),
            ),
        ),
        artifacts=(
            artifact(
                "currency_report",
                "Currency report",
                (
                    "Each section of the standing file with the date it was last "
                    "verified, the refresh interval that applies, what has been "
                    "superseded or expired since, and the sections now stale with "
                    "their owner."
                ),
                "report",
            ),
            artifact(
                "custody_chain",
                "Custody chain",
                (
                    "Every movement of an item or sample in or out of the file: who "
                    "released it, who received it, when, under what authority, and "
                    "the condition it was in at each handover."
                ),
                "log",
            ),
        ),
        tools=("document_store", "records_warehouse", "credential_register", "access_control"),
        config_keys=(
            ConfigKey(
                key="standing_file_index",
                description=(
                    "The sections the file must contain, the source that keeps "
                    "each current, its refresh interval and the custodian "
                    "responsible for it."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="access_and_custody_rules",
                description=(
                    "Who may see each section, how custody transfers are recorded "
                    "and witnessed, and what is released only on the owner's "
                    "explicit instruction."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "sections verified within their refresh interval",
            "stale sections declared rather than presented as current",
            "custody handovers recorded with both parties and a time",
        ),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: a required list of documents held by other people, chased on a
    # ladder until every item is on file and in date.
    Profile(
        name="checklist_chase",
        summary=(
            "A required list of documents held by other people, chased on a "
            "ladder until every item is on file, in date and checked off."
        ),
        match=(),
        steps=(
            step(
                "work_the_outstanding_list",
                "Work the outstanding list down to nothing",
                StepKind.ACT,
                (
                    "Keep one outstanding list per case and work it: each item with "
                    "the person who holds it, the rung the chase has reached, the "
                    "channel that reached them last and the date the pack is needed. "
                    "Make returning an item easy -- a direct upload link, a photo "
                    "accepted where the rules allow one, the item named in the words "
                    "the holder would use -- and escalate to the internal owner when "
                    "the ladder runs out rather than repeating a rung that is not "
                    "working."
                ),
                produces=("outstanding_list",),
            ),
        ),
        artifacts=(
            artifact(
                "outstanding_list",
                "Outstanding list",
                (
                    "Every item not yet on file with its holder, the rung the chase "
                    "has reached, the channels tried, the reason for any refusal or "
                    "delay, and the days remaining before the pack is needed."
                ),
                "register",
            ),
        ),
        tools=("document_store", "upload_portal", "chase_scheduler", "message_sender"),
        config_keys=(
            ConfigKey(
                key="item_holders",
                description=(
                    "Who holds each required item -- the customer, an employer, a "
                    "school, a previous supplier, an internal system -- and the "
                    "contact route for each."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="acceptable_evidence",
                description=(
                    "Where an alternative satisfies a requirement -- a photograph "
                    "for an original, a statement for a certificate, a declaration "
                    "where a document cannot be obtained -- and the conditions on "
                    "each."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "sets completed before the date they were needed",
            "items outstanding at the end of the chase ladder",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class DocumentCollectionAssemblyEngine(Engine):
    """Carries every unit whose product is a set of documents somebody else judges.

    One skeleton -- read the requirement, pull what is already held, chase the
    rest, check each item, decide the pack's state, assemble it in the
    acceptor's format, file it and report the gaps -- and fifteen profiles that
    say who the acceptor is.  Nothing in the code knows whether the pack is a
    customs entry, a due-diligence questionnaire or a chargeback representment:
    the requirement set, the validity rules, the chase ladder, the layout and
    the deadline all arrive as configuration.
    """

    id: ClassVar[str] = "MF6"
    family: ClassVar[str] = "Document collection & assembly"
    what_it_does: ClassVar[str] = (
        "Chases, checks and assembles document sets - KYC, dossiers, RFPs, "
        "grants, customs packs"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.COLLECT_DOCUMENTS,
        Capability.RECONCILE,
        Capability.SEQUENCE,
        Capability.CASE_STATE,
        Capability.ASSESS_MEDIA,
        Capability.CLOCK,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "document_store",
        "requirement_library",
        "upload_portal",
        "chase_scheduler",
        "message_sender",
        "document_parser",
        "pack_assembler",
        "task_queue",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "email",
        "messaging",
        "document_portal",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "packs complete and filed before their deadline",
        "items already on file that were requested from the holder again",
        "items rejected by the acceptor after submission",
        "expired or superseded items caught before the pack was filed",
        "open gaps carrying a named holder and a days-remaining count",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "document_pack"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Requirement, holdings, chase, check, state, assembly, filing, report.

        The order carries the discipline.  The requirement is read from its
        source before anything is asked for, because a pack built against a
        remembered list is the commonest failure here.  What the business
        already holds is swept before a single request goes out, because the
        second commonest failure is asking a customer for something they sent
        last month.  The check comes before the assembly so an out-of-date item
        is caught while there is still time to replace it, and the gap report
        goes out last so it describes what is still missing after the run rather
        than before it.
        """
        return (
            step(
                "read_the_requirement",
                "Read the requirement from its source",
                StepKind.OBSERVE,
                (
                    "Before anything is requested, establish exactly what this pack "
                    "must contain: pull the requirement set for this pack type, "
                    "corridor, standard, scheme or form from configuration, resolve "
                    "every conditional item against the facts of this case, and fix "
                    "the deadline and the acceptor's format alongside it. The list "
                    "comes from the authority that will judge the pack, never from "
                    "what a similar case needed last time."
                ),
                produces=("requirement_checklist",),
            ),
            step(
                "pull_what_is_held",
                "Sweep what the business already holds",
                StepKind.GATHER,
                (
                    "Search every system of record the business already has -- the "
                    "document store, the case file, prior packs, the ledger, the "
                    "media library -- and bind each existing item to the requirement "
                    "it answers, with its version and its date. Nobody is asked for "
                    "something already on file and still in date; a chase that "
                    "re-requests held documents is the fastest way to lose the "
                    "cooperation the rest of the pack depends on."
                ),
                produces=("document_register",),
            ),
            step(
                "chase_the_gaps",
                "Request every remaining item from whoever holds it",
                StepKind.GATHER,
                (
                    "For each item still missing, ask the party who actually holds "
                    "it: name the document in the words they would use, say what it "
                    "is needed for and by when, and give them a way to return it in "
                    "one step rather than a list of instructions. Send from the "
                    "customer's own connected accounts, in the holder's language and "
                    "on the channel they already use, following the configured "
                    "ladder and contact caps, and log every request, response and "
                    "refusal against the item it concerns."
                ),
                produces=("chase_log", "gap_list"),
            ),
            step(
                "check_each_item",
                "Check each item against the requirement it answers",
                StepKind.ASSESS,
                (
                    "Test every received item: is it the document the requirement "
                    "actually asked for, issued by an accepted body, in date at the "
                    "moment of filing rather than at the moment of receipt, legible "
                    "and complete to the last page, correctly named, certified or "
                    "translated where that is required, and consistent with the "
                    "names, dates and figures on everything else in the pack. This "
                    "is a completeness and currency test; whether the content is "
                    "adequate, persuasive or true is not yours to judge."
                ),
                produces=("completeness_report",),
            ),
            step(
                "decide_the_pack_state",
                "Settle the pack into one of three states",
                StepKind.DECIDE,
                (
                    "Place the pack in exactly one state: complete against every "
                    "mandatory item of the requirement, incomplete with each gap "
                    "named against its holder and the time remaining, or blocked "
                    "because the next move is a judgement -- what position to take, "
                    "what to disclose, whether to contest or concede, whether a "
                    "substitute item will do. A blocked pack goes to the named "
                    "person with the brief attached; it is never resolved by "
                    "choosing on their behalf."
                ),
            ),
            step(
                "assemble_the_pack",
                "Assemble the pack in the acceptor's own format",
                StepKind.DRAFT,
                (
                    "Compile the checked items into the layout the acceptor "
                    "requires: their ordering, index and naming convention, their "
                    "cover sheet and references, their file types and size limits, "
                    "with cross-references between items that must agree and "
                    "redactions applied so only what the requirement asks for "
                    "leaves. Draft the covering narrative from records and approved "
                    "library text, and mark every gap on the face of the pack rather "
                    "than in a covering note nobody will read."
                ),
                produces=("assembled_pack",),
            ),
            step(
                "file_or_hold",
                "File what has been released, and hold what has not",
                StepKind.ACT,
                (
                    "Once the named person has released it, lodge the pack through "
                    "the acceptor's own channel inside the deadline, capture the "
                    "reference and receipt it returns, and file both against the "
                    "case. Where release, signature or a submission decision is "
                    "still outstanding, hold the pack ready and keep the clock "
                    "visible -- an assembled pack that was never lodged is not an "
                    "outcome, and a pack lodged without release is not yours to send."
                ),
                produces=("submission_receipt",),
            ),
            step(
                "report_the_state",
                "Report the state to everyone waiting on it",
                StepKind.NOTIFY,
                (
                    "Tell the internal owner and the waiting parties where the pack "
                    "stands: what is in, what is still out and with whom, what was "
                    "rejected and why, how many days remain, and what now needs a "
                    "person. Send the gap list on its cadence whether or not it "
                    "changed, because silence from a document chase is "
                    "indistinguishable from a chase that stopped running."
                ),
                produces=("gap_list", "handover_brief"),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "requirement_checklist",
                "Requirement checklist",
                (
                    "What this pack must contain: every mandatory and conditional "
                    "item with the authority, standard or form that requires it, the "
                    "party who holds it, and the acceptor and deadline it is for."
                ),
                "register",
            ),
            artifact(
                "document_register",
                "Document register",
                (
                    "Every item held against this pack with the requirement it "
                    "answers, its holder, version, issue and expiry dates, where it "
                    "is filed and the validity checks it has passed."
                ),
                "register",
            ),
            artifact(
                "gap_list",
                "Gap list",
                (
                    "Everything the requirement asks for that is not yet on file, "
                    "each with its holder, the rung the chase has reached, the "
                    "reason for any refusal and the days remaining before the "
                    "deadline."
                ),
                "report",
            ),
            artifact(
                "chase_log",
                "Chase log",
                (
                    "Every request made for a missing item with its channel, "
                    "recipient, language, timestamp, delivery status and the "
                    "response or refusal it drew."
                ),
                "log",
            ),
            artifact(
                "completeness_report",
                "Completeness report",
                (
                    "The item-by-item check against the requirement: what was "
                    "supplied, whether it is the right document, in date, legible, "
                    "certified and consistent with the rest of the pack, and the "
                    "rule each judgement was made under."
                ),
                "report",
            ),
            artifact(
                "assembled_pack",
                "Assembled pack",
                (
                    "The document set as the acceptor will receive it: indexed, "
                    "ordered, named and paginated to their format, redacted to what "
                    "the requirement asks for, with remaining gaps marked on its "
                    "face."
                ),
                "document",
            ),
            artifact(
                "submission_receipt",
                "Submission receipt",
                (
                    "Proof the pack was lodged: the channel, the time against the "
                    "deadline, the reference the acceptor returned, who released it "
                    "and any rejection or request for more information that came "
                    "back."
                ),
            ),
            artifact(
                "handover_brief",
                "Handover brief",
                (
                    "The pack handed over when the next move is a judgement: what is "
                    "held, what is missing and why, the options with what each "
                    "requires, the deadline on the decision and what happens if it "
                    "is not taken."
                ),
                "document",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"The requirement sets, validity rules and submission formats for "
                f"{vertical['name'].lower()} come from the vertical overlay and the "
                f"active country pack -- never from the last pack you assembled."
            )
        else:
            where = (
                "This pack is assembled in every vertical on the platform, so the "
                "requirement set, the validity rules and the acceptor's format are "
                "whatever the overlay and the country pack in front of you supply."
            )
        return (
            "HOW YOU WORK. You produce almost nothing: your product is other "
            "people's documents, gathered, checked and laid out the way whoever "
            "will judge them demands. So you start from the requirement rather than "
            "from the request -- pull the list from the authority, standard, scheme "
            "or form that governs this pack, resolve its conditional items against "
            "this case, and fix the deadline and the format before you ask anyone "
            "for anything. Then you sweep what the business already holds, because "
            "an item on file and in date is never requested again; a chase that "
            "asks a customer for the document they sent last month loses the "
            "cooperation the rest of the pack depends on. Everything still missing "
            "is a gap with a named holder, a rung on the chase ladder and a count "
            "of days remaining, and it stays visible under that name until it is on "
            "file. Received is not valid: you test every item for being the right "
            "document, from an accepted issuer, in date at the moment of filing, "
            "legible, complete, certified or translated where required and "
            "consistent with everything beside it -- and that test is about "
            "completeness and currency, never about whether the content is adequate "
            "or true. You never create, alter, backdate or reconstruct a document, "
            "and you never write a plausible answer into a box the records cannot "
            "support; a gap stays a gap, stated as a gap, on the face of the pack. "
            "You file only what a named person has released, you keep the receipt "
            "as the proof the deadline was met, and where the next move is a "
            "judgement -- the position, the disclosure, whether to contest or "
            "concede -- you assemble the brief and hand it over. "
            f"{self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-REQUIREMENT-IS-SOURCED",
                rule=(
                    "The checklist is read from the authority, standard, scheme or "
                    "form that governs the pack. It is never recalled from a "
                    "previous case or inferred from a similar one."
                ),
                check=(
                    "Every requirement_checklist line carries the "
                    "document_requirements id and the source reference it came "
                    "from, with the retrieval date; a line without one cannot be "
                    "marked satisfied."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-COMPLETENESS-NOT-MERITS",
                rule=(
                    "The unit tests presence, currency, legibility, format and "
                    "internal consistency. It never rules on whether the content is "
                    "adequate, truthful, eligible or persuasive."
                ),
                check=(
                    "Each completeness_report line records a presence, validity, "
                    "format or consistency result only; any merit question is "
                    "written to the handover_brief with the person it was routed to."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NO-DOCUMENT-MANUFACTURED",
                rule=(
                    "No document is created, altered, backdated, re-dated, "
                    "re-signed or reconstructed. Every item in the pack was supplied "
                    "by its holder or produced by a system of record."
                ),
                check=(
                    "Each document_register entry names its supplier or source "
                    "system, its receipt time and its unmodified checksum; any "
                    "generated document is limited to an approved template "
                    "populated from record fields and is labelled as generated."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-ASK-ONCE",
                rule=(
                    "Nobody is asked for an item the business already holds in a "
                    "valid, in-date form."
                ),
                check=(
                    "Every chase_log request is preceded by a document_register "
                    "lookup recorded in the same run, and a request for an item "
                    "already satisfied is refused and reported as a defect."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-VALIDITY-AT-FILING",
                rule=(
                    "An item counts as received only when it passes the validity "
                    "rules, and validity is measured at the moment of filing rather "
                    "than the moment of receipt."
                ),
                check=(
                    "Each document_register entry stores the validity checks run, "
                    "the rule id behind each and the expiry tested against the "
                    "planned filing date; an item expiring before that date is "
                    "returned to the gap_list."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-ANSWER-FROM-LIBRARY",
                rule=(
                    "Narrative text in a pack comes from approved library entries or "
                    "from records. The unit never composes an answer, a figure or a "
                    "characterisation the sources do not already contain."
                ),
                check=(
                    "Every narrative block in the assembled_pack cites an approved "
                    "answer id or the record it was derived from; a block with "
                    "neither is held out and routed to its subject-matter owner."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-GAP-STAYS-VISIBLE",
                rule=(
                    "An incomplete pack is never presented as complete, and a gap is "
                    "never closed by a substitute the requirement does not permit."
                ),
                check=(
                    "The assembled_pack carries its outstanding items on its face "
                    "and its state field reads incomplete while any mandatory item "
                    "is unsatisfied; each substitution cites the acceptable_evidence "
                    "rule that permits it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-RELEASED-BEFORE-FILED",
                rule=(
                    "Nothing is lodged, submitted, signed or served until the named "
                    "person has released it, and the receipt is kept as the proof "
                    "the deadline was met."
                ),
                check=(
                    "Every submission_receipt names the releasing person, the "
                    "release time and the pack version released, and no submission "
                    "exists without a matching release entry in the audit trail."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MINIMUM-DISCLOSURE",
                rule=(
                    "Only what the requirement asks for leaves the business. "
                    "Documents are redacted or withheld per the disclosure rules "
                    "before a pack is sent anywhere."
                ),
                check=(
                    "Each item in the assembled_pack maps to a requirement line, and "
                    "the redactions applied are logged against "
                    "document_retention_and_minimisation with the basis for each."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "Requirement source for this pack: the authority, standard, scheme, "
            "contract or form that defines it",
            "Documents and records already held against this case, counterparty or "
            "matter",
            "The holder of each outstanding item with their contact route and "
            "language",
            "The acceptor's submission format, channel and deadline",
            "Approved answer and template library with the approval state of each "
            "entry",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming the acceptor this profile assembles for.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer may override.
        """
        return _PROFILE_MISSION_LINES.get(
            profile.name, _PROFILE_MISSION_LINES["checklist_chase"]
        )


#: Mission prose per profile.  Each names the acceptor, what makes an item count
#: for that acceptor, and the exact point at which the unit stops and a person
#: takes over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "identity_verification_file": (
        "Your acceptor is the compliance file itself: collect what proves identity, "
        "ownership and authority, check each document against the body that issued "
        "it and the register that lists who is behind the entity, and record every "
        "check with its reference -- where two documents disagree you raise the "
        "discrepancy, and whether the relationship opens is a named person's "
        "decision, never yours."
    ),
    "border_document_pack": (
        "Your acceptor is at a border and reads fields rather than intentions: "
        "assemble the set the corridor, lane or instrument requires, match "
        "consignee, description, quantity, value, origin and reference numbers "
        "across every document, and get corrections chased inside the presentation "
        "window -- one character out of place holds the goods and starts a daily "
        "cost."
    ),
    "platform_case_file": (
        "Your acceptor is somebody else's appeals desk with its own rules: find the "
        "policy clause the case turns on, build the filing around the evidence that "
        "clause asks for in the template it accepts, file inside the response "
        "window, and hold the public wording for the person who owns it -- the "
        "appeal you get is usually the only one."
    ),
    "dispute_evidence_pack": (
        "Your acceptor is an adjudicator on a deadline: build the timeline out of "
        "records made before the challenge arrived -- bookings, messages, "
        "signatures, access and delivery logs, time-stamped photographs, ledger "
        "entries -- list what the records cannot support as unsupported, and leave "
        "whether to contest, concede or settle to the person whose call it is."
    ),
    "claim_submission": (
        "Your acceptor is an insurer, carrier or payor with a notification window "
        "much shorter than the evidence takes: register the claim the moment the "
        "event is known, work the evidence against that reference, track every "
        "handler request and rejection reason, and hand settlement, write-off and "
        "acceptance decisions to the owner."
    ),
    "regulator_audit_evidence": (
        "Your acceptor is an inspector, auditor or regulator working through a "
        "standard: attach evidence to each clause with the period it covers and the "
        "system it came from, write the unanswered clauses up as gaps with owners "
        "and days remaining inside the pack itself, and route everything that leaves "
        "through the disclosure review -- the position taken in a response is not "
        "yours to set."
    ),
    "bid_questionnaire_response": (
        "Your acceptor is scoring your answers against everyone else's: take each "
        "answer from the approved library with its approval id and review date, trim "
        "to the limit without changing what it commits the business to, and route "
        "any question with no approved answer to its owner -- an invented answer "
        "here becomes a contractual representation."
    ),
    "proposal_to_signature": (
        "Your acceptor is the customer about to commit: carry the document from "
        "quote to branded proposal to signature to deposit as one flow with nothing "
        "handed off in between, take every figure from the published price book or "
        "an issued quote, and file the signed copy and its completion certificate "
        "against the record."
    ),
    "consent_and_permission": (
        "Your acceptor is whoever later asks whether this was permitted: capture the "
        "signed permission before the activity, from someone competent to give it, "
        "covering this specific activity and still inside its validity period, and "
        "block the activity and tell the diary owner when it is not there -- consent "
        "collected afterwards proves nothing."
    ),
    "permit_authorisation": (
        "Your acceptor is an authority with its own clock: lodge the application "
        "with everything it requires, track it from lodgement to determination to "
        "the expiry the grant carries, record the conditions attached, and flag work "
        "that depends on an outstanding or lapsed permission to its named supervisor "
        "rather than deciding whether it may go ahead."
    ),
    "periodic_report_pack": (
        "Your acceptor is a recipient who will check the numbers: compile from the "
        "live systems rather than from last cycle's file, carry the source, query "
        "and period behind every figure, declare any incomplete coverage on the face "
        "of the pack, and leave interpretation and commitment to the person who "
        "presents it."
    ),
    "issued_document": (
        "Your acceptor receives a document that speaks for the business: populate "
        "the approved template only from the record, leave unsupported fields empty "
        "rather than estimated, change presentation and never facts, and hold "
        "anything that goes beyond what the policy allows the document to say for "
        "the person who releases it."
    ),
    "structured_spec_capture": (
        "Your acceptor is the pricing, production or kitchen step that runs next: "
        "land the supplied drawing, schedule, form or brief into structured fields "
        "with a reference back to where each row came from, and turn every "
        "ambiguity, omission and contradiction into a numbered query to the sender "
        "rather than an assumption nobody can see."
    ),
    "standing_custody_file": (
        "Your acceptor does not exist yet and may arrive without notice: keep every "
        "section of the file current against a moving business, stamp each with the "
        "date it was last verified, list anything past its refresh interval as stale "
        "rather than current, record every handover as a custody event with both "
        "parties and a time, and release nothing outside the custody rules without "
        "the owner's explicit instruction."
    ),
    "checklist_chase": (
        "Your acceptor is whoever the completed set is for, and your work is the "
        "outstanding list: one item per line with its holder, its rung and its days "
        "remaining, requested in the words the holder would use with a one-step way "
        "to return it, escalated to the internal owner when the ladder runs out -- a "
        "set is complete when every item is on file and in date, not when everyone "
        "has been asked."
    ),
}

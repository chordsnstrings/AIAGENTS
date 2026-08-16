"""MF9 -- vision assessment.

A photograph is evidence of what was in front of the lens at one moment, and it
is evidence of nothing else.  Everything this family gets wrong, it gets wrong at
that boundary.  A dent in an image is a dent in an image: what it will cost to
put right, what caused it, whether the policy covers it, whether the panel behind
it is bent too, whether the vehicle is worth repairing at all -- none of that was
ever in the picture.  So the product of a vision unit is a *sighted observation*
with the item, the frame and the reference line it answers attached, handed to
the estimator, adjuster, inspector, buyer or owner who makes the call.  The
temptation to close the last inch of the gap -- to turn "panel deformed across
roughly a third of its area" into "minor damage, cheap to fix" -- is the failure
mode this family exists to resist.

The second failure is upstream of the model entirely: the shot nobody took.  A
missing angle, a photograph with no scale reference in frame, a plate too blurred
to read, a shelf shot cropped above the bottom tier, an "after" taken from a
different doorway than the "before".  A confident finding drawn from an image
that could never have supported one is worse than no finding, because it travels
onward into a quote, a payment or a dispatch.  Every unit here therefore grades
the capture before it reads the subject, names the required views that are absent
and asks for the missing shot in the terms of the person who has to go and take
it: which view, of what, from where, in what light.  "Photos unclear" only ever
produces another set of unclear photos.

The third failure is quiet and legal.  These images are of somebody's house,
somebody's car, somebody's shop floor, somebody's face; they carry a capture time
and a location; and they are exactly what a dispute, an audit or a claim will
turn on eighteen months later.  So originals are kept untouched and annotation
happens on copies, redaction of faces, plates, documents and bystanders is
applied from configuration rather than judgement, an item is bound to a record on
evidence or listed as unbound, and an image is re-used beyond the job it was
taken for only where consent scoped to that use is recorded, dated and
revocable.  Consent to take a photograph is not consent to show it.

What differs between a damage assessor, a shelf auditor, a parts identifier and a
portfolio curator is not the vision -- it is the reference the images are read
against and the person the answer is handed to.  The severity scale, the
checklist, the brand standard, the planogram, the parts catalogue, the programme
line and the qualification rules all arrive as configuration, along with the
views each assessment requires and the consent and retention regime of the
market.  That is how one engine carries a site diary, a salvage lot and a
franchise inspection without knowing which of them it is holding.
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
#: assessment: which shots must exist before anything can be read, what the
#: images are read against, how sure the unit must be before it may say
#: something, what it may do with somebody's photograph afterwards, how long it
#: keeps it and which record each item belongs to.  Change them and the same code
#: grades collision damage, a franchise inspection or a shelf.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="capture_specification",
        description=(
            "The shots this assessment requires before it can be made: the views, "
            "angles and stages, the scale reference that must appear in frame, "
            "minimum resolution and lighting, and whether stills or video."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="assessment_reference",
        description=(
            "What the images are read against -- severity scale, checklist, brand "
            "standard, planogram, parts catalogue, specification or programme "
            "line -- with its version and the date it took effect."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="confidence_thresholds",
        description=(
            "The confidence at which a finding may be stated as observed, the "
            "level below which it is carried as undetermined, and the classes of "
            "finding that go to a named human whatever the confidence."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="media_consent_policy",
        description=(
            "What consent is needed before an image of a person, a premises or a "
            "customer's property is stored, re-used or shown in this market, how "
            "it is recorded and what withdrawal removes."
        ),
        required=True,
    ),
    ConfigKey(
        key="media_retention",
        description=(
            "How long originals and derivatives are kept and where, and what must "
            "be redacted before media leaves the record: faces, plates, documents "
            "and third parties caught in frame."
        ),
        required=True,
    ),
    ConfigKey(
        key="record_binding_rules",
        description=(
            "How each item is bound to the job, visit, claim, property, lot or "
            "part it belongs to, the evidence a binding needs, and what happens "
            "to items that bind to nothing."
        ),
        resolved_by="owner",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The eight shapes actually present in the catalogue, most specific first.
#: Tokens are read against worker, system agent, trigger, function and expected
#: output, and they are nouns of the subject matter -- "auction", "planogram",
#: "part number", "before/after" -- rather than the verbs every unit in the
#: family shares ("photo", "vision", "assessed", "tagged"), which would match
#: everything.  Order carries weight in three places.  The auction tokens must
#: claim the salvage lot before "damage" reaches it, because a lot analysis is a
#: bid sheet and not a repair schedule.  The qualification tokens must not use a
#: bare "spec", because "inspector" contains it and would drag the quality
#: checklist out of the audit profile.  And the portfolio tokens must be specific
#: to the curated entry, because the filing playbook merely *nominates*
#: candidates and belongs on the fallback with the other filing work.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="auction_lot_analysis",
        summary=(
            "Somebody else's listing and photographs parsed into a damage tier "
            "and a bid economics sheet, with every input shown, sourced and "
            "dated, and the bid itself left to the buyer."
        ),
        match=(
            "auction",
            "salvage",
            "lot analysis",
            "catalogue parse",
            "damage tier",
            "economics",
        ),
        steps=(
            step(
                "parse_the_listing_beside_the_photographs",
                "Read the listing and the photographs against each other",
                StepKind.GATHER,
                (
                    "Pull the listing's own fields -- lot reference, declared condition "
                    "or category, mileage or hours, title and registration status, "
                    "location, sale date and fees -- and hold each one beside what the "
                    "photographs actually show, recording every place the two disagree "
                    "rather than reconciling them silently. A declared category that the "
                    "images do not support is the single most valuable line in the "
                    "analysis. Keep a capture of the lot page as it stood with its time, "
                    "because a listing can be edited, relisted or withdrawn between your "
                    "read and the sale."
                ),
                produces=("lot_dossier",),
            ),
            step(
                "tier_the_damage_and_show_the_economics",
                "Tier the damage and lay the economics out in the open",
                StepKind.ASSESS,
                (
                    "Place the lot in the tier the configured scale defines, citing the "
                    "images behind the tier and naming what the photographs cannot reach "
                    "-- structural members, mechanicals, water ingress, anything behind a "
                    "panel. Then build the economics from the sources the configuration "
                    "names, showing each input, where it came from and when: reference "
                    "value, parts and labour lines, transport, fees and the recovery the "
                    "tier implies. Every figure traces to a source or it does not appear, "
                    "and the ceiling that falls out is an arithmetic result rather than a "
                    "recommendation. Placing the bid is the buyer's act, not yours."
                ),
                produces=("lot_economics",),
            ),
        ),
        artifacts=(
            artifact(
                "lot_dossier",
                "Lot dossier",
                (
                    "The listing as captured with its time and address, its declared "
                    "fields, the photographs it carried and every disagreement between "
                    "what was declared and what is visible."
                ),
                "bundle",
            ),
            artifact(
                "lot_economics",
                "Lot economics sheet",
                (
                    "The damage tier with the images behind it, what the photographs "
                    "could not reach, and every economic input with its source, its date "
                    "and the ceiling the arithmetic produces."
                ),
                "report",
            ),
        ),
        tools=("listing_parser", "listing_capture", "valuation_inputs"),
        config_keys=(
            ConfigKey(
                key="damage_tiers",
                description=(
                    "The tiers a lot is placed in, what evidence each tier requires "
                    "and the recovery each implies in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="economics_inputs",
                description=(
                    "The reference value, parts, labour, transport and fee sources "
                    "the sheet may draw on, and the freshness each must have."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "lots tiered with the images that support the tier attached",
            "economic inputs carrying a source and a date",
            "declared conditions the analysis found the photographs contradicted",
        ),
    ),
    Profile(
        name="damage_assessment",
        summary=(
            "Damage graded from photographs against a named severity scale -- "
            "item, location and extent -- with what the images cannot reach said "
            "plainly and the price, the cause and the cover left to the decider."
        ),
        match=(
            "damage",
            "claim",
            "repair",
            "collision",
            "peril",
            "write-off",
            "loss adjust",
        ),
        steps=(
            step(
                "locate_each_item_and_state_its_extent",
                "Name the item, its location and how far the damage runs",
                StepKind.ASSESS,
                (
                    "Work item by item: what is damaged, where it sits on the subject, "
                    "what kind of damage is visible and how far it extends, each line "
                    "citing the image and the region within it. Give extent in the terms "
                    "the reference uses -- panel, component, area, count, dimension "
                    "against a scale reference in frame -- and not in adjectives, because "
                    "'minor' and 'severe' mean a different number to every reader. Then "
                    "write down what these images cannot show: what is behind a panel, "
                    "under a covering, inside a unit or hidden by the angle the "
                    "photographs were taken from. The unseen list is part of the "
                    "assessment and the commonest thing left out of it."
                ),
                produces=("damage_schedule",),
            ),
            step(
                "assemble_the_pack_for_whoever_decides",
                "Assemble the pack for the person who owns the decision",
                StepKind.DRAFT,
                (
                    "Put the schedule, the images it cites, the documents collected and "
                    "the job, policy or claim reference into one pack addressed to the "
                    "estimator, adjuster or engineer the configuration names, with their "
                    "determination field left empty. Where the reference maps a graded "
                    "item to a labour, parts or settlement line in the price book the "
                    "configuration names, cite the line and its version; where it does "
                    "not, the line stays blank rather than estimated. Cover, fault, "
                    "cause, total loss and final cost are theirs "
                    "to decide, and the pack's whole job is to let them decide quickly "
                    "without going back to the photographs themselves."
                ),
                produces=("assessment_pack",),
            ),
        ),
        artifacts=(
            artifact(
                "damage_schedule",
                "Damage schedule",
                (
                    "Every damaged item with its location, damage type, extent in the "
                    "reference's own units, the image and region it was read from, its "
                    "confidence, and the list of what the images could not show."
                ),
                "report",
            ),
            artifact(
                "assessment_pack",
                "Assessment pack",
                (
                    "The schedule, the cited images, the collected documents and the "
                    "case reference in one pack for the named decider, with the "
                    "determination, cover and cost fields left for them."
                ),
                "bundle",
            ),
        ),
        tools=("severity_reference", "region_annotator", "case_record"),
        config_keys=(
            ConfigKey(
                key="severity_scale",
                description=(
                    "How damage is graded in this vertical: the bands, what evidence "
                    "each band requires and the wording each band is stated in."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="hidden_damage_policy",
                description=(
                    "What must be declared as unassessable from images alone, and "
                    "the inspection each such item is referred to."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="decision_owner",
                description=(
                    "The licensed or authorised role each class of assessment is "
                    "handed to, with the out-of-hours fallback."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "graded items citing an image, a region and a scale band",
            "packs the decider accepted without returning for more photographs",
            "gradings the decider revised after seeing the subject",
        ),
    ),
    Profile(
        name="pre_visit_qualification",
        summary=(
            "A job tested against the owner's qualification rules from photographs "
            "and a written spec, so a visit is spent only where the images cannot "
            "close the question."
        ),
        match=("pre-visit", "site visit", "qualif", "photo/spec"),
        steps=(
            step(
                "test_the_job_against_the_qualification_rules",
                "Run the images and the spec against the owner's rules",
                StepKind.ASSESS,
                (
                    "Test what the photographs and the written spec show against the "
                    "rules the owner set -- the work the business takes and the work it "
                    "does not, access, size band, materials, condition, distance, and the "
                    "shape of job that has lost money before -- recording rule by rule "
                    "which is met, which is failed and which cannot be answered from what "
                    "was supplied. A rule you cannot answer is not a rule that passed."
                ),
                produces=("qualification_result",),
            ),
            step(
                "build_the_job_file_or_name_what_the_visit_is_for",
                "Build the file, or say exactly what the visit is still for",
                StepKind.DRAFT,
                (
                    "Build the file the estimator would otherwise build standing in the "
                    "driveway: the scope as far as the images support it, measurements "
                    "taken against a scale reference in frame, access and constraint "
                    "notes, the assumptions made and the open questions ranked by how "
                    "much each one moves the number. Where the file cannot be closed from "
                    "images, name what the visit is for, what it must measure and how "
                    "long it needs, so the visit is booked against a question rather than "
                    "a hope. A job that fails the rules leaves with a specific, courteous "
                    "reason and whatever referral the configuration allows."
                ),
                produces=("qualified_job_file",),
            ),
        ),
        artifacts=(
            artifact(
                "qualification_result",
                "Qualification result",
                (
                    "Every qualification rule with its answer -- met, failed or "
                    "unanswerable from the supplied media -- and the image or spec line "
                    "behind each answer."
                ),
            ),
            artifact(
                "qualified_job_file",
                "Qualified job file",
                (
                    "The scope as the images support it, measurements with their scale "
                    "reference, access and constraint notes, stated assumptions, ranked "
                    "open questions and what a site visit would still be for."
                ),
                "document",
            ),
        ),
        tools=("qualification_rules", "measurement_from_image", "job_file_builder"),
        config_keys=(
            ConfigKey(
                key="qualification_rules",
                description=(
                    "The work this business takes and declines, with the access, "
                    "size, material and distance bands each rule tests."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="visit_trigger_conditions",
                description=(
                    "What must be answered on site rather than from images in this "
                    "vertical, and the visit length each condition needs."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "jobs qualified from images with no visit spent",
            "visits booked against a named open question",
            "site visits spent on jobs the rules would have declined",
        ),
    ),
    Profile(
        name="progress_diary",
        summary=(
            "The same subject photographed from fixed positions on a cadence, read "
            "as movement between then and now, and written for the client with "
            "what did not move named as plainly as what did."
        ),
        match=("progress", "site diary", "diary", "milestone", "week-on-week"),
        steps=(
            step(
                "compare_this_capture_against_the_last",
                "Set today's capture against the last one from the same position",
                StepKind.ASSESS,
                (
                    "Compare each of today's images against the last set taken from the "
                    "same fixed position and say what changed, what did not and what is "
                    "now waiting on something. Hold the positions the configuration fixes: "
                    "two photographs taken from different places cannot be compared, and a "
                    "diary whose angle drifts records nothing. State movement against the "
                    "programme line it belongs to, and record a line that has not moved "
                    "for several captures as its own finding -- stillness is the thing the "
                    "client is paying you to notice."
                ),
                produces=("progress_delta",),
            ),
            step(
                "write_the_period_report_for_the_client",
                "Write the period for the client, not for the site",
                StepKind.DRAFT,
                (
                    "Write it for somebody who was not there and does not read drawings: "
                    "what was done in the period, what it means for the dates they care "
                    "about, what is waiting on a decision of theirs, and the photographs "
                    "that show each claim. Where the images show something that is not "
                    "progress -- damage, an obstruction, work that will need doing twice, "
                    "a condition that looks hazardous -- record it and route it to the "
                    "site manager the configuration names, without grading it, explaining "
                    "it away or softening it out of the report."
                ),
                produces=("progress_report",),
            ),
        ),
        artifacts=(
            artifact(
                "progress_delta",
                "Period delta",
                (
                    "Each fixed position with its previous and current capture, what "
                    "moved, what did not, how many captures a stalled line has been "
                    "still, and the programme line each is stated against."
                ),
            ),
            artifact(
                "progress_report",
                "Client progress report",
                (
                    "The period written for the client: work done, effect on the dates "
                    "they care about, decisions awaited from them, the photographs behind "
                    "each claim and anything routed on rather than reported."
                ),
                "document",
            ),
        ),
        tools=("capture_positions", "period_comparer", "client_report_composer"),
        config_keys=(
            ConfigKey(
                key="capture_positions",
                description=(
                    "The fixed vantage points each subject is photographed from, "
                    "their framing and the cadence they are captured on."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="programme_lines",
                description=(
                    "The programme, stage or milestone structure progress is stated "
                    "against in this vertical, with its current baseline."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "periods reported on their cadence with the fixed positions captured",
            "report claims carrying the photograph that shows them",
            "stalled lines reported before the client asked about them",
        ),
    ),
    Profile(
        name="standards_audit",
        summary=(
            "A written standard worked line by line against photographic "
            "evidence, scored only where the evidence supports a score, with the "
            "unevidenced lines left visibly unevidenced."
        ),
        match=(
            "audit",
            "checklist",
            "inspector",
            "brand-standard",
            "standards evidence",
            "shelf",
            "planogram",
            "in-store execution",
            "per property",
            "per visit",
            "quality",
        ),
        steps=(
            step(
                "collect_the_evidence_line_by_line",
                "Work the standard in its own order and demand its evidence",
                StepKind.GATHER,
                (
                    "Go through the standard in its own order and require the evidence "
                    "each line names -- that area, that fixture, that display, that room, "
                    "at that stage, from that angle -- rather than accepting whatever the "
                    "field capture happened to contain. Index each image to the line it "
                    "answers and leave lines with nothing against them empty. An "
                    "unevidenced line is unevidenced; it is never quietly scored from the "
                    "general impression the other photographs gave."
                ),
                produces=("evidence_index",),
            ),
            step(
                "score_only_what_the_evidence_shows",
                "Score against the version in force, citing the image",
                StepKind.ASSESS,
                (
                    "Mark every line met, not met or unevidenced against the version of "
                    "the standard that was in force on the date of the visit rather than "
                    "the version current today, quoting the line's own wording and citing "
                    "the image that answers it. Where a line is not met, describe the gap "
                    "in the standard's own terms and stop there: the re-visit, the "
                    "charge-back, the franchise notice, the score that affects somebody's "
                    "contract and the judgement of whether a site or a person is "
                    "performing all belong to the human the configuration routes it to."
                ),
                produces=("standard_scorecard",),
            ),
        ),
        artifacts=(
            artifact(
                "evidence_index",
                "Evidence index",
                (
                    "Each line of the standard with the images indexed against it, the "
                    "required evidence that was supplied and the lines left with nothing "
                    "against them."
                ),
            ),
            artifact(
                "standard_scorecard",
                "Standard scorecard",
                (
                    "Every line marked met, not met or unevidenced against the version "
                    "in force on the visit date, with the quoted line, the cited image "
                    "and the gap described in the standard's own terms."
                ),
                "report",
            ),
        ),
        tools=("standard_register", "checklist_runner", "field_capture_app"),
        config_keys=(
            ConfigKey(
                key="standard_definition",
                description=(
                    "The checklist, brand standard or planogram in force for this "
                    "vertical, its version history and the effective date of each."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="evidence_requirements",
                description=(
                    "The photographic evidence each line of the standard requires: "
                    "subject, angle, stage and how recent it must be."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="remediation_owner",
                description=(
                    "Who receives a not-met line and who decides the consequence "
                    "attached to it, with the escalation ladder above them."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "standard lines scored with an image cited against them",
            "audits carrying every required view at first capture",
            "lines scored met that the reviewing human found unevidenced",
        ),
    ),
    Profile(
        name="reference_match",
        summary=(
            "A photographed object matched against a reference catalogue and "
            "returned as ranked candidates with the feature that tells them apart "
            "and the physical check that settles it."
        ),
        match=(
            "part number",
            "spare-part",
            "parts catalogue",
            "identifier",
            "identification",
            "photo-matched",
        ),
        steps=(
            step(
                "rank_the_candidates_on_visible_features",
                "Rank candidates on the features the catalogue keys on",
                StepKind.ASSESS,
                (
                    "Read off the features the reference catalogue actually keys on -- "
                    "form, mounting, connector, orientation, counts, cast or stamped "
                    "markings, dimensions taken against a scale reference in frame -- and "
                    "return ranked candidates, each with the feature evidence behind it "
                    "and the one feature that tells it apart from the next. A single answer "
                    "with no runner-up hides how close the call was; the ranking is the "
                    "honest output and the shortlist is a legitimate result."
                ),
                produces=("candidate_matches",),
            ),
            step(
                "name_the_check_that_settles_it",
                "Name the physical check that settles the match",
                StepKind.DRAFT,
                (
                    "For the leading candidate, name the confirmation the person at the "
                    "other end can actually perform before anything is ordered or fitted: "
                    "the stamped number to read off, the dimension to measure, the "
                    "fitment to check against the machine's own serial or build record. "
                    "Say what a wrong match costs here -- a shipped part, a stripped "
                    "machine, a shift lost -- because that is what decides whether the "
                    "check is worth the two minutes. A confident wrong identification is "
                    "far more expensive than an honest shortlist."
                ),
                produces=("match_confirmation",),
            ),
        ),
        artifacts=(
            artifact(
                "candidate_matches",
                "Ranked candidate matches",
                (
                    "Each candidate from the reference catalogue with its confidence, "
                    "the visible features supporting it, the images they were read from "
                    "and the feature that tells it apart from the next candidate."
                ),
                "report",
            ),
            artifact(
                "match_confirmation",
                "Confirmation instruction",
                (
                    "The physical check that settles the identification, where to "
                    "perform it, what a pass and a fail look like, and the consequence "
                    "of proceeding on the wrong match."
                ),
                "document",
            ),
        ),
        tools=("reference_catalogue", "feature_extractor", "fitment_lookup"),
        config_keys=(
            ConfigKey(
                key="reference_catalogue",
                description=(
                    "The catalogue matches are made against, the features it keys "
                    "on, its version and how supersessions are represented."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="match_confidence_floor",
                description=(
                    "The confidence below which a shortlist is returned instead of a "
                    "leading candidate in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "identifications confirmed correct by the person who fitted the part",
            "matches returned with a ranked runner-up and a distinguishing feature",
            "wrong items ordered against a stated match",
        ),
    ),
    Profile(
        name="portfolio_consent",
        summary=(
            "Field photographs paired into before/after entries, held until "
            "consent scoped to that use is on file, and put out only from the "
            "customer's own accounts."
        ),
        match=(
            "portfolio curator",
            "portfolio loop",
            "portfolio entries",
            "before/after",
            "consented",
        ),
        steps=(
            step(
                "pair_the_before_with_the_after",
                "Pair the shots and hold them to the business's own standard",
                StepKind.ASSESS,
                (
                    "Pair each 'after' with the 'before' of the same job taken from the "
                    "same vantage point, and hold the pair to the standard the owner "
                    "would want their name on: comparable angle and light, the work "
                    "plainly visible, and nothing in frame that identifies a customer, a "
                    "child, a plate, a door number, a document or a security arrangement. "
                    "A pair that only works because the 'before' was badly lit is not a "
                    "portfolio entry, and a striking photograph of somebody's front door "
                    "is not one either."
                ),
                produces=("portfolio_candidates",),
            ),
            step(
                "hold_for_consent_and_the_owner_s_pick",
                "Hold for scoped consent and the owner's pick",
                StepKind.GATE,
                (
                    "Hold every candidate until two things exist: consent covering this "
                    "specific use, recorded, dated, scoped and revocable, and the owner's "
                    "own selection of which pairs represent the business. Consent to "
                    "photograph a job is not consent to show it, and a consent given for "
                    "a case file is not a consent for a storefront -- where the record "
                    "carries only the first, ask for the second in writing. Anything "
                    "missing either stays in the candidate list indefinitely."
                ),
                produces=("consent_record",),
            ),
            step(
                "place_the_entry_on_the_customer_s_own_surfaces",
                "Publish from the customer's own accounts, never from ours",
                StepKind.ACT,
                (
                    "Take the pairs the owner selected at the gate and publish them to "
                    "the customer's own website, storefront and connected profiles under "
                    "the grants held for those accounts, in the business's own voice, "
                    "with the caption naming the work rather than the client. The "
                    "platform never posts from an account it owns. Record where each "
                    "entry went and keep the link, so a later withdrawal of consent can "
                    "be executed everywhere the pair reached rather than only where it "
                    "was first placed."
                ),
                produces=("portfolio_entry",),
            ),
        ),
        artifacts=(
            artifact(
                "portfolio_candidates",
                "Portfolio candidates",
                (
                    "Each before/after pair with the job it came from, the vantage "
                    "point, the quality assessment and the identifying detail found or "
                    "cleared from frame."
                ),
            ),
            artifact(
                "consent_record",
                "Scoped consent record",
                (
                    "The consent held for each pair: who gave it, when, for which use, "
                    "how long it lasts, how it is withdrawn and what withdrawal removes."
                ),
            ),
            artifact(
                "portfolio_entry",
                "Published portfolio entry",
                (
                    "The live entry with its caption, the surfaces it reached, the "
                    "account grant it went out under and the link held for withdrawal."
                ),
                "record",
            ),
        ),
        tools=("consent_register", "media_editor", "storefront_connector"),
        config_keys=(
            ConfigKey(
                key="portfolio_consent_scope",
                description=(
                    "The consent this market requires before a customer's job, "
                    "premises or likeness is shown, and what a withdrawal must undo."
                ),
                required=True,
            ),
            ConfigKey(
                key="portfolio_standards",
                description=(
                    "What the owner will and will not show: quality bar, captioning, "
                    "the work types featured and what must never appear in frame."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "entries live with scoped consent recorded before publication",
            "candidates the owner released without an edit",
            "entries withdrawn from every surface within the withdrawal window",
        ),
        channels=("website", "social_profiles", "listing_profiles"),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: loose media arrives, each item is bound to the record it belongs
    # to, the set is checked against what the stage requires, and what is
    # missing is asked for.  The units that land here -- the front desk's photo
    # and document triage, and the playbook that fires when job photos are
    # sitting unfiled -- are exactly that and nothing more.
    Profile(
        name="media_intake_filing",
        summary=(
            "Loose photographs and documents brought under control: bound to the "
            "job, customer and stage they belong to, checked against what the "
            "stage requires, and nothing filed on a guess."
        ),
        match=(),
        steps=(
            step(
                "check_the_set_against_what_the_stage_requires",
                "Check the filed set against what this stage requires",
                StepKind.ASSESS,
                (
                    "Hold the filed set against what the record's current stage requires "
                    "-- the views, the documents, the readings, the signatures -- and "
                    "report three lists: present and usable, missing, and present but too "
                    "poor to serve. Readiness is a statement about the set of files and "
                    "nothing else: you report whether the paperwork and the photographs "
                    "are complete, never whether the job, the vehicle, the property or "
                    "the claim behind them is in order."
                ),
                produces=("readiness_result",),
            ),
            step(
                "surface_the_gaps_and_the_candidates",
                "Ask for the gaps and nominate what is worth keeping",
                StepKind.DRAFT,
                (
                    "Get two lists out of the one pass. The first is what is still "
                    "needed, addressed to whoever can actually get it and written in the "
                    "words of the person who has to go and take the photograph. The "
                    "second is what is worth another use later -- a before/after pair, a "
                    "finished job worth showing, evidence a dispute may want -- flagged "
                    "as a candidate with its consent state attached and handed to "
                    "whoever owns that use. A candidate is a nomination and never a "
                    "publication: nothing leaves the record on your say-so."
                ),
                produces=("chase_list", "reuse_candidates"),
            ),
        ),
        artifacts=(
            artifact(
                "readiness_result",
                "Readiness result",
                (
                    "What this stage requires, what is present and usable, what is "
                    "missing and what is present but unusable, with the reason each "
                    "unusable item failed."
                ),
                "report",
            ),
            artifact(
                "chase_list",
                "Outstanding-items list",
                (
                    "Each missing or unusable item with who can supply it, exactly what "
                    "is wanted, and what the record cannot proceed to without it."
                ),
            ),
            artifact(
                "reuse_candidates",
                "Nominated candidates",
                (
                    "Items flagged as worth another use, the use nominated, the consent "
                    "state on file and the owner of that use, held as nominations only."
                ),
            ),
        ),
        tools=("media_library", "record_index", "stage_requirements"),
        config_keys=(
            ConfigKey(
                key="stage_requirements",
                description=(
                    "What media and documents each stage of the record requires in "
                    "this vertical before the stage may be treated as complete."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="unbound_media_policy",
                description=(
                    "Where items that bind to no record are held, who reviews them "
                    "and how long they wait before the owner is asked."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "items bound to a record with binding evidence on first pass",
            "records reaching their next stage without a chase for media",
            "items filed against the wrong record and later re-bound",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class VisionAssessmentEngine(Engine):
    """Carries every unit whose raw material is a photograph or a video frame.

    The engine holds one pipeline -- take delivery of the media, bind each item
    to its record, grade the capture, read what is visible against the configured
    reference, decide what may be stated, write it, file it, and hand it over
    with the gaps named -- and eight profiles that say what the images are being
    read against and who the answer belongs to.  Nothing in the code knows
    whether it is holding collision damage, a shelf, a site diary or a salvage
    lot; the required views, the reference, the confidence thresholds and the
    consent and retention regime all arrive as configuration.
    """

    id: ClassVar[str] = "MF9"
    family: ClassVar[str] = "Vision assessment"
    what_it_does: ClassVar[str] = (
        "Photo and video assessment - damage, progress, proof, portfolio, "
        "shelf audit"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.ASSESS_MEDIA,
        Capability.COLLECT_DOCUMENTS,
        Capability.SCORE,
        Capability.RECONCILE,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "media_intake",
        "metadata_reader",
        "record_binder",
        "capture_quality_grader",
        "vision_reader",
        "reference_lookup",
        "annotation_writer",
        "media_vault",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "field_capture",
        "owner_dashboard",
        "email",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "findings citing the item, the region and the reference line behind them",
        "required views present at first capture",
        "assessments accepted without sending somebody back to re-photograph",
        "findings the deciding human revised once they saw the subject",
        "items bound to the wrong record, or left unbound",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "media_dossier"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Take delivery, bind, grade the capture, read, decide, write, file, hand over.

        Two placements in that order carry most of the weight.  The capture is
        graded *before* the subject is read, because a model asked to describe an
        unusable image will describe it anyway, and the resulting sentence is
        indistinguishable from a good one by the time it reaches a quote.  And
        binding happens *before* assessment rather than after it, because an
        assessment written against the wrong job is not a mistake anybody catches
        downstream -- it is simply believed.  The hand-over is last and always
        names the gaps, since the entire value of an honest 'cannot be determined
        from these images' is destroyed if it never leaves the working file.
        """
        return (
            step(
                "take_delivery_of_the_media",
                "Enumerate everything that arrived, before looking at any of it",
                StepKind.OBSERVE,
                (
                    "List every image, video, frame and accompanying document that "
                    "arrived for this assessment before you read anything into them: "
                    "file, format, dimensions, duration, the capture time the file itself "
                    "carries rather than the time it reached you, the device or account "
                    "it came from and who supplied it. Count what arrived against what "
                    "was asked for. An item with no timestamp of its own is recorded as "
                    "undated rather than dated by its arrival, and a set you never "
                    "enumerated cannot be shown to have been complete when a dispute "
                    "reaches it eighteen months later."
                ),
                produces=("media_manifest",),
            ),
            step(
                "bind_each_item_to_its_record",
                "Bind every item to its record, on evidence",
                StepKind.GATHER,
                (
                    "Bind each item to the record it belongs to -- the job, the visit, "
                    "the claim, the property, the lot, the part, the stage -- using the "
                    "binding rules the configuration sets, and record the evidence for "
                    "every binding: the reference in the request, the location tag, the "
                    "capture time against the visit window, the label or asset tag in "
                    "frame. Capture the consent state that already exists for each item "
                    "at the same moment, because it governs everything that can be done "
                    "with it afterwards. An item that binds to nothing goes on the "
                    "unbound list with the reason and waits for a person: a photograph "
                    "attached to the nearest plausible record is worse than one nobody "
                    "filed, because it will be believed."
                ),
                produces=("provenance_record",),
            ),
            step(
                "grade_the_capture_before_the_subject",
                "Grade the images before you read them",
                StepKind.ASSESS,
                (
                    "Test whether these images can carry the assessment being asked of "
                    "them before you read anything into them: resolution, focus, "
                    "exposure, framing, obstruction, whether a scale reference is in "
                    "frame, and which of the views the capture specification requires are "
                    "present, missing or unusable. Mark the unusable ones and say why in "
                    "terms the person who took them can act on. A confident finding drawn "
                    "from an image that could never have supported one is the "
                    "characteristic failure of this work, and it is undetectable "
                    "downstream: by the time it reaches a quote or a payment it reads "
                    "exactly like a good finding."
                ),
                produces=("capture_assessment",),
            ),
            step(
                "read_what_is_visible_against_the_reference",
                "Say what is visible, and where, and against which line",
                StepKind.ASSESS,
                (
                    "Read each usable item against the reference the configuration names "
                    "-- the severity scale, the checklist line, the standard, the "
                    "planogram, the catalogue entry, the specification, the previous "
                    "capture -- and record findings one at a time: what is visible, in "
                    "which item, in which region of the frame, which reference line it "
                    "answers and how sure you are. Describe, and do not interpret. "
                    "'Panel deformed across roughly a third of its area, rear near-side "
                    "door, image 4 of 9, high confidence' is a finding; 'minor damage, "
                    "cheap to fix' is two judgements the photograph never contained. Any "
                    "reference line the images do not reach is recorded as unanswered "
                    "rather than left out."
                ),
                produces=("visual_findings",),
            ),
            step(
                "decide_what_may_be_stated",
                "Sort findings by what the images will actually bear",
                StepKind.DECIDE,
                (
                    "Sort every finding against the configured confidence thresholds "
                    "into three groups and record which threshold produced each answer: "
                    "what may be stated as observed, what is carried as undetermined "
                    "until better images arrive, and what goes to a named human whatever "
                    "the confidence because its class always does. A finding below the "
                    "threshold is never rounded up into a statement, and undetermined is "
                    "a real answer rather than a failure to produce one -- it is the line "
                    "that stops somebody pricing, paying, ordering or dispatching against "
                    "a guess."
                ),
                produces=("confidence_decision",),
            ),
            step(
                "write_the_assessment",
                "Write it so every line walks back to an image",
                StepKind.DRAFT,
                (
                    "Write the output in the shape the record needs -- a filed and tagged "
                    "set, a scored checklist, a scoped draft, a period report, a tiered "
                    "lot, a ranked match -- with every line carrying the item it came "
                    "from, the region within it, the reference line it answers and its "
                    "confidence. Keep the undetermined findings and the missing views in "
                    "the body of the document rather than in a footnote nobody reads. "
                    "Nothing about price, cause, fault, cover, safety or compliance "
                    "enters the draft: those belong to the estimator, the adjuster, the "
                    "inspector or the owner, and what you are writing is the thing they "
                    "decide from."
                ),
                produces=("assessment_record",),
            ),
            step(
                "file_the_media_and_the_findings",
                "File the originals untouched, work on copies",
                StepKind.ACT,
                (
                    "Write the originals, the derivatives you generated and the findings "
                    "against the record, keeping every original unaltered beside any "
                    "annotated, cropped or enhanced copy and recording which "
                    "transformation produced which derivative. Apply the redaction the "
                    "configuration requires -- faces, plates, documents and bystanders "
                    "who never agreed to be in frame -- to the derivatives rather than to "
                    "the originals, and start the retention clock the market sets. The "
                    "original is the evidence; once it has been annotated over, whatever "
                    "the image would have shown a reviewer is gone for good."
                ),
                produces=("filed_media_set",),
            ),
            step(
                "hand_it_over_with_the_gaps_named",
                "Hand it over naming the gaps and the exact shot that fixes them",
                StepKind.NOTIFY,
                (
                    "Tell whoever asked what was produced and, in the same breath, what "
                    "could not be assessed and precisely which shot would settle it: "
                    "which view, of what, from where, at what distance, in what light. A "
                    "request that says 'photos unclear' reliably produces another set of "
                    "unclear photos. Where the assessment feeds somebody's decision -- a "
                    "price, a payment, a dispatch, an order, a bid -- state which lines "
                    "are observed and which are undetermined, so a gap in the evidence is "
                    "never read as a clean result."
                ),
                produces=("assessment_handover",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "media_manifest",
                "Media manifest",
                (
                    "Every item that arrived: file, format, dimensions or duration, its "
                    "own capture time, the device or account it came from, who supplied "
                    "it, and what was expected against what turned up."
                ),
                "log",
            ),
            artifact(
                "provenance_record",
                "Provenance and binding record",
                (
                    "Per item: the record it was bound to, the evidence for that "
                    "binding, the consent state already on file, and the unbound items "
                    "with the reason each could not be placed."
                ),
            ),
            artifact(
                "capture_assessment",
                "Capture assessment",
                (
                    "Every required view marked present, missing or unusable, with the "
                    "technical reason each unusable item failed, written so the person "
                    "who took it can act on it."
                ),
                "report",
            ),
            artifact(
                "visual_findings",
                "Visual findings",
                (
                    "One line per observation: what is visible, the item and region it "
                    "was read from, the reference line it answers, its confidence, and "
                    "the reference lines the images did not reach."
                ),
            ),
            artifact(
                "confidence_decision",
                "Confidence decision",
                (
                    "For every finding: the threshold applied, whether it is stated, "
                    "carried as undetermined or routed to a human, and the class rule "
                    "that forced a routing regardless of confidence."
                ),
            ),
            artifact(
                "assessment_record",
                "Assessment record",
                (
                    "The output in the shape the record needs, every line carrying its "
                    "item, region, reference line and confidence, with the undetermined "
                    "findings and missing views in the body."
                ),
                "document",
            ),
            artifact(
                "filed_media_set",
                "Filed media set",
                (
                    "The originals held unaltered beside every derivative, the "
                    "transformation behind each derivative, the redaction applied and "
                    "the retention clock running on both."
                ),
                "bundle",
            ),
            artifact(
                "assessment_handover",
                "Hand-over note",
                (
                    "What was produced, what could not be assessed, which lines are "
                    "observed and which undetermined, and the exact shot that would "
                    "settle each gap."
                ),
                "document",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"Which views a {vertical['name'].lower()} assessment requires, what "
                f"the images are read against, how a finding is graded there and what "
                f"may be done with a customer's photograph afterwards all come from "
                f"the vertical overlay and the active country pack -- read both "
                f"rather than deciding for yourself what a good capture or a fair "
                f"grade looks like here."
            )
        else:
            where = (
                "This unit runs across every vertical on the platform, so the views "
                "each assessment requires, the reference the images are read against "
                "and the consent and retention rules that govern them all come from "
                "whatever overlay and country pack is in front of you."
            )
        return (
            "HOW YOU WORK. A photograph is evidence of what was in front of the lens "
            "at one moment and of nothing else, so everything you produce stays on "
            "the near side of that line: you say what is visible, in which item, in "
            "which region of the frame, against which line of the reference you were "
            "given, and how sure you are. Grade the capture before you read the "
            "subject -- resolution, focus, framing, obstruction, scale reference, and "
            "the required views present or missing -- because a confident finding "
            "drawn from an image that could never have carried one is this work's "
            "characteristic failure and is undetectable by the time it reaches a "
            "quote. Bind every item to its record on evidence and put what will not "
            "bind onto the unbound list, since a photograph attached to the nearest "
            "plausible job is worse than one nobody filed: it will be believed. Treat "
            "'cannot be determined from these images' as a real answer and carry it "
            "all the way into the output, because it is the line that stops somebody "
            "pricing, paying or dispatching against a guess, and it is the first "
            "thing a hurried draft loses. When something is missing, ask for the "
            "exact shot -- which view, of what, from where, in what light -- since "
            "'photos unclear' only ever produces another set of unclear photos. Keep "
            "the original untouched and do your annotating, cropping and redaction on "
            "copies, applying the redaction the configuration requires to faces, "
            "plates, documents and bystanders who never agreed to be in frame. Use an "
            "image beyond the job it was taken for only where consent scoped to that "
            "use is recorded, dated and revocable, because consent to take a "
            "photograph is not consent to show it. And stop where the photograph "
            "stops: price, cause, fault, cover, safety and compliance verdicts belong "
            "to the estimator, adjuster, inspector, engineer or owner you hand the "
            f"pack to. {self._profile_line(profile)} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-VISIBLE-NOT-INFERRED",
                rule=(
                    "The unit reports what is visible and the reference line it "
                    "answers. It never states price, cause, fault, cover, safety or "
                    "a compliance verdict from a photograph."
                ),
                check=(
                    "Every line of visual_findings and assessment_record cites an item, "
                    "a region and a reference line; no line asserts a cost, a cause, a "
                    "liability or a clearance the named reference does not carry."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CAPTURE-GRADED-FIRST",
                rule=(
                    "The images are graded for whether they can support the "
                    "assessment before the subject is read."
                ),
                check=(
                    "capture_assessment is produced before visual_findings and marks "
                    "every view in capture_specification present, missing or unusable; "
                    "no finding cites an item graded unusable."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-UNDETERMINED-SURVIVES",
                rule=(
                    "'Cannot be determined from these images' is a first-class "
                    "result and reaches the recipient intact."
                ),
                check=(
                    "confidence_decision classifies every finding against a named "
                    "threshold, and each undetermined line appears in the body of "
                    "assessment_record and in assessment_handover with the shot that "
                    "would resolve it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-BINDING-ON-EVIDENCE",
                rule=(
                    "An item is bound to a record on stated evidence or it is not "
                    "bound at all. Nothing is filed against the nearest plausible "
                    "match."
                ),
                check=(
                    "provenance_record carries the binding evidence for every bound "
                    "item and lists the unbound ones with a reason; bindings resolve to "
                    "record_binding_rules."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-ORIGINAL-IS-PRESERVED",
                rule=(
                    "Originals are retained unaltered with their metadata. "
                    "Annotation, cropping, enhancement and redaction happen on "
                    "derivatives."
                ),
                check=(
                    "filed_media_set holds an unaltered original for every derivative "
                    "with the transformation recorded, and the redaction media_retention "
                    "requires is applied to derivatives before any item leaves the "
                    "record."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CONSENT-SCOPED-TO-USE",
                rule=(
                    "An image is used beyond the job it was taken for only under "
                    "consent scoped to that use. Consent to photograph is not "
                    "consent to show."
                ),
                check=(
                    "Every item re-used for a portfolio, a listing, a report or a case "
                    "resolves to a consent entry naming that use, its date and its "
                    "withdrawal route, per media_consent_policy; withdrawal removes it "
                    "from every surface it reached."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "The media itself: images, video and frames with the metadata each file carries",
            "The record the media belongs to -- job, visit, claim, property, lot or part -- with its stage",
            "Capture specification in force: the views this assessment requires and the standard each must meet",
            "The reference the images are read against, with its version and effective date",
            "Consent already recorded against the subject, its scope and any withdrawal",
            "Prior captures of the same subject, where the assessment is a comparison",
        )

    # -- internals ----------------------------------------------------------
    def _profile_line(self, profile: Profile) -> str:
        """One sentence naming what this profile's images are read against.

        Kept beside the profiles rather than inside them because it is prose
        about the mission, not configuration a customer can override.
        """
        return _PROFILE_MISSION_LINES.get(
            profile.name, _PROFILE_MISSION_LINES["media_intake_filing"]
        )


#: Mission prose per profile.  Each names the reference the images are read
#: against, the artefact that proves the work, and the exact point at which the
#: assessment stops and a person takes over.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "auction_lot_analysis": (
        "What you read here is somebody else's listing: capture the lot page as it "
        "stood, hold every declared field against what the photographs actually "
        "show and report each disagreement, then tier the damage and build the "
        "economics with every input sourced and dated -- the ceiling is arithmetic "
        "you show your working for, and placing the bid is the buyer's act."
    ),
    "damage_assessment": (
        "What you read here is damage: name the item, where it sits and how far it "
        "runs in the reference's own units rather than in adjectives, write down "
        "plainly what is behind a panel or under a covering and therefore unseen, "
        "and hand the schedule and its images to the estimator or adjuster with "
        "their determination field empty -- cover, fault, total loss and final cost "
        "are theirs."
    ),
    "pre_visit_qualification": (
        "What you read here decides whether a visit gets spent: answer each of the "
        "owner's qualification rules from the photographs and the written spec, "
        "treat a rule you cannot answer as unanswered rather than passed, and "
        "either close the job file or say exactly what the visit is for, what it "
        "must measure and how long it needs."
    ),
    "progress_diary": (
        "What you read here is the same subject over time: compare only captures "
        "taken from the same fixed position, state movement against the programme "
        "line it belongs to, treat a line that has not moved for several captures "
        "as a finding in its own right, and route anything that is not progress to "
        "the site manager rather than grading it yourself."
    ),
    "standards_audit": (
        "What you read here is a written standard: work it line by line in its "
        "own order, demand the evidence each line names, score against the version "
        "in force on the visit date while quoting the line and citing the image, "
        "and leave an unevidenced line visibly unevidenced -- the consequence of a "
        "line not met belongs to the human it routes to."
    ),
    "reference_match": (
        "What you read here is an object against a catalogue: extract the features "
        "the catalogue actually keys on, return ranked candidates with the feature "
        "that tells the top two apart rather than a lone confident answer, and name "
        "the physical check -- the stamped number, the dimension, the fitment -- "
        "that settles it before anything is ordered or fitted."
    ),
    "portfolio_consent": (
        "What you read here will be seen in public: pair before with after from the "
        "same vantage point, clear every identifying detail out of frame, hold the "
        "pair until consent scoped to this exact use and the owner's own pick both "
        "exist, and put it out only from the customer's connected accounts with the "
        "link kept so a withdrawal can be executed everywhere it reached."
    ),
    "media_intake_filing": (
        "What you read here is a pile of loose media: bind each item to its job, "
        "customer and stage on evidence, report the set against what the stage "
        "requires as present, missing or unusable, ask for the gaps in the words of "
        "whoever must go and take the photograph, and nominate what is worth "
        "another use later without ever acting on the nomination yourself."
    ),
}


__all__ = ["VisionAssessmentEngine"]

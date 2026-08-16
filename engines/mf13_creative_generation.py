"""MF13 -- creative generation.

Every small business is told it must produce content continuously and none of
them has an hour spare to do it, so the work goes one of two ways.  It goes to
an agency, which writes the sentence that would fit any plumber, clinic or firm
in the country and gets sacked eighteen months later for exactly that.  Or it
goes to a generation model with a prompt, which writes fluent, confident,
plausible copy about a business it has never seen -- inventing the guarantee,
the timescale, the award and the fleet.  This family exists because neither
failure is necessary: the business is already producing the raw material.  The
job finished on Tuesday with a photograph and a fault nobody expected, the
review left on Thursday, the question the front desk has now answered four
times this month, the role that opened, the fixture that was played, the quarter
that closed.  The work is turning that record into something publishable and
adding nothing to it.

So the direction of travel is fixed and it runs from the record outward.  You
read the operational entries the run is built on, collect the permission behind
every person, premises, image, clip and quote the piece could carry, test each
statement against what may actually be claimed in this market, set a brief, and
only then write.  Every factual sentence traces back to an entry; every figure
comes from published pricing; a claim with no source is removed rather than
softened, because a hedge is how an invented fact survives review.  Then the
draft is read back against the thing it came from -- what a model writes is
fluent by construction and true only by inspection -- and it stops at the
approval queue.  Drafting is the whole of the authority here.  A person
releases; the unit never does, and a piece that has gone out is public from the
moment it lands and cannot be recalled from the people who already read it.

Generated imagery and video change the economics of this and nothing else.  An
asset that costs cents can be made in hundreds, which is the point of the stack
and also its hazard: the cost of a wrong asset was never the cost of making it.
A generation model produces a convincing picture of a business of this kind, not
a picture of this business, so anything depicting work, premises, staff,
equipment or a product is checked against what the customer actually has and
discarded when it is not -- a van in the wrong livery, safety equipment nobody
owns, a room that does not exist.  Every asset carries its provenance: the
model, the prompt, the references and the licence each of them came under, plus
whatever disclosure this market requires of synthetic media.  And cheapness is
never a reason to produce: a calendar slot with no operational entry behind it
is left empty and reported, because filling it is the precise moment the
programme starts writing about nothing.

The rest is configuration.  The owner's voice, the brand kit, which operational
systems may become content and which fields of them never leave the building,
what may be claimed here and with what disclosure, what consent a customer,
employee or property must have given, the format specification of every surface
and who releases what -- all of it resolves from the owner's setup, the vertical
overlay and the active country pack.  That is how one engine carries a review
reply written in an afternoon, a compliance-gated quarterly commentary, a job
advert bound by employment law, a matchday clip cut nine ways and a marketplace
listing completed attribute by attribute, without knowing which of them it is
holding.
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
#: difference between one vertical's content and another's: whose voice it is
#: written in, what it may look like, which operational records it is allowed to
#: draw on, what may lawfully be claimed in this market, what permission a person
#: or a property must have given before appearing, and who releases the result.
#: Change them and the same code writes a review reply, a fund commentary and a
#: job advert.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="brand_voice",
        description=(
            "The owner's voice held as configuration: the samples behind it, the "
            "register and vocabulary, the words they use for their own services, "
            "and the phrasing they never use."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="brand_kit",
        description=(
            "The marks, palette, type, imagery rules and legal marks every visual "
            "asset is built to, the formats each surface takes, and who may vary "
            "any of it."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="grounding_sources",
        description=(
            "Which operational systems may become content in this vertical, which "
            "of their fields may be used, and which never leave the building."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="claim_rules",
        description=(
            "What may be claimed in this market: superlatives, guarantees, outcome "
            "and comparative claims, testimonials and endorsements, with the "
            "disclosure or qualification each permitted claim must carry."
        ),
        required=True,
    ),
    ConfigKey(
        key="consent_policy",
        description=(
            "What permission a customer, client, employee or property must have "
            "given before appearing in content, how it is evidenced, how long it "
            "lasts, and what happens to material already out when it is withdrawn."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="approval_policy",
        description=(
            "Who releases which kind of piece, how long the queue waits for them, "
            "and what becomes of a draft nobody released."
        ),
        resolved_by="owner",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The nine creative shapes present in the catalogue, most specific first.
#: Tokens are the nouns of the *source* and the *surface* rather than the verbs
#: the whole family shares -- "draft", "content", "posts", "queued for approval"
#: would each swallow half the family, and "content drafter" is the fallback
#: unit's own system-agent name.  Three orderings carry weight.  The catalogue
#: profile must claim its unit before anything reaches the word "images", which
#: appears both in the generated-asset stack and in a marketplace listing.  The
#: review-reply tokens are all two-word phrases, because "review" alone sits
#: inside the journalist's source list and inside a quarterly pack "drafted for
#: review".  And the journalism profile must run ahead of the recruitment one,
#: since "jobs" is what the operational feed is full of and "job ads" is a
#: different trade entirely.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="generated_media",
        summary=(
            "Branded images and short video produced by a generation model at unit "
            "cost, built to the brand kit rather than to a prompt, and checked "
            "against what the business actually has before either becomes a "
            "deliverable."
        ),
        match=(
            "seedream",
            "seedance",
            "studio designer",
            "creative generation stack",
            "branded images",
            "branded assets",
            "short videos",
            "cents per",
        ),
        steps=(
            step(
                "generate_against_the_brand_kit_not_a_prompt",
                "Build each asset from the kit and the real references, not from a sentence",
                StepKind.DRAFT,
                (
                    "Build every asset from the brand kit and the campaign brief -- the "
                    "palette, the type, the marks and their placement, the format each "
                    "surface takes -- and use the customer's own photography of their own "
                    "premises, product and team as the reference wherever it exists. Record "
                    "the model and its version, the full prompt, the seed and every "
                    "reference asset with the licence it came under. An asset whose origin "
                    "nobody can reconstruct is one nobody can defend when a platform, a "
                    "client or a rights-holder asks where it came from."
                ),
                produces=("asset_manifest",),
            ),
            step(
                "look_at_what_came_back_before_it_becomes_a_deliverable",
                "Inspect every frame against what the business really has",
                StepKind.ASSESS,
                (
                    "Look at every generated frame before it goes anywhere: malformed text "
                    "and lettering, hands and faces, counts of people and objects, livery, "
                    "uniforms, safety equipment, tools, signage and anything else the model "
                    "has supplied because it looks right. The output is a convincing image "
                    "of a business of this kind, not of this one, so anything depicting "
                    "work, premises, staff or equipment is set against what the customer "
                    "actually has and discarded when it does not match. Log the cost of "
                    "each call against the period ceiling as you go: volume is what makes "
                    "this cheap and also what makes an unchecked run expensive."
                ),
                produces=("asset_review",),
            ),
        ),
        artifacts=(
            artifact(
                "asset_manifest",
                "Asset manifest",
                (
                    "Every generated asset with the model and version behind it, the full "
                    "prompt, the seed, each reference asset and its licence, the brand-kit "
                    "rules it was built to and what the call cost."
                ),
            ),
            artifact(
                "asset_review",
                "Asset review",
                (
                    "Per asset: what the inspection found -- invented detail, malformed "
                    "lettering, wrong livery, a depiction the business cannot support -- "
                    "and whether the asset was kept, remade or discarded."
                ),
                "report",
            ),
        ),
        tools=(
            "image_model",
            "video_model",
            "brand_kit_renderer",
            "reference_library",
            "asset_inspector",
            "generation_cost_meter",
        ),
        config_keys=(
            ConfigKey(
                key="generation_budget",
                description=(
                    "Which generation models this customer may use, the cost ceiling "
                    "per asset and per period, and what happens to a run that would "
                    "exceed it."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="synthetic_media_disclosure",
                description=(
                    "Whether this market requires generated imagery, video or voice "
                    "to be declared as generated, in what words, and on which "
                    "surfaces."
                ),
                required=True,
            ),
        ),
        kpis=(
            "assets delivered with a complete provenance record",
            "assets discarded at inspection before reaching a deliverable",
            "cost per delivered asset against the period ceiling",
        ),
        channels=("asset_library",),
    ),
    Profile(
        name="catalogue_enrichment",
        summary=(
            "A product record completed at volume -- title, attributes, copy and "
            "imagery -- against the schema of the marketplace it actually sits on, "
            "where every filled field is a promise the seller is held to."
        ),
        # Claims its unit early: this is the other shape in the family that talks
        # about images, and it means a photograph of a real product rather than a
        # generated one.
        match=(
            "catalog enrichment",
            "catalogue editor",
            "enriched listing",
            "titles, attributes",
            "attributes and images",
        ),
        steps=(
            step(
                "measure_each_record_against_the_schema_that_matters",
                "Score completeness against the marketplace's own model, not a general one",
                StepKind.ASSESS,
                (
                    "Measure every record against the schema of the marketplace it is "
                    "listed on: the required attributes, the category-specific fields, the "
                    "title pattern and its length, the image count and dimensions, the "
                    "prohibited terms. Rank the gaps by what that platform ranks and "
                    "filters on rather than by how empty they look, because an unfilled "
                    "attribute in a filter is a product that does not exist at all to the "
                    "buyer using it."
                ),
                produces=("completeness_gap_report",),
            ),
            step(
                "fill_each_field_from_the_product_record_only",
                "Write from the specification, never from what similar products say",
                StepKind.DRAFT,
                (
                    "Write each title, attribute, bullet and description from the product "
                    "record, the supplier specification and the measured item -- never from "
                    "what comparable listings say, however consistent they look. An "
                    "attribute is a statement about dimensions, materials, compatibility, "
                    "origin and safety marking that the seller answers for on a return, in "
                    "a dispute and to a regulator, so a field the record cannot support is "
                    "left empty and reported as a gap for a person to resolve."
                ),
                produces=("enriched_records",),
            ),
        ),
        artifacts=(
            artifact(
                "completeness_gap_report",
                "Completeness gap report",
                (
                    "Per record: which required and ranked fields are missing, malformed "
                    "or prohibited under that marketplace's schema, and what each gap "
                    "costs in visibility."
                ),
                "report",
            ),
            artifact(
                "enriched_records",
                "Enriched product records",
                (
                    "Each record with its completed title, attributes, copy and imagery, "
                    "the source behind every value, and the fields deliberately left "
                    "empty with the reason."
                ),
                "bundle",
            ),
        ),
        tools=(
            "catalogue_reader",
            "marketplace_schema",
            "attribute_extractor",
            "listing_composer",
            "product_image_checker",
        ),
        config_keys=(
            ConfigKey(
                key="marketplace_schema",
                description=(
                    "Required and ranked attributes, category fields, title patterns, "
                    "prohibited terms and image rules for each marketplace this "
                    "vertical sells on."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="attribute_sources",
                description=(
                    "Which system owns which attribute -- supplier feed, specification "
                    "sheet, measurement, certification -- and which attributes may "
                    "never be inferred from anything."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "records complete against the marketplace's own required-attribute set",
            "attribute values traceable to a specification or measurement",
            "listings suppressed or corrected by the platform after they went up",
        ),
    ),
    Profile(
        name="review_reply_draft",
        summary=(
            "A reply to one named customer's public review, written fast, in the "
            "owner's voice, saying nothing about that customer the business is not "
            "free to say in public."
        ),
        # Two-word tokens throughout: "review" on its own sits in the journalist's
        # source list and inside "drafted for review" on the quarterly pack.
        match=(
            "review responder",
            "reputation assistant",
            "review replies",
            "reply drafts",
            "on-brand reply",
        ),
        steps=(
            step(
                "read_the_review_against_the_record_behind_it",
                "Find what actually happened before drafting a word",
                StepKind.ASSESS,
                (
                    "Find the job, visit, order or matter the review is about and read what "
                    "the record says happened: what was booked, what was done, who "
                    "attended, what was charged, what has already been said to this person "
                    "and by whom. A reply that argues about facts nobody checked is the one "
                    "that gets photographed and shared, and a reply that concedes a failing "
                    "that never happened is evidence somebody keeps."
                ),
                produces=("review_context",),
            ),
            step(
                "answer_in_public_without_disclosing_anything_private",
                "Reply to the substance and leave the customer's details out of it",
                StepKind.DRAFT,
                (
                    "Draft the reply to the substance of the review in the owner's voice, "
                    "and keep everything the record holds off a public surface: the "
                    "treatment, the matter, the order, the value, the address, and -- where "
                    "confidentiality applies in this market -- whether this person was a "
                    "customer at all. Offer no refund, discount, settlement or admission. "
                    "Where the review alleges harm, a regulated failing or anything a "
                    "licensed person must answer, you draft the acknowledgement and the "
                    "invitation to continue it privately, and the substance goes to that "
                    "person."
                ),
                produces=("reply_draft",),
            ),
        ),
        artifacts=(
            artifact(
                "review_context",
                "Review context",
                (
                    "The review set against the operational record behind it: the job or "
                    "matter, what was done and by whom, what was charged, and everything "
                    "already said to this customer."
                ),
            ),
            artifact(
                "reply_draft",
                "Reply draft",
                (
                    "The drafted public reply with the surface it is for, the version of "
                    "the review it answers, the private details deliberately withheld and "
                    "the parts routed to a person."
                ),
                "document",
            ),
        ),
        tools=(
            "review_feed",
            "record_lookup",
            "reply_composer",
            "confidentiality_filter",
        ),
        config_keys=(
            ConfigKey(
                key="reply_policy",
                description=(
                    "How quickly each review surface is answered, who signs the reply, "
                    "what may be offered in public and what must be taken private."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="confidentiality_rules",
                description=(
                    "What this market and vertical forbid disclosing about a named "
                    "individual in public, including whether the business may confirm "
                    "they were a customer."
                ),
                required=True,
            ),
        ),
        kpis=(
            "reviews answered inside the configured window",
            "replies released without a rewrite by the owner",
            "replies disclosing something about a named individual that should not have been public",
        ),
        channels=("review_surfaces",),
    ),
    Profile(
        name="operations_journalism",
        summary=(
            "The week's real work turned into material worth reading -- the job "
            "done, the review left, the question asked twice, the fixture played "
            "-- where the specific detail is the whole product."
        ),
        # "journalist" catches both the in-house and the club variant; the feed
        # tokens catch anything later added that harvests the operational record.
        match=(
            "journalist",
            "content-from-operations",
            "grounded posts",
            "operational feed",
            "real feed",
            "matchday",
            "fan content",
            "never generic",
        ),
        steps=(
            step(
                "harvest_the_week_from_the_operational_feed",
                "Sweep the record for the few things a stranger would care about",
                StepKind.GATHER,
                (
                    "Sweep the operational feed for anything a stranger outside the "
                    "business would read to the end: work completed with a before and an "
                    "after, a review worth quoting, a question the front desk has answered "
                    "more than once, seasonal work the calendar says is starting, a result "
                    "or an event as it happens. Record for each candidate what happened, "
                    "when, who was involved and which permissions already exist, and score "
                    "it honestly. Most of what a business does is not a story, and a week "
                    "that yields nothing is a finding to report rather than a licence to "
                    "invent one."
                ),
                produces=("story_candidates",),
            ),
            step(
                "write_it_as_the_specific_thing_that_happened",
                "Keep only what could not be written about anyone else",
                StepKind.DRAFT,
                (
                    "Build each piece around the detail that could only have come from this "
                    "job, this fixture, this customer or this week -- the fault actually "
                    "found, the hours it actually took, the number, the thing the customer "
                    "actually said -- and cut every sentence that would read identically "
                    "for any other business in the vertical. Generic filler is the failure "
                    "this unit exists to prevent: it is what the last agency was sacked "
                    "for, and it is indistinguishable from the copy a record cannot "
                    "support."
                ),
                produces=("grounded_pieces",),
            ),
        ),
        artifacts=(
            artifact(
                "story_candidates",
                "Story candidates",
                (
                    "Everything the feed offered this run: what happened, when, who was "
                    "involved, the permissions already held, and whether it is worth "
                    "anyone's attention at all."
                ),
                "report",
            ),
            artifact(
                "grounded_pieces",
                "Grounded pieces",
                (
                    "Each drafted piece with the operational entry it was built from, the "
                    "specific detail that grounds it, and the surfaces it has been cut "
                    "for."
                ),
                "bundle",
            ),
        ),
        tools=(
            "operations_feed",
            "review_feed",
            "faq_index",
            "seasonal_calendar",
            "story_scorer",
            "media_library",
        ),
        config_keys=(
            ConfigKey(
                key="editorial_calendar",
                description=(
                    "What this business puts out, how often, and around which "
                    "seasonal, statutory and vertical events."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="publishable_operations",
                description=(
                    "Which operational records may become content in this vertical, "
                    "which of their fields, and what must be removed from each before "
                    "it can be read outside the business."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "pieces traceable to a named operational entry",
            "pieces carrying a detail that could not be written about another business",
            "calendar slots left empty because the record had nothing to carry them",
        ),
    ),
    Profile(
        name="recruitment_copy",
        summary=(
            "A role turned into copy that both attracts and complies -- the "
            "advert, the description and the employer-brand post around it -- with "
            "every enquiry it produces routed straight to hiring."
        ),
        match=(
            "hiring publicist",
            "employer-brand",
            "job opening",
            "job-ad",
            "job ads",
            "jd drafter",
            "role brief",
            "applicant",
        ),
        steps=(
            step(
                "take_the_role_from_whoever_actually_owns_it",
                "Get the real duties, the real pay and the real requirements first",
                StepKind.GATHER,
                (
                    "Take the role from the hiring manager's brief and the existing record: "
                    "duties, hours and pattern, pay range, location and travel, reporting "
                    "line, start date, and the qualifications genuinely required set apart "
                    "from the ones merely preferred. A description written from a job title "
                    "reads well and attracts the wrong people, and a requirement that is not "
                    "really a requirement is the one that filters out the person who would "
                    "have taken the job."
                ),
                produces=("role_brief",),
            ),
            step(
                "write_to_the_employment_rules_then_route_what_comes_back",
                "Draft it lawfully, put it where candidates are, and hand over every enquiry",
                StepKind.ACT,
                (
                    "Draft the advert, the description and the post to the employment rules "
                    "the country pack holds: the pay transparency this market requires, the "
                    "wording that is discriminatory here even where it is idiomatic "
                    "elsewhere, the age, gender, nationality, health and family phrasing "
                    "that is unlawful, and the statutory notices and entitlements that must "
                    "appear. Once released, publish each advert to the boards and profiles "
                    "the configuration names, from the customer's own connected accounts "
                    "and never from an account this platform owns, then route every "
                    "applicant enquiry it produces to hiring with the advert it answered "
                    "attached."
                ),
                produces=("job_advert", "applicant_routing_record"),
            ),
        ),
        artifacts=(
            artifact(
                "role_brief",
                "Role brief",
                (
                    "The role as its owner states it: duties, hours, pay range, location, "
                    "reporting line, start date, and required qualifications set apart "
                    "from preferred ones."
                ),
                "document",
            ),
            artifact(
                "job_advert",
                "Job advert set",
                (
                    "The advert, description and employer-brand post as drafted, with the "
                    "employment-rule wording each carries and the surfaces each is cut "
                    "for."
                ),
                "bundle",
            ),
            artifact(
                "applicant_routing_record",
                "Applicant routing record",
                (
                    "Each enquiry the advert produced with the advert behind it, the time "
                    "it arrived, where it was routed and when hiring received it."
                ),
                "log",
            ),
        ),
        tools=(
            "role_brief_intake",
            "advert_composer",
            "employment_rules_checker",
            "job_board_connector",
            "applicant_router",
        ),
        config_keys=(
            ConfigKey(
                key="employment_advertising_rules",
                description=(
                    "What a job advert must and must not say in this market: pay "
                    "transparency, protected characteristics, statutory notices, "
                    "right-to-work wording and the languages it must appear in."
                ),
                required=True,
            ),
            ConfigKey(
                key="hiring_routing",
                description=(
                    "Where an applicant enquiry goes, how quickly, and which system "
                    "holds the application once it arrives."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "adverts released carrying this market's required pay and statutory wording",
            "applicant enquiries reaching hiring inside the configured window",
            "adverts withdrawn or amended for wording that breached employment rules",
        ),
        channels=("job_boards", "social_platforms"),
    ),
    Profile(
        name="regulated_narrative",
        summary=(
            "A periodic narrative written over numbers somebody else owns -- "
            "commentary, a quarterly pack -- where the words are a regulated "
            "communication and a licensed reviewer, not the unit, decides they may "
            "go out."
        ),
        match=(
            "commentary",
            "compliance-gated",
            "quarterly",
            "reporting pack",
            "report drafter",
            "reporting writer",
        ),
        steps=(
            step(
                "freeze_the_figures_from_the_book_of_record",
                "Take every number from the book at a stated as-at time and fix it",
                StepKind.GATHER,
                (
                    "Take every figure, holding, valuation, return, flow and date from the "
                    "book of record at a stated as-at time, and hold that snapshot fixed "
                    "for the whole draft. Nothing is recalculated by you, restated in "
                    "rounder terms or carried over from the last period, and a figure still "
                    "provisional is labelled provisional in the text rather than quietly "
                    "firmed up. This pack is read as a statement of fact by an investor, a "
                    "client or a regulator, and it is reconciled against the same book "
                    "afterwards by somebody who will notice."
                ),
                produces=("figure_snapshot",),
            ),
            step(
                "describe_what_happened_without_saying_what_to_do",
                "Attribute and describe; leave the recommendation to a licensed person",
                StepKind.DRAFT,
                (
                    "Write the narrative as description and attribution -- what moved, by "
                    "how much, against which benchmark, over which period, and what the "
                    "manager stated drove it -- and stop there. Performance appears with "
                    "the periods, fees, basis and warnings the rules require and never "
                    "without them, and no sentence forecasts, recommends, reassures or "
                    "invites a decision to invest. Assemble the reviewer's pack alongside "
                    "the text: every claim with its source line, the disclosures applied, "
                    "the required wording used and the passages you want a licensed person "
                    "to look at first."
                ),
                produces=("narrative_draft", "reviewer_pack"),
            ),
        ),
        artifacts=(
            artifact(
                "figure_snapshot",
                "Frozen figure snapshot",
                (
                    "Every figure the narrative uses, taken from the book of record at a "
                    "stated as-at time, with its source line and whether it is final or "
                    "provisional."
                ),
            ),
            artifact(
                "narrative_draft",
                "Narrative draft",
                (
                    "The drafted commentary or pack with each factual sentence tied to a "
                    "line of the snapshot and each required disclosure in place."
                ),
                "document",
            ),
            artifact(
                "reviewer_pack",
                "Compliance reviewer pack",
                (
                    "What the licensed reviewer needs to decide: every claim with its "
                    "source line, the disclosures applied, the mandated wording used and "
                    "the passages flagged for their attention."
                ),
                "bundle",
            ),
        ),
        tools=(
            "book_of_record_reader",
            "figure_extractor",
            "disclosure_library",
            "narrative_composer",
            "compliance_queue",
        ),
        config_keys=(
            ConfigKey(
                key="reporting_period_rules",
                description=(
                    "The as-at date, the reporting period, the required tables, the "
                    "mandated disclosures and the wording each figure must carry in "
                    "this market."
                ),
                required=True,
            ),
            ConfigKey(
                key="compliance_review_route",
                description=(
                    "Which licensed reviewer releases this communication, what they "
                    "must see with it, and what may never leave without them."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "figures in the narrative reconciling to the frozen snapshot",
            "drafts reaching the reviewer with a complete claim-and-source pack",
            "passages amended or removed by the reviewer for regulated wording",
        ),
        channels=("compliance_queue",),
    ),
    Profile(
        name="change_announcement",
        summary=(
            "A change that has already shipped, explained to the accounts it "
            "actually affects -- what changed, what they must do and by when -- "
            "rather than broadcast to a list."
        ),
        match=(
            "release announcer",
            "release-notes",
            "release notes",
            "changes communicated",
            "affected accounts",
        ),
        steps=(
            step(
                "work_out_who_is_actually_affected",
                "Resolve the change log to the accounts it really touches",
                StepKind.ASSESS,
                (
                    "Take the change log and resolve it to the accounts, users, "
                    "configurations and integrations the change actually touches, saying "
                    "for each what stops working, what needs doing and by when. A note sent "
                    "to everybody is deleted by everybody, and the account that needed to "
                    "act is the one that did not read it. Where the record cannot tell you "
                    "the blast radius, that is a finding for engineering rather than a "
                    "reason to send it to the whole list."
                ),
                produces=("impact_segments",),
            ),
            step(
                "say_what_changed_and_what_they_must_do",
                "Lead with the breaking part, then send it only where it applies",
                StepKind.ACT,
                (
                    "Write one note per segment in the order the reader needs it: what "
                    "changed, whether anything they built stops working, exactly what they "
                    "must do, the date it takes effect and where to go when it breaks. Name "
                    "the removals and breaking changes first and plainly, because a "
                    "deprecation buried under new features is how a customer finds out from "
                    "an outage. Once released, publish each note to its own segment from "
                    "the customer's own connected account, never from an account this "
                    "platform owns."
                ),
                produces=("release_notes",),
            ),
        ),
        artifacts=(
            artifact(
                "impact_segments",
                "Impact segments",
                (
                    "Each affected account, user, configuration and integration with what "
                    "the change does to it, what they must do and the date it takes "
                    "effect."
                ),
                "report",
            ),
            artifact(
                "release_notes",
                "Targeted release notes",
                (
                    "One note per segment with the breaking changes named first, the "
                    "required action, the effective date, the support route and the "
                    "recipients it went to."
                ),
                "bundle",
            ),
        ),
        tools=(
            "change_log_reader",
            "account_segmenter",
            "dependency_map",
            "notice_composer",
            "notice_sender",
        ),
        config_keys=(
            ConfigKey(
                key="change_classification",
                description=(
                    "Which changes are announced at all, which count as breaking, and "
                    "the notice period each class requires under this market's rules "
                    "and the contract."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="notice_recipients",
                description=(
                    "Who at an account receives which class of notice, on which rail, "
                    "and the contractual notice terms that override the default."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "breaking changes announced inside their contractual notice period",
            "notes delivered only to the accounts the change actually affects",
            "support contacts about a change that was announced but not read as breaking",
        ),
        channels=("account_email", "in_product_notice"),
    ),
    Profile(
        name="format_repurposing",
        summary=(
            "One released piece cut into every format it has to live in, where "
            "each cut is a new piece with its own constraints and none of them may "
            "say something the original did not."
        ),
        match=(
            "repurpos",
            "clips editor",
            "every format",
            "cross-platform",
            "article to",
            "into newsletter",
        ),
        steps=(
            step(
                "read_the_source_and_its_rights_before_you_cut_it",
                "Pull out the argument, the moments and the restrictions that came with them",
                StepKind.ASSESS,
                (
                    "Read the source piece and pull out what it actually argues, the moments "
                    "that carry it, the claims it makes and the conditions attached to each "
                    "-- then pull out the rights: the quote, the footage, the music, the "
                    "contributor, the embargo and the licence that limits where any of it "
                    "may appear. A cut inherits every restriction of the original and adds "
                    "the restrictions of wherever it lands, so the rights come out before "
                    "the scissors do."
                ),
                produces=("source_analysis",),
            ),
            step(
                "cut_for_each_surface_without_changing_what_it_says",
                "Fit the surface, keep the meaning",
                StepKind.DRAFT,
                (
                    "Produce each format to that surface's real constraints -- running "
                    "length, aspect ratio, caption limit, safe area, opening seconds, "
                    "subtitle and alt-text requirements -- while keeping the meaning intact. "
                    "A clip that ends before the qualification, a headline that states what "
                    "the article hedged and a summary that drops the condition on a claim "
                    "are all new claims the business never made. Every cut carries its own "
                    "accessibility text and points back to the source piece it came from."
                ),
                produces=("format_variants",),
            ),
        ),
        artifacts=(
            artifact(
                "source_analysis",
                "Source analysis",
                (
                    "What the source piece argues, the moments that carry it, the claims "
                    "and their conditions, and every licence, embargo and contributor term "
                    "that came with it."
                ),
                "report",
            ),
            artifact(
                "format_variants",
                "Format variants",
                (
                    "Each cut with the surface it is for, the constraints it was fitted "
                    "to, its accessibility text, the rights that apply to it and the "
                    "source piece behind it."
                ),
                "bundle",
            ),
        ),
        tools=(
            "source_reader",
            "clip_selector",
            "media_transcoder",
            "caption_generator",
            "format_spec_library",
        ),
        config_keys=(
            ConfigKey(
                key="format_specs",
                description=(
                    "Length, ratio, caption, safe-area and accessibility rules for "
                    "every surface this business cuts for in this market."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="source_rights",
                description=(
                    "What licence, embargo and contributor terms came with the source "
                    "material, and where each derived cut may therefore appear."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "cuts delivered for every surface in the configured mix",
            "cuts carrying captions and alt text to this market's accessibility rules",
            "cuts found to state something the source piece did not",
        ),
    ),
    # Fallback.  Deliberately the family's plain shape rather than a dumping
    # ground: source material in the owner's own words becomes the page, post or
    # offer they would have written themselves, and it waits in the queue until
    # they release it.  The unit that lands here is exactly that, and so is any
    # creative unit the catalogue adds later that is a brief in and a draft out.
    Profile(
        name="owner_voice_copy",
        summary=(
            "Source material in the owner's own words turned into the page, post "
            "or offer they would have written themselves, held in the queue until "
            "they release it."
        ),
        match=(),
        steps=(
            step(
                "mine_the_owners_own_words",
                "Start from how they actually talk about their own work",
                StepKind.GATHER,
                (
                    "Start from what the owner has actually said: the voice memo, the note "
                    "scribbled between jobs, the last thing they wrote themselves, the way "
                    "they answer this question on the phone. Transcribe it and keep their "
                    "vocabulary, their sentence length and the things they always say, "
                    "recording which sample each choice came from. A page that sounds like "
                    "everybody else's page is a page they will rewrite, and after the second "
                    "rewrite they stop sending memos."
                ),
                produces=("voice_sample_set",),
            ),
            step(
                "write_the_page_the_owner_would_have_written",
                "Their words for their services, and their offer exactly as it stands",
                StepKind.DRAFT,
                (
                    "Compose the page, post or offer from the brief and the samples: their "
                    "words for their own services, the terms their customers actually use, "
                    "the offer exactly as the price book and the policy state it, and the "
                    "call to action the market's messaging rail supports. Where a memo "
                    "asserts something the record does not carry -- a guarantee, a "
                    "timescale, a claim about a competitor, a figure -- you draft around it "
                    "and put the question back to the owner rather than turning an off-hand "
                    "remark into a public commitment."
                ),
                produces=("copy_draft",),
            ),
        ),
        artifacts=(
            artifact(
                "voice_sample_set",
                "Voice sample set",
                (
                    "The owner's own words behind this draft -- memos, notes and prior "
                    "writing -- with the transcript of each and the choices it justifies."
                ),
            ),
            artifact(
                "copy_draft",
                "Copy draft",
                (
                    "The drafted page, post or offer with the samples behind its voice, "
                    "the price-book and policy references behind its offer, and the "
                    "questions put back to the owner."
                ),
                "document",
            ),
        ),
        tools=(
            "voice_memo_transcriber",
            "voice_profile_builder",
            "page_composer",
            "offer_builder",
        ),
        config_keys=(
            ConfigKey(
                key="voice_samples",
                description=(
                    "The owner's own writing and speech held as the reference for "
                    "their voice, and what of it may be quoted verbatim."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="page_inventory",
                description=(
                    "Which pages, posts and offers a business in this vertical needs, "
                    "which already exist, and the structure each one takes."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "drafts released by the owner without a substantive rewrite",
            "offers and figures in a draft resolving to the price book or a stated policy",
            "memos turned into a queued draft inside the configured window",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class CreativeGenerationEngine(Engine):
    """Carries every unit whose output is a piece of writing or a made asset.

    The engine holds one pipeline -- read the record, collect the permissions,
    test the claims, set the brief, write it, check it back, queue it, report --
    and nine profiles that say what kind of piece is being made and what it can
    fail at.  Nothing in the code knows whether it is holding a review reply, a
    fund commentary, a job advert, a matchday cut or a marketplace listing; the
    voice, the kit, the permitted claims, the consents, the formats and the
    release authority all arrive as configuration.

    The family deliberately does *not* declare the publish capability.  Most of
    these units draft into a queue and hand the released piece to the publishing
    connectors, and declaring the capability family-wide would attach a
    connected-accounts grant to a compliance commentary that only ever goes to a
    reviewer -- which would make the customer-owned-channels rule look satisfied
    everywhere and mean nothing anywhere.  The two profiles that genuinely do
    send say so in their own steps, and the grant is attached there.
    """

    id: ClassVar[str] = "MF13"
    family: ClassVar[str] = "Creative generation"
    what_it_does: ClassVar[str] = (
        "Operations-grounded content plus ModelArk image and video assets"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.GENERATE_CREATIVE,
        Capability.ASSESS_MEDIA,
        Capability.SCORE,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "operations_record_reader",
        "brand_voice_profile",
        "brand_kit",
        "consent_register",
        "claim_rule_checker",
        "draft_composer",
        "format_spec_library",
        "approval_queue",
        "asset_library",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "approval_queue",
        "owner_dashboard",
        "content_library",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "drafted statements traceable to a named record entry",
        "drafts released by their named approver without a substantive rewrite",
        "time from the source event to a draft sitting in the queue",
        "assets carrying a complete consent, licence and generation provenance",
        "released items later corrected or withdrawn for something the draft asserted",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "draft_state"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Record, permissions, claims, brief, draft, check, gate, report.

        Three placements carry most of the weight.  The permissions and the
        claims are settled *before* the brief rather than after the draft,
        because a piece written first and cleaned up afterwards keeps whatever
        made it good -- the customer's face, the number nobody sourced, the
        guarantee the owner does not offer -- and the rewrite loses the only
        thing that made it worth reading.  The check is a step of its own rather
        than a flourish on the draft, since fluent prose is the one thing a
        generation model always produces and truth is the one thing it never
        checks.  And the plan ends at a gate and a report, never at a
        publication: drafting is the whole of the authority this family holds,
        and what leaves the queue leaves on a person's release.
        """
        return (
            step(
                "read_the_record_this_piece_comes_from",
                "Start from the thing that actually happened",
                StepKind.OBSERVE,
                (
                    "Start from the operational entries that produced this run: the job "
                    "that completed, the review that landed, the change that shipped, the "
                    "fixture that was played, the role that opened, the period that closed. "
                    "Record which entries are in scope, when each happened, which system "
                    "holds it and how much usable detail it actually carries. Everything "
                    "this family makes is a retelling of something in that record, so a run "
                    "where the record holds nothing produces a finding and no draft -- an "
                    "empty week is a fact about the business, not a gap for you to fill."
                ),
                produces=("source_material",),
            ),
            step(
                "collect_the_permission_behind_everything_you_would_use",
                "Establish who owns each face, place, frame and phrase before using it",
                StepKind.GATHER,
                (
                    "Gather the permission behind every person, property, image, clip, "
                    "quote, mark and logo the piece could carry, recording for each who it "
                    "belongs to, what consent or licence covers this use, the date it was "
                    "given, the surfaces it extends to and how it can be withdrawn. Anything "
                    "without a permission still in force is left out rather than cropped, "
                    "blurred or anonymised on the way past: a customer, an employee, a "
                    "client's premises or a photographer's frame used without one is a "
                    "complaint, a takedown or a claim, and how well the piece performed is "
                    "no part of the answer to it."
                ),
                produces=("rights_record",),
            ),
            step(
                "test_every_claim_against_the_rules_of_this_market",
                "Decide what may actually be said here, and with what qualification",
                StepKind.ASSESS,
                (
                    "Set every statement the piece could make against the claim rules the "
                    "country pack and the vertical overlay hold: superlatives, guarantees, "
                    "outcomes, comparisons with a named competitor, testimonials, and "
                    "anything on a health, financial or legal subject that a licensed "
                    "person must say. Record for each the entry that supports it, whether "
                    "it may be stated here at all, the disclosure or qualification it must "
                    "carry, and the ones held back with the rule that held them. A claim "
                    "with no source is not a claim you soften -- it comes out, and the "
                    "sentence is rebuilt on what the record does support."
                ),
                produces=("claim_ledger",),
            ),
            step(
                "set_the_brief",
                "Fix what this piece is before writing a word of it",
                StepKind.DECIDE,
                (
                    "Fix what this piece is: the surface and format it must fit, who is "
                    "reading it, what it is for, which ledger entries it is built on, what "
                    "it must not say, and which parts need the owner, a hiring manager or a "
                    "licensed reviewer before they go anywhere. Set the volume the record "
                    "can carry at the same time -- how many pieces, how many assets, at what "
                    "cost -- because the constraint in this family is never how much can be "
                    "produced, it is how much there is to say."
                ),
                produces=("creative_brief",),
            ),
            step(
                "write_it_in_the_owners_voice",
                "Compose it to the brief, in their voice, from the ledger",
                StepKind.DRAFT,
                (
                    "Compose the piece against the brief, in the voice the brand voice "
                    "profile defines and the brand kit renders: their register, their words "
                    "for their own services, the terms their customers use, the structure "
                    "the destination surface expects, in the language set the country pack "
                    "names. Every factual sentence traces to a row of the claim ledger and "
                    "every figure to the published price book. Where a sentence would read "
                    "identically for any other business in the vertical it is filler and it "
                    "comes out: the specific thing that happened is the only part worth a "
                    "reader's attention."
                ),
                produces=("draft_set",),
            ),
            step(
                "check_the_draft_against_what_you_started_from",
                "Read it back against the ledger, the rights and the format spec",
                StepKind.ASSESS,
                (
                    "Read the finished draft back against the claim ledger, the rights "
                    "record, the brief, the voice profile and the format specification, and "
                    "mark every divergence: a sentence asserting something no entry "
                    "supports, a figure absent from the price book, a person or premises "
                    "whose permission has lapsed, a claim missing its disclosure, a cut that "
                    "dropped the qualification off the end, a caption or alt text missing "
                    "where the accessibility rules require one. Fluency is what a generation "
                    "model produces by construction and accuracy is what it produces by "
                    "accident, so the findings travel with the draft to whoever releases it "
                    "rather than being quietly corrected out of sight."
                ),
                produces=("draft_review",),
            ),
            step(
                "hold_the_draft_until_a_person_releases_it",
                "Queue it with everything needed to judge it, and wait",
                StepKind.GATE,
                (
                    "Put the draft in front of whoever the approval policy names -- the "
                    "owner, the hiring manager, the licensed reviewer -- with the sources "
                    "beside it, the claims flagged, the permissions listed and the check "
                    "findings shown, and wait. Nothing leaves on your own authority: a piece "
                    "is public from the moment it lands and cannot be taken back from the "
                    "people who already read it. A draft nobody has released ages in the "
                    "queue and is escalated when it does, and any edit made on release is "
                    "recorded as the version of record."
                ),
                produces=("approval_record",),
            ),
            step(
                "report_what_was_made_and_what_could_not_be",
                "Tell the owner what is queued, what went out, and what the record could not carry",
                StepKind.NOTIFY,
                (
                    "Report in one place what was drafted, what was released and by whom, "
                    "what was held and against which rule, what the run cost to produce, "
                    "and what the brief asked for that the record could not support. That "
                    "last list is the useful one: it is where the operational gap shows up, "
                    "and a report carrying only what was produced is how a content "
                    "programme drifts into writing about nothing."
                ),
                produces=("production_report",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "source_material",
                "Source material",
                (
                    "The operational entries this run is built from: what happened, when, "
                    "which system holds each one and how much usable detail it carries."
                ),
            ),
            artifact(
                "rights_record",
                "Rights and consent record",
                (
                    "Every person, property, image, clip, quote, mark and logo the piece "
                    "could carry, with the permission covering it, its date, its scope, "
                    "the surfaces it extends to and how it is withdrawn."
                ),
            ),
            artifact(
                "claim_ledger",
                "Claim ledger",
                (
                    "Every statement the piece could make with the record entry that "
                    "supports it, whether it may be stated in this market, the disclosure "
                    "it must carry, and the claims held back with the rule that held them."
                ),
            ),
            artifact(
                "creative_brief",
                "Creative brief",
                (
                    "What this piece is: the surface, the format, the reader, the purpose, "
                    "the ledger entries behind it, what it must not say, the volume "
                    "authorised and the parts reserved for a named person."
                ),
                "document",
            ),
            artifact(
                "draft_set",
                "Draft set",
                (
                    "The piece as drafted, in every version produced, each factual "
                    "sentence tied to a row of the claim ledger and each variant tied to "
                    "the surface it is for."
                ),
                "bundle",
            ),
            artifact(
                "draft_review",
                "Draft review",
                (
                    "The read-back of the finished draft against the ledger, the rights "
                    "record, the brief, the voice profile and the format spec, with every "
                    "divergence found and what was done about it."
                ),
                "report",
            ),
            artifact(
                "approval_record",
                "Approval record",
                (
                    "What went to whom and when, what they decided, the edits made on "
                    "release, and the version of record that resulted."
                ),
                "log",
            ),
            artifact(
                "production_report",
                "Production report",
                (
                    "What was drafted, released and held, with the rule behind each hold, "
                    "what the run cost, and what the brief asked for that the record could "
                    "not support."
                ),
                "report",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"What may be said, shown and claimed by {vertical['name'].lower()} "
                f"businesses -- and what a person in that trade must say instead of "
                f"you -- comes from the vertical overlay and the active country pack. "
                f"Read both before you write, rather than reusing what cleared review "
                f"for the last customer."
            )
        else:
            where = (
                "This unit runs across every vertical on the platform, so the voice, "
                "the kit, the permitted claims, the consents and the release authority "
                "all come from the owner's setup and whatever overlay and country pack "
                "is in front of you -- never from what usually works."
            )
        return (
            "HOW YOU WORK. You write from the record outward. The business is already "
            "producing everything worth saying about it -- the job that finished, the "
            "review that landed, the question the front desk keeps answering, the "
            "period that closed -- and your work is turning that into something worth "
            "reading while adding nothing to it. So the source material comes first, "
            "then the permission behind every face, premises, frame and quote you would "
            "use, then the test of what may lawfully be claimed here, and only then the "
            "writing. Every factual sentence traces to an entry you can name and every "
            "figure to published pricing; a claim you cannot source is removed rather "
            "than hedged, because a hedge is how an invented fact survives a review. "
            "The voice you write in is borrowed and configured, not yours to invent: "
            "you do not give the owner an opinion, a promise or a personality they "
            "never offered, and where a memo of theirs asserts something the record "
            "cannot carry you put the question back rather than turning an off-hand "
            "remark into a public commitment. Read the finished draft back against the "
            "thing it came from, because fluent is what you are by construction and "
            "accurate is only what you are by checking. Then stop: you draft and you "
            "queue, a named person releases, and what has gone out cannot be recalled "
            "from the people who already read it. And treat cheapness as a hazard "
            "rather than a licence -- an asset that costs cents can be made in "
            "hundreds, and a calendar slot with no operational entry behind it is left "
            f"empty and reported, never filled. {_PROFILE_MISSION_LINES[profile.name]} "
            f"{where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-GROUNDED-IN-THE-RECORD",
                rule=(
                    "Every factual statement resolves to a named operational entry. "
                    "The unit never supplies a detail because the sentence needs one."
                ),
                check=(
                    "Each factual sentence in draft_set maps to a row of claim_ledger "
                    "naming its source entry and date; a sentence with no row is removed "
                    "before the draft reaches the queue, and draft_review records that "
                    "it was."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-NOTHING-WRITTEN-TO-FILL-A-SLOT",
                rule=(
                    "A calendar slot is not a reason to produce. Where the record has "
                    "nothing to carry a piece, the slot is left empty and reported."
                ),
                check=(
                    "production_report names the operational entry behind every item "
                    "produced and lists every planned item the record could not support, "
                    "rather than reporting only what was made."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CONSENT-BEFORE-LIKENESS",
                rule=(
                    "No customer, client, employee, property or third-party work "
                    "appears in content without a recorded permission that is still in "
                    "force for that surface."
                ),
                check=(
                    "rights_record holds a permission with its scope, surfaces and "
                    "expiry for everything named or shown in draft_set; a lapsed or "
                    "withdrawn permission removes the item and raises a recall of "
                    "anything already released carrying it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CLAIMS-WITHIN-THE-MARKET-RULES",
                rule=(
                    "Superlatives, guarantees, outcome claims, testimonials and "
                    "comparisons are made only where this market and vertical permit "
                    "them, with the disclosure each one requires."
                ),
                check=(
                    "Every entry in claim_ledger is tested against claim_rules and the "
                    "regulator guardrails in the active country pack, and each permitted "
                    "claim carries its disclosure text in draft_set."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-VOICE-IS-BORROWED",
                rule=(
                    "The owner's voice is configuration, not invention. The unit never "
                    "gives the business an opinion, a promise or a commitment it has "
                    "not made."
                ),
                check=(
                    "draft_review scores the draft against brand_voice and flags every "
                    "first-person commitment, opinion or promise that is not present in "
                    "source_material or the price book."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-GENERATED-ASSET-CARRIES-ITS-ORIGIN",
                rule=(
                    "Every generated image, video or voice carries its provenance and, "
                    "where this market requires it, a declaration that it was "
                    "generated. Nothing generated depicts a capability, a place or a "
                    "person the business does not have."
                ),
                check=(
                    "asset_manifest records the model, version, prompt, seed, reference "
                    "assets and licences for each asset; asset_review records the check "
                    "against what the business actually has, and the disclosure required "
                    "by the country pack is applied."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-DRAFT-AND-QUEUE-A-PERSON-RELEASES",
                rule=(
                    "The unit drafts and queues. A named person releases. Nothing "
                    "reaches a public surface on the unit's own authority."
                ),
                check=(
                    "approval_record names the approver, the version released and the "
                    "time for every item that left the queue; an unreleased draft ages "
                    "in the queue and is escalated under approval_policy, never sent."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-CONTENT-TRACKS-THE-RECORD-IT-CAME-FROM",
                rule=(
                    "A released piece stays tied to the entries behind it, so a price, "
                    "a service, a person or a consent that changes raises the piece for "
                    "correction or withdrawal rather than leaving it standing."
                ),
                check=(
                    "Every released item in production_report links to its source "
                    "entries and rights_record rows, and a change or withdrawal in any "
                    "of them raises the item for correction with the surfaces it is "
                    "live on."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "The source event: which operational entries this piece is built from and when",
            "The brand voice profile and the brand kit, with the owner's own samples behind them",
            "The consent and licence register for every person, property and asset in scope",
            "The claim rules in force in this market and vertical, with their disclosures",
            "The format specification of every surface this piece has to fit",
            "The approval queue: what is released, what is waiting and for how long",
            "Previously released pieces and the record entries still standing behind them",
        )


#: Mission prose per profile.  Each names what is being made, the artefact that
#: proves it was made honestly, and the specific way that shape fails -- which is
#: not the same for a public reply about a named customer, a regulated quarterly
#: narrative and a generated image of a van.  Kept beside the engine rather than
#: inside the profiles because it is prose about the mission, not configuration a
#: customer can override.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "generated_media": (
        "What you make here is cheap enough to make badly at scale: build every asset "
        "from the brand kit and the customer's own references rather than from a "
        "sentence, record the model, prompt, seed and licence behind each one, and look "
        "at every frame before it becomes a deliverable -- the output is a convincing "
        "picture of a business of this kind, not of this one, and a van in the wrong "
        "livery or safety equipment nobody owns is a claim about the customer that they "
        "will be held to."
    ),
    "catalogue_enrichment": (
        "What you fill here is a schema somebody else wrote: measure each record against "
        "that marketplace's own required and ranked fields, write every title and "
        "attribute from the specification or the measured item rather than from "
        "comparable listings, and leave empty what the record cannot support -- an "
        "attribute is a promise about materials, compatibility, origin and safety "
        "marking that the seller answers for on a return and to a regulator."
    ),
    "review_reply_draft": (
        "What you draft here is a public answer about a named individual: read the job or "
        "matter behind the review before writing a word, reply to the substance in the "
        "owner's voice, and keep the record off the public surface entirely -- the "
        "treatment, the order, the value, the address, and whether they were a customer "
        "at all where confidentiality applies. Offer nothing, admit nothing, and hand "
        "anything alleging harm to the person who must answer it."
    ),
    "operations_journalism": (
        "What you harvest here is a week of real work: sweep the feed for the few things "
        "a stranger would read to the end, build each piece around the detail that could "
        "only have come from that job or that fixture, and cut every sentence that would "
        "read identically for any other business in the vertical -- generic filler is the "
        "failure this unit exists to prevent, and a week that yields nothing is a finding "
        "rather than a licence to invent one."
    ),
    "recruitment_copy": (
        "What you write here is bound by employment law before it is bound by taste: take "
        "the real duties, hours, pay range and genuine requirements from whoever owns the "
        "role, draft to this market's pay-transparency, protected-characteristic and "
        "statutory-notice rules, and route every enquiry the advert produces to hiring "
        "with the advert it answered attached -- an advert that attracts and breaches is "
        "worse than one that never ran."
    ),
    "regulated_narrative": (
        "What you draft here is a regulated communication over numbers you do not own: "
        "freeze the figures from the book of record at a stated as-at time and never "
        "restate them, describe and attribute what moved without forecasting, "
        "recommending or reassuring, and assemble the claim-and-source pack the licensed "
        "reviewer needs -- they release it, not you, and the pack is reconciled against "
        "the same book afterwards by somebody who will notice."
    ),
    "change_announcement": (
        "What you send here goes only where it applies: resolve the change log to the "
        "accounts, configurations and integrations actually affected, lead each note with "
        "what stops working and exactly what they must do by when, and send it to that "
        "segment alone from the customer's own account -- a note broadcast to everybody "
        "is deleted by everybody, and the account that needed to act is the one that did "
        "not read it."
    ),
    "format_repurposing": (
        "What you cut here inherits everything the original carried: pull out the "
        "argument, the moments and the licence, embargo and contributor terms before the "
        "scissors come out, fit each surface's real length, ratio, caption and "
        "accessibility rules, and keep the meaning intact -- a clip that ends before the "
        "qualification and a headline that states what the article hedged are new claims "
        "the business never made."
    ),
    "owner_voice_copy": (
        "What you write here has to sound like the person who will be asked about it: "
        "start from their memo, their note, the way they answer this on the phone, keep "
        "their vocabulary and their sentence length, and state the offer exactly as the "
        "price book and the policy do -- where their memo asserts a guarantee, a "
        "timescale or a figure the record cannot carry, you draft around it and put the "
        "question back rather than making it a public commitment."
    ),
}


__all__ = ["CreativeGenerationEngine"]

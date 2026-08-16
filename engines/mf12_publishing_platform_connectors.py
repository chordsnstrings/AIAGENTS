"""MF12 -- publishing & platform connectors.

A business's opening hours exist in a dozen places at once: on its own site, on
the map profile its customers actually look at, in the directories that feed the
other directories, in the booking rules, in the out-of-hours greeting, in an
index an assistant will quote from next week.  None of those places belong to
the business.  Each holds a copy, each has its own schema, its own review queue,
its own rate limit and its own quiet way of rejecting a change an hour after
accepting it, and each can be edited by the platform, by the public or by
whoever set it up years ago and left.  This family is the wiring between the one
record the business owns and every surface that carries a copy of it.

The work runs in one direction and is never finished when the push succeeds.
The business's record is the truth and a surface is a projection of it, so the
plan reads the record, reads what each surface actually says, diffs the two and
changes only what diverged -- a blind push overwrites something nobody looked
at.  Everything leaves through the customer's own connected account, because the
second standing rule is not a preference in this family: it is the premise of
it, and a grant that quietly lapsed looks exactly like a surface where nothing
needed changing.  Then the plan reads back.  A platform that accepted a payload
has promised nothing; the change may sit in review for a week, arrive truncated,
be rejected asynchronously or be reverted by a suggested edit from a stranger,
and the only artefact that proves a change is the surface saying the right thing
when you read it again.

Two failure modes here are worse than being wrong.  The first is losing the
surface itself.  These units publish at volume -- pages, posts, citations,
audiences -- and every platform sets its own limits on content, uniqueness,
media and frequency; a breach costs the profile rather than the item that earned
it, and it takes weeks to undo.  Those limits are hard stops, not targets.  The
second is a machine-readable surface that is confidently stale.  Structured
data, a declared answer file and an agent endpoint are read verbatim by
something that will not ring up to check, so a price, an hour or an availability
published there is a commitment the business gets held to, and it comes from the
system of record and the published price book with the date it was last true
attached to it.

The third standing rule lands on the approval queue.  Anything with a public
face goes out on the owner's release where the configuration reserves it: the
unit drafts the post, the page, the correction and the cascade, and a person
releases it.  Which surfaces exist, who granted access to them, what may go out
unreleased, what each platform permits and when a change takes effect all
resolve from the connected-surface register, the vertical overlay and the active
country pack, which is how one engine carries a map profile, a citation sweep, a
paid-social sync and an agent endpoint without knowing which it is holding.
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
#: connector: which surfaces exist and under whose grant, which canonical field
#: lands in which surface field, what may go out without a person releasing it,
#: what each platform permits, how long you wait before calling a change live,
#: and how you get back.  Change them and the same code keeps a map profile, a
#: citation set, an ad account and an agent endpoint current.
_FAMILY_CONFIG_KEYS: tuple[ConfigKey, ...] = (
    ConfigKey(
        key="connected_surfaces",
        description=(
            "Every surface this unit writes to: what it is, the customer's grant "
            "it is written under with that grant's scope and expiry, the fields "
            "it holds and who else can edit it."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="surface_field_map",
        description=(
            "Which canonical field lands in which field of each surface, which "
            "fields the surface owns rather than the business, and the format and "
            "length each one accepts."
        ),
        resolved_by="vertical",
        required=True,
    ),
    ConfigKey(
        key="publication_policy",
        description=(
            "What may go out on the unit's own authority and what always waits "
            "for the owner's release, with the volume ceiling, the cadence and "
            "the quiet periods for each surface."
        ),
        resolved_by="owner",
        required=True,
    ),
    ConfigKey(
        key="platform_rules",
        description=(
            "Each surface's own rules in this market on content, uniqueness, "
            "media, disclosure and volume, and what the unit does when a push "
            "would breach one."
        ),
        required=True,
    ),
    ConfigKey(
        key="verification_window",
        description=(
            "How long after a push each surface is read back before the change is "
            "called live, what counts as live there, and how a change still held "
            "in the platform's review is reported."
        ),
        required=True,
    ),
    ConfigKey(
        key="rollback_policy",
        description=(
            "What prior state is kept for each surface, how long it is kept, and "
            "who may order a published change reverted."
        ),
        resolved_by="owner",
        required=True,
    ),
)


# --------------------------------------------------------------------------- #
# profiles
# --------------------------------------------------------------------------- #

#: The nine connector shapes actually present in the catalogue, most specific
#: first.  Tokens are the nouns of the surface being written to -- "llms.txt",
#: "nap", "click-to-chat", "lead ads" -- rather than the verbs the whole family
#: shares ("published", "live", "synced", "logged"), which would match
#: everything.  Order carries weight in three places.  The endpoint and answer
#: tokens must claim the two machine surfaces before anything else sees the word
#: "schema".  The listing tokens must claim the map-profile agents before the
#: citation tokens reach the "citations" sitting inside C2's own function line.
#: And no earlier profile may hold a bare platform token such as "gbp", because
#: three units mention that platform only as one stop on a cascade or a link
#: placement -- hence the longer, unambiguous forms here.
_PROFILES: tuple[Profile, ...] = (
    Profile(
        name="agent_endpoint",
        summary=(
            "A live machine surface answering another agent's questions from the "
            "systems of record at the moment they are asked, inside a declared "
            "boundary, with every query and commitment logged."
        ),
        match=("mcp", "storefront keeper", "agent endpoint", "queryable"),
        steps=(
            step(
                "declare_what_the_endpoint_answers",
                "Draw the boundary of the surface before you open it",
                StepKind.DRAFT,
                (
                    "Write down exactly which questions this endpoint answers, which it "
                    "refuses, what a caller may commit the business to and what it may "
                    "never commit it to, and publish that boundary as part of the surface "
                    "itself. A question outside the boundary returns a handover to a "
                    "person rather than a best guess, because the caller is a machine "
                    "that will act on the answer without noticing that it was hedged."
                ),
                produces=("endpoint_contract",),
            ),
            step(
                "serve_and_log_every_transaction",
                "Answer from the live record, and log the whole exchange",
                StepKind.ACT,
                (
                    "Answer each query by reading the system of record at the moment of "
                    "the question rather than from a cache, and return the record's "
                    "version and the time it was read alongside the answer. Anything that "
                    "would commit the business -- a held slot, a quoted figure, a booking "
                    "-- goes through the same rules and the same limits a human enquiry "
                    "would meet, and every query, answer, source and commitment is written "
                    "to the transaction log with the calling agent's identity."
                ),
                produces=("transaction_log",),
            ),
        ),
        artifacts=(
            artifact(
                "endpoint_contract",
                "Endpoint contract",
                (
                    "The declared surface: the questions answered, the questions "
                    "refused, what a caller may commit the business to, the freshness "
                    "guarantee and the authentication and rate limits in force."
                ),
                "document",
            ),
            artifact(
                "transaction_log",
                "Transaction log",
                (
                    "Every query with the caller's identity, the answer served, the "
                    "record and version it was read from, the time of the read and any "
                    "commitment made on the business's behalf."
                ),
                "log",
            ),
        ),
        tools=("endpoint_gateway", "record_reader", "caller_registry", "transaction_ledger"),
        config_keys=(
            ConfigKey(
                key="endpoint_surface",
                description=(
                    "Which questions the endpoint answers, which it refuses, and "
                    "what a calling agent may commit the business to without a "
                    "person in the loop."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="caller_authentication",
                description=(
                    "How a calling agent is identified, rate-limited, revoked and "
                    "recorded, and what an unauthenticated caller may see."
                ),
                required=True,
            ),
        ),
        kpis=(
            "queries answered from a record read at the moment of the question",
            "commitments made through the endpoint that the diary honoured",
            "queries answered outside the declared endpoint boundary",
        ),
        channels=("agent_endpoint",),
    ),
    Profile(
        name="answer_corpus",
        summary=(
            "The machine-readable answer surface an assistant quotes: a declared "
            "file set, a complete structured-data graph and answers written to be "
            "lifted verbatim, checked by what actually comes back."
        ),
        match=(
            "llms.txt",
            "aeo",
            "ai-discover",
            "citable",
            "ai-mention",
            "schema graph",
            "q&a pack",
        ),
        steps=(
            step(
                "write_answers_to_be_lifted_whole",
                "Write each answer so it survives being quoted alone",
                StepKind.DRAFT,
                (
                    "Compose one answer per question, complete in itself, grounded in a "
                    "source you can name -- the service list, the published price book, "
                    "the policy, the vertical overlay -- and stamped with the date it was "
                    "last true. What quotes you will take the sentence and leave the page "
                    "around it behind, so a sentence that is only true in context is a "
                    "sentence that will be repeated wrongly to somebody about to ring up."
                ),
                produces=("answer_pack",),
            ),
            step(
                "check_what_is_actually_being_quoted",
                "Sample the assistants and record what they say",
                StepKind.ASSESS,
                (
                    "Put the configured prompts to the assistant surfaces the "
                    "configuration names and record what each one actually says about "
                    "this business: quoted correctly, quoted stale, attributed to a "
                    "competitor, or absent altogether. The file being live proves nothing "
                    "on its own -- what comes back is the only measure this profile has, "
                    "and each check is logged with its prompt, its response and its date."
                ),
                produces=("citation_check_log",),
            ),
        ),
        artifacts=(
            artifact(
                "answer_pack",
                "Citable answer pack",
                (
                    "Each question with an answer written to stand alone under "
                    "quotation, the named source that grounds it and the date it was "
                    "last verified true."
                ),
                "document",
            ),
            artifact(
                "citation_check_log",
                "Assistant citation checks",
                (
                    "Each assistant surface sampled with the prompt used, the response "
                    "returned, whether the business was quoted, whether the quote was "
                    "current and whether it was attributed."
                ),
                "log",
            ),
        ),
        tools=("structured_data_builder", "answer_pack_composer", "assistant_probe"),
        config_keys=(
            ConfigKey(
                key="answer_surface_files",
                description=(
                    "The declared files and structured-data types this market and "
                    "vertical expect, where each is served from and how it is "
                    "refreshed."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="citation_check_schedule",
                description=(
                    "Which assistant surfaces are sampled, with which prompts, how "
                    "often, and what a wrong or missing answer triggers."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "answers carrying a named grounding source and a last-verified date",
            "assistant checks in which the business was quoted correctly",
            "live answers the source of truth no longer supports",
        ),
    ),
    Profile(
        name="programmatic_pages",
        summary=(
            "A page set generated from the service list and the service area, "
            "each page distinct enough to stand on its own, deduplicated before "
            "publication and followed through to the index."
        ),
        match=(
            "programmatic",
            "service x area",
            "service-by-area",
            "page generation",
            "deduplicated",
            "indexed",
        ),
        steps=(
            step(
                "generate_and_deduplicate_before_publishing",
                "Measure every page against the set before any of it goes out",
                StepKind.DRAFT,
                (
                    "Build one page per service-and-area pair the matrix authorises, each "
                    "carrying something only true of that pair -- the real coverage, the "
                    "travel time, the local constraint, the work actually done there -- "
                    "and score every page against the rest of the set before a single one "
                    "is published. Near-identical pages at volume are what a search "
                    "platform treats as doorway spam, and the penalty lands on the whole "
                    "site rather than on the pages that earned it."
                ),
                produces=("page_set",),
            ),
            step(
                "follow_each_page_into_the_index",
                "Track the pages through to the index, and stop if they stop landing",
                StepKind.ASSESS,
                (
                    "Follow each published page through to the index -- submitted, "
                    "crawled, indexed, excluded, or judged thin -- and record the date and "
                    "the reason given for each. A generated page no index holds is a cost "
                    "with no return, and a set that starts being excluded is the signal to "
                    "stop generating and raise it, never the signal to generate more."
                ),
                produces=("index_state",),
            ),
        ),
        artifacts=(
            artifact(
                "page_set",
                "Generated page set",
                (
                    "Every generated page with the service and area pair it covers, the "
                    "distinct content it carries, its structured data and its uniqueness "
                    "score against the rest of the set."
                ),
            ),
            artifact(
                "index_state",
                "Index state",
                (
                    "Per page: submitted, crawled, indexed, excluded or thin, with the "
                    "date of each transition and the reason the platform gave."
                ),
                "report",
            ),
        ),
        tools=("page_generator", "uniqueness_scorer", "index_status_reader", "sitemap_writer"),
        config_keys=(
            ConfigKey(
                key="page_matrix",
                description=(
                    "Which service and area pairs are authorised, which are "
                    "excluded, and the cap on pages published in one period."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="uniqueness_floor",
                description=(
                    "How distinct a generated page must be from the rest of the set "
                    "before it may be published in this vertical."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "generated pages clearing the uniqueness floor",
            "published pages reaching the index",
            "pages excluded or marked thin by the platform",
        ),
    ),
    Profile(
        name="listing_profile",
        summary=(
            "The business's own profile on a listings platform kept complete and "
            "current -- fields, media, posts and answered questions -- on a "
            "surface the platform and the public can both edit underneath you."
        ),
        # Deliberately long tokens.  A bare platform abbreviation would also match
        # the link-placement agent and the hours cascade, which mention the same
        # platform only as one destination among several.
        match=(
            "local listings manager",
            "local seo",
            "google profile manager",
            "gbp autopilot",
            "google business profile",
            "posts, photos",
            "profile completeness",
        ),
        steps=(
            step(
                "fill_every_field_the_platform_offers",
                "Work the platform's own completeness model, not a general idea of one",
                StepKind.GATHER,
                (
                    "Fill every category, attribute, service, hour set, media slot and "
                    "question the platform exposes, each from the source of truth, and "
                    "record the ones deliberately left empty with the reason. "
                    "Completeness against the platform's own model is what it ranks and "
                    "what the public reads, and a field nobody filled is the field the "
                    "customer needed."
                ),
                produces=("profile_completeness_record",),
            ),
            step(
                "answer_the_public_and_watch_the_edits_you_did_not_make",
                "Hold the profile against everyone else who can change it",
                StepKind.ACT,
                (
                    "Publish the scheduled posts, media and service updates from the "
                    "customer's own profile, answer the questions the public asks on it "
                    "within the configured window, and watch for the changes you did not "
                    "make: a third-party suggestion the platform accepted, an attribute "
                    "flipped, a photo removed, a duplicate profile appearing. Anything "
                    "altered underneath you goes back onto the divergence report as "
                    "something to correct, never onto the record as the new truth."
                ),
                produces=("public_interaction_log",),
            ),
        ),
        artifacts=(
            artifact(
                "profile_completeness_record",
                "Profile completeness record",
                (
                    "Every field the platform offers with the value published, the "
                    "source it came from, and the fields deliberately left empty with "
                    "the reason."
                ),
                "report",
            ),
            artifact(
                "public_interaction_log",
                "Public interaction log",
                (
                    "Questions asked on the profile with the answers published, plus "
                    "every third-party edit, accepted suggestion and duplicate profile "
                    "found and what was done about each."
                ),
                "log",
            ),
        ),
        tools=(
            "listings_api",
            "profile_completeness_checker",
            "media_library",
            "duplicate_finder",
        ),
        config_keys=(
            ConfigKey(
                key="profile_field_set",
                description=(
                    "Which categories, attributes and services a profile in this "
                    "vertical should carry, and which are left empty deliberately."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="posting_calendar",
                description=(
                    "What is posted to the profile, how often, with which media, "
                    "and the window inside which a public question is answered."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "profile fields complete against the platform's own model",
            "scheduled posts and media published on their calendar",
            "third-party profile edits caught before a customer hit them",
        ),
        channels=("listings_platform",),
    ),
    Profile(
        name="citation_sync",
        summary=(
            "One name, address and phone number reconciled across a long tail of "
            "directories and the aggregators that feed them, where the wrong copy "
            "propagates and the fix takes weeks to land."
        ),
        match=("nap", "citation", "directory", "directories", "name/address/phone"),
        steps=(
            step(
                "crawl_the_whole_directory_set",
                "Read every record, including the ones nobody created",
                StepKind.GATHER,
                (
                    "Read every directory, aggregator and data source in the configured "
                    "set and record what each one holds, when it was read, where it was "
                    "fed from and whether it can be edited at all. Include the records "
                    "nobody set up: an old listing with a dead number that the business "
                    "never created still ranks, still gets rung, and still sends people "
                    "to an address it moved out of."
                ),
                produces=("citation_index",),
            ),
            step(
                "correct_upstream_and_hold_the_entry_open",
                "Fix the source that feeds the copies, then wait and re-read",
                StepKind.ACT,
                (
                    "Submit each correction to the source that feeds the copies rather "
                    "than to each copy, because a directory fed by an aggregator will "
                    "overwrite whatever you write straight into it within the month. "
                    "Record the submission, the propagation window the configuration "
                    "expects and the date the record is read again, and hold the entry "
                    "open until the corrected value is the one actually showing."
                ),
                produces=("correction_ledger",),
            ),
        ),
        artifacts=(
            artifact(
                "citation_index",
                "Citation index",
                (
                    "Every directory and aggregator holding a record for this business: "
                    "what it holds, where it was fed from, whether it is editable and "
                    "when it was last read."
                ),
            ),
            artifact(
                "correction_ledger",
                "Correction ledger",
                (
                    "Each submitted correction with the source it went to, the "
                    "submission date, the expected propagation window, the re-read date "
                    "and the value now showing."
                ),
                "log",
            ),
        ),
        tools=("directory_crawler", "citation_submitter", "aggregator_feed", "duplicate_finder"),
        config_keys=(
            ConfigKey(
                key="directory_set",
                description=(
                    "The directories, aggregators and data sources that carry weight "
                    "in this market, and which of them feeds which."
                ),
                required=True,
            ),
            ConfigKey(
                key="authoritative_nap",
                description=(
                    "The single authoritative name, address and contact number the "
                    "business publishes, with the variants that are acceptable and "
                    "the ones that must be corrected."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "directories holding the authoritative record",
            "corrections confirmed on re-read rather than on submission",
            "stale records found that the business never created",
        ),
    ),
    Profile(
        name="social_publishing",
        summary=(
            "A calendar of items the owner has released, recut for each platform "
            "in the mix and going out on schedule from the customer's own "
            "accounts, never from ours."
        ),
        match=(
            "social media",
            "channel-mix",
            "platform mix",
            "approval queue",
            "right platforms",
            "content calendar",
        ),
        steps=(
            step(
                "recut_the_item_for_each_platform",
                "Fit the item to each platform rather than posting one asset everywhere",
                StepKind.DRAFT,
                (
                    "Recut each released item for every platform in the mix: the aspect "
                    "ratio, the running length, the caption limit, the tagging and the "
                    "link handling that platform actually allows, with alt text and "
                    "captions wherever the accessibility rules in the country pack "
                    "require them. One asset pushed unchanged to four platforms reads as "
                    "somebody else's work reposted, which is the impression this profile "
                    "exists to avoid."
                ),
                produces=("platform_variants",),
            ),
            step(
                "hold_the_queue_until_the_owner_releases_it",
                "Publish nothing the owner has not released",
                StepKind.GATE,
                (
                    "Put every drafted item in front of the owner with the platform it "
                    "goes to, the time it goes out and the media attached, and wait. A "
                    "post is public the second it lands and cannot be taken back from the "
                    "people who already saw it, so an item nobody released stays in the "
                    "queue and ages there; a queue that has gone quiet is escalated rather "
                    "than emptied on your own authority."
                ),
            ),
        ),
        artifacts=(
            artifact(
                "content_calendar",
                "Content calendar",
                (
                    "Every scheduled item with its platform, its time, the media "
                    "attached, the release that authorised it and its published state."
                ),
                "report",
            ),
            artifact(
                "platform_variants",
                "Per-platform variants",
                (
                    "Each released item recut per platform with its dimensions, running "
                    "length, caption, tags, link handling and accessibility text."
                ),
                "bundle",
            ),
        ),
        tools=("post_scheduler", "media_transcoder", "approval_queue", "social_publisher"),
        config_keys=(
            ConfigKey(
                key="platform_mix",
                description=(
                    "Which platforms this archetype and vertical actually publish "
                    "to, at what cadence, in what format and at what length."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="release_authority",
                description=(
                    "Who releases an item, how long the queue waits for them and "
                    "what happens to an item nobody released."
                ),
                resolved_by="owner",
                required=True,
            ),
        ),
        kpis=(
            "published posts carrying an owner release",
            "scheduled items published at their scheduled time",
            "items published to a platform in the wrong format",
        ),
        channels=("social_platforms",),
    ),
    Profile(
        name="ad_platform_sync",
        summary=(
            "A two-way sync with the customer's own ad accounts: leads in fast "
            "enough to still be answerable, audiences out from the CRM with "
            "consent applied, and the money left with the owner."
        ),
        match=("lead ads", "paid social", "ads coordinator", "audiences", "spend report", "budget"),
        steps=(
            step(
                "pull_each_lead_the_moment_it_lands",
                "Take the lead out of the platform inbox immediately",
                StepKind.ACT,
                (
                    "Take each lead the instant the platform releases it, write it into "
                    "the CRM with the campaign, form and creative it came from, and hand "
                    "it straight to whatever answers enquiries. A lead form is filled in a "
                    "moment of intent that decays in minutes, and a lead left sitting in a "
                    "platform inbox overnight has already been answered by somebody else "
                    "-- the spend that bought it is gone either way."
                ),
                produces=("lead_intake_log",),
            ),
            step(
                "push_the_audiences_and_report_the_spend",
                "Sync the segments out, then report and stop",
                StepKind.ACT,
                (
                    "Build each audience from the CRM segment the configuration names, "
                    "test every record against its consent and suppression state before it "
                    "leaves the building, and push the audience to the customer's own ad "
                    "account. Then report what was spent against what came back, campaign "
                    "by campaign, and stop there: the budget, the bid and the decision to "
                    "keep a campaign running belong to the owner and are set out as "
                    "options with their consequences, never moved by you."
                ),
                produces=("audience_sync_record", "spend_report"),
            ),
        ),
        artifacts=(
            artifact(
                "lead_intake_log",
                "Lead intake log",
                (
                    "Each lead with the campaign, form and creative behind it, the time "
                    "the platform released it, the time it reached the CRM and the time "
                    "it reached a responder."
                ),
                "log",
            ),
            artifact(
                "audience_sync_record",
                "Audience sync record",
                (
                    "Each audience pushed with the CRM segment behind it, the consent "
                    "and suppression state applied, the records withheld, the resulting "
                    "size and the account it went to."
                ),
            ),
            artifact(
                "spend_report",
                "Spend report",
                (
                    "Spend by campaign set against the leads, bookings and revenue "
                    "attributed back to it, with the options for the owner and the "
                    "consequence of each."
                ),
                "report",
            ),
        ),
        tools=("ads_api", "crm_writer", "audience_builder", "consent_register"),
        config_keys=(
            ConfigKey(
                key="ad_accounts",
                description=(
                    "The customer's own ad accounts, the campaigns in scope, and who "
                    "may change a budget, a bid or a campaign state."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="audience_segments",
                description=(
                    "Which CRM segments become audiences in this vertical, how often "
                    "each refreshes and which records must never be included."
                ),
                resolved_by="vertical",
                required=True,
            ),
            ConfigKey(
                key="data_sharing_consent",
                description=(
                    "What a record must carry in this market before it may be shared "
                    "with an advertising platform, and the suppression state that "
                    "overrides everything else."
                ),
                required=True,
            ),
        ),
        kpis=(
            "lead-ads leads reaching the CRM inside the configured seconds",
            "audiences refreshed on schedule with consent state applied",
            "records pushed to a platform that should have been suppressed",
        ),
        channels=("ad_platforms",),
    ),
    Profile(
        name="deep_link_placement",
        summary=(
            "The market's messaging rail signposted on every surface the business "
            "controls, each placement tagged so the enquiry that arrives can be "
            "traced back to the surface that produced it."
        ),
        match=("click-to-chat", "deep link", "signposter", "channel-attributed"),
        steps=(
            step(
                "place_the_link_on_every_surface_the_business_controls",
                "Signpost the rail everywhere, in the form each surface accepts",
                StepKind.ACT,
                (
                    "Put the rail's deep link on every surface in the placement map -- the "
                    "site, the profile, the ads, the printed and physical placements -- in "
                    "the form each surface accepts, and prefill whatever context that "
                    "surface already knows so the customer does not have to explain where "
                    "they came from. A rail the business has and never signposts converts "
                    "no better than one it does not have."
                ),
                produces=("placement_map",),
            ),
            step(
                "prove_the_tag_arrives_at_the_other_end",
                "Test each placement from the customer's side",
                StepKind.ASSESS,
                (
                    "Give every placement its own tag, then send a test enquiry through it "
                    "and confirm the tag arrived in the record rather than assuming the "
                    "link was built correctly. An untagged or broken placement produces "
                    "enquiries nobody can attribute, and the surface that was quietly "
                    "working hardest gets dropped at the next review because nothing ever "
                    "proved it."
                ),
                produces=("attribution_check",),
            ),
        ),
        artifacts=(
            artifact(
                "placement_map",
                "Placement map",
                (
                    "Every surface carrying a link, the form it takes there, who "
                    "controls that surface, the tag it carries and the date it was last "
                    "confirmed working."
                ),
            ),
            artifact(
                "attribution_check",
                "Attribution check",
                (
                    "The test enquiry sent through each placement, the tag that arrived "
                    "in the record, and the placements that produced nothing or produced "
                    "an untagged enquiry."
                ),
                "log",
            ),
        ),
        tools=("link_builder", "placement_publisher", "code_generator", "attribution_tester"),
        config_keys=(
            ConfigKey(
                key="link_placements",
                description=(
                    "Every surface a deep link is placed on, the form it takes there "
                    "and who controls that surface."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="rail_link_format",
                description=(
                    "The deep-link format, prefill rules and fallback rail for this "
                    "market's primary messaging channel."
                ),
                required=True,
            ),
        ),
        kpis=(
            "placements confirmed live and carrying their tag",
            "enquiries arriving attributed to a named placement",
            "broken placements found by a test rather than by a customer",
        ),
    ),
    # Fallback.  Deliberately the family's canonical shape rather than a dumping
    # ground: one fact the business owns has changed, and every surface holding a
    # copy of it has to be found, changed against an effective date and read back.
    # The units that land here -- an hours change, a price change, a rebrand or a
    # move -- are exactly that, and so is any connector the catalogue adds later
    # that is a projection of the record and nothing more.
    Profile(
        name="surface_cascade",
        summary=(
            "One change to a fact the business owns, carried to every surface "
            "holding a copy of it, against an effective date, with commitments "
            "already made honoured and a checklist that proves nothing was left."
        ),
        match=(),
        steps=(
            step(
                "enumerate_every_copy_of_the_changed_fact",
                "List every surface holding a copy before you change any of them",
                StepKind.GATHER,
                (
                    "List every place the changed fact appears before touching one of "
                    "them: the site, the profiles, the directories and the aggregators "
                    "behind them, the booking rules, the greetings and out-of-hours "
                    "messages, the templates, signatures, documents and printed material. "
                    "Treat the list as incomplete until the owner has seen it, because "
                    "what kills a cascade is never the surface that failed -- it is the "
                    "one nobody put on the list."
                ),
                produces=("surface_register",),
            ),
            step(
                "apply_the_effective_date_and_the_in_flight_rule",
                "Change each copy on its effective date, and honour what is already promised",
                StepKind.ACT,
                (
                    "Change each copy against the effective date the instruction carries "
                    "rather than the moment it was given, and handle everything already in "
                    "flight by the rule the configuration sets: quotes issued, bookings "
                    "taken, messages scheduled, documents sent. A change applied "
                    "retrospectively to everything breaks commitments the business has "
                    "already made, and a change applied to nothing leaves it publishing a "
                    "fact that stopped being true -- both come back as a dispute."
                ),
                produces=("in_flight_disposition", "cascade_checklist"),
            ),
        ),
        artifacts=(
            artifact(
                "surface_register",
                "Surface register",
                (
                    "Every surface holding a copy of the changed fact: who controls it, "
                    "how it is changed, who last changed it and whether it was reached "
                    "this run."
                ),
            ),
            artifact(
                "cascade_checklist",
                "Verification checklist",
                (
                    "Surface by surface: changed, pending, failed or not applicable, "
                    "with the read-back that proves each one and the items still open "
                    "with their owner."
                ),
                "report",
            ),
            artifact(
                "in_flight_disposition",
                "In-flight disposition",
                (
                    "Each commitment already made under the previous value, the rule "
                    "applied to it, what the counterparty was told and when."
                ),
            ),
        ),
        tools=("cascade_planner", "template_updater", "surface_publisher", "checklist_runner"),
        config_keys=(
            ConfigKey(
                key="cascade_surfaces",
                description=(
                    "Every surface a change of this kind must reach, who controls "
                    "each one and how it is changed."
                ),
                resolved_by="owner",
                required=True,
            ),
            ConfigKey(
                key="effective_date_rules",
                description=(
                    "When a change takes effect on each surface in this vertical, and "
                    "how a commitment already made under the previous value is "
                    "honoured."
                ),
                resolved_by="vertical",
                required=True,
            ),
        ),
        kpis=(
            "surfaces confirmed changed against the register",
            "cascades completed inside the effective-date window",
            "surfaces found stale after the cascade was called complete",
        ),
    ),
)


# --------------------------------------------------------------------------- #
# the engine
# --------------------------------------------------------------------------- #


@register
class PublishingPlatformConnectorsEngine(Engine):
    """Carries every unit whose work is keeping somebody else's surface correct.

    The engine holds one pipeline -- read the record, read the surfaces, diff
    them, plan the change, compose what each surface takes, push it under the
    customer's grant, read it back and report -- and nine profiles that say what
    kind of surface is on the other end.  Nothing in the code knows whether it is
    holding a map profile, a citation sweep, a page set, an ad account or an
    agent endpoint; the surfaces, the field maps, the release policy, the
    platform limits and the effective dates all arrive as configuration.
    """

    id: ClassVar[str] = "MF12"
    family: ClassVar[str] = "Publishing & platform connectors"
    what_it_does: ClassVar[str] = (
        "SEO/AEO surfaces, social publishing, ad-platform sync, MCP endpoint"
    )
    capabilities: ClassVar[tuple[Capability, ...]] = (
        Capability.PUBLISH,
        Capability.RECONCILE,
        Capability.GENERATE_CREATIVE,
        Capability.WATCH_SIGNAL,
        Capability.SCHEDULE,
    )
    default_tools: ClassVar[tuple[str, ...]] = (
        "surface_registry",
        "connected_account_grants",
        "source_of_truth_reader",
        "surface_reader",
        "payload_composer",
        "surface_publisher",
        "read_back_verifier",
        "rollback_store",
    )
    default_channels: ClassVar[tuple[str, ...]] = (
        "owner_dashboard",
        "website",
        "listings_platforms",
        "social_platforms",
    )
    default_kpis: ClassVar[tuple[str, ...]] = (
        "changes confirmed live by a read-back rather than by a platform response",
        "surfaces holding the current value at the end of each run",
        "publications leaving from the customer's own connected account",
        "platform rejections, holds and policy warnings resolved before the next run",
        "stale surfaces found by a customer or the owner before the unit found them",
    )
    config_keys: ClassVar[tuple[ConfigKey, ...]] = _FAMILY_CONFIG_KEYS
    state_object: ClassVar[str] = "surface_state"

    # -- hooks -------------------------------------------------------------
    @property
    def profiles(self) -> tuple[Profile, ...]:
        return _PROFILES

    def base_plan(self, record: Mapping[str, Any]) -> tuple[Step, ...]:
        """Read the truth, read the surface, diff, plan, compose, push, read back, report.

        Three placements in that order carry most of the weight.  The surfaces
        are read *before* anything is written, because a connector that pushes
        without looking overwrites the edit the platform, the public or the
        owner's business partner made last week, and nobody finds out until a
        customer does.  The push sits late and narrow: one step, one grant, one
        surface at a time, so a run that fails halfway leaves a legible partial
        state rather than an unknown one.  And the read-back is a step of its own
        rather than a flourish on the push, because in this family the platform
        accepting a payload and the change being live are genuinely different
        events, often days apart, and only the second one is the product.
        """
        return (
            step(
                "read_the_source_of_truth",
                "Take the canonical values from the systems that own them",
                StepKind.OBSERVE,
                (
                    "Take each value this run may publish from the system of record that "
                    "owns it -- the business profile, the service list, the diary, the "
                    "published price book -- with its version, the time it was read and "
                    "the effective date of any change carried by the trigger. Where the "
                    "record is missing, ambiguous or contradicted by another system, that "
                    "is the finding: you raise it and publish nothing, because a surface "
                    "confidently repeating the wrong hour or the wrong figure is worse "
                    "than one that is merely out of date."
                ),
                produces=("source_of_truth_snapshot",),
            ),
            step(
                "read_every_connected_surface",
                "Read what each surface actually says, and the grant it is read under",
                StepKind.GATHER,
                (
                    "Read the current live state of every surface in scope through the "
                    "customer's own grant, and record for each one what it holds, when it "
                    "was read, the grant's scope and expiry, and whether it answered at "
                    "all. A surface that did not answer is recorded as unverified rather "
                    "than assumed correct, and a grant that has lapsed or been narrowed is "
                    "raised as a blocked surface rather than quietly skipped -- the two "
                    "look identical from the outside and only one of them is harmless."
                ),
                produces=("surface_inventory",),
            ),
            step(
                "diff_the_surfaces_against_the_truth",
                "Compare field by field and classify every divergence",
                StepKind.ASSESS,
                (
                    "Set each surface against the snapshot field by field through the "
                    "field map, and classify every difference: stale, missing, truncated "
                    "by the platform, rejected, or changed by somebody other than this "
                    "unit. Say since when where the surface carries a modification time. "
                    "The direction is fixed -- the record is the truth and the surface is "
                    "a copy of it -- so a value that exists only on a surface is a "
                    "divergence to be resolved, never a fact to be copied back inward."
                ),
                produces=("divergence_report",),
            ),
            step(
                "set_the_change_plan",
                "Decide what this run changes, in what order, and what waits for a person",
                StepKind.DECIDE,
                (
                    "Decide which divergences this run corrects, in which order across "
                    "surfaces -- upstream sources before the copies they feed -- and which "
                    "are held for the owner's release under the publication policy. Test "
                    "every intended item against that surface's own content, uniqueness, "
                    "media and volume rules first and hold anything that would breach one, "
                    "citing the rule. Record what you deliberately left alone and why, "
                    "because an unexplained gap in a cascade reads to the next reviewer as "
                    "a failure."
                ),
                produces=("change_plan",),
            ),
            step(
                "compose_what_each_surface_takes",
                "Compose the payload in the form the surface actually accepts",
                StepKind.DRAFT,
                (
                    "Compose each change in the form its destination takes: the field "
                    "names, the length and format limits, the media dimensions, the "
                    "structured-data shape, the language set and the disclosures the "
                    "country pack requires. Capture the value the surface holds now "
                    "alongside the value replacing it, so the change can be reverted "
                    "rather than argued about. Any figure in a payload comes from the "
                    "published price book and any claim from the source snapshot; nothing "
                    "is written to fill a field that the record cannot support."
                ),
                produces=("publication_payload",),
            ),
            step(
                "publish_through_the_customers_own_account",
                "Push it under the customer's grant, one surface at a time",
                StepKind.ACT,
                (
                    "Publish each released payload from the customer's own connected "
                    "account and never from an account this platform owns, one surface at "
                    "a time, inside that surface's rate limits and outside its quiet "
                    "periods. Record for every push the surface, the grant used, the "
                    "payload sent, the response returned, the identifier it came back "
                    "with and the prior value kept for reversion. A push that errors "
                    "stops the surface and is raised; it is never retried blindly into a "
                    "duplicate."
                ),
                produces=("publication_log",),
            ),
            step(
                "read_the_surface_back",
                "Confirm from the surface itself that the change is live",
                StepKind.ASSESS,
                (
                    "Read every changed surface again after the configured window and "
                    "record what it actually says now: live as intended, still held in the "
                    "platform's review, truncated, rejected, or reverted by somebody else. "
                    "A response that said the payload was accepted proves only that it was "
                    "received. Anything not confirmed live goes back onto the divergence "
                    "report with what the surface returned, and stays there until a later "
                    "read finds it correct."
                ),
                produces=("live_verification",),
            ),
            step(
                "report_the_state_of_every_surface",
                "Give the owner one view of where every surface stands",
                StepKind.NOTIFY,
                (
                    "Report in one place which surfaces now carry the current value, which "
                    "are waiting on a platform review with the date they were submitted, "
                    "which were rejected and on what stated ground, which could not be "
                    "read at all, and which need the owner's decision before anything more "
                    "happens. Name the surfaces that could not be verified rather than "
                    "omitting them: a run that reports only its successes cannot be told "
                    "apart from one that stopped checking."
                ),
                produces=("surface_status_report",),
            ),
        )

    def base_artifacts(self, record: Mapping[str, Any]) -> tuple[Artifact, ...]:
        return (
            artifact(
                "source_of_truth_snapshot",
                "Source-of-truth snapshot",
                (
                    "The canonical values this run publishes from, each with the system "
                    "that owns it, its version, the time it was read and the effective "
                    "date of any change carried by the trigger."
                ),
            ),
            artifact(
                "surface_inventory",
                "Connected-surface inventory",
                (
                    "Every surface in scope: what it currently holds, when it was read, "
                    "the customer's grant it was read under with that grant's scope and "
                    "expiry, and the surfaces that did not answer."
                ),
                "report",
            ),
            artifact(
                "divergence_report",
                "Divergence report",
                (
                    "Field by field and surface by surface: what the record says, what "
                    "the surface says, how it diverged -- stale, missing, truncated, "
                    "rejected or externally edited -- and since when."
                ),
                "report",
            ),
            artifact(
                "change_plan",
                "Change plan",
                (
                    "What this run changes on which surface and in what order, what is "
                    "held for the owner's release, what was held against a platform rule "
                    "with the rule cited, and what was deliberately left alone."
                ),
            ),
            artifact(
                "publication_payload",
                "Publication payload",
                (
                    "Per surface: the exact payload to be written, the fields it sets, "
                    "the media and structured data attached, the limits it was fitted to "
                    "and the value it replaces."
                ),
                "bundle",
            ),
            artifact(
                "publication_log",
                "Publication log",
                (
                    "Every push with its surface, the grant it went under, the payload "
                    "sent, the platform's response and identifier, the time, and the "
                    "prior state retained for reversion."
                ),
                "log",
            ),
            artifact(
                "live_verification",
                "Live verification",
                (
                    "The read-back of every changed surface: what is live, what is still "
                    "in the platform's review, what was rejected, truncated or reverted, "
                    "and the time of the read that proved it."
                ),
                "report",
            ),
            artifact(
                "surface_status_report",
                "Surface status report",
                (
                    "One view for the owner: which surfaces are current, which are "
                    "pending, which were rejected, which could not be read and what "
                    "needs a decision before the next run."
                ),
                "report",
            ),
        )

    def mission_body(self, record: Mapping[str, Any], profile: Profile) -> str:
        vertical = record.get("vertical") or {}
        if vertical:
            where = (
                f"Which surfaces matter to {vertical['name'].lower()} businesses, what "
                f"each one is expected to carry there and when a change takes effect "
                f"come from the vertical overlay and the active country pack -- read "
                f"both rather than publishing what worked for the last customer."
            )
        else:
            where = (
                "This connector runs across every vertical on the platform, so which "
                "surfaces exist, who granted access to them, what each platform "
                "permits and how a change is worded all come from the connected-surface "
                "register and whatever overlay and country pack is in front of you."
            )
        return (
            "HOW YOU WORK. Every surface you write to belongs to somebody else -- a "
            "platform, a directory, an index, an assistant -- and holds a copy of a "
            "fact the business owns, so you work in one direction only: the business's "
            "record is the truth and the surface is a projection of it, never the "
            "other way round. Read the record, read what each surface actually says "
            "and diff the two before you touch anything, because a surface gets edited "
            "by the platform, by the public and by whoever had the password last, and "
            "a change pushed blind overwrites something you never saw. Push only "
            "through the customer's own connected account, and treat a grant that has "
            "expired or narrowed as a stop rather than a surface to skip -- a lapsed "
            "grant looks exactly like a surface where nothing needed changing. Nothing "
            "is done because the platform accepted it: a push can sit in review for a "
            "week, arrive truncated, be rejected an hour later or be reverted by a "
            "stranger's suggested edit, so you read the surface again and report what "
            "it says now. Keep the prior value of everything you change, because a "
            "publication is public the moment it lands and the only way back is a "
            "reversion you prepared before you needed it. Treat each platform's own "
            "rules on content, uniqueness, media and volume as a hard limit and hold "
            "anything that would breach one: a suspended profile costs more than every "
            "post, page or citation it would ever have carried, and it takes weeks to "
            "recover. And publish the fact rather than your version of it -- a price, "
            "an opening hour, an availability or a service you put on a machine-"
            "readable surface will be quoted by something that never checks and held "
            "against the business by somebody who believed it, so it comes from the "
            "system of record and the published price book with the date it was last "
            f"true attached. {_PROFILE_MISSION_LINES[profile.name]} {where}"
        )

    def family_guardrails(self, record: Mapping[str, Any]) -> tuple[Guardrail, ...]:
        return (
            Guardrail(
                id="GR-READ-BACK-PROVES-LIVE",
                rule=(
                    "A change is live when the surface says so on a later read, not "
                    "when the platform accepted the payload."
                ),
                check=(
                    "live_verification carries a post-publication read of every surface "
                    "named in publication_log, taken inside verification_window; "
                    "anything not confirmed live returns to divergence_report."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-RECORD-IS-THE-SOURCE",
                rule=(
                    "The business's record is the truth and every surface is a copy "
                    "of it. A value found only on a surface is a divergence, never a "
                    "fact to be copied back inward."
                ),
                check=(
                    "Every published field resolves to a field of "
                    "source_of_truth_snapshot with its version; no artefact carries a "
                    "value whose only source is an external surface."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-GRANT-BEFORE-PUSH",
                rule=(
                    "Every push leaves through the customer's own connected account, "
                    "and a lapsed or narrowed grant stops that surface rather than "
                    "being passed over in silence."
                ),
                check=(
                    "publication_log names the grant used for each push and it resolves "
                    "to connected_accounts; surface_inventory records each grant's scope "
                    "and expiry, and a missing one is reported as blocked."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-PLATFORM-LIMIT-IS-A-STOP",
                rule=(
                    "A push that would breach a surface's own content, uniqueness, "
                    "media or volume rules is held and raised, never attempted. The "
                    "penalty falls on the profile, not on the item."
                ),
                check=(
                    "change_plan names the platform_rules limit tested for every "
                    "intended item, and each held item cites the rule that held it."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-REVERSIBLE-BY-DEFAULT",
                rule=(
                    "The value a surface held is captured before it is replaced, so a "
                    "wrong publication can be reverted rather than debated."
                ),
                check=(
                    "publication_log stores the prior value and the reversion route for "
                    "every changed field, retained for the period rollback_policy sets."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-MACHINE-SURFACES-CARRY-THEIR-FRESHNESS",
                rule=(
                    "Anything a machine reads -- structured data, a declared answer "
                    "file, an endpoint response -- carries the version and date of the "
                    "record behind it, and any money figure comes from published "
                    "pricing."
                ),
                check=(
                    "Every machine-readable value published names its source record and "
                    "the time that record was read; figures resolve to "
                    "published_price_book."
                ),
                source="mechanism_family",
            ),
            Guardrail(
                id="GR-UNREAD-SURFACE-IS-NOT-A-CORRECT-ONE",
                rule=(
                    "A surface that could not be read is reported as unverified. "
                    "Silence from a platform is never recorded as agreement with the "
                    "record."
                ),
                check=(
                    "surface_inventory holds a read result for every surface in "
                    "connected_surfaces, and surface_status_report names those that "
                    "could not be read and what that leaves unproven."
                ),
                source="mechanism_family",
            ),
        )

    def family_inputs(self, record: Mapping[str, Any]) -> tuple[str, ...]:
        return (
            "The change signal: which fact moved, when it takes effect and who ordered it",
            "The system of record for every field this unit publishes, with its version",
            "The connected-surface register, with the grant, scope and expiry for each",
            "The last verified state of every surface and the divergences still open",
            "Platform rules, volume limits and quiet periods in force for each surface",
            "The approval queue: what is released, what is waiting and for how long",
        )


#: Mission prose per profile.  Each names the surface being written to, the
#: artefact that proves the work landed, and the specific way that surface fails
#: -- which is different for a directory, a queue of public posts and an endpoint
#: another machine is reading.  Kept beside the engine rather than inside the
#: profiles because it is prose about the mission, not configuration a customer
#: can override.
_PROFILE_MISSION_LINES: dict[str, str] = {
    "agent_endpoint": (
        "What you keep here is a surface another machine reads: declare exactly which "
        "questions it answers and which it refuses, serve every answer from the record "
        "read at the moment of the question with its version attached, put anything "
        "that commits the business through the same limits a human enquiry meets, and "
        "log every exchange with the caller's identity -- a caller that cannot ring up "
        "to check will act on whatever you return."
    ),
    "answer_corpus": (
        "What you keep here is the text an assistant quotes: write each answer to stand "
        "alone under quotation, ground it in a source you can name and stamp it with the "
        "date it was last true, then sample the assistants and record what actually "
        "comes back -- the file being live proves nothing, and a stale answer quoted "
        "confidently is worse than no answer at all."
    ),
    "programmatic_pages": (
        "What you keep here is a page set that scales into a penalty if you let it: "
        "give every page something only true of its own service and area, score it "
        "against the rest of the set before publication, and follow each one into the "
        "index -- a set that starts being excluded is the signal to stop generating and "
        "raise it, never to generate more."
    ),
    "listing_profile": (
        "What you keep here is a profile the platform and the public can both edit "
        "underneath you: fill every field the platform's own completeness model exposes, "
        "publish the posts, media and answers on their calendar from the customer's own "
        "profile, and treat any change you did not make -- an accepted suggestion, a "
        "flipped attribute, a duplicate profile -- as a divergence to correct rather "
        "than a new truth to accept."
    ),
    "citation_sync": (
        "What you keep here is one name, address and contact number spread across a long "
        "tail of directories: read them all including the records nobody created, submit "
        "the correction upstream to whatever feeds the copies rather than to each copy, "
        "and hold the entry open until a later read shows the corrected value actually "
        "showing -- submission is not correction here, and the propagation takes weeks."
    ),
    "social_publishing": (
        "What you keep here is a public queue: recut each released item for the platform "
        "it is going to rather than pushing one asset everywhere, publish only what the "
        "owner has released and only from the customer's own accounts, and let an item "
        "nobody released age in the queue -- a post is public the second it lands and "
        "cannot be taken back from the people who already read it."
    ),
    "ad_platform_sync": (
        "What you keep here is a two-way sync with the customer's own ad accounts: take "
        "each lead out of the platform inbox the instant it lands and get it to whoever "
        "answers enquiries, push audiences out only with the consent and suppression "
        "state tested on every record, and report the spend against what came back -- "
        "the budget, the bid and the campaign are the owner's to move, not yours."
    ),
    "deep_link_placement": (
        "What you keep here is one message rail signposted everywhere the business "
        "controls a surface: place the link in the form each surface accepts with the "
        "context prefilled, tag every placement, and prove from the other end that the "
        "tag arrives in the record -- an untagged placement produces enquiries nobody "
        "can attribute, and it gets cut at the next review because nothing proved it."
    ),
    "surface_cascade": (
        "What you keep here is one fact and every copy of it: list the surfaces before "
        "you change any of them and treat the list as incomplete until the owner has "
        "seen it, apply the change against its effective date rather than the moment of "
        "the instruction, honour what is already in flight by the configured rule, and "
        "finish on a checklist that shows a read-back for every surface -- the one that "
        "ends a cascade is always the surface nobody listed."
    ),
}


__all__ = ["PublishingPlatformConnectorsEngine"]

"""The country-pack source table.

Split out of ``build_country_packs.py`` because it is data, not logic, and it is
long.  Everything a unit may need to know about a market lives here and nowhere
else: the standing rule is that vertical and country differences resolve to
configuration, and a key that is declared but unpopulated is the worst of both
worlds -- the spec reads as though the value is handled, and at runtime the model
fills the hole from its own training. That failure mode is not hypothetical. A
safety-critical gas-leak protocol, run against an external model with these keys
empty, announced that it did not have the number loaded and then supplied a
national emergency number from memory in the same breath -- a different one on a
later run.

Three layers, applied in order:

``DEFAULTS``            the platform's cross-market baseline for a key.
``PER_MARKET``          values that genuinely differ by jurisdiction.
``REQUIRED_PER_MARKET`` keys with no baseline at all. Every market must state
                        them explicitly or the build fails. Emergency routing is
                        here because a default emergency number is a wrong
                        emergency number.

OPERATOR NOTE. The per-market values below are the platform's starting position
and carry a ``confirm_locally`` flag where an operator must verify them against
the jurisdiction before go-live -- utility emergency lines in particular are
distributor-specific in most markets and have no national number. Where a market
has no national line the entry says so in words rather than leaving a hole,
because a hole is what invites a fabricated answer.
"""

from __future__ import annotations

from typing import Any

# --------------------------------------------------------------------------- #
# keys that must be stated per market, with no fallback
# --------------------------------------------------------------------------- #

REQUIRED_PER_MARKET: tuple[str, ...] = (
    "emergency_routing",
    "working_calendar",
    "contactable_hours",
    "consent_basis",
    "tax_display_rules",
    "statutory_clocks",
)

# --------------------------------------------------------------------------- #
# emergency routing -- no default, ever
# --------------------------------------------------------------------------- #

#: Fields: general, police, fire, ambulance, poison, gas_leak, electricity,
#: script, confirm_locally.
#: "gas_leak" and "electricity" are distributor-specific in most markets; where
#: there is no national line the value says so explicitly and routes to the
#: general number, so a unit reading this pack is never left to guess.
EMERGENCY_ROUTING: dict[str, dict[str, Any]] = {
    "US": {
        "general": "911", "police": "911", "fire": "911", "ambulance": "911",
        "poison": "1-800-222-1222 (Poison Help)",
        "gas_leak": "No national gas line. Call 911, then the gas utility on the customer record.",
        "electricity": "No national line. Call 911, then the electricity utility on the customer record.",
        "confirm_locally": ["gas_leak", "electricity"],
    },
    "CA": {
        "general": "911", "police": "911", "fire": "911", "ambulance": "911",
        "poison": "1-844-764-7669 (Poison Centres)",
        "gas_leak": "No national gas line. Call 911, then the provincial gas utility on the customer record.",
        "electricity": "No national line. Call 911, then the provincial utility.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "UK": {
        "general": "999 (112 also connects)", "police": "999", "fire": "999", "ambulance": "999",
        "poison": "111 (NHS), or 999 if the person is seriously unwell",
        "gas_leak": "0800 111 999 (National Gas Emergency Service, 24h)",
        "electricity": "105 (national power cut and emergency line)",
        "confirm_locally": [],
    },
    "IE": {
        "general": "112 or 999", "police": "112 or 999", "fire": "112 or 999", "ambulance": "112 or 999",
        "poison": "01 809 2166 (National Poisons Information Centre)",
        "gas_leak": "1800 20 50 50 (Gas Networks Ireland emergency, 24h)",
        "electricity": "1800 372 999 (ESB Networks emergency)",
        "confirm_locally": [],
    },
    "DE": {
        "general": "112", "police": "110", "fire": "112", "ambulance": "112",
        "poison": "Giftnotruf - regional centre; 112 if the person is seriously unwell",
        "gas_leak": "No national gas line. Call 112, then the local Gasnetzbetreiber Entstoerungsdienst on the customer record.",
        "electricity": "No national line. Call the local Netzbetreiber Entstoerungsdienst; 112 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "FR": {
        "general": "112", "police": "17", "fire": "18", "ambulance": "15 (SAMU)",
        "poison": "Centre antipoison regional; 15 if the person is seriously unwell",
        "gas_leak": "0800 47 33 33 (GRDF urgence securite gaz, 24h)",
        "electricity": "09 72 67 50 + department number (Enedis depannage)",
        "confirm_locally": ["poison", "electricity"],
    },
    "ES": {
        "general": "112", "police": "091", "fire": "080", "ambulance": "061",
        "poison": "91 562 04 20 (Instituto Nacional de Toxicologia)",
        "gas_leak": "No single national line. Call 112, then the gas distributor on the customer record.",
        "electricity": "No national line. Call the distributor; 112 if there is danger to life.",
        "confirm_locally": ["gas_leak", "electricity"],
    },
    "IT": {
        "general": "112", "police": "112", "fire": "115", "ambulance": "118",
        "poison": "Centro antiveleni regionale; 118 if the person is seriously unwell",
        "gas_leak": "No single national line. Call 112, then the gas distributor on the customer record.",
        "electricity": "803 500 (Enel guasti) where Enel is the distributor; otherwise the local distributor.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "NL": {
        "general": "112", "police": "112 (0900-8844 non-urgent)", "fire": "112", "ambulance": "112",
        "poison": "030 274 88 88 (Nationaal Vergiftigingen Informatie Centrum, professionals)",
        "gas_leak": "0800 9009 (national gas leak line, 24h)",
        "electricity": "No national line. Call the regional netbeheerder; 112 if there is danger to life.",
        "confirm_locally": ["electricity"],
    },
    "PL": {
        "general": "112", "police": "997", "fire": "998", "ambulance": "999",
        "poison": "Regional osrodek toksykologii; 999 if the person is seriously unwell",
        "gas_leak": "992 (pogotowie gazowe)",
        "electricity": "991 (pogotowie energetyczne)",
        "confirm_locally": ["poison"],
    },
    "AE": {
        "general": "999", "police": "999", "fire": "997", "ambulance": "998",
        "poison": "8004272 (Drug and Poison Information Centre, MoHAP)",
        "gas_leak": "997 (Civil Defence), then the gas supplier on the customer record.",
        "electricity": "Utility emergency line per emirate (DEWA 991 in Dubai); 999 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "SA": {
        "general": "911 in Riyadh, Makkah and Eastern Province; 999 elsewhere",
        "police": "999 (911 in unified-service regions)", "fire": "998", "ambulance": "997",
        "poison": "937 (MOH health line)",
        "gas_leak": "998 (Civil Defence), then the gas supplier on the customer record.",
        "electricity": "933 (Saudi Electricity Company); 998 if there is danger to life.",
        "confirm_locally": ["general", "gas_leak"],
    },
    "IN": {
        "general": "112", "police": "100 or 112", "fire": "101 or 112", "ambulance": "102 / 108 or 112",
        "poison": "1800 116 117 (National Poisons Information Centre, AIIMS)",
        "gas_leak": "1906 (LPG emergency helpline)",
        "electricity": "1912 (state electricity complaint line); 112 if there is danger to life.",
        "confirm_locally": ["poison", "electricity"],
    },
    "BR": {
        "general": "190 police / 192 SAMU / 193 bombeiros", "police": "190",
        "fire": "193", "ambulance": "192",
        "poison": "0800 722 6001 (Disque Intoxicacao, ANVISA)",
        "gas_leak": "No national line. Call 193, then the gas distributor on the customer record.",
        "electricity": "No national line. Call the distributor; 193 if there is danger to life.",
        "confirm_locally": ["gas_leak", "electricity"],
    },
    "MX": {
        "general": "911", "police": "911", "fire": "911", "ambulance": "911",
        "poison": "800 000 4400 (SINTOX)",
        "gas_leak": "No national line. Call 911, then the gas supplier on the customer record.",
        "electricity": "071 (CFE); 911 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak"],
    },
    "JP": {
        "general": "110 police / 119 fire and ambulance", "police": "110",
        "fire": "119", "ambulance": "119",
        "poison": "072-727-2499 (Japan Poison Information Center, Osaka)",
        "gas_leak": "No national line. Call 119, then the gas supplier's 24h emergency number on the customer record.",
        "electricity": "No national line. Call the regional power company; 119 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "KR": {
        "general": "112 police / 119 fire and ambulance", "police": "112",
        "fire": "119", "ambulance": "119",
        "poison": "1339 (emergency medical information)",
        "gas_leak": "1544-4500 (Korea Gas Safety Corporation)",
        "electricity": "123 (KEPCO); 119 if there is danger to life.",
        "confirm_locally": [],
    },
    "CN": {
        "general": "110 police / 119 fire / 120 ambulance", "police": "110",
        "fire": "119", "ambulance": "120",
        "poison": "No single national line; 120 if the person is seriously unwell",
        "gas_leak": "No national line. Call 119, then the local gas company on the customer record.",
        "electricity": "95598 (State Grid); 119 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak"],
    },
    "SG": {
        "general": "999 police / 995 fire and ambulance", "police": "999",
        "fire": "995", "ambulance": "995",
        "poison": "6423 9119 (Drug and Poison Information Centre)",
        "gas_leak": "1800 752 1800 (City Energy gas emergency)",
        "electricity": "1800 778 8888 (SP Group)",
        "confirm_locally": [],
    },
    "AU": {
        "general": "000 (112 from a mobile)", "police": "000", "fire": "000", "ambulance": "000",
        "poison": "13 11 26 (Poisons Information Centre)",
        "gas_leak": "No national line. Call 000, then the state gas distributor on the customer record.",
        "electricity": "13 13 51 in some states; otherwise the state distributor. 000 if there is danger to life.",
        "confirm_locally": ["gas_leak", "electricity"],
    },
    "NZ": {
        "general": "111", "police": "111", "fire": "111", "ambulance": "111",
        "poison": "0800 764 766 (National Poisons Centre)",
        "gas_leak": "0800 800 111 (First Gas emergency) where First Gas is the network; otherwise the local network.",
        "electricity": "No national line. Call the local lines company; 111 if there is danger to life.",
        "confirm_locally": ["gas_leak", "electricity"],
    },
    "ZA": {
        "general": "112 from a mobile", "police": "10111", "fire": "10177", "ambulance": "10177",
        "poison": "0861 555 777 (Poisons Information Helpline)",
        "gas_leak": "No national line. Call 10177, then the gas supplier on the customer record.",
        "electricity": "08600 37566 (Eskom) or the municipal distributor; 10177 if there is danger to life.",
        "confirm_locally": ["gas_leak", "electricity"],
    },
    "KE": {
        "general": "999, 112 or 911", "police": "999 or 112", "fire": "999 or 112", "ambulance": "999 or 112",
        "poison": "No national line; go to the nearest emergency department",
        "gas_leak": "No national line. Call 999, then the LPG supplier on the customer record.",
        "electricity": "97771 (Kenya Power); 999 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "NG": {
        "general": "112", "police": "112 (767 or 112 in Lagos)", "fire": "112", "ambulance": "112",
        "poison": "No national line; go to the nearest emergency department",
        "gas_leak": "No national line. Call 112, then the LPG supplier on the customer record.",
        "electricity": "No national line. Call the DisCo on the customer record; 112 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "TR": {
        "general": "112", "police": "112 (155)", "fire": "112 (110)", "ambulance": "112",
        "poison": "114 (Ulusal Zehir Danisma Merkezi)",
        "gas_leak": "187 (dogalgaz acil / ariza)",
        "electricity": "186 (elektrik ariza)",
        "confirm_locally": [],
    },
    "VN": {
        "general": "113 police / 114 fire / 115 ambulance", "police": "113",
        "fire": "114", "ambulance": "115",
        "poison": "No national line; go to the nearest emergency department",
        "gas_leak": "No national line. Call 114, then the gas supplier on the customer record.",
        "electricity": "No national line. Call the provincial EVN line; 114 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
    "TH": {
        "general": "191 police / 199 fire / 1669 ambulance", "police": "191",
        "fire": "199", "ambulance": "1669",
        "poison": "1367 (Ramathibodi Poison Center)",
        "gas_leak": "No national line. Call 199, then the LPG supplier on the customer record.",
        "electricity": "1129 (MEA, Bangkok) or 1129/1130 per authority; 199 if there is danger to life.",
        "confirm_locally": ["gas_leak", "electricity"],
    },
    "ID": {
        "general": "112", "police": "110", "fire": "113", "ambulance": "118 or 119",
        "poison": "1500 533 (BPOM HALO)",
        "gas_leak": "No national line. Call 113, then the gas supplier on the customer record.",
        "electricity": "123 (PLN); 113 if there is danger to life.",
        "confirm_locally": ["gas_leak"],
    },
    "PH": {
        "general": "911", "police": "911 (117)", "fire": "911", "ambulance": "911",
        "poison": "(02) 8524 1078 (National Poison Management and Control Centre)",
        "gas_leak": "No national line. Call 911, then the LPG supplier on the customer record.",
        "electricity": "16211 (Meralco); 911 if there is danger to life.",
        "confirm_locally": ["poison", "gas_leak", "electricity"],
    },
}

#: Appended to every emergency_routing entry. The protective actions are not
#: jurisdiction-specific, so they are stated once and are always available even
#: where a number is not.
EMERGENCY_SCRIPT = (
    "Deliver the protective actions first and without waiting for anyone: get "
    "everyone out and away from the building, touch no switches, plugs, lights "
    "or ignition sources, do not use a doorbell or a phone inside, leave doors "
    "open on the way out if it is safe to, and do not go back in. Then give the "
    "number exactly as written in this pack. Quote no number that is not written "
    "here. If the entry you need says there is no national line, say that, give "
    "the general number, and escalate to the named human contact immediately."
)


# --------------------------------------------------------------------------- #
# per-market operational configuration
# --------------------------------------------------------------------------- #

#: Weekend conventions that are not Saturday/Sunday.
_WEEKEND = {"AE": ["saturday", "sunday"], "SA": ["friday", "saturday"]}

_TIMEZONE = {
    "US": "America/New_York (business may sit in any of six zones - read the site record)",
    "CA": "America/Toronto (six zones - read the site record)",
    "UK": "Europe/London", "IE": "Europe/Dublin", "DE": "Europe/Berlin",
    "FR": "Europe/Paris", "ES": "Europe/Madrid", "IT": "Europe/Rome",
    "NL": "Europe/Amsterdam", "PL": "Europe/Warsaw", "AE": "Asia/Dubai",
    "SA": "Asia/Riyadh", "IN": "Asia/Kolkata", "BR": "America/Sao_Paulo",
    "MX": "America/Mexico_City", "JP": "Asia/Tokyo", "KR": "Asia/Seoul",
    "CN": "Asia/Shanghai", "SG": "Asia/Singapore",
    "AU": "Australia/Sydney (five zones - read the site record)",
    "NZ": "Pacific/Auckland", "ZA": "Africa/Johannesburg", "KE": "Africa/Nairobi",
    "NG": "Africa/Lagos", "TR": "Europe/Istanbul", "VN": "Asia/Ho_Chi_Minh",
    "TH": "Asia/Bangkok", "ID": "Asia/Jakarta", "PH": "Asia/Manila",
}

#: The lawful basis and opt-out regime for an outbound touch, per market. These
#: differ enough that a shared default would be wrong nearly everywhere.
_CONSENT_BASIS = {
    "US": "TCPA: prior express written consent for marketing calls and texts to mobiles; "
          "honour national and internal DNC within 10 days; CAN-SPAM for email with a "
          "working unsubscribe and a physical address. State laws (FL, OK) are stricter.",
    "CA": "CASL: express or documented implied consent before any commercial electronic "
          "message, with a two-year implied window from a transaction; sender identity and "
          "a working unsubscribe in every message; retain the consent record.",
    "UK": "PECR plus UK GDPR: opt-in for electronic marketing to individuals, soft opt-in "
          "for existing customers on similar products; legitimate interest may cover B2B; "
          "opt-out in every message and honoured within 28 days.",
    "IE": "ePrivacy Regulations plus GDPR: opt-in for electronic marketing, soft opt-in for "
          "existing customers within 12 months; opt-out in every message.",
    "DE": "UWG plus GDPR: prior express opt-in for email, SMS and calls, with double opt-in "
          "the accepted standard of proof; no soft opt-in for cold contact; retain the "
          "confirmation record.",
    "FR": "GDPR plus CNIL guidance: opt-in for B2C electronic marketing, opt-out acceptable "
          "for B2B on a professional address related to the role; Bloctel for telephone.",
    "ES": "LSSI plus GDPR: prior consent for commercial electronic communication, with an "
          "existing-customer exception for similar products; Lista Robinson for telephone.",
    "IT": "GDPR plus Garante guidance: prior consent for electronic marketing; Registro "
          "Pubblico delle Opposizioni for telephone; consent must be separable per purpose.",
    "NL": "Telecommunicatiewet plus GDPR: opt-in for electronic marketing, soft opt-in for "
          "existing customers; Bel-me-niet register obligations for telephone.",
    "PL": "Telecommunications Law plus GDPR: prior consent for electronic marketing and for "
          "automated calling; consent per channel, evidenced.",
    "AE": "UAE PDPL plus TDRA rules: consent before marketing SMS and calls, sender id "
          "registered, opt-out honoured; marketing outside permitted hours is prohibited.",
    "SA": "SA PDPL plus CITC rules: registered sender id and prior consent for marketing "
          "messages; unsubscribe keyword in Arabic and English.",
    "IN": "TRAI TCCCPA: DLT registration of sender, header and template; consent recorded on "
          "the DLT platform; DPDP Act notice and withdrawal mechanism; NCPR preferences bind.",
    "BR": "LGPD: a lawful basis per purpose, consent or legitimate interest, recorded and "
          "revocable; opt-out in every message; Procon rules on telephone contact.",
    "MX": "LFPDPPP: privacy notice before collection, opt-out honoured; REPEP registry binds "
          "telephone marketing.",
    "JP": "APPI plus the Act on Specified Commercial Transactions: opt-in for marketing email, "
          "sender identity and opt-out in every message; refusal must be recorded and honoured.",
    "KR": "PIPA plus the Network Act: prior consent for commercial messages, mandatory "
          "(광고) prefix, and separate consent for contact between 21:00 and 08:00.",
    "CN": "PIPL: separate consent per purpose, easy withdrawal, and no marketing to a person "
          "who has refused; cross-border transfer requires its own basis.",
    "SG": "PDPA: consent or an applicable exception before marketing; DNC Registry must be "
          "checked before calls, texts and faxes; clear identification of the sender.",
    "AU": "Spam Act plus Privacy Act: express or inferred consent, sender identification and a "
          "functional unsubscribe honoured within 5 business days; Do Not Call Register binds.",
    "NZ": "Unsolicited Electronic Messages Act plus Privacy Act 2020: consent, clear sender "
          "identification and a functional unsubscribe.",
    "ZA": "POPIA plus CPA: opt-in for electronic direct marketing to non-customers, one "
          "approach permitted to obtain consent; opt-out in every message.",
    "KE": "Data Protection Act 2019: consent for direct marketing, with an easy objection "
          "route recorded against the contact.",
    "NG": "NDPA: lawful basis and recorded consent for direct marketing; opt-out honoured.",
    "TR": "KVKK plus IYS: commercial electronic messages must be registered in the IYS system "
          "with consent recorded there; opt-out via IYS honoured.",
    "VN": "Decree 91 on anti-spam plus PDPD: prior consent for advertising messages, sender "
          "registration, and a refusal mechanism honoured within 24 hours.",
    "TH": "PDPA: consent or legitimate interest recorded per purpose, withdrawal as easy as "
          "consent; sender identity in every message.",
    "ID": "PDP Law: consent per purpose, recorded and revocable; sender identity required.",
    "PH": "Data Privacy Act: consent or an applicable criterion, recorded; opt-out honoured "
          "and the DPO route stated.",
}

#: Hours in which an automated touch may be sent, read in the recipient's own
#: timezone. Several markets legislate this; the rest carry the platform's own
#: floor, which is deliberately conservative.
_CONTACTABLE_HOURS = {
    "US": "08:00-21:00 recipient local time (TCPA). No marketing calls or texts outside it. "
          "State curfews may be tighter; the tighter one wins.",
    "CA": "09:00-21:30 weekdays, 10:00-18:00 weekends (CRTC telemarketing rules).",
    "UK": "08:00-20:00 Mon-Sat for cold contact; no unsolicited Sunday marketing. "
          "Transactional and service messages are exempt.",
    "IE": "08:00-20:00 Mon-Sat for cold contact.",
    "DE": "08:00-20:00 weekdays. No marketing on Sundays or public holidays.",
    "FR": "10:00-13:00 and 14:00-20:00 Mon-Fri only; no marketing calls on Saturdays, "
          "Sundays or public holidays.",
    "ES": "09:00-21:00 weekdays; telephone marketing restricted on weekends.",
    "IT": "09:00-20:00 weekdays.",
    "NL": "09:00-20:00 weekdays.",
    "PL": "08:00-20:00 weekdays.",
    "AE": "09:00-21:00. No marketing during prayer times or before 09:00 on Fridays; "
          "reduce cadence during Ramadan daylight hours.",
    "SA": "09:00-21:00. No marketing during prayer times; reduce cadence during Ramadan "
          "daylight hours.",
    "IN": "09:00-21:00 (TRAI). No commercial communication outside it.",
    "BR": "08:00-20:00 weekdays, 08:00-14:00 Saturdays; none on Sundays or holidays.",
    "MX": "08:00-20:00 weekdays.",
    "JP": "09:00-20:00. Avoid contact during Obon and the New Year period unless the "
          "customer initiated it.",
    "KR": "08:00-21:00. Advertising messages between 21:00 and 08:00 require separate "
          "prior consent.",
    "CN": "09:00-21:00.",
    "SG": "09:00-21:00.",
    "AU": "09:00-20:00 Mon-Fri, 09:00-17:00 Sat; none on Sundays or public holidays.",
    "NZ": "09:00-20:00 Mon-Sat.",
    "ZA": "08:00-20:00 Mon-Sat, 09:00-13:00 Sun (CPA direct marketing hours).",
    "KE": "08:00-20:00.",
    "NG": "08:00-20:00.",
    "TR": "09:00-20:00; no commercial messages on Sundays or public holidays.",
    "VN": "07:00-22:00; advertising messages limited per sender per day.",
    "TH": "08:00-20:00.",
    "ID": "08:00-21:00.",
    "PH": "08:00-21:00.",
}

_TAX_DISPLAY = {
    "US": "Prices shown exclusive of sales tax; tax added at checkout by ship-to or "
          "service jurisdiction. Never state a tax-inclusive total as the price.",
    "CA": "Prices shown exclusive of GST/HST/PST; tax added at checkout by province.",
    "UK": "Consumer prices shown inclusive of VAT. B2B may be shown exclusive if labelled "
          "'+ VAT'. The VAT rate and registration number come from the business record.",
    "IE": "Consumer prices inclusive of VAT; B2B may be exclusive if labelled.",
    "DE": "Consumer prices inclusive of USt (Endpreis, PAngV). B2B may be exclusive if "
          "clearly labelled 'zzgl. MwSt.'.",
    "FR": "Consumer prices inclusive of TVA (TTC); B2B may be shown HT if labelled.",
    "ES": "Consumer prices inclusive of IVA; B2B may be exclusive if labelled.",
    "IT": "Consumer prices inclusive of IVA; B2B may be exclusive if labelled.",
    "NL": "Consumer prices inclusive of BTW; B2B may be exclusive if labelled.",
    "PL": "Consumer prices inclusive of VAT (brutto); B2B commonly netto, labelled.",
    "AE": "Prices shown inclusive of VAT to consumers; the TRN appears on every tax invoice.",
    "SA": "Prices shown inclusive of VAT to consumers; the VAT number appears on every invoice.",
    "IN": "Prices shown inclusive of GST to consumers; the GSTIN and the CGST/SGST/IGST split "
          "appear on the invoice.",
    "BR": "Prices shown inclusive of taxes; the invoice states the tax burden per the "
          "consumer transparency law.",
    "MX": "Prices shown inclusive of IVA to consumers; CFDI states the split.",
    "JP": "Total-price display inclusive of consumption tax is required to consumers.",
    "KR": "Prices shown inclusive of VAT to consumers.",
    "CN": "Prices shown inclusive of VAT to consumers; fapiao states the split.",
    "SG": "Prices shown inclusive of GST to consumers where the business is GST-registered.",
    "AU": "Prices shown inclusive of GST to consumers; single figure must be the total price.",
    "NZ": "Prices shown inclusive of GST to consumers.",
    "ZA": "Prices shown inclusive of VAT to consumers.",
    "KE": "Prices shown inclusive of VAT to consumers.",
    "NG": "Prices shown inclusive of VAT to consumers.",
    "TR": "Prices shown inclusive of KDV to consumers.",
    "VN": "Prices shown inclusive of VAT to consumers.",
    "TH": "Prices shown inclusive of VAT to consumers.",
    "ID": "Prices shown inclusive of PPN to consumers.",
    "PH": "Prices shown inclusive of VAT to consumers; senior and PWD discounts stated.",
}

#: How a legal or contractual period is counted. This is the part of
#: "statutory_clocks" that genuinely is jurisdictional; the specific intervals
#: come from the vertical overlay, which the value says explicitly.
_STATUTORY_CLOCKS = {
    "UK": "Periods run in clear days unless the instrument says calendar days; a deadline "
          "falling on a weekend or bank holiday moves to the next working day. Deemed "
          "service: second business day for first-class post, same day for email sent "
          "before 16:30. Specific intervals come from the vertical overlay.",
    "DE": "Fristen computed under BGB 187-193: the triggering day is not counted, and a "
          "deadline falling on a Saturday, Sunday or public holiday moves to the next "
          "working day. Specific intervals come from the vertical overlay.",
    "FR": "Delais francs: the triggering day is not counted and the last day runs to "
          "midnight; a deadline falling on a weekend or holiday moves to the next working "
          "day. Specific intervals come from the vertical overlay.",
    "US": "Periods generally counted in calendar days unless the rule says business days; "
          "federal and state holidays differ and the applicable one moves the deadline to "
          "the next business day. Specific intervals come from the vertical overlay.",
    "IN": "Periods counted under the General Clauses Act: the first day excluded, and a "
          "deadline falling on a holiday moves to the next working day. Specific intervals "
          "come from the vertical overlay.",
    "JP": "Periods computed under the Civil Code: the initial day is not counted, and a "
          "deadline falling on a holiday moves to the next working day. Specific intervals "
          "come from the vertical overlay.",
    "AE": "Periods counted in calendar days unless stated otherwise; deadlines falling on "
          "Friday, a public holiday or an Eid holiday move to the next working day. "
          "Specific intervals come from the vertical overlay.",
    "SA": "Periods counted in calendar days; Hijri dates apply to some filings. Deadlines "
          "falling on Friday, Saturday or a public holiday move to the next working day. "
          "Specific intervals come from the vertical overlay.",
}

_STATUTORY_CLOCKS_DEFAULT = (
    "Periods are counted in calendar days unless the governing instrument says working "
    "days; the day of the triggering event is not counted; a deadline falling on a "
    "non-working day in this market's working_calendar moves to the next working day. "
    "Specific intervals come from the vertical overlay, not from this pack, and never "
    "from recall."
)


# --------------------------------------------------------------------------- #
# cross-market baseline for every remaining key
# --------------------------------------------------------------------------- #

#: The platform's own policy where it does not vary by jurisdiction. These are
#: real operating positions, not filler: each one tells the unit what to do and
#: where the jurisdiction-specific part comes from when there is one.
DEFAULTS: dict[str, str] = {
    "evidence_standard":
        "Capture at the time of the event, never reconstructed afterwards: what happened, "
        "when, where, who was present, who recorded it, and the system that produced each "
        "item. Photographs carry their timestamp and location; statements are in the "
        "witness's own words and taken separately; readings carry the instrument and its "
        "calibration date. Retain for the longer of seven years, the limitation period in "
        "regulator_guardrails, or any contractual period in the vertical overlay.",
    "evidence_retention":
        "Every observation is stored with its source, its timestamp and the actor who "
        "recorded it, and kept for the longer of seven years or the limitation period that "
        "applies to the matter under regulator_guardrails. Originals are never overwritten; "
        "corrections are appended.",
    "evidence_retention_window":
        "Quotes, approvals, signatures and delivery proof remain retrievable for seven "
        "years, or longer where the vertical overlay or regulator_guardrails requires it.",
    "notification_matrix":
        "For every event class: the customer first where they are affected, then the owner, "
        "then any third party under contract, then any regulator named in "
        "regulator_guardrails. Safety events go to the human contact immediately and in "
        "parallel, never in sequence. Each notification records recipient, channel, time "
        "sent and delivery state. Which notifications are mandatory rather than courteous "
        "is set by regulator_guardrails for this market.",
    "document_validity_rules":
        "An item counts when it is legible at full page width, unexpired at the date of "
        "filing, issued by a body the vertical overlay accepts, and complete including "
        "every page and both sides where the document has them. Scans are colour, "
        "unedited and unwatermarked. Expiry is measured at the filing date, not the "
        "collection date. Anything failing these is chased, never accepted with a note.",
    "submission_deadlines":
        "Each pack type carries its deadline in the vertical overlay; this pack sets how it "
        "is counted (see statutory_clocks and working_calendar) and the internal lead time: "
        "an incomplete pack is escalated at 50% of the remaining window, and again at 80%, "
        "rather than at the deadline itself.",
    "tolerance_and_rounding":
        "Absorb without raising a break: rounding to the minor unit of the currency, "
        "documented currency-conversion spreads, and known settlement timing offsets inside "
        "the settlement_calendar window. Anything above 1% of the transaction or the "
        "equivalent of 50 units of the pack currency, whichever is lower, raises a break. "
        "Tolerances are never applied cumulatively to hide a trend.",
    "citation_style":
        "Name the source, its date and its version, and link to it where the contact can "
        "open it. A position without a citation is not shown to a contact.",
    "deadline_rules":
        "See statutory_clocks for how a period is counted in this market. Service is "
        "effective when delivery is evidenced, not when the message is sent.",
    "standards_and_clause_sets":
        "The standards and licence conditions the business is held to come from the vertical "
        "overlay and from regulator_guardrails; each clause is evidenced against "
        "evidence_standard and cited with its version and effective date.",
    "capture_policy":
        "Every third-party reading is stored with its source system, the time it was taken "
        "and the identifier of the record it was taken against, and retained per "
        "evidence_retention so it can still be produced in a dispute.",
    "adverse_action_wording":
        "A negative result states the decision, the specific reason, the evidence relied on, "
        "the route to challenge it and the time limit on that route. It never states or "
        "implies a diagnosis, a judgement of character, or a conclusion the business is not "
        "qualified to reach. Wording required by a regulator overrides this and comes from "
        "regulator_guardrails.",
    "scheme_rules":
        "The adjudication or statutory scheme governing a dispute comes from "
        "regulator_guardrails for this market; its deadlines run under statutory_clocks and "
        "its evidence bar under evidence_standard. Failing to respond inside a scheme "
        "deadline is treated as a breach and escalated, never allowed to lapse silently.",
    "claim_rules":
        "No superlative, guarantee, outcome or comparative claim is made without evidence "
        "held on file and dated. Testimonials are real, attributed, unedited in substance "
        "and accompanied by any typicality qualifier. Endorsements disclose the material "
        "connection. Anything a regulator in regulator_guardrails restricts is not said at "
        "all.",
    "statutory_clock_calendar":
        "Statutory response windows run under statutory_clocks and are adjusted against "
        "working_calendar before any due date is published.",
    "platform_rules":
        "Each surface's own policy governs content, uniqueness, media, disclosure and "
        "volume. Where a push would breach one, the push is held and the conflict is "
        "surfaced; the platform's rule is never worked around, and no content is published "
        "from an account the customer does not own.",
    "verification_window":
        "A change is read back on the surface before it is called live: within 1 hour for "
        "an API-backed surface and within 72 hours for one that reviews submissions. A "
        "change still pending in the platform's own queue is reported as pending, never as "
        "live.",
    "media_consent_policy":
        "Written consent before an identifiable person, a customer's premises or their "
        "property is stored, re-used or shown, recorded against the asset with its date, "
        "scope and expiry. Consent for one use is not consent for another. Withdrawal "
        "removes the asset from every surface it reached.",
    "media_retention":
        "Originals are held per evidence_retention and derivatives no longer than the "
        "consent that permits them. Faces of non-consenting people, vehicle plates, "
        "documents and third-party property are redacted before any media leaves the "
        "record.",
    "risk_typologies":
        "Patterns and thresholds that raise a flag come from regulator_guardrails and the "
        "vertical overlay, and every flag cites the rule id that raised it. A flag is a "
        "flag: the unit never concludes that a typology is or is not made out.",
    "referral_route":
        "Flags go to the compliance contact in escalation_contacts inside one working day, "
        "and to the statutory route named in regulator_guardrails inside that route's own "
        "deadline. The unit refers; it does not decide.",
    "monitored_surfaces":
        "The surfaces in review_surface and messaging_channel for this market, plus any "
        "community or group named in the vertical overlay, checked hourly during a live "
        "comms window and daily otherwise.",
    "forecast_thresholds":
        "Work is held or re-sequenced rather than attempted when the feeds in the vertical "
        "overlay report conditions beyond their stated thresholds. Where no threshold is "
        "set for a condition, the unit holds and asks rather than proceeding.",
    "verification_standard":
        "Two independent factors before any account detail is discussed, at least one of "
        "which is not the channel the contact arrived on. A failed verification ends the "
        "disclosure, not the conversation.",
    "disclosure_handling_rules":
        "What may be asked and what must be recorded come from the vertical overlay; "
        "nothing about an identified individual is shared outside the people named in "
        "escalation_contacts, and special-category information is recorded once, minimally, "
        "and never repeated in an outbound message.",
    "presentation_windows":
        "The window to present or correct documents comes from the instrument or the lane "
        "in the vertical overlay; the unit runs the clock under statutory_clocks, states "
        "what accrues per day once missed, and names who bears it.",
    "consent_wording":
        "State who is collecting, for what purpose, on what basis under consent_basis, how "
        "long it is kept, and how to withdraw. Withdrawal must be as easy as giving it.",
    "travel_time_model":
        "Estimate from the routing provider in the vertical overlay with live traffic where "
        "available, then add a buffer: 15 minutes urban, 25 minutes where access, parking "
        "or site sign-in is involved, 40 minutes where a crossing, ferry or controlled "
        "access is on the route. Never publish an ETA tighter than the estimate.",
    "dispute_hold_rules":
        "A contested amount is held, not pursued, while the dispute is open, and the "
        "response deadlines come from scheme_rules. Collection activity on a held amount is "
        "a breach.",
    "claim_notification_windows":
        "Notification windows come from the policy or carrier contract in the vertical "
        "overlay. The unit notifies at the earliest point the facts are known, states what "
        "is not yet known rather than waiting for it, and never lets a window pass "
        "unnotified because the file is incomplete.",
    "protocol_clock":
        "Every signal class starts its clock on detection, not on triage, and carries the "
        "deadline set in the vertical overlay. The clock is never restarted by an internal "
        "handover.",
    "settlement_calendar":
        "Settlement cycles and cut-offs come from the payment_rails in use and the vertical "
        "overlay. A break is closed by the next cut-off after it is raised, or escalated.",
    "breach_notification_rules":
        "Thresholds, recipients and clocks come from regulator_guardrails for this market. "
        "The unit assembles the notification and starts the clock; whether to notify is a "
        "human decision, and the unit escalates it immediately rather than assessing it.",
    "claim_rule_set":
        "Entitlement rules come from the policy, scheme or statute named in the vertical "
        "overlay, cited with their version. The unit computes the position those rules "
        "produce and never states the outcome.",
    "verification_standards":
        "Identity, address, ownership, control and source of funds are proven to the "
        "standard in regulator_guardrails before a relationship opens, with the accepted "
        "document classes and their validity taken from document_validity_rules.",
    "rule_book":
        "The rule set an item is tested against comes from regulator_guardrails or the "
        "vertical overlay, cited with its version and effective date. An untested item is "
        "reported as untested, never as passing.",
    "consent_forms":
        "Permission wording, its version history, its validity period and who is competent "
        "to give it come from the vertical overlay; where the subject cannot consent for "
        "themselves, the authorised person and the evidence of their authority are recorded "
        "before anything proceeds.",
    "estate_document_checklist":
        "The documents an estate or authorised representative must produce come from the "
        "vertical overlay for this market. Nothing is released, and no balance or detail is "
        "disclosed, until the authority is evidenced and a human has approved the release.",
    "disclosure_limits":
        "Each document type states only what the vertical overlay permits it to state. "
        "Where the record holds more than the document may show, the extra is withheld and "
        "the requester is told a fuller record exists and how to request it properly.",
    "certificate_regimes":
        "Which tests and certificates apply to each asset class, how often they fall due and "
        "who may issue them come from statutory_date_sets for this market and the vertical "
        "overlay. The unit tracks and reminds; it never certifies.",
    "reportable_event_criteria":
        "What counts as reportable comes from regulator_guardrails for this market. Where an "
        "event is arguably reportable, it is escalated as reportable and a human decides.",
    "reporting_deadlines":
        "Deadlines for each reportable event type come from regulator_guardrails and run "
        "under statutory_clocks. The clock starts at the moment of awareness.",
    "channel_switch_policy":
        "Offer a switch to the market's primary messaging_channel when the thread needs "
        "documents, a signature or continuity across days; carry the full context across; "
        "never start a new thread that loses history.",
    "aging_ladder":
        "Day 1 a neutral reminder, day 7 a restatement with the payment link, day 14 a "
        "notice of the contractual consequence, day 30 escalation to a human. Tone stays "
        "factual throughout. Any fee is the one in the published terms and is applied only "
        "where those terms allow it.",
    "working_time_rules":
        "Maximum hours, minimum rest, breaks, staffing ratios, lone-working rules and the "
        "qualification each shift requires come from regulator_guardrails and the vertical "
        "overlay. A roster that breaches one is not published; it is escalated.",
    "exit_policy":
        "Notice periods, final billing, returns and data handling on exit come from the "
        "contract in the vertical overlay. Data is returned in a portable format before it "
        "is deleted, and deletion is confirmed in writing.",
    "notice_service_rules":
        "Form, channel and minimum period come from the contract or statute in the vertical "
        "overlay; service is proved by delivery evidence retained under evidence_retention, "
        "and the period runs under statutory_clocks.",
    "filing_obligations":
        "Which returns are owed, to which office and on what frequency come from "
        "tax_filing_calendar for this market and the vertical overlay. The unit tracks and "
        "prepares; a human files.",
    "identity_keys":
        "Match on the national identifier where the market has one, then on normalised "
        "email, then on E.164 phone, then on normalised name plus date of birth plus "
        "postcode. Exact on identifiers, normalised on contact fields, fuzzy only on name, "
        "and never fuzzy alone.",
    "review_surfaces":
        "The surfaces listed in review_surface for this market, in the order given there.",
    "chase_ladder":
        "Three automated touches at 3, 7 and 14 days, each restating the amount, the reason "
        "and the route to dispute it, then a human. Automated chasing stops entirely once a "
        "dispute is raised or hardship is disclosed.",
    "call_recording_policy":
        "Announce recording before it starts, in the languages in language_set, and state "
        "the purpose and retention. Whether one-party or all-party consent applies comes "
        "from regulator_guardrails for this market; where a caller refuses, the call "
        "continues unrecorded or is transferred, and the refusal is logged.",
    "voice_disclosure":
        "State that the caller is speaking to an automated assistant in the first turn, "
        "before anything is collected, in the languages in language_set, and offer a route "
        "to a person at any point.",
    "recording_retention":
        "Audio and transcripts are held per evidence_retention, with payment details and "
        "special-category content redacted before storage. An erasure request is actioned "
        "against both the audio and the transcript.",
    "signature_requirements":
        "Signer identity, signing order, witnessing, cooling-off notices and the copies each "
        "party receives come from the contract type in the vertical overlay and from "
        "regulator_guardrails. An unsigned or out-of-order document is not treated as "
        "executed.",
    "pay_rules":
        "Rates, premiums, statutory additions and deductions and the order they are "
        "calculated in come from the vertical overlay and regulator_guardrails for this "
        "market. The unit computes and presents; a human approves before anything is paid.",
    "statutory_limits":
        "Ratios, duty hours, rest periods and qualification requirements come from "
        "regulator_guardrails and the vertical overlay. A breach is surfaced immediately, "
        "not averaged away across a period.",
    "authorisation_types":
        "Which permissions an activity requires, the authority for each, the documents each "
        "application needs and the statutory response time come from the vertical overlay "
        "and statutory_date_sets for this market.",
    "employment_advertising_rules":
        "Pay transparency, protected characteristics, statutory notices and right-to-work "
        "wording come from regulator_guardrails for this market. No advert states or implies "
        "a preference on a protected characteristic, and no advert is published without the "
        "statutory notices that market requires.",
    "client_money_rules":
        "Money held for another party is held separately, never used for the business's own "
        "purposes, and reconciled at the frequency regulator_guardrails mandates for this "
        "market. A shortfall is escalated the same day.",
    "same_day_clock":
        "A break is surfaced to the owner inside four working hours of detection, and "
        "immediately to the out-of-hours contact in escalation_contacts where it opens "
        "outside working_calendar hours.",
    "notifiable_breach_route":
        "Which breaches are reportable, to which body and inside what deadline come from "
        "regulator_guardrails for this market. The unit assembles and escalates; a human "
        "decides and reports.",
    "media_consent":
        "Written consent before an identifiable person appears in any asset, held against "
        "the asset with its scope and expiry, per media_consent_policy.",
    "reporting_period_rules":
        "The as-at date, reporting period, required tables and mandated disclosures come "
        "from regulator_guardrails and the vertical overlay, with each figure carrying its "
        "basis of preparation and its source system.",
    "synthetic_media_disclosure":
        "Generated imagery, video and voice are labelled as generated wherever they are "
        "published, in the languages in language_set. Where a market or a surface requires "
        "specific wording it comes from regulator_guardrails and platform_rules; where "
        "neither specifies, the label is still applied.",
    "data_sharing_consent":
        "A record is shared with an advertising platform only where consent_basis permits it "
        "for that purpose, and never where a suppression or objection flag is set. The "
        "suppression state overrides every other signal on the record.",
    "financing_providers":
        "Providers, their products, eligibility rules and the agreed commission come from "
        "the business record. The unit presents offers and discloses the commercial "
        "relationship per referral_disclosure; it never recommends one, and never states "
        "eligibility.",
    "referral_disclosure":
        "The commercial relationship and any commission are disclosed alongside the offer, "
        "before the customer acts on it, in the languages in language_set and to the "
        "standard regulator_guardrails sets for this market.",
    "confidentiality_rules":
        "Nothing about a named individual is confirmed or disclosed in public, including "
        "whether they are a customer. Public replies move to a private channel before any "
        "detail is discussed.",
    "caller_authentication":
        "A calling agent is identified by a credential issued to it, rate-limited per "
        "credential, revocable without a deploy, and recorded on every call. An "
        "unauthenticated caller sees published information only: never availability against "
        "a named person, never a price outside the published price book, and never anything "
        "about an identified customer.",
    "rail_link_format":
        "Deep links are built for the primary channel in messaging_channel for this market, "
        "prefilled with the business identifier and the thread reference, with a web fallback "
        "for any device that cannot open the rail.",
    "directory_set":
        "The directories and aggregators in attach_to_platforms for this market, with the "
        "primary listing feeding the rest so name, address and phone are corrected once.",
    "portfolio_consent_scope":
        "Consent before a customer's job, premises or likeness is shown, recorded per "
        "media_consent_policy with its scope and expiry. Withdrawal removes the asset from "
        "every surface it reached and is confirmed back to the customer.",
}


def working_calendar(code: str, weekend: list[str], timezone: str) -> str:
    return (
        f"Working days are Monday to Friday with a {'/'.join(weekend)} weekend. "
        f"Time zone {timezone}. Public holidays for {code} come from the holiday "
        "calendar on the business record and are treated as non-working days. Quiet "
        "hours are those outside contactable_hours. Every due date and every send is "
        "adjusted against this calendar before it is published or scheduled."
    )

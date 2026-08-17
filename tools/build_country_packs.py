#!/usr/bin/env python3
"""Emit the country packs under ``packs/countries/``.

A country pack is the whole of the platform's market knowledge. The standing
rule is that vertical and country differences resolve to configuration, so a
pack is the only place a market-specific fact is allowed to live: no engine and
no unit spec may hard-code a language, a channel, a review surface, a payment
rail, a statutory date set or a regulator.

The table below is the source; the YAML files are generated so every pack has
the same shape and a missing key is a build error rather than a runtime surprise.
Each field corresponds to a row of the workbook's Localization sheet.

    python tools/build_country_packs.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required: pip install pyyaml")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pack_data  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "packs" / "countries"

#: Fields every pack must define. Mirrors catalogue/localization.yaml.
REQUIRED_FIELDS = (
    "language_set",
    "messaging_channel",
    "review_surface",
    "attach_to_platforms",
    "payment_rails",
    "tax_filing_calendar",
    "statutory_date_sets",
    "regulator_guardrails",
    "seasonal_calendar",
)

# Regulator sets shared by several markets, named once so they stay consistent.
_EU_FINANCIAL = "Financial promotions: ESMA + national regulator"
_GDPR = "Data protection: GDPR"

PACKS: dict[str, dict[str, Any]] = {
    "US": {
        "name": "United States",
        "language_set": ["en-US", "es-US"],
        "messaging_channel": ["SMS/RCS", "iMessage", "WhatsApp"],
        "review_surface": ["Google", "Yelp", "BBB"],
        "attach_to_platforms": ["Angi", "Thumbtack", "Zocdoc", "OpenTable", "Booksy", "Zillow"],
        "payment_rails": ["Cards", "ACH", "Apple Pay", "Google Pay"],
        "tax_filing_calendar": ["State sales tax", "Federal income tax (Apr 15)", "Quarterly estimated tax"],
        "statutory_date_sets": ["Smog check (CA)", "State vehicle inspection", "Contractor licence renewal"],
        "regulator_guardrails": [
            "Health: HIPAA",
            "Legal advertising per state bar",
            "Financial promotions: SEC/FINRA",
            "TCPA consent for SMS and calls",
            "FTC endorsement and testimonial rules",
        ],
        "seasonal_calendar": ["Black Friday", "Thanksgiving", "Tax season", "Summer AC peak", "Winter heating peak"],
        "settings": {"date_format": "MM/DD/YYYY", "currency": "USD", "week_starts": "sunday", "measurement": "imperial"},
    },
    "CA": {
        "name": "Canada",
        "language_set": ["en-CA", "fr-CA"],
        "messaging_channel": ["SMS/RCS", "iMessage", "WhatsApp"],
        "review_surface": ["Google", "Yelp", "HomeStars"],
        "attach_to_platforms": ["HomeStars", "OpenTable", "Booksy", "Realtor.ca"],
        "payment_rails": ["Cards", "Interac e-Transfer", "PAD"],
        "tax_filing_calendar": ["GST/HST", "Corporate tax", "Provincial sales tax"],
        "statutory_date_sets": ["Provincial vehicle inspection", "Trade licence renewal"],
        "regulator_guardrails": [
            "Health: provincial colleges + PHIPA/PIPEDA",
            "Legal advertising per provincial law society",
            "Financial promotions: CIRO",
            "CASL consent for electronic messages",
            "Bilingual obligations in Quebec (Bill 96)",
        ],
        "seasonal_calendar": ["Black Friday", "Victoria Day", "Winter heating peak", "Tax season"],
        "settings": {"date_format": "YYYY-MM-DD", "currency": "CAD", "week_starts": "sunday", "measurement": "metric"},
    },
    "UK": {
        "name": "United Kingdom",
        "language_set": ["en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Trustpilot", "Checkatrade"],
        "attach_to_platforms": ["Checkatrade", "Rightmove", "OpenTable", "Fresha", "Treatwell"],
        "payment_rails": ["Cards", "FPS", "Direct Debit (Bacs)", "Open Banking"],
        "tax_filing_calendar": ["VAT quarterly", "Corporation tax", "Self assessment (31 Jan)", "PAYE RTI"],
        "statutory_date_sets": ["Gas Safety certificate", "EPC", "EICR", "MOT", "PAT testing"],
        "regulator_guardrails": [
            "Health: CQC/GMC/GDC",
            "Legal advertising per SRA",
            "Financial promotions: FCA",
            "PECR/UK GDPR consent for marketing",
            "ASA/CAP advertising code",
        ],
        "seasonal_calendar": ["Black Friday", "Bank holidays", "Winter heating peak", "Tax year end (5 Apr)"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "GBP", "week_starts": "monday", "measurement": "metric"},
    },
    "IE": {
        "name": "Ireland",
        "language_set": ["en-IE", "ga-IE"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Trustpilot"],
        "attach_to_platforms": ["Daft.ie", "OpenTable", "Fresha"],
        "payment_rails": ["Cards", "SEPA", "Revolut"],
        "tax_filing_calendar": ["VAT bi-monthly", "Corporation tax", "Income tax (31 Oct)"],
        "statutory_date_sets": ["NCT vehicle test", "BER certificate", "Gas safety"],
        "regulator_guardrails": ["Health: HIQA/Medical Council", "Legal advertising per Law Society", _EU_FINANCIAL, _GDPR],
        "seasonal_calendar": ["Black Friday", "Bank holidays", "Winter heating peak"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "EUR", "week_starts": "monday", "measurement": "metric"},
    },
    "DE": {
        "name": "Germany",
        "language_set": ["de-DE", "tr-DE", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Trustpilot", "ProvenExpert"],
        "attach_to_platforms": ["Doctolib", "Treatwell", "ImmobilienScout24", "OpenTable"],
        "payment_rails": ["SEPA", "Cards", "PayPal", "Klarna"],
        "tax_filing_calendar": ["Umsatzsteuer-Voranmeldung", "Körperschaftsteuer", "Gewerbesteuer"],
        "statutory_date_sets": ["TÜV/HU vehicle inspection", "Schornsteinfeger inspection", "Energieausweis"],
        "regulator_guardrails": [
            "Health: statutory funds + Heilmittelwerbegesetz (HWG)",
            "Legal advertising per BRAO",
            _EU_FINANCIAL,
            _GDPR,
            "UWG unfair-competition rules on advertising",
        ],
        "seasonal_calendar": ["Black Friday", "Weihnachtsmarkt", "Winter heating peak", "Summer holidays"],
        "settings": {"date_format": "DD.MM.YYYY", "currency": "EUR", "week_starts": "monday", "measurement": "metric"},
    },
    "FR": {
        "name": "France",
        "language_set": ["fr-FR", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Trustpilot", "PagesJaunes"],
        "attach_to_platforms": ["Doctolib", "TheFork", "Planity", "SeLoger"],
        "payment_rails": ["SEPA", "Cards", "Carte Bancaire"],
        "tax_filing_calendar": ["TVA", "Impôt sur les sociétés", "URSSAF"],
        "statutory_date_sets": ["Contrôle technique", "DPE energy diagnostic", "Gas installation check"],
        "regulator_guardrails": ["Health: HAS/Ordre des médecins", "Legal advertising per CNB", _EU_FINANCIAL, _GDPR],
        "seasonal_calendar": ["Black Friday", "Soldes", "August holidays", "Winter heating peak"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "EUR", "week_starts": "monday", "measurement": "metric"},
    },
    "ES": {
        "name": "Spain",
        "language_set": ["es-ES", "ca-ES", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Trustpilot"],
        "attach_to_platforms": ["TheFork", "Treatwell", "Idealista"],
        "payment_rails": ["SEPA", "Cards", "Bizum"],
        "tax_filing_calendar": ["IVA quarterly", "Impuesto de Sociedades", "IRPF"],
        "statutory_date_sets": ["ITV vehicle inspection", "Certificado energético", "Gas inspection"],
        "regulator_guardrails": ["Health: Consejo General de Colegios", "Legal advertising per bar", _EU_FINANCIAL, _GDPR],
        "seasonal_calendar": ["Black Friday", "Rebajas", "August holidays", "Summer AC peak"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "EUR", "week_starts": "monday", "measurement": "metric"},
    },
    "IT": {
        "name": "Italy",
        "language_set": ["it-IT", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Trustpilot", "TripAdvisor"],
        "attach_to_platforms": ["TheFork", "Treatwell", "Immobiliare.it"],
        "payment_rails": ["SEPA", "Cards", "Satispay"],
        "tax_filing_calendar": ["IVA", "IRES", "Fattura elettronica (SdI)"],
        "statutory_date_sets": ["Revisione vehicle inspection", "APE energy certificate", "Boiler check"],
        "regulator_guardrails": ["Health: Ordine dei Medici", "Legal advertising per CNF", _EU_FINANCIAL, _GDPR],
        "seasonal_calendar": ["Black Friday", "Ferragosto", "Winter heating peak"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "EUR", "week_starts": "monday", "measurement": "metric"},
    },
    "NL": {
        "name": "Netherlands",
        "language_set": ["nl-NL", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Trustpilot", "Klantenvertellen"],
        "attach_to_platforms": ["Treatwell", "Funda", "TheFork"],
        "payment_rails": ["iDEAL", "SEPA", "Cards"],
        "tax_filing_calendar": ["BTW quarterly", "Vennootschapsbelasting"],
        "statutory_date_sets": ["APK vehicle inspection", "Energielabel", "Gas installation check"],
        "regulator_guardrails": ["Health: IGJ/BIG register", "Legal advertising per NOvA", _EU_FINANCIAL, _GDPR],
        "seasonal_calendar": ["Black Friday", "Sinterklaas", "Winter heating peak"],
        "settings": {"date_format": "DD-MM-YYYY", "currency": "EUR", "week_starts": "monday", "measurement": "metric"},
    },
    "PL": {
        "name": "Poland",
        "language_set": ["pl-PL", "en-GB", "uk-UA"],
        "messaging_channel": ["WhatsApp", "SMS", "Messenger"],
        "review_surface": ["Google", "Trustpilot"],
        "attach_to_platforms": ["Booksy", "Otodom", "ZnanyLekarz"],
        "payment_rails": ["BLIK", "SEPA", "Cards", "Przelewy24"],
        "tax_filing_calendar": ["VAT JPK", "CIT", "ZUS contributions"],
        "statutory_date_sets": ["Vehicle technical inspection", "Chimney and gas inspection", "Energy certificate"],
        "regulator_guardrails": ["Health: NFZ + medical chamber", "Legal advertising per bar", _EU_FINANCIAL, _GDPR],
        "seasonal_calendar": ["Black Friday", "Christmas", "Winter heating peak"],
        "settings": {"date_format": "DD.MM.YYYY", "currency": "PLN", "week_starts": "monday", "measurement": "metric"},
    },
    "AE": {
        "name": "United Arab Emirates",
        "language_set": ["en-AE", "ar-AE", "hi-IN", "ur-PK"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Talabat", "Zomato"],
        "attach_to_platforms": ["Bayut", "Property Finder", "Fresha", "Zomato"],
        "payment_rails": ["Cards", "Apple Pay", "Tabby", "Bank transfer"],
        "tax_filing_calendar": ["VAT quarterly", "Corporate tax", "ESR filing"],
        "statutory_date_sets": ["Ejari registration", "RERA renewals", "RTA vehicle registration and test", "Trade licence renewal"],
        "regulator_guardrails": [
            "Health: DHA/DOH/MOHAP advertising permits",
            "Legal advertising per emirate",
            "Financial promotions: SCA/DFSA",
            "Advertising: NMC permit for health claims",
        ],
        "seasonal_calendar": ["Ramadan", "Eid al-Fitr", "Eid al-Adha", "Summer AC peak", "DSF shopping festival"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "AED", "week_starts": "monday", "weekend": ["saturday", "sunday"], "measurement": "metric"},
    },
    "SA": {
        "name": "Saudi Arabia",
        "language_set": ["ar-SA", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Jahez", "HungerStation"],
        "attach_to_platforms": ["Aqar", "Jahez", "Fresha"],
        "payment_rails": ["mada", "Cards", "Apple Pay", "Tamara"],
        "tax_filing_calendar": ["VAT monthly", "Zakat", "e-invoicing (FATOORA)"],
        "statutory_date_sets": ["MVPI vehicle inspection", "Ejar tenancy registration", "Commercial registration renewal"],
        "regulator_guardrails": ["Health: MOH/SFDA advertising rules", "Financial promotions: CMA/SAMA", "PDPL data protection"],
        "seasonal_calendar": ["Ramadan", "Eid al-Fitr", "Eid al-Adha", "Summer AC peak", "National Day"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "SAR", "week_starts": "sunday", "weekend": ["friday", "saturday"], "measurement": "metric"},
    },
    "IN": {
        "name": "India",
        "language_set": ["en-IN", "hi-IN", "ta-IN", "te-IN", "mr-IN", "bn-IN"],
        "messaging_channel": ["WhatsApp", "SMS", "RCS"],
        "review_surface": ["Google", "JustDial", "Practo"],
        "attach_to_platforms": ["Practo", "99acres", "MagicBricks", "Zomato", "UrbanClap"],
        "payment_rails": ["UPI", "Cards", "NetBanking", "Wallets"],
        "tax_filing_calendar": ["GSTR-1 and GSTR-3B monthly", "TDS quarterly", "Income tax (31 Jul)"],
        "statutory_date_sets": ["Vehicle PUC certificate", "Fitness certificate", "Shops and Establishments renewal"],
        "regulator_guardrails": [
            "Health: NMC advertising rules + Drugs and Magic Remedies Act",
            "Legal advertising per Bar Council of India (advertising restricted)",
            "Financial promotions: SEBI/RBI",
            "TRAI DLT registration for SMS",
            "DPDP Act consent",
        ],
        "seasonal_calendar": ["Diwali", "Holi", "Monsoon", "Wedding season", "Financial year end (31 Mar)"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "INR", "week_starts": "monday", "measurement": "metric"},
    },
    "BR": {
        "name": "Brazil",
        "language_set": ["pt-BR"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Reclame Aqui", "TripAdvisor"],
        "attach_to_platforms": ["iFood", "QuintoAndar", "Booksy"],
        "payment_rails": ["Pix", "Cards", "Boleto"],
        "tax_filing_calendar": ["Simples Nacional", "ICMS", "NF-e issuance"],
        "statutory_date_sets": ["Vehicle licensing (IPVA)", "AVCB fire certificate", "CREA/CAU registration"],
        "regulator_guardrails": ["Health: CFM/ANVISA advertising rules", "Legal advertising per OAB", "Financial promotions: CVM", "LGPD consent"],
        "seasonal_calendar": ["Carnaval", "Black Friday", "Festa Junina", "Christmas", "Summer (Dec-Feb)"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "BRL", "week_starts": "sunday", "measurement": "metric"},
    },
    "MX": {
        "name": "Mexico",
        "language_set": ["es-MX"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "TripAdvisor"],
        "attach_to_platforms": ["Rappi", "Inmuebles24", "Booksy"],
        "payment_rails": ["SPEI", "Cards", "OXXO cash"],
        "tax_filing_calendar": ["IVA monthly", "ISR", "CFDI e-invoicing"],
        "statutory_date_sets": ["Verificación vehicular", "Tenencia", "Licencia de funcionamiento"],
        "regulator_guardrails": ["Health: COFEPRIS advertising permits", "Financial promotions: CNBV", "LFPDPPP data protection"],
        "seasonal_calendar": ["Día de Muertos", "Buen Fin", "Semana Santa", "Christmas"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "MXN", "week_starts": "monday", "measurement": "metric"},
    },
    "JP": {
        "name": "Japan",
        "language_set": ["ja-JP", "en-GB"],
        "messaging_channel": ["LINE", "SMS"],
        "review_surface": ["Google", "Tabelog", "Hot Pepper"],
        "attach_to_platforms": ["Hot Pepper Beauty", "Tabelog", "SUUMO"],
        "payment_rails": ["Cards", "PayPay", "Konbini", "Bank transfer"],
        "tax_filing_calendar": ["Consumption tax", "Corporate tax", "Qualified invoice system"],
        "statutory_date_sets": ["Shaken vehicle inspection", "Fire equipment inspection", "Building inspection"],
        "regulator_guardrails": [
            "Health: Medical Care Act advertising restrictions",
            "Financial promotions: FSA",
            "APPI data protection",
            "Pharmaceutical and Medical Device Act (Yakukihou) claims",
        ],
        "seasonal_calendar": ["Golden Week", "Obon", "New Year (Shogatsu)", "Cherry blossom", "Summer AC peak"],
        "settings": {"date_format": "YYYY/MM/DD", "currency": "JPY", "week_starts": "sunday", "measurement": "metric"},
    },
    "KR": {
        "name": "South Korea",
        "language_set": ["ko-KR", "en-GB"],
        "messaging_channel": ["KakaoTalk", "SMS"],
        "review_surface": ["Google", "Naver Place", "Kakao Map"],
        "attach_to_platforms": ["Naver Booking", "Baemin", "Zigbang"],
        "payment_rails": ["Cards", "KakaoPay", "Naver Pay", "Bank transfer"],
        "tax_filing_calendar": ["VAT semi-annual", "Corporate tax", "e-Tax invoice"],
        "statutory_date_sets": ["Vehicle inspection", "Fire safety inspection", "Business registration renewal"],
        "regulator_guardrails": ["Health: MFDS advertising review", "Financial promotions: FSC", "PIPA data protection"],
        "seasonal_calendar": ["Seollal", "Chuseok", "Lunar New Year", "Summer AC peak"],
        "settings": {"date_format": "YYYY-MM-DD", "currency": "KRW", "week_starts": "sunday", "measurement": "metric"},
    },
    "CN": {
        "name": "China",
        "language_set": ["zh-CN", "en-GB"],
        "messaging_channel": ["WeChat", "SMS"],
        "review_surface": ["Dianping", "Meituan", "Xiaohongshu"],
        "attach_to_platforms": ["Meituan", "Dianping", "Ke.com"],
        "payment_rails": ["WeChat Pay", "Alipay", "UnionPay"],
        "tax_filing_calendar": ["VAT monthly", "Corporate income tax", "Fapiao issuance"],
        "statutory_date_sets": ["Vehicle annual inspection", "Fire safety inspection", "Business licence renewal"],
        "regulator_guardrails": ["Health: NMPA advertising review", "Advertising Law claim restrictions", "PIPL data protection"],
        "seasonal_calendar": ["Lunar New Year", "Golden Week", "Singles Day (11.11)", "Mid-Autumn Festival"],
        "settings": {"date_format": "YYYY-MM-DD", "currency": "CNY", "week_starts": "monday", "measurement": "metric"},
    },
    "SG": {
        "name": "Singapore",
        "language_set": ["en-SG", "zh-CN", "ms-MY", "ta-IN"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Facebook", "Carousell"],
        "attach_to_platforms": ["Chope", "PropertyGuru", "Fresha"],
        "payment_rails": ["PayNow", "Cards", "GrabPay"],
        "tax_filing_calendar": ["GST quarterly", "Corporate tax (ECI)", "CPF contributions"],
        "statutory_date_sets": ["Vehicle inspection", "Fire safety certificate", "Licence renewals"],
        "regulator_guardrails": ["Health: MOH/HSA advertising rules", "Financial promotions: MAS", "PDPA + DNC registry"],
        "seasonal_calendar": ["Lunar New Year", "Hari Raya", "Deepavali", "Great Singapore Sale"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "SGD", "week_starts": "monday", "measurement": "metric"},
    },
    "AU": {
        "name": "Australia",
        "language_set": ["en-AU"],
        "messaging_channel": ["SMS", "WhatsApp"],
        "review_surface": ["Google", "ProductReview.com.au", "TripAdvisor"],
        "attach_to_platforms": ["hipages", "Domain", "OpenTable", "Fresha"],
        "payment_rails": ["Cards", "PayID/NPP", "BPAY"],
        "tax_filing_calendar": ["BAS quarterly", "Company tax", "Superannuation quarterly"],
        "statutory_date_sets": ["Vehicle rego inspection", "Smoke alarm compliance", "Trade licence renewal"],
        "regulator_guardrails": ["Health: AHPRA advertising rules", "Legal advertising per state", "Financial promotions: ASIC", "Spam Act consent"],
        "seasonal_calendar": ["Black Friday", "Christmas (summer)", "EOFY (30 Jun)", "Summer AC peak", "Bushfire season"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "AUD", "week_starts": "monday", "measurement": "metric"},
    },
    "NZ": {
        "name": "New Zealand",
        "language_set": ["en-NZ", "mi-NZ"],
        "messaging_channel": ["SMS", "WhatsApp"],
        "review_surface": ["Google", "TripAdvisor"],
        "attach_to_platforms": ["Trade Me", "Fresha", "OpenTable"],
        "payment_rails": ["Cards", "Bank transfer", "POLi"],
        "tax_filing_calendar": ["GST bi-monthly", "Income tax", "PAYE"],
        "statutory_date_sets": ["WOF vehicle inspection", "Building WOF", "Licence renewals"],
        "regulator_guardrails": ["Health: Medical Council + Medicines Act", "Financial promotions: FMA", "Privacy Act 2020"],
        "seasonal_calendar": ["Christmas (summer)", "EOFY (31 Mar)", "Winter heating peak"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "NZD", "week_starts": "monday", "measurement": "metric"},
    },
    "ZA": {
        "name": "South Africa",
        "language_set": ["en-ZA", "af-ZA", "zu-ZA"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "HelloPeter"],
        "attach_to_platforms": ["Property24", "Mr D", "Fresha"],
        "payment_rails": ["Cards", "EFT", "SnapScan", "PayShap"],
        "tax_filing_calendar": ["VAT bi-monthly", "Corporate tax", "PAYE monthly"],
        "statutory_date_sets": ["Vehicle roadworthy certificate", "COC electrical certificate", "Business licence renewal"],
        "regulator_guardrails": ["Health: HPCSA advertising rules", "Legal advertising per LPC", "Financial promotions: FSCA", "POPIA consent"],
        "seasonal_calendar": ["Black Friday", "December holidays", "Load-shedding season"],
        "settings": {"date_format": "YYYY/MM/DD", "currency": "ZAR", "week_starts": "monday", "measurement": "metric"},
    },
    "KE": {
        "name": "Kenya",
        "language_set": ["en-KE", "sw-KE"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Facebook"],
        "attach_to_platforms": ["Jumia", "BuyRentKenya", "Glovo"],
        "payment_rails": ["M-Pesa", "Cards", "Bank transfer"],
        "tax_filing_calendar": ["VAT monthly", "Corporate tax", "eTIMS invoicing"],
        "statutory_date_sets": ["Vehicle inspection", "Single business permit renewal", "Fire safety certificate"],
        "regulator_guardrails": ["Health: KMPDC advertising rules", "Financial promotions: CMA", "Data Protection Act 2019"],
        "seasonal_calendar": ["Long rains (Mar-May)", "Short rains (Oct-Dec)", "Christmas", "Back to school"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "KES", "week_starts": "monday", "measurement": "metric"},
    },
    "NG": {
        "name": "Nigeria",
        "language_set": ["en-NG", "yo-NG", "ha-NG", "ig-NG"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Facebook"],
        "attach_to_platforms": ["Jumia", "PropertyPro", "Chowdeck"],
        "payment_rails": ["Cards", "Bank transfer (NIP)", "USSD"],
        "tax_filing_calendar": ["VAT monthly", "Companies income tax", "PAYE monthly"],
        "statutory_date_sets": ["Vehicle roadworthiness", "Business premises permit", "Fire safety certificate"],
        "regulator_guardrails": ["Health: MDCN + NAFDAC advertising approval", "Financial promotions: SEC Nigeria", "NDPA data protection", "ARCON advertising approval"],
        "seasonal_calendar": ["Rainy season", "Harmattan", "Christmas", "Eid"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "NGN", "week_starts": "monday", "measurement": "metric"},
    },
    "TR": {
        "name": "Türkiye",
        "language_set": ["tr-TR", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Sikayetvar", "Yemeksepeti"],
        "attach_to_platforms": ["Yemeksepeti", "Sahibinden", "Fresha"],
        "payment_rails": ["Cards", "Havale/EFT", "Papara"],
        "tax_filing_calendar": ["KDV monthly", "Corporate tax", "e-Fatura"],
        "statutory_date_sets": ["TÜVTÜRK vehicle inspection", "Building earthquake compliance", "Business licence renewal"],
        "regulator_guardrails": ["Health: Ministry of Health advertising ban on medical claims", "Financial promotions: SPK", "KVKK data protection"],
        "seasonal_calendar": ["Ramadan", "Kurban Bayramı", "Summer AC peak", "Back to school"],
        "settings": {"date_format": "DD.MM.YYYY", "currency": "TRY", "week_starts": "monday", "measurement": "metric"},
    },
    "VN": {
        "name": "Vietnam",
        "language_set": ["vi-VN", "en-GB"],
        "messaging_channel": ["Zalo", "SMS"],
        "review_surface": ["Google", "Foody", "Facebook"],
        "attach_to_platforms": ["ShopeeFood", "Batdongsan", "Zalo OA"],
        "payment_rails": ["Bank transfer (napas)", "MoMo", "ZaloPay", "Cards"],
        "tax_filing_calendar": ["VAT monthly", "Corporate income tax", "e-invoice"],
        "statutory_date_sets": ["Vehicle inspection (đăng kiểm)", "Fire safety inspection", "Business licence renewal"],
        "regulator_guardrails": ["Health: MOH advertising approval", "Advertising Law claim restrictions", "PDPD data protection"],
        "seasonal_calendar": ["Tết (Lunar New Year)", "Mid-Autumn", "Rainy season", "Summer AC peak"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "VND", "week_starts": "monday", "measurement": "metric"},
    },
    "TH": {
        "name": "Thailand",
        "language_set": ["th-TH", "en-GB"],
        "messaging_channel": ["LINE", "SMS"],
        "review_surface": ["Google", "Wongnai", "Facebook"],
        "attach_to_platforms": ["LINE MAN", "DDproperty", "Agoda"],
        "payment_rails": ["PromptPay", "Cards", "TrueMoney"],
        "tax_filing_calendar": ["VAT monthly (PP30)", "Corporate income tax", "Withholding tax"],
        "statutory_date_sets": ["Vehicle inspection (ตรอ.)", "Fire safety inspection", "Business licence renewal"],
        "regulator_guardrails": ["Health: FDA Thailand advertising approval", "Financial promotions: SEC Thailand", "PDPA consent"],
        "seasonal_calendar": ["Songkran", "Loy Krathong", "Rainy season", "High season (Nov-Feb)"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "THB", "week_starts": "monday", "measurement": "metric"},
    },
    "ID": {
        "name": "Indonesia",
        "language_set": ["id-ID", "en-GB"],
        "messaging_channel": ["WhatsApp", "SMS"],
        "review_surface": ["Google", "Tokopedia", "Facebook"],
        "attach_to_platforms": ["GoFood", "Rumah123", "Traveloka"],
        "payment_rails": ["QRIS", "Bank transfer", "GoPay", "OVO", "Cards"],
        "tax_filing_calendar": ["PPN monthly", "Corporate income tax", "e-Faktur"],
        "statutory_date_sets": ["Vehicle inspection (KIR)", "Building permit (PBG)", "Business licence (NIB) renewal"],
        "regulator_guardrails": ["Health: BPOM advertising approval", "Financial promotions: OJK", "PDP Law consent"],
        "seasonal_calendar": ["Ramadan", "Idul Fitri", "Rainy season", "Harbolnas (12.12)"],
        "settings": {"date_format": "DD/MM/YYYY", "currency": "IDR", "week_starts": "monday", "measurement": "metric"},
    },
    "PH": {
        "name": "Philippines",
        "language_set": ["en-PH", "fil-PH"],
        "messaging_channel": ["SMS", "Messenger", "WhatsApp"],
        "review_surface": ["Google", "Facebook"],
        "attach_to_platforms": ["GrabFood", "Lamudi", "Agoda"],
        "payment_rails": ["GCash", "Maya", "InstaPay", "Cards"],
        "tax_filing_calendar": ["VAT quarterly", "Income tax", "BIR e-filing"],
        "statutory_date_sets": ["LTO vehicle registration", "Fire safety inspection certificate", "Mayor's permit renewal (Jan)"],
        "regulator_guardrails": ["Health: FDA Philippines advertising approval", "Financial promotions: SEC PH", "Data Privacy Act consent"],
        "seasonal_calendar": ["Christmas (Sep-Dec)", "Typhoon season", "Holy Week", "Undas"],
        "settings": {"date_format": "MM/DD/YYYY", "currency": "PHP", "week_starts": "sunday", "measurement": "metric"},
    },
}


def resolved_settings(code: str, pack: dict[str, Any]) -> dict[str, Any]:
    """Everything this market answers, beyond the nine Localization fields.

    Built as baseline-then-override so a key can never be silently absent: the
    defaults supply the platform's cross-market position, the per-market tables
    replace it where the jurisdiction differs, and the keys in
    ``REQUIRED_PER_MARKET`` have no baseline at all -- a market that fails to
    state one fails the build rather than shipping a plausible default. An
    emergency number is the case that forces this: a default emergency number is
    a wrong emergency number.
    """
    settings: dict[str, Any] = dict(pack_data.DEFAULTS)

    routing = pack_data.EMERGENCY_ROUTING.get(code)
    if routing is None:
        raise AssertionError(
            f"country pack {code} has no emergency_routing. This key has no default: "
            "state it for the market or remove the pack."
        )
    settings["emergency_routing"] = {
        **routing,
        "script": pack_data.EMERGENCY_SCRIPT,
        "absent_script": pack_data.EMERGENCY_ABSENT_SCRIPT,
    }

    weekend = pack.get("settings", {}).get("weekend", ["saturday", "sunday"])
    timezone = pack_data._TIMEZONE[code]
    settings["working_calendar"] = pack_data.working_calendar(code, weekend, timezone)
    settings["timezone"] = timezone
    settings["contactable_hours"] = pack_data._CONTACTABLE_HOURS[code]
    settings["consent_basis"] = pack_data._CONSENT_BASIS[code]
    settings["tax_display_rules"] = pack_data._TAX_DISPLAY[code]
    settings["statutory_clocks"] = pack_data._STATUTORY_CLOCKS.get(
        code, pack_data._STATUTORY_CLOCKS_DEFAULT
    )

    settings.update(pack.get("settings", {}))
    return settings


def build() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for code, pack in PACKS.items():
        missing = [f for f in REQUIRED_FIELDS if f not in pack]
        if missing:
            raise AssertionError(f"country pack {code} is missing: {missing}")
        settings = resolved_settings(code, pack)
        absent = [k for k in pack_data.REQUIRED_PER_MARKET if k not in settings]
        if absent:
            raise AssertionError(f"country pack {code} is missing per-market keys: {absent}")
        document = {
            "code": code,
            "name": pack["name"],
            **{field: pack[field] for field in REQUIRED_FIELDS},
            "settings": settings,
        }
        path = OUT_DIR / f"{code.lower()}.yaml"
        with path.open("w", encoding="utf-8") as handle:
            handle.write(
                f"# Country pack: {pack['name']} ({code})\n"
                "# Generated by tools/build_country_packs.py -- edit the table there, not this file.\n"
                "# Every market-specific fact the platform knows lives here. No engine and no unit\n"
                "# spec may hard-code any of it.\n"
            )
            yaml.safe_dump(
                document, handle, sort_keys=False, allow_unicode=True, default_flow_style=False, width=100
            )
        written.append(code)
    print(f"wrote {len(written)} country packs to {OUT_DIR}")
    print("  " + " ".join(sorted(written)))
    print(f"  keys answered per pack: {len(REQUIRED_FIELDS) + len(resolved_settings('US', PACKS['US']))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())

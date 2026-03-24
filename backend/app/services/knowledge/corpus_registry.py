"""Authoritative registry of Church documents available for ingestion.

Every entry in CORPUS_REGISTRY describes a single magisterial document,
council constitution, encyclical, patristic text, or scripture corpus.

The registry is the single source of truth for:
  - Which documents the knowledge base contains
  - Their canonical metadata (title, author, year, type, language)
  - Where to fetch them (vatican.va, bible APIs, local files)
  - Which Qdrant collection stores their chunks
  - Theological tagging for precision retrieval

Qdrant collection layout
------------------------
  biblia_pl        — Polish Bible (Biblia Gdańska / Tysiąclecia)
  biblia_la        — Latin Vulgate (Clementine)
  biblia_en        — English Douay-Rheims
  katechizm        — Catechism of the Catholic Church (CCC) — all 2865 §§
  sobory           — Vatican I + Vatican II constitutions/decrees/declarations
  magisterium      — Papal encyclicals + apostolic exhortations (Leo XIII → Francis)
  patrystyka       — Church Fathers + Saints' writings
  liturgia         — Liturgical texts (Roman Rite prayers, prefaces, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class DocumentType(str, Enum):
    # Scripture
    BIBLE = "bible"
    # Councils
    DOGMATIC_CONSTITUTION = "dogmatic_constitution"
    PASTORAL_CONSTITUTION = "pastoral_constitution"
    DECREE = "decree"
    DECLARATION = "declaration"
    # Papal
    ENCYCLICAL = "encyclical"
    APOSTOLIC_EXHORTATION = "apostolic_exhortation"
    APOSTOLIC_CONSTITUTION = "apostolic_constitution"
    APOSTOLIC_LETTER = "apostolic_letter"
    # Catechism
    CATECHISM = "catechism"
    # Patristic
    PATRISTIC = "patristic"
    LITURGICAL = "liturgical"


class QdrantCollection(str, Enum):
    BIBLIA_PL = "biblia_pl"
    BIBLIA_LA = "biblia_la"
    BIBLIA_EN = "biblia_en"
    KATECHIZM = "katechizm"
    SOBORY = "sobory"
    MAGISTERIUM = "magisterium"
    PATRYSTYKA = "patrystyka"
    LITURGIA = "liturgia"


ChunkStrategy = Literal["verse", "paragraph", "section", "sliding_window"]


@dataclass
class CorpusDocument:
    doc_id: str                          # unique slug, e.g. "lumen-gentium"
    title: str                           # original title
    title_pl: str                        # Polish title
    doc_type: DocumentType
    collection: QdrantCollection
    author: str                          # pope name, council, or Father
    year: int
    language: str = "la"                 # primary language of canonical text
    chunk_strategy: ChunkStrategy = "paragraph"
    theology_tags: list[str] = field(default_factory=list)
    tradition_tags: list[str] = field(default_factory=list)
    fetch_url: str = ""                  # canonical source URL
    local_file: str = ""                 # relative path under data/corpus/
    description: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# BIBLE
# ─────────────────────────────────────────────────────────────────────────────

BIBLE_BOOKS_OT = [
    ("Rdz", "Genesis"), ("Wj", "Exodus"), ("Kpł", "Leviticus"), ("Lb", "Numbers"),
    ("Pwt", "Deuteronomy"), ("Joz", "Joshua"), ("Sdz", "Judges"), ("Rt", "Ruth"),
    ("1Sm", "1 Samuel"), ("2Sm", "2 Samuel"), ("1Krl", "1 Kings"), ("2Krl", "2 Kings"),
    ("1Krn", "1 Chronicles"), ("2Krn", "2 Chronicles"), ("Ezd", "Ezra"),
    ("Ne", "Nehemiah"), ("Tb", "Tobit"), ("Jdt", "Judith"), ("Est", "Esther"),
    ("1Mch", "1 Maccabees"), ("2Mch", "2 Maccabees"), ("Hi", "Job"),
    ("Ps", "Psalms"), ("Prz", "Proverbs"), ("Koh", "Ecclesiastes"), ("Pnp", "Song of Songs"),
    ("Mdr", "Wisdom"), ("Syr", "Sirach"), ("Iz", "Isaiah"), ("Jr", "Jeremiah"),
    ("Lm", "Lamentations"), ("Ba", "Baruch"), ("Ez", "Ezekiel"), ("Dn", "Daniel"),
    ("Oz", "Hosea"), ("Jl", "Joel"), ("Am", "Amos"), ("Ab", "Obadiah"),
    ("Jon", "Jonah"), ("Mi", "Micah"), ("Na", "Nahum"), ("Ha", "Habakkuk"),
    ("So", "Zephaniah"), ("Ag", "Haggai"), ("Za", "Zechariah"), ("Ml", "Malachi"),
]

BIBLE_BOOKS_NT = [
    ("Mt", "Matthew"), ("Mk", "Mark"), ("Łk", "Luke"), ("J", "John"),
    ("Dz", "Acts"), ("Rz", "Romans"), ("1Kor", "1 Corinthians"), ("2Kor", "2 Corinthians"),
    ("Ga", "Galatians"), ("Ef", "Ephesians"), ("Flp", "Philippians"), ("Kol", "Colossians"),
    ("1Tes", "1 Thessalonians"), ("2Tes", "2 Thessalonians"), ("1Tm", "1 Timothy"),
    ("2Tm", "2 Timothy"), ("Tt", "Titus"), ("Flm", "Philemon"), ("Hbr", "Hebrews"),
    ("Jk", "James"), ("1P", "1 Peter"), ("2P", "2 Peter"), ("1J", "1 John"),
    ("2J", "2 John"), ("3J", "3 John"), ("Jud", "Jude"), ("Ap", "Revelation"),
]

BIBLE_TRANSLATIONS = {
    "BG":  {"language": "pl", "name": "Biblia Gdańska (1632)",          "collection": QdrantCollection.BIBLIA_PL,  "public_domain": True},
    "BT5": {"language": "pl", "name": "Biblia Tysiąclecia V",            "collection": QdrantCollection.BIBLIA_PL,  "public_domain": False},
    "VUL": {"language": "la", "name": "Wulgata Klemensa VIII (1592)",    "collection": QdrantCollection.BIBLIA_LA,  "public_domain": True},
    "DRB": {"language": "en", "name": "Douay-Rheims Bible (1899)",       "collection": QdrantCollection.BIBLIA_EN,  "public_domain": True},
    "GNT": {"language": "el", "name": "Greek New Testament (NA28)",       "collection": QdrantCollection.BIBLIA_LA,  "public_domain": True},
    "BHQ": {"language": "he", "name": "Hebrew Bible (Biblia Hebraica)",   "collection": QdrantCollection.BIBLIA_LA,  "public_domain": True},
}


# ─────────────────────────────────────────────────────────────────────────────
# CATECHISM
# ─────────────────────────────────────────────────────────────────────────────

CCC_PARTS = {
    1: {"title": "Wyznanie Wiary", "title_la": "Professio Fidei",       "para_range": (1, 1065)},
    2: {"title": "Celebracja Misterium Chrześcijańskiego", "title_la": "Celebratio Mysterii Christiani", "para_range": (1066, 1690)},
    3: {"title": "Życie w Chrystusie", "title_la": "Vita in Christo",   "para_range": (1691, 2557)},
    4: {"title": "Modlitwa Chrześcijańska", "title_la": "Oratio Christiana", "para_range": (2558, 2865)},
}


# ─────────────────────────────────────────────────────────────────────────────
# VATICANUM I & II — Councils
# ─────────────────────────────────────────────────────────────────────────────

COUNCIL_DOCUMENTS: list[CorpusDocument] = [
    # ── Vatican I (1869–1870) ──────────────────────────────────────────────
    CorpusDocument(
        doc_id="dei-filius",
        title="Dei Filius",
        title_pl="Syn Boży — O wierze katolickiej",
        doc_type=DocumentType.DOGMATIC_CONSTITUTION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum I",
        year=1870,
        language="la",
        theology_tags=["faith", "reason", "revelation", "natural_theology"],
        fetch_url="https://www.vatican.va/archive/hist_councils/i-vatican-council/documents/vat-i_const_18700424_dei-filius_en.html",
        description="Konstytucja dogmatyczna o wierze katolickiej; definiuje relację wiary i rozumu.",
    ),
    CorpusDocument(
        doc_id="pastor-aeternus",
        title="Pastor Aeternus",
        title_pl="Pasterz Wieczny — O prymacie papieskim",
        doc_type=DocumentType.DOGMATIC_CONSTITUTION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum I",
        year=1870,
        language="la",
        theology_tags=["papacy", "infallibility", "ecclesiology", "primacy"],
        fetch_url="https://www.vatican.va/archive/hist_councils/i-vatican-council/documents/vat-i_constitution_18700718_pastor-aeternus_en.html",
        description="Konstytucja dogmatyczna o Kościele; definiuje nieomylność papieską.",
    ),

    # ── Vatican II (1962–1965) — Constitutions ─────────────────────────────
    CorpusDocument(
        doc_id="lumen-gentium",
        title="Lumen Gentium",
        title_pl="Światło Narodów — O Kościele",
        doc_type=DocumentType.DOGMATIC_CONSTITUTION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1964,
        language="la",
        theology_tags=["ecclesiology", "people_of_god", "hierarchy", "laity", "mary", "eschatology"],
        tradition_tags=["all"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_const_19641121_lumen-gentium_en.html",
        description="Centralna konstytucja eklezjologiczna Soboru; Kościół jako Lud Boży.",
    ),
    CorpusDocument(
        doc_id="dei-verbum",
        title="Dei Verbum",
        title_pl="Słowo Boże — O Objawieniu Bożym",
        doc_type=DocumentType.DOGMATIC_CONSTITUTION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1965,
        language="la",
        theology_tags=["revelation", "scripture", "tradition", "inspiration", "hermeneutics"],
        tradition_tags=["all"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_const_19651118_dei-verbum_en.html",
        description="Konstytucja o Objawieniu; fundamentalna dla Lectio Divina.",
    ),
    CorpusDocument(
        doc_id="sacrosanctum-concilium",
        title="Sacrosanctum Concilium",
        title_pl="Święty Sobór — O Liturgii",
        doc_type=DocumentType.PASTORAL_CONSTITUTION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1963,
        language="la",
        theology_tags=["liturgy", "eucharist", "sacraments", "active_participation", "inculturation"],
        tradition_tags=["benedictine"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_const_19631204_sacrosanctum-concilium_en.html",
        description="Konstytucja o liturgii; reforma liturgiczna, aktywne uczestnictwo.",
    ),
    CorpusDocument(
        doc_id="gaudium-et-spes",
        title="Gaudium et Spes",
        title_pl="Radość i Nadzieja — Kościół w świecie współczesnym",
        doc_type=DocumentType.PASTORAL_CONSTITUTION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1965,
        language="la",
        theology_tags=["social_teaching", "human_dignity", "marriage", "culture", "peace", "economics"],
        tradition_tags=["dominican", "franciscan"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_const_19651207_gaudium-et-spes_en.html",
        description="Konstytucja pastoralna; Kościół wobec współczesnych wyzwań.",
    ),

    # ── Vatican II — Decrees ───────────────────────────────────────────────
    CorpusDocument(
        doc_id="unitatis-redintegratio",
        title="Unitatis Redintegratio",
        title_pl="Przywrócenie Jedności — O Ekumenizmie",
        doc_type=DocumentType.DECREE,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1964,
        theology_tags=["ecumenism", "unity", "separated_brethren"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_decree_19641121_unitatis-redintegratio_en.html",
    ),
    CorpusDocument(
        doc_id="presbyterorum-ordinis",
        title="Presbyterorum Ordinis",
        title_pl="O Posłudze i Życiu Kapłanów",
        doc_type=DocumentType.DECREE,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1965,
        theology_tags=["priesthood", "ministry", "celibacy", "spirituality"],
        tradition_tags=["ignatian"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_decree_19651207_presbyterorum-ordinis_en.html",
    ),
    CorpusDocument(
        doc_id="apostolicam-actuositatem",
        title="Apostolicam Actuositatem",
        title_pl="O Apostolstwie Świeckich",
        doc_type=DocumentType.DECREE,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1965,
        theology_tags=["laity", "apostolate", "vocation"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_decree_19651118_apostolicam-actuositatem_en.html",
    ),
    CorpusDocument(
        doc_id="ad-gentes",
        title="Ad Gentes",
        title_pl="Do Narodów — O Misyjnej Działalności Kościoła",
        doc_type=DocumentType.DECREE,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1965,
        theology_tags=["mission", "evangelization", "inculturation"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_decree_19651207_ad-gentes_en.html",
    ),

    # ── Vatican II — Declarations ──────────────────────────────────────────
    CorpusDocument(
        doc_id="nostra-aetate",
        title="Nostra Aetate",
        title_pl="W Naszych Czasach — O Religiach Niechrześcijańskich",
        doc_type=DocumentType.DECLARATION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1965,
        theology_tags=["interreligious", "judaism", "islam", "dialogue"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_decl_19651028_nostra-aetate_en.html",
    ),
    CorpusDocument(
        doc_id="dignitatis-humanae",
        title="Dignitatis Humanae",
        title_pl="Godność Człowieka — O Wolności Religijnej",
        doc_type=DocumentType.DECLARATION,
        collection=QdrantCollection.SOBORY,
        author="Vaticanum II",
        year=1965,
        theology_tags=["religious_freedom", "human_dignity", "conscience"],
        fetch_url="https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_decl_19651207_dignitatis-humanae_en.html",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# ENCYCLICALS — Leo XIII → Francis
# ─────────────────────────────────────────────────────────────────────────────

ENCYCLICAL_DOCUMENTS: list[CorpusDocument] = [
    # Leo XIII
    CorpusDocument(doc_id="rerum-novarum", title="Rerum Novarum", title_pl="O kwestii robotniczej",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Leon XIII", year=1891, theology_tags=["social_teaching", "labor", "property", "justice"],
        fetch_url="https://www.vatican.va/content/leo-xiii/en/encyclicals/documents/hf_l-xiii_enc_15051891_rerum-novarum.html"),
    CorpusDocument(doc_id="aeterni-patris", title="Aeterni Patris", title_pl="O studiowaniu filozofii scholastycznej",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Leon XIII", year=1879, theology_tags=["philosophy", "thomism", "reason"]),

    # Pius XI
    CorpusDocument(doc_id="quadragesimo-anno", title="Quadragesimo Anno", title_pl="O ustroju społecznym",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Pius XI", year=1931, theology_tags=["social_teaching", "subsidiarity", "solidarity"]),
    CorpusDocument(doc_id="mit-brennender-sorge", title="Mit Brennender Sorge", title_pl="O sytuacji Kościoła w Niemczech",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Pius XI", year=1937, language="de", theology_tags=["nazism", "human_dignity", "persecution"]),

    # Pius XII
    CorpusDocument(doc_id="mystici-corporis", title="Mystici Corporis Christi", title_pl="O Mistycznym Ciele Chrystusa",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Pius XII", year=1943, theology_tags=["ecclesiology", "mystical_body", "church"]),
    CorpusDocument(doc_id="mediator-dei", title="Mediator Dei", title_pl="O liturgii świętej",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Pius XII", year=1947, theology_tags=["liturgy", "eucharist", "worship"]),
    CorpusDocument(doc_id="humani-generis", title="Humani Generis", title_pl="O błędach zagrażających wierze",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Pius XII", year=1950, theology_tags=["truth", "dogma", "evolution", "theology"]),

    # John XXIII
    CorpusDocument(doc_id="mater-et-magistra", title="Mater et Magistra", title_pl="O chrześcijańskiej nauce społecznej",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan XXIII", year=1961, theology_tags=["social_teaching", "development", "labor"]),
    CorpusDocument(doc_id="pacem-in-terris", title="Pacem in Terris", title_pl="Pokój na ziemi",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan XXIII", year=1963, theology_tags=["peace", "human_rights", "international_order"]),

    # Paul VI
    CorpusDocument(doc_id="populorum-progressio", title="Populorum Progressio", title_pl="O popieraniu rozwoju ludów",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Paweł VI", year=1967, theology_tags=["development", "poverty", "justice", "globalization"]),
    CorpusDocument(doc_id="humanae-vitae", title="Humanae Vitae", title_pl="O ludzkiej płodności",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Paweł VI", year=1968, theology_tags=["marriage", "life", "sexuality", "contraception"]),
    CorpusDocument(doc_id="evangelii-nuntiandi", title="Evangelii Nuntiandi", title_pl="O ewangelizacji w świecie współczesnym",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Paweł VI", year=1975, theology_tags=["evangelization", "mission", "liberation"]),

    # John Paul II
    CorpusDocument(doc_id="redemptor-hominis", title="Redemptor Hominis", title_pl="Odkupiciel Człowieka",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=1979, theology_tags=["christology", "human_dignity", "redemption"]),
    CorpusDocument(doc_id="dives-in-misericordia", title="Dives in Misericordia", title_pl="Bogaty w Miłosierdziu",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=1980, theology_tags=["mercy", "father", "parable_of_prodigal_son"]),
    CorpusDocument(doc_id="laborem-exercens", title="Laborem Exercens", title_pl="O pracy ludzkiej",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=1981, theology_tags=["work", "labor", "human_dignity", "social_teaching"]),
    CorpusDocument(doc_id="familiaris-consortio", title="Familiaris Consortio", title_pl="O rodzinie chrześcijańskiej",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=1981, theology_tags=["family", "marriage", "sexuality", "children"]),
    CorpusDocument(doc_id="veritatis-splendor", title="Veritatis Splendor", title_pl="Blask Prawdy",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=1993, theology_tags=["moral_theology", "natural_law", "truth", "freedom"]),
    CorpusDocument(doc_id="evangelium-vitae", title="Evangelium Vitae", title_pl="Ewangelia Życia",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=1995, theology_tags=["life", "abortion", "euthanasia", "death_penalty"]),
    CorpusDocument(doc_id="fides-et-ratio", title="Fides et Ratio", title_pl="Wiara i Rozum",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=1998, theology_tags=["faith", "reason", "philosophy", "truth"]),
    CorpusDocument(doc_id="ecclesia-de-eucharistia", title="Ecclesia de Eucharistia", title_pl="Kościół żyje Eucharystią",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Jan Paweł II", year=2003, theology_tags=["eucharist", "church", "real_presence"]),

    # Benedict XVI
    CorpusDocument(doc_id="deus-caritas-est", title="Deus Caritas Est", title_pl="Bóg jest Miłością",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Benedykt XVI", year=2005, theology_tags=["love", "charity", "eros", "agape"],
        tradition_tags=["all"]),
    CorpusDocument(doc_id="spe-salvi", title="Spe Salvi", title_pl="Nadzieją zbawieni",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Benedykt XVI", year=2007, theology_tags=["hope", "eschatology", "salvation"],
        tradition_tags=["all"]),
    CorpusDocument(doc_id="caritas-in-veritate", title="Caritas in Veritate", title_pl="Miłość w Prawdzie",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Benedykt XVI", year=2009, theology_tags=["social_teaching", "development", "ecology"]),
    CorpusDocument(doc_id="verbum-domini", title="Verbum Domini", title_pl="Słowo Pańskie",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Benedykt XVI", year=2010, theology_tags=["scripture", "lectio_divina", "revelation"],
        tradition_tags=["all"],
        description="Posynodalna adhortacja o Słowie Bożym; bezpośrednio definiuje Lectio Divina."),

    # Francis
    CorpusDocument(doc_id="evangelii-gaudium", title="Evangelii Gaudium", title_pl="Radość Ewangelii",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Franciszek", year=2013, theology_tags=["evangelization", "joy", "poverty", "mission"],
        tradition_tags=["franciscan"]),
    CorpusDocument(doc_id="laudato-si", title="Laudato Si'", title_pl="Laudato Si' — O trosce o wspólny dom",
        doc_type=DocumentType.ENCYCLICAL, collection=QdrantCollection.MAGISTERIUM,
        author="Franciszek", year=2015, theology_tags=["ecology", "creation", "social_teaching", "poverty"],
        tradition_tags=["franciscan"]),
    CorpusDocument(doc_id="amoris-laetitia", title="Amoris Laetitia", title_pl="Radość Miłości",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Franciszek", year=2016, theology_tags=["family", "marriage", "mercy", "accompaniment"]),
    CorpusDocument(doc_id="gaudete-et-exsultate", title="Gaudete et Exsultate", title_pl="Radujcie się i cieszcie — O powołaniu do świętości",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Franciszek", year=2018, theology_tags=["holiness", "saints", "beatitudes", "discernment"],
        tradition_tags=["ignatian", "all"]),
    CorpusDocument(doc_id="christus-vivit", title="Christus Vivit", title_pl="Chrystus żyje",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Franciszek", year=2019, theology_tags=["youth", "vocation", "discernment", "synodality"]),
    CorpusDocument(doc_id="laudate-deum", title="Laudate Deum", title_pl="Chwalcie Boga",
        doc_type=DocumentType.APOSTOLIC_EXHORTATION, collection=QdrantCollection.MAGISTERIUM,
        author="Franciszek", year=2023, theology_tags=["ecology", "climate", "creation"]),
]


# ─────────────────────────────────────────────────────────────────────────────
# PATRISTIC TEXTS
# ─────────────────────────────────────────────────────────────────────────────

PATRISTIC_DOCUMENTS: list[CorpusDocument] = [
    CorpusDocument(doc_id="augustine-confessions", title="Confessiones", title_pl="Wyznania",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Augustyn", year=400, language="la",
        theology_tags=["prayer", "conversion", "heart", "grace", "restlessness"],
        tradition_tags=["all"],
        description="'Niespokojne jest serce nasze, dopóki nie spocznie w Tobie.'"),
    CorpusDocument(doc_id="augustine-city-of-god", title="De Civitate Dei", title_pl="Państwo Boże",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Augustyn", year=426, language="la",
        theology_tags=["history", "eschatology", "church", "society"]),
    CorpusDocument(doc_id="thomas-summa-theologiae", title="Summa Theologiae", title_pl="Suma teologiczna",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Tomasz z Akwinu", year=1274, language="la",
        theology_tags=["theology", "philosophy", "virtues", "law", "sacraments"],
        tradition_tags=["dominican"]),
    CorpusDocument(doc_id="teresa-interior-castle", title="Interior Castle", title_pl="Twierdza wewnętrzna",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Teresa z Ávili", year=1577,
        theology_tags=["prayer", "contemplation", "mysticism", "soul"],
        tradition_tags=["carmelite"]),
    CorpusDocument(doc_id="john-of-the-cross-dark-night", title="Dark Night of the Soul", title_pl="Noc ciemna",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Jan od Krzyża", year=1584,
        theology_tags=["mysticism", "purification", "union", "suffering", "contemplation"],
        tradition_tags=["carmelite"]),
    CorpusDocument(doc_id="ignatius-spiritual-exercises", title="Spiritual Exercises", title_pl="Ćwiczenia Duchowe",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Ignacy Loyola", year=1548,
        theology_tags=["discernment", "election", "prayer", "imagination", "consolation"],
        tradition_tags=["ignatian"]),
    CorpusDocument(doc_id="benedict-rule", title="Regula Sancti Benedicti", title_pl="Reguła Benedykta",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Benedykt z Nursji", year=516, language="la",
        theology_tags=["community", "ora_et_labora", "obedience", "stability", "lectio_divina"],
        tradition_tags=["benedictine"]),
    CorpusDocument(doc_id="francis-canticle-of-sun", title="Canticum Fratris Solis", title_pl="Pieśń Słoneczna",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="św. Franciszek z Asyżu", year=1225,
        theology_tags=["creation", "praise", "ecology", "poverty"],
        tradition_tags=["franciscan"]),
    CorpusDocument(doc_id="guigo-ladder-monks", title="Scala Claustralium", title_pl="Drabina mnichów",
        doc_type=DocumentType.PATRISTIC, collection=QdrantCollection.PATRYSTYKA,
        author="Guigo II Kartuz", year=1150, language="la",
        theology_tags=["lectio_divina", "prayer", "contemplation", "meditation"],
        tradition_tags=["benedictine", "all"],
        description="Pierwszy systematyczny opis czterech etapów Lectio Divina."),
]


# ─────────────────────────────────────────────────────────────────────────────
# MASTER REGISTRY
# ─────────────────────────────────────────────────────────────────────────────

CORPUS_REGISTRY: list[CorpusDocument] = (
    COUNCIL_DOCUMENTS + ENCYCLICAL_DOCUMENTS + PATRISTIC_DOCUMENTS
)

CORPUS_BY_ID: dict[str, CorpusDocument] = {doc.doc_id: doc for doc in CORPUS_REGISTRY}

CORPUS_BY_COLLECTION: dict[QdrantCollection, list[CorpusDocument]] = {}
for _doc in CORPUS_REGISTRY:
    CORPUS_BY_COLLECTION.setdefault(_doc.collection, []).append(_doc)


def get_document(doc_id: str) -> CorpusDocument | None:
    return CORPUS_BY_ID.get(doc_id)


def get_collection_documents(collection: QdrantCollection) -> list[CorpusDocument]:
    return CORPUS_BY_COLLECTION.get(collection, [])


def search_registry(
    theology_tag: str | None = None,
    tradition: str | None = None,
    doc_type: DocumentType | None = None,
    author: str | None = None,
) -> list[CorpusDocument]:
    """Filter corpus registry by metadata."""
    results = CORPUS_REGISTRY
    if theology_tag:
        results = [d for d in results if theology_tag in d.theology_tags]
    if tradition:
        results = [d for d in results if tradition in d.tradition_tags or "all" in d.tradition_tags]
    if doc_type:
        results = [d for d in results if d.doc_type == doc_type]
    if author:
        results = [d for d in results if author.lower() in d.author.lower()]
    return results

"""Kalendarz świętych — patron dnia według kalendarza Kościoła Katolickiego.

Dane w języku polskim, pokrywają cały rok liturgiczny.
Kluczowe święta polskich i powszechnych patronów.
Format klucza: "MM-DD"
"""

from __future__ import annotations

from datetime import date
from typing import TypedDict


class SaintInfo(TypedDict):
    name: str
    description: str
    patronage: str       # krótkie wyliczenie patronatów
    icon: str            # emoji reprezentujące świętego/święto
    died: str            # rok/okres śmierci lub "żyjący" dla Matki Bożej


# ── Baza danych świętych ──────────────────────────────────────────────────────

_SAINTS: dict[str, SaintInfo] = {
    # Styczeń
    "01-01": SaintInfo(name="Świętej Bożej Rodzicielki Maryi", description="Uroczystość Świętej Bożej Rodzicielki — Maryja, Matka Pana, proklamowana Theotokos na Soborze Efeskim (431). Pierwszy dzień roku pod opieką Matki Bożej.", patronage="Polacy, matki, pokój na świecie", icon="✨", died="I w."),
    "01-03": SaintInfo(name="Najświętszego Imienia Jezus", description="Wspomnienie Najświętszego Imienia Jezus — imię, które jest ponad wszelkie imię (Flp 2,9). Tradycja polecania nowego roku Bożemu miłosierdziu.", patronage="Wszystkich chrześcijan", icon="✝", died="—"),
    "01-06": SaintInfo(name="Objawienie Pańskie — Trzej Królowie", description="Uroczystość Objawienia Pańskiego. Trzej Mędrcy ze Wschodu — Kacper, Melchior i Baltazar — oddają hołd Dzieciątku Jezus. Epifania — objawienie Boga narodom.", patronage="Podróżni, pielgrzymi, astronomowie", icon="⭐", died="I w."),
    "01-13": SaintInfo(name="Św. Hilarego z Poitiers", description="Doktor Kościoła, Ojciec Kościoła Zachodniego IV wieku. Obrońca bóstwa Chrystusa przeciw arianizmowi. Napisał traktat 'O Trójcy'.", patronage="Teolodzy, chorzy na gorączkę", icon="📖", died="367"),
    "01-17": SaintInfo(name="Św. Antoniego Opata", description="Ojciec monastycyzmu chrześcijańskiego, pustelnik egipski (251–356). Porzucił majątek i udał się na pustynię, gdzie spędził ponad 80 lat w modlitwie. Jego życie opisał Atanazy Wielki.", patronage="Mnisi, zwierzęta domowe, skórnicy", icon="🏔", died="356"),
    "01-20": SaintInfo(name="Św. Fabiana i Sebastiana", description="Fabian — papież i męczennik (III w.); Sebastian — oficer gwardii cesarskiej zamęczony za wiarę. Obaj oddali życie za Chrystusa w prześladowaniach Decjusza.", patronage="Żołnierze, sportowcy, chorzy na zarazę", icon="⚔", died="258"),
    "01-21": SaintInfo(name="Św. Agnieszki", description="Dziewica i męczennica z Rzymu (ok. 291–304). Odrzuciła miłość syna prefekta, wolała śmierć niż zdradę Oblubieńca-Chrystusa. Symbol dziewiczej wiary.", patronage="Dziewczęta, zaręczeni, harcerki", icon="🌹", died="304"),
    "01-24": SaintInfo(name="Św. Franciszka Salezego", description="Doktor Kościoła, Biskup Genewy (1567–1622). Apostoł łagodności — nauczał, że do Boga prowadzi miłość, nie lęk. Patron dziennikarzy i pisarzy katolickich.", patronage="Dziennikarze, pisarze, głusi", icon="🖊", died="1622"),
    "01-25": SaintInfo(name="Nawrócenie Św. Pawła Apostoła", description="Święto upamiętniające dramatyczne nawrócenie Szawła pod Damaszkiem — z prześladowcy do największego apostoła pogan. 'Kto nas odłączy od miłości Chrystusa?' (Rz 8,35)", patronage="Misjonarze, teolodzy, nawróceni", icon="⚡", died="67"),
    "01-28": SaintInfo(name="Św. Tomasza z Akwinu", description="Doktor Kościoła, dominikanin (1225–1274). Anielski Doktor — Suma Teologiczna to fundament teologii katolickiej. Pogodził wiarę z rozumem: 'Wiara i rozum to dwa skrzydła ducha.'", patronage="Studenci, filozofowie, teolodzy, szkoły", icon="📚", died="1274"),
    "01-31": SaintInfo(name="Św. Jana Bosco", description="Ksiądz salezjanin (1815–1888), ojciec i nauczyciel młodzieży. Założył Towarzystwo Salezjańskie dla wychowania chłopców z ubogich rodzin Turynu.", patronage="Młodzież, wychowawcy, drukarze", icon="👦", died="1888"),
    # Luty
    "02-02": SaintInfo(name="Ofiarowanie Pańskie — Matki Bożej Gromnicznej", description="Uroczystość Ofiarowania Pańskiego — Symeon i Anna rozpoznają w Dziecięciu Zbawiciela. Procesja ze świecami symbolizuje Chrystusa — Światłość Narodów (Lumen gentium).", patronage="Konsekrowani, zakonnicy, matki", icon="🕯", died="—"),
    "02-03": SaintInfo(name="Św. Błażeja", description="Biskup Sebasty w Armenii, męczennik (III/IV w.). Patron chorych na gardło — według tradycji uzdrowił chłopca z ością w gardle. Błogosławieństwo gardeł 3 lutego.", patronage="Chorzy na gardło, lekarze, weterynarze", icon="✝", died="316"),
    "02-05": SaintInfo(name="Św. Agaty", description="Sycylijska dziewica i męczennica z III wieku. Odmówiła zdrady wiary i czystości, zamęczona za panowania Decjusza. Patron chorych na raka piersi i odlewników dzwonów.", patronage="Pielęgniarki, chorzy, Sycylia", icon="🌹", died="251"),
    "02-11": SaintInfo(name="NMP z Lourdes", description="Wspomnienie Matki Bożej z Lourdes — objawień dla Bernadetty Soubirous (1858). 'Jestem Niepokalane Poczęcie.' Lourdes to jedno z największych miejsc pielgrzymkowych na świecie.", patronage="Chorzy, pielgrzymi, służba zdrowia", icon="💧", died="—"),
    "02-14": SaintInfo(name="Śś. Cyryla i Metodego", description="Apostołowie Słowian (IX w.) — bracia z Tesaloniki, twórcy pisma słowiańskiego (głagolica i cyrylica). Patron Europy i Słowian.", patronage="Europa, Słowianie, studenci językoznawcy", icon="📜", died="869/885"),
    "02-22": SaintInfo(name="Katedry Świętego Piotra", description="Święto upamiętniające władzę pasterską Piotra Apostoła. Katedra — cathedra — to tron nauczycielski. 'Ty jesteś Piotr i na tej skale zbuduję Kościół mój.' (Mt 16,18)", patronage="Papieże, Kościół", icon="⛪", died="—"),
    "02-23": SaintInfo(name="Św. Polikarpa ze Smyrny", description="Uczeń Apostoła Jana, Ojciec Kościoła (69–155). Męczennik w Smyrnie, odmówił wyrzeczenia się Chrystusa: 'Osiemdziesiąt sześć lat Mu służę — jakże mam bluźnić mojemu Królowi?'", patronage="Biskupi, świadkowie wiary", icon="🔥", died="155"),
    # Marzec
    "03-07": SaintInfo(name="Śś. Perpetuy i Felicyty", description="Męczennice z Kartaginy (203). Perpetua — szlachetna matka, Felicyta — niewolnica. Obie zginęły na arenie za Chrystusa. Symbol jedności wiary ponad podziałami społecznymi.", patronage="Matki, więźniowie, pasterze zwierząt", icon="🦁", died="203"),
    "03-17": SaintInfo(name="Św. Patryka", description="Apostoł Irlandii (385–461). Porwany jako młodzieniec do Irlandii, po ucieczce wrócił jako misjonarz. Chrzcił królów, zakładał klasztory. Patron Irlandii.", patronage="Irlandia, inżynierowie, wyklęci", icon="☘", died="461"),
    "03-19": SaintInfo(name="Św. Józefa, Oblubieńca NMP", description="Uroczystość Św. Józefa — Opiekuna Świętej Rodziny, milczącego robotnika z Nazaretu. Patron Kościoła Powszechnego (od 1870), robotników i umierających.", patronage="Kościół, robotnicy, umierający, Polska", icon="🪚", died="I w."),
    "03-25": SaintInfo(name="Zwiastowanie Pańskie", description="Uroczystość Zwiastowania — Archanioł Gabriel ogłasza Maryi, że pocznie Syna Bożego. 'Oto ja służebnica Pańska.' Dziewięć miesięcy przed Bożym Narodzeniem.", patronage="Polska, dyplomaci, poczta", icon="🌸", died="—"),
    # Kwiecień
    "04-02": SaintInfo(name="Bł. Jana Pawła II", description="Jan Paweł II (Karol Wojtyła, 1920–2005) — pierwszy Papież-Słowianin, beatyfikowany 2011. Pielgrzym pokoju, apostoł miłosierdzia. 'Nie lękajcie się! Otwórzcie na oścież drzwi Chrystusowi!'", patronage="Polska, młodzież, rodziny", icon="✝", died="2005"),
    "04-05": SaintInfo(name="Św. Wincentego Ferreriusza", description="Dominikanin (1350–1419), wielki kaznodzieja XV w. Nawrócił tysiące ludzi przez całą Europę. Przeczuwał bliski Sąd Ostateczny i wzywał do pokuty.", patronage="Budowniczowie, misjonarze", icon="🕊", died="1419"),
    "04-07": SaintInfo(name="Bł. Jerzego Popiełuszki", description="Polski Ksiądz-Męczennik (1947–1984). Kapelan Solidarności, zamordowany przez komunistyczną SB. Głosił: 'Zło dobrem zwyciężaj.' Beatyfikowany w 2010.", patronage="Robotnicy, Solidarność, Polska", icon="🕯", died="1984"),
    "04-11": SaintInfo(name="Św. Stanisława Biskupa i Męczennika", description="Patron Polski (1030–1079). Biskup Krakowa, zamordowany na rozkaz króla Bolesława Śmiałego za upomnienie władcy. Jeden z patronów głównych Polski.", patronage="Polska, Kraków, biskupi", icon="⚔", died="1079"),
    "04-23": SaintInfo(name="Św. Wojciecha Biskupa i Męczennika", description="Patron Polski (956–997). Misjonarz Prusów, zamęczony nad Bałtykiem. Jego relikwie złożono w Gnieźnie. Jeden z patronów głównych Polski.", patronage="Polska, Czechy, Prusy, misjonarze", icon="✝", died="997"),
    "04-29": SaintInfo(name="Św. Katarzyny ze Sieny", description="Doktor Kościoła, tercjarka dominikańska (1347–1380). Mistyczka i doradczyni papieży — nakłoniła Grzegorza XI do powrotu z Awinionu do Rzymu. Patron Europy.", patronage="Europa, Włochy, pielęgniarki, strażacy", icon="🌹", died="1380"),
    # Maj
    "05-01": SaintInfo(name="Św. Józefa Robotnika", description="Wspomnienie Św. Józefa Robotnika — ustanowione przez Piusa XII w 1955 r. jako odpowiedź Kościoła na komunistyczne święto pracy. Godność pracy ludzkiej.", patronage="Robotnicy, rzemieślnicy, ojcowie", icon="🔨", died="I w."),
    "05-03": SaintInfo(name="NMP Królowej Polski", description="Uroczystość Najświętszej Maryi Panny Królowej Polski — 333. rocznica Ślubów Lwowskich Jana Kazimierza (1656). Maryja Królową Polski przez zawołanie 'Za wolność waszą i naszą'.", patronage="Polska, narody słowiańskie", icon="👑", died="—"),
    "05-13": SaintInfo(name="NMP Fatimskiej", description="Wspomnienie Matki Bożej Fatimskiej — objawień dla trojga dzieci w Fatimie (1917). Wezwanie do modlitwy różańcowej i nawrócenia. 'Rosja nawróci się, a świat zazna pokoju.'", patronage="Rosja, Portugalia, pokój", icon="📿", died="—"),
    "05-16": SaintInfo(name="Św. Andrzeja Boboli", description="Patron Polski, jezuita (1591–1657). Apostoł Polesia, zamęczony przez kozaków w Janowie Poleskim. Kanonizowany w 1938. Zwany 'duszołowcą'.", patronage="Polska", icon="✝", died="1657"),
    "05-18": SaintInfo(name="Bł. Jana Pawła II (ur. 1920)", description="W tym dniu 1920 roku przyszedł na świat Karol Józef Wojtyła w Wadowicach. Syn Karola i Emilii. Przyszły Papież-Pielgrzym, Święty Jan Paweł II.", patronage="Polska, młodzież, sport", icon="🎂", died="2005"),
    "05-26": SaintInfo(name="Św. Filipa Neri", description="Apostoł Rzymu (1515–1595), założyciel Oratorium. Mistyk przepełniony radością — 'Wesoły Święty.' Mówił: 'Jeśli chcesz być posłuszny Bogu, bądź wesoły.'", patronage="Rzym, młodzież, poczucie humoru", icon="😊", died="1595"),
    # Czerwiec
    "06-13": SaintInfo(name="Św. Antoniego z Padwy", description="Doktor Kościoła, franciszkanin (1195–1231). Kaznodzieja niezrównany — głosił nawet ryby wg legendy. Patron zgubionych rzeczy i ubogich.", patronage="Ubodzy, zaginieni, podróżni, Portugalia", icon="📖", died="1231"),
    "06-21": SaintInfo(name="Św. Alojzego Gonzagi", description="Jezuita (1568–1591), oddał się opiece chorych na dżumę i sam zachorował w wieku 23 lat. Symbol młodzieńczej świętości i czystości.", patronage="Młodzież, studenci, chorzy na AIDS", icon="🌸", died="1591"),
    "06-24": SaintInfo(name="Narodzenie Św. Jana Chrzciciela", description="Uroczystość Narodzenia Jana Chrzciciela — sześć miesięcy przed Chrystusem. Głos wołający na pustyni: 'Przygotujcie drogę Pańską.' Jedyny święty (poza Maryją), który ma święto narodzin.", patronage="Francja, Jordan, skórnicy, zbudzona sumienia", icon="🌊", died="~29"),
    "06-29": SaintInfo(name="Śś. Piotra i Pawła Apostołów", description="Uroczystość dwóch filarów Kościoła: Piotra — skały i Pawła — narzędzia wybranego. Obaj zginęli w Rzymie za panowania Nerona.", patronage="Papieże, Rzym, rybacy, misjonarze", icon="🗝", died="64/67"),
    "06-30": SaintInfo(name="Pierwszych Męczenników Kościoła Rzymskiego", description="Wspomnienie chrześcijan zamordowanych przez Nerona po pożarze Rzymu (64). Pierwsi świadkowie wiary Kościoła Stolicy Apostolskiej.", patronage="Misjonarze, świadkowie wiary", icon="🔥", died="64"),
    # Lipiec
    "07-11": SaintInfo(name="Św. Benedykta z Nursji", description="Ojciec monastycyzmu zachodniego (480–547), Patron Europy. Reguła: 'Módl się i pracuj' (Ora et labora). Założył Klasztor na Monte Cassino.", patronage="Europa, mnisi, studenci, truciznobójcy", icon="☦", died="547"),
    "07-13": SaintInfo(name="Św. Henryka", description="Cesarz Henryk II (973–1024) — pierwszy cesarz kanonizowany. Budował kościoły, bronił Kościoła, żył w celibacie z żoną. Wzór władcy chrześcijańskiego.", patronage="Władcy, małżeństwa, kalecy", icon="👑", died="1024"),
    "07-16": SaintInfo(name="NMP z Góry Karmel", description="Wspomnienie Matki Bożej z Góry Karmel. Tradycja szkaplerzna — Maryja obiecała wybawienie z czyśćca tym, którzy noszą szkaplerzyk. 'Ja i ty na Karmelu.'", patronage="Karmelici, dusze w czyśćcu", icon="🏔", died="—"),
    "07-22": SaintInfo(name="Św. Marii Magdaleny", description="Apostołka Apostołów (I w.) — pierwsza ujrzała Zmartwychwstałego. Chrystus uwolnił ją od siedmiu złych duchów. Symbol miłosierdzia Bożego i nowego początku.", patronage="Pokutujący, perfumiarze, ogrodnicy", icon="🌺", died="I w."),
    "07-25": SaintInfo(name="Św. Jakuba Apostoła", description="Apostoł i męczennik, syn Zebedeusza (†44). Brat Jana Ewangelisty. Patronuje pielgrzymom — Droga Świętego Jakuba (Camino de Santiago) to jedna z wielkich tras pielgrzymkowych.", patronage="Pielgrzymi, Hiszpania, żołnierze", icon="🐚", died="44"),
    "07-26": SaintInfo(name="Śś. Joachima i Anny", description="Rodzice Najświętszej Maryi Panny — dziadkowie Jezusa. Tradycja przekazuje imiona i pobożność rodziców Maryi. Wzór dla chrześcijańskich dziadków.", patronage="Dziadkowie, wdowy, rodziny", icon="👴", died="I w. p.n.e."),
    # Sierpień
    "08-04": SaintInfo(name="Św. Jana Marii Vianneya", description="Proboszcz z Ars (1786–1859), Patron kapłanów. Spędzał 16-18h dziennie w konfesjonale. Pomimo trudności w nauce, stał się mistrzem duchowego kierownictwa.", patronage="Kapłani, duszpasterze", icon="⛪", died="1859"),
    "08-06": SaintInfo(name="Przemienienie Pańskie", description="Uroczystość Przemienienia Pańskiego na Górze Tabor. Piotr, Jakub i Jan ujrzeli Chrystusa w Jego chwale. 'To jest mój Syn umiłowany, Jego słuchajcie.'", patronage="—", icon="✨", died="—"),
    "08-10": SaintInfo(name="Św. Wawrzyńca", description="Diakon i męczennik (†258). Zarządzał dobrami Kościoła Rzymskiego, rozdał je ubogim. Zamęczony na rozżarzonym ruszcie. 'Przewróć mnie — już jestem dopieczony.'", patronage="Kucharze, biedni, bibliotekarze, Polska", icon="🔥", died="258"),
    "08-14": SaintInfo(name="Św. Maksymiliana Marii Kolbe", description="Polski franciszkanin (1894–1941), Rycerz Niepokalanej. W obozie Auschwitz oddał życie za współwięźnia — ojca rodziny. Beatyfikowany przez Jana Pawła II jako Męczennik Miłości.", patronage="Polska, Auschwitz, dziennikarze, uzależnieni", icon="🌹", died="1941"),
    "08-15": SaintInfo(name="Wniebowzięcie NMP", description="Uroczystość Wniebowzięcia Najświętszej Maryi Panny — dogmat ogłoszony przez Piusa XII w 1950. Maryja z duszą i ciałem wzięta do nieba. Największe święto maryjne.", patronage="Polska, Kościół, umierający", icon="👑", died="—"),
    "08-22": SaintInfo(name="NMP Królowej", description="Wspomnienie Najświętszej Maryi Panny Królowej — tydzień po Wniebowzięciu. Maryja koronuje się na Królową nieba i ziemi w chwale zmartwychwstania.", patronage="Kościół, Polska, wszystkie narody", icon="♛", died="—"),
    "08-28": SaintInfo(name="Św. Augustyna z Hippony", description="Doktor Kościoła (354–430), Ojciec Kościoła Zachodniego. 'Niespokojne jest serce nasze, dopóki nie spocznie w Tobie.' Wyznania to arcydzieło literatury chrześcijańskiej.", patronage="Teolodzy, drukarze, Afryka", icon="📖", died="430"),
    # Wrzesień
    "09-08": SaintInfo(name="Narodzenie NMP", description="Święto Narodzenia Najświętszej Maryi Panny. Tradycja kościelna przechowuje to wspomnienie od VI wieku. Narodziny Tej, która wyda na świat Zbawiciela.", patronage="Narodziny, Polska, żeglarze", icon="🌸", died="—"),
    "09-13": SaintInfo(name="Św. Jana Chryzostoma", description="Doktor Kościoła (344–407), 'Złotousty' Biskup Konstantynopola. Homilista niezrównany — komentarze do Pawła i Ewangelii to klasyka teologii. Wypędzony i zamęczony za prawdę.", patronage="Kaznodzieje, mówcy, pedagogowie", icon="📣", died="407"),
    "09-14": SaintInfo(name="Podwyższenie Krzyża Świętego", description="Uroczystość Podwyższenia Krzyża Świętego — znalezienie Krzyża przez św. Helenę (326). 'A Ja, gdy zostanę nad ziemię wywyższony, przyciągnę wszystkich do siebie.' (J 12,32)", patronage="—", icon="✝", died="—"),
    "09-15": SaintInfo(name="NMP Bolesnej", description="Wspomnienie Matki Bożej Bolesnej — Mater Dolorosa. Siedem boleści Maryi: przepowiednia Symeona, ucieczka do Egiptu, zgubienie Jezusa, Droga Krzyżowa, ukrzyżowanie, złożenie z krzyża, złożenie do grobu.", patronage="Matki, żałobnicy, cierpiący", icon="💔", died="—"),
    "09-22": SaintInfo(name="Bł. Karoliny Kózkówny", description="Polska Błogosławiona (1898–1914) z Wał-Rudy. Zamordowana przez żołnierza za obronę czystości. Symbol niewinności i odwagi moralnej. Patronka Polskiej Młodzieży.", patronage="Polska młodzież, dziewczęta", icon="🌺", died="1914"),
    "09-29": SaintInfo(name="Śś. Michała, Gabriela i Rafała Archaniołów", description="Uroczystość trzech Archaniołów: Michał — wódz wojsk niebieskich, Gabriel — zwiastun, Rafał — uzdrowiciel. Aniołowie — posłańcy Boga.", patronage="Wojsko, policja, lekarze, telekomunikacja", icon="⚔", died="—"),
    "09-30": SaintInfo(name="Św. Hieronima", description="Doktor Kościoła (345–420), autor Wulgaty — łacińskiego tłumaczenia Biblii. Asceta z Betlejem. 'Nieznajomość Pisma jest nieznajomością Chrystusa.'", patronage="Biblijna, tłumacze, bibliotekarze", icon="📜", died="420"),
    # Październik
    "10-01": SaintInfo(name="Św. Teresy od Dzieciątka Jezus", description="Doktor Kościoła (1873–1897), karmelitanka z Lisieux. Mała Droga — duchowość dziecięctwa Bożego. 'Po śmierci zesypię deszcz róż.' Patronka misji i Francji.", patronage="Misje, Francja, chorzy, kwiaciarze", icon="🌹", died="1897"),
    "10-02": SaintInfo(name="Aniołów Stróżów", description="Wspomnienie Świętych Aniołów Stróżów — każdy człowiek ma swego anioła (Mt 18,10). 'Oto posyłam anioła przed tobą, aby cię strzegł w drodze.' (Wj 23,20)", patronage="Dzieci, podróżni, policja", icon="👼", died="—"),
    "10-04": SaintInfo(name="Św. Franciszka z Asyżu", description="Założyciel franciszkanów (1181–1226). Porzucił bogactwo, przyrzekł ubóstwo. Otrzymał stygmaty. 'Pieśń słoneczna' — hymn stworzeniu. Patron ekologii i pokoju.", patronage="Ekologia, ubodzy, Włochy, zwierzęta", icon="🐦", died="1226"),
    "10-05": SaintInfo(name="Św. Faustyny Kowalskiej", description="Apostołka Miłosierdzia Bożego (1905–1938). Wizje Chrystusa Miłosiernego, 'Dzienniczek duchowy'. Obraz 'Jezu, ufam Tobie' i Koronka do Miłosierdzia Bożego.", patronage="Polska, miłosierdzie, siostry zakonne", icon="💙", died="1938"),
    "10-07": SaintInfo(name="NMP Różańcowej", description="Wspomnienie Najświętszej Maryi Panny Różańcowej — ustanowione po zwycięstwie pod Lepanto (1571). Różaniec to streszczenie Ewangelii i szkoła kontemplacji.", patronage="Różaniec, pokój, żołnierze", icon="📿", died="—"),
    "10-16": SaintInfo(name="Bł. Jana Pawła II (wybór na papieża 1978)", description="16 października 1978 — Karol Wojtyła zostaje papieżem. 'Nie lękajcie się!' — pierwsze słowa na placu Świętego Piotra. Rozpoczął pontyfikat trwający 26 lat.", patronage="Polska, młodzież, Kościół", icon="✝", died="2005"),
    "10-17": SaintInfo(name="Św. Ignacego Antiocheńskiego", description="Ojciec Kościoła, Biskup Antiochii (35–107). Uczeń Apostoła Jana, zamęczony w Rzymie. Listy do Kościołów to perła literatury wczesnochrześcijańskiej.", patronage="Kościół Wschodni, modlitwa", icon="🦁", died="107"),
    "10-22": SaintInfo(name="Św. Jana Pawła II", description="Uroczystość Świętego Jana Pawła II (1920–2005) — kanonizowany przez Franciszka w 2014. Papież Miłosierdzia, Pielgrzym Pokoju, Świadek Nadziei.", patronage="Polska, młodzież, rodziny, Europa", icon="✝", died="2005"),
    "10-28": SaintInfo(name="Śś. Szymona i Judy Tadeusza Apostołów", description="Dwaj apostołowie Chrystusa — Szymon Gorliwy i Juda Tadeusz, autor listu o wytrwałości w wierze. Patron spraw beznadziejnych.", patronage="Sprawy beznadziejne, szpitale", icon="🙏", died="I w."),
    # Listopad
    "11-01": SaintInfo(name="Uroczystość Wszystkich Świętych", description="Uroczystość Wszystkich Świętych — święto każdego, kto jest z Bogiem w niebie, znanych i nieznanych. 'Błogosławieni czystego serca, albowiem oni Boga oglądać będą.'", patronage="—", icon="👑", died="—"),
    "11-02": SaintInfo(name="Wspomnienie Wszystkich Wiernych Zmarłych", description="Dzień modlitwy za dusze czyśćcowe — 'wszystkich wiernych zmarłych'. Indulgencje zupełne za modlitwę na cmentarzu. Pamięć o tych, którzy odeszli.", patronage="Dusze czyśćcowe, umierający", icon="🕯", died="—"),
    "11-04": SaintInfo(name="Św. Karola Boromeusza", description="Arcybiskup Mediolanu (1538–1584), reformator Kościoła po Soborze Trydenckim. Osobiście opiekował się chorymi na dżumę. Wzór pasterza oddanego swej trzodzie.", patronage="Biskupi, Seminaria, Apple", icon="📿", died="1584"),
    "11-09": SaintInfo(name="Rocznica Poświęcenia Bazyliki Laterańskiej", description="Święto Bazyliki Laterańskiej — 'Matki i Głowy wszystkich kościołów świata.' Symbol jedności Kościoła wokół Stolicy Piotrowej.", patronage="Jedność Kościoła", icon="⛪", died="—"),
    "11-11": SaintInfo(name="Św. Marcina z Tours", description="Biskup Tours (315–397), patron ubogich i Francji. Legenda: podzielił płaszcz z żebrakiem, w nocy ujrzał Chrystusa w tym płaszczu. Patron żołnierzy i żebraków.", patronage="Francja, żołnierze, żebracy, gęsi", icon="🧥", died="397"),
    "11-13": SaintInfo(name="Bł. Honorata Koźmińskiego", description="Polski kapucyn (1829–1916), założyciel 26 ukrytych zgromadzeń zakonnych działających w zaborze rosyjskim. Apostoł III zakonu i ludzi pracy.", patronage="Zakonnicy, Polska", icon="✝", died="1916"),
    "11-22": SaintInfo(name="Św. Cecylii", description="Dziewica i męczennica z Rzymu (II-III w.), patron muzyki kościelnej. Wg tradycji, śpiewała w swoim sercu podczas ślubu. Symbol piękna w służbie Boga.", patronage="Muzycy, śpiewacy, poeci", icon="🎵", died="230"),
    "11-24": SaintInfo(name="Śś. Andrzeja Dũng-Lạc i Towarzyszy", description="Wietnamskie Martyrologium — 117 męczenników (1745–1862). Misjonarze i wierni, którzy oddali życie za Chrystusa w Wietnamie. Beatyfikowani przez Jana Pawła II.", patronage="Wietnam, misjonarze", icon="🌺", died="1862"),
    "11-30": SaintInfo(name="Św. Andrzeja Apostoła", description="Apostoł i brat Piotra (I w.), patron Szkocji, Rumunii i Rosji. Pierwsza powołany przez Jezusa. Zamęczony na krzyżu X-kształtnym w Patras.", patronage="Szkocja, Rosja, rybacy, marynarze", icon="⚓", died="60"),
    # Grudzień
    "12-03": SaintInfo(name="Św. Franciszka Ksawerego", description="Jezuita (1506–1552), Apostoł Indii i Japonii. Ochrzcił setki tysięcy ludzi. 'Więcej, Panie, więcej' — modlitwa misjonarza pragnącego więcej dusz.", patronage="Misje, Indie, Japonia", icon="⚓", died="1552"),
    "12-06": SaintInfo(name="Św. Mikołaja", description="Biskup Miry (270–343), patron dzieci i żeglarzy. Słynął z tajemniczej hojności — nocami podrzucał posagi ubogim pannom. Wzór chrześcijańskiej filantropii.", patronage="Dzieci, marynarze, Rosja, prawnicy", icon="🎁", died="343"),
    "12-08": SaintInfo(name="Niepokalane Poczęcie NMP", description="Uroczystość Niepokalanego Poczęcia — dogmat z 1854 roku (Pius IX). Maryja od chwili poczęcia wolna od grzechu pierworodnego 'na mocy przewidzianych zasług Chrystusa'.", patronage="Polska, USA, Francja, zakonnicy", icon="🌸", died="—"),
    "12-12": SaintInfo(name="NMP z Guadalupe", description="Wspomnienie Matki Bożej z Guadalupe — objawień dla bł. Juana Diego w Meksyku (1531). Wizerunek na tilmie. Patronka Americas i nienarodzonych.", patronage="Ameryki, nienarodzeni, Meksyk", icon="🌹", died="—"),
    "12-13": SaintInfo(name="Św. Łucji", description="Dziewica i męczennica z Syrakuz (†304). W czasach Dioklecjana oddała majątek ubogim i zginęła za wiarę. Patron chorych na oczy — jej imię znaczy 'Światło'.", patronage="Niewidomi, elektrycy, Szwecja", icon="🕯", died="304"),
    "12-25": SaintInfo(name="Narodzenie Pańskie — Boże Narodzenie", description="Uroczystość Narodzenia Pańskiego. Słowo stało się Ciałem i zamieszkało wśród nas. 'Chwała na wysokości Bogu, a na ziemi pokój ludziom dobrej woli.'", patronage="—", icon="⭐", died="—"),
    "12-26": SaintInfo(name="Św. Szczepana", description="Pierwszy Męczennik (Protomartyr, I w.). Diakon Kościoła Jerozolimskiego, ukamienowany za wiarę. Przy jego egzekucji trzymał płaszcze Szaweł — przyszły Paweł.", patronage="Kamieniarze, diakoni, koronczarki", icon="✝", died="~36"),
    "12-27": SaintInfo(name="Św. Jana Apostoła i Ewangelisty", description="Umiłowany Uczeń Jezusa (I w.), jedyny Apostoł, który nie poniósł śmierci męczeńskiej. Ewangelia Jana, Listy, Apokalipsa. 'Bóg jest miłością.'", patronage="Teolodzy, pisarze, przyjaciele", icon="📖", died="~100"),
    "12-28": SaintInfo(name="Świętych Młodzianków", description="Wspomnienie Dzieci zabitych przez Heroda w Betlejem (I w.). Niewinne ofiary prześladowania Chrystusa. Kościół czci ich jako pierwszych niewinnych świadków.", patronage="Dzieci, chorzy, porzuceni niemowlęta", icon="🕊", died="I w."),
}

_DEFAULT_SAINT = SaintInfo(
    name="Wszyscy Święci i Błogosławieni",
    description="W każdym dniu roku Kościół czci wielu świętych i błogosławionych, których imion nie wymawia publicznie. Módlmy się przez ich wstawiennictwo.",
    patronage="Wszystkich wiernych",
    icon="✨",
    died="—",
)


def get_saint_today(d: date | None = None) -> SaintInfo:
    """Zwraca świętego dnia dla podanej daty (domyślnie dzisiaj)."""
    if d is None:
        d = date.today()
    key = d.strftime("%m-%d")
    return _SAINTS.get(key, _DEFAULT_SAINT)


def get_saint_for_date(month: int, day: int) -> SaintInfo:
    """Zwraca świętego dla konkretnej daty miesiąc-dzień."""
    key = f"{month:02d}-{day:02d}"
    return _SAINTS.get(key, _DEFAULT_SAINT)

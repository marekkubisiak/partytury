"""Logika programu: opis partii w PDF, kolejność partytury, duplikaty, eksport."""
import json
import os
import re
import zipfile

import pypdf
import pypdfium2 as pdfium

# =====================================================================
# Baza nazw instrumentów (polskie i angielskie nazwy oraz skróty)
# Każda nazwa sprowadzana jest do jednej postaci (np. "Sax alt 1", "AS 1",
# "1st Eb Alto Saxophone", "Saksofon altowy 1" -> "Alto Sax 1").
# Kolejność wpisów = kolejność sprawdzania (pierwszy pasujący wygrywa).
# Wzorce są pisane bez polskich znaków (tekst jest do nich sprowadzany).
# (nazwa, pozycja w partyturze, wzorzec)
# =====================================================================
INSTRUMENTS = [
    ("Okładka",          0,    r"oklad|\bcover\b|\bobsada\b|instrumentation"),
    ("Partytura",        1,    r"partytur|\bscore\b|conductor|dyrygent|\bfull\s*sc|\bcond\b"),
    # bas elektryczny zanim gitara ("bass guitar", "gitara basowa")
    ("Bass",             64,   r"bass\s*guitar|gitara\s*basow|electric\s*bass|\bebass\b|\be\.?\s*bass\b|"
                               r"\bel\.?\s*bass\b|bas\s*elektr|\bbas\s*el\b|\bb\.?\s*git\b|\bbgtr\b"),
    ("Guitar",           60,   r"guitar|gitar|\bgtr\b|\bgit\b|\bgt\b|\bagit\b|\begit\b|\bchit\b|"
                               r"\b[aej]\.?\s*gtr\b"),
    ("Piano",            62,   r"piano|fortepian|pianin|\bpno\b|\bpf\b|\bpfte\b|keyboard|\bkeys?\b|\bkbd\b|"
                               r"klawisz|klawiatur|rhodes|wurlitzer|celest|\bcel\b|apiano"),
    ("Organ",            62.5, r"\borgan|\borgany\b|hammond|\borg\b"),
    ("Synthesizer",      62.7, r"synth|syntezator"),
    ("Accordion",        63,   r"accord|akordeon|\bacc\b"),
    ("Vocal",            10,   r"\bvoc|\bvoice|\bvox\b|wokal|\bspiew|\bglos\b|\blyrics?\b|\btekst\b|"
                               r"\bchoir\b|\bchor\b|\bchorus\b|\bvce\b|singer"),
    ("Bass Clarinet",    23,   r"bass\s*clar|klarnet\s*basow|\bb\.?\s*cl\b|\bbcl\b|\bcl\.?\s*b\b|\bclb\b|"
                               r"bs\.?\s*cl|clarinetto\s*basso|basklarnet"),
    ("Bass Trombone",    49,   r"bass\s*(trombone|tbn|bone|tb|trb)\b|puzon\s*basow|\bb\.?\s*tbn\b|\bbtbn\b|"
                               r"\bbtrb\b|\bb\.?\s*bone\b|\btn\.?\s*b\b|\btrb\.?\s*basso|trombone\s*basso|"
                               r"\btbn\.?\s*basso"),
    ("Bass Sax",         35,   r"bass\s*sax|saksofon\s*basow"),
    ("Contrabassoon",    23.7, r"contra\s*bassoon|contrabassoon|kontrafagot|contrafag|\bc\.?-?\s*fg\b|\bcbsn\b|\bcbssn\b"),
    ("Euphonium",        49.5, r"euphon|eufon|baritone\s*horn|\beuph\b|sakshorn\s*baryton"),
    ("English Horn",     21.5, r"english\s*horn|cor\s*anglais|\bcora\b|\bc\.?\s*a\b|\be\.?\s*h\b|"
                               r"eng\.?\s*hn|rozek\s*angiel|corno\s*inglese"),
    ("Flute",            20,   r"alto\s*flute|flet\s*altow|\bafl\b"),
    ("Cello",            76,   r"\bcell|violoncel|wiolonczel|\bvc\b|\bvcl\b|\bvlc\b|\bvcs\b"),
    ("Viola",            74,   r"\bviola\b|\bviole\b|\bvla\b|\bvle\b|\bva\b|altowk|\bvl\b(?!\s*\.?\s*[1-4i])"),
    ("Violin",           70,   r"violin|skrzyp|\bvln\b|\bvn\b|\bvni\b|\bvl\b|\bvi\b(?=\s*\.?\s*[1-4i])"),
    ("Clarinet/Alto Sax", 25.5, r"clar\w*\s*/\s*alto|klarnet\s*/\s*alt"),
    # puzony przed saksofonami ("Tenor Trombone", "puzon tenorowy")
    ("Trombone",         45,   r"tromb|puzon|\btbn\b|\btb\b|\btrb\b|\bbone\b|\btn\b|\btrbn\b|\bpos\b|posaune|"
                               r"\btbne\b"),
    ("Soprano Sax",      24,   r"sopran\w*\s*sax|sax\w*\s*sopran|\bsop\.?\s*sax|\bs\.?\s*sax|\bs\.?\s*sx\b|"
                               r"\bss\b|\bssx\b|\bsoprano\b|\bsopran\b|\bsop\b"),
    ("Alto Sax",         26,   r"\balto\b|\balt\b|altow|\bas\b|\basx\b|\ba\.?\s*sax|\ba\.?\s*sx\b|\basax\b"),
    ("Tenor Sax",        30,   r"\btenor|tenorow|\bten\b|\bts\b|\btsx\b|\bt\.?\s*sax|\bt\.?\s*sx\b|\btsax\b"),
    ("Baritone Sax",     34,   r"\bbari|barit|baryton|\bbs\b|\bbsx\b|\bb\.?\s*sax|\bb\.?\s*sx\b|\bbsax\b"),
    ("Saxophone",        28,   r"\bsax|saksofon|\bsx\b"),
    ("Piccolo",          18,   r"piccolo|pikolo|\bpicc?\b|ottavino"),
    ("Flute",            20,   r"\bflut|\bflet|\bfl\b|\bflt\b|\bflauto|\bflauti\b"),
    ("Oboe",             21,   r"\boboe|\boboj|\bob\b|\bobs\b"),
    ("Clarinet",         22,   r"clar|klarnet|\bcl\b|\bkl\b|\bcls\b|\bclt\b"),
    ("Bassoon",          23.5, r"bassoon|fagot|\bbsn\b|\bbssn\b|\bfg\b|\bfag\b|\bbn\b"),
    ("Horn",             38,   r"french\s*horn|\bhorns?\b|waltorni|\bhn\b|\bhns\b|\bhrn\b|\bcor\b|\bcr\b|"
                               r"\bcorni?\b|\bwalt\b|\brog\b"),
    ("Flugelhorn",       40.6, r"flugel|flgh|\bflg\b|\bfgh\b|skrzydlowk"),
    ("Cornet",           40.8, r"cornet|kornet|\bcrnt\b|\bcnt\b"),
    ("Trumpet",          40,   r"trump|tromp|trabk|\btpt\b|\btpts\b|\btp\b|\btr\b|\btrp\b|\btrpt\b|\btrbe\b|"
                               r"\btromba\b|\bbb\s*tpt\b"),
    ("Tuba",             50,   r"\btuba|\btba\b|sousaphon|suzafon"),
    ("Bass",             64,   r"kontrabas|contrabass|contrabbass|double\s*bass|upright\s*bass|string\s*bass|"
                               r"acoustic\s*bass|\bd\.?\s*b\b|\bdb\b|\bcb\b|\bkb\b|\bbass\b|\bbas\b|\bbasso\b|"
                               r"\bbs\b|\ba\.\s*b\.|\bbass\s*\d"),
    ("Drums",            66,   r"drum|perkusja|zestaw\s*perk|\bdr\b|\bdrs\b|\bdms\b|\bd\.\s*s\.|\bbatt?\b|"
                               r"\bbatteria\b|schlagzeug|\bperk\b"),
    ("Timpani",          69.5, r"timpan|\btimp\b|\btmp\b|kotl"),
    ("Bells",            68.2, r"\bbells?\b|dzwonk|glock|carillon|dzwony"),
    ("Vibraphone",       68.4, r"vibra|wibraf|\bvib\b|\bvibr\b"),
    ("Xylophone",        68.5, r"xylo|ksylof|\bxyl\b"),
    ("Marimba",          68.6, r"marimb|\bmar\b"),
    ("Percussion",       68,   r"perc|perkusjonal|instr\w*\s*perkus|triang|trojkat|conga|kong|bongo|shaker|"
                               r"tambour|tamburyn|cabasa|claves|cowbell|\baux\b|guiro|cymbal|talerz"),
    ("Harp",             69.8, r"\bharp|harfa|\barpa\b|\bhp\b|\bhfe\b"),
]
_INSTR = [(n, pos, re.compile(pat)) for n, pos, pat in INSTRUMENTS]

# Lista podpowiedzi w programie (można wpisać dowolną inną nazwę – po polsku lub angielsku)
PART_NAMES = [
    "Okładka", "Partytura", "Vocal", "Piccolo", "Flute", "Oboe", "English Horn",
    "Clarinet", "Bass Clarinet", "Bassoon", "Soprano Sax",
    "Alto Sax 1", "Alto Sax 2", "Tenor Sax 1", "Tenor Sax 2", "Baritone Sax",
    "Horn 1", "Horn 2", "Trumpet 1", "Trumpet 2", "Trumpet 3", "Trumpet 4", "Flugelhorn",
    "Trombone 1", "Trombone 2", "Trombone 3", "Trombone 4", "Bass Trombone", "Euphonium", "Tuba",
    "Guitar", "Piano", "Organ", "Synthesizer", "Accordion", "Bass", "Drums",
    "Percussion", "Bells", "Vibraphone", "Timpani", "Harp",
    "Violin 1", "Violin 2", "Viola", "Cello", "Inne",
]

# Grupy do wyodrębniania (pozycje z INSTRUMENTS)
CATEGORIES = {
    "Bas / kontrabas": {64},
    "Fortepian / keyboard": {62, 62.5, 62.7},
    "Gitara": {60},
    "Perkusja": {66},
    "Perkusjonalia (dzwonki, wibrafon...)": {68, 68.2, 68.4, 68.5, 68.6, 69.5},
    "Wokal": {10},
    "Partytura": {1},
    "Saksofony (wszystkie)": {24, 25.5, 26, 28, 30, 34, 35},
    "Trąbki (wszystkie)": {40, 40.6, 40.8},
    "Puzony (wszystkie)": {45, 49},
    "Smyczki (wszystkie)": {70, 74, 76},
}

_ORDINALS = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5, "6th": 6,
             "ii": 2, "iii": 3, "iv": 4, "v": 5,
             "pierwszy": 1, "pierwsza": 1, "drugi": 2, "druga": 2, "trzeci": 3, "trzecia": 3,
             "czwarty": 4, "czwarta": 4, "first": 1, "second": 2, "third": 3, "fourth": 4,
             "lead": 1}
_FOLD = str.maketrans("ąćęłńóśźżĄĆĘŁŃÓŚŹŻ", "acelnoszzACELNOSZZ")


def fold(text):
    """Małe litery, bez polskich znaków, kropki/ukośniki/myślniki jako spacje wokół."""
    t = (text or "").translate(_FOLD).lower().replace("♭", "b").replace("♯", "#")
    return " " + re.sub(r"\s+", " ", t) + " "


def _number(name):
    n = fold(name)
    m = re.search(r"(?<![\d.])([1-6])(?![\d])", n)
    if m:
        return int(m.group(1))
    for w in re.findall(r"[a-z0-9]+", n):
        if w in _ORDINALS:
            return _ORDINALS[w]
    m = re.search(r"\b(i{1,3}|iv)\b(?!\s*sax)", n)        # Tr. I, Cl. II
    if m and re.search(r"\b(vn|vl|vni|cl|fl|ob|fg|cr|cor|tr|tn|tbn|tpt|hn|sax|kl)\b", n):
        return {"i": 1, "ii": 2, "iii": 3, "iv": 4}[m.group(1)]
    return 0


def canonical(name):
    """(nazwa ujednolicona, pozycja w partyturze) albo (None, 90)."""
    n = fold(name)
    for canon, pos, rx in _INSTR:
        if rx.search(n):
            return canon, pos
    return None, 90


_SPECIFIC = {"Bass Clarinet", "Bass Trombone", "Bass Sax", "Contrabassoon", "English Horn", "Euphonium"}


def _hits(name):
    """Wszystkie instrumenty wymienione w nazwie (np. 'Tenor 1/Flute' -> Tenor Sax, Flute).
    Dla nazw złożonych typu 'Bass Clarinet' liczy się tylko ten jeden instrument."""
    main = canonical(name)
    if main[0] in _SPECIFIC:
        return {main}
    n = fold(name)
    return {(canon, pos) for canon, pos, rx in _INSTR if rx.search(n)}


def standard_name(name):
    """'Sax alt 1' -> 'Alto Sax 1'; nieznana nazwa zostaje bez zmian."""
    canon, _ = canonical(name)
    if not canon:
        return name
    k = _number(name)
    return f"{canon} {k}" if k else canon


def section(name):
    """Pozycja grupy instrumentów w partyturze (mniejsza = wyżej)."""
    return canonical(name)[1]


def order_key(name):
    return (section(name), _number(name))


def matches(name, query):
    """Czy partia 'name' pasuje do szukanej: grupy z CATEGORIES albo nazwy instrumentu
    wpisanej po polsku lub angielsku (np. 'Sax alt 1', 'Trąbka 2', 'klarnet basowy')."""
    hits = _hits(name)
    if query in CATEGORIES:
        poss = CATEGORIES[query]
        main = canonical(name)[1]
        if main in (45, 49, 23, 35) and not poss & {45, 49, 23, 35}:
            return False                       # np. puzon basowy to nie "bas"
        return any(pos in poss for _, pos in hits)
    qc, _ = canonical(query)
    if qc:
        qn = _number(query)
        if not any(c == qc for c, _ in hits):
            return False
        return qn == 0 or _number(name) == qn
    return fold(query).strip() in fold(name)


def same_part(a, b):
    """Czy dwie nazwy oznaczają tę samą partię (do ostrzeżeń o powtórzeniach)."""
    return standard_name(a).lower() == standard_name(b).lower()


def next_name(name):
    """Trumpet 1 -> Trumpet 2 (podpowiedź następnej partii)."""
    m = re.search(r"(\d)(?!.*\d)", name)
    if m and int(m.group(1)) < 4:
        return name[:m.start()] + str(int(m.group(1)) + 1) + name[m.end():]
    return name


class Project:
    """Jeden plik PDF z opisem: gdzie zaczyna się każda partia i które strony usunąć."""

    def __init__(self, path):
        self.path = path
        self.json_path = path + ".partie.json"
        self.n = len(pypdf.PdfReader(path).pages)
        self.starts = {}      # nr strony (od 1) -> nazwa partii
        self.excluded = set()  # strony do pominięcia
        self.dups = {}        # strona -> wcześniejsza identyczna strona (podpowiedź)
        self._pdfium = None
        self.load()

    # --- zapis/odczyt opisu ---
    def load(self):
        if os.path.exists(self.json_path):
            with open(self.json_path, encoding="utf-8") as f:
                d = json.load(f)
            self.starts = {int(k): v for k, v in d.get("starts", {}).items() if 1 <= int(k) <= self.n}
            self.excluded = {int(p) for p in d.get("excluded", []) if 1 <= int(p) <= self.n}

    @property
    def described(self):
        return bool(self.starts)

    def save(self):
        d = {"pdf": os.path.basename(self.path), "pages": self.n,
             "starts": {str(k): v for k, v in sorted(self.starts.items())},
             "excluded": sorted(self.excluded)}
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)

    # --- podgląd ---
    def render(self, page, scale):
        if self._pdfium is None:
            self._pdfium = pdfium.PdfDocument(self.path)
        return self._pdfium[page - 1].render(scale=scale).to_pil()

    def close(self):
        if self._pdfium is not None:
            self._pdfium.close()
            self._pdfium = None

    # --- partie ---
    def part_of(self, page):
        """(nazwa partii, czy to pierwsza strona partii)"""
        for p in range(page, 0, -1):
            if p in self.starts:
                return self.starts[p], p == page
        return None, False

    def parts(self):
        """Lista (nazwa, [strony]) w kolejności z pliku, bez usuniętych stron."""
        out = []
        cur = None
        for p in range(1, self.n + 1):
            if p in self.starts:
                cur = [self.starts[p], []]
                out.append(cur)
            if p in self.excluded:
                continue
            if cur is None:
                cur = ["(bez nazwy)", []]
                out.append(cur)
            cur[1].append(p)
        return [(n, ps) for n, ps in out if ps]

    def ordered_parts(self):
        parts = self.parts()
        keys, prev = [], (-1, 0)
        for name, _ in parts:
            if name.startswith(UNKNOWN) or name == "(bez nazwy)":
                k = prev          # nierozpoznana partia zostaje za poprzednią
            else:
                k = order_key(name)
            keys.append(k)
            prev = k
        order = sorted(range(len(parts)), key=lambda i: keys[i])
        return [parts[i] for i in order]

    def repeated_names(self):
        seen, rep = set(), set()
        for n, _ in self.parts():
            if n.startswith(UNKNOWN) or n == "(bez nazwy)":
                continue
            key = standard_name(n).strip().lower()
            if key in seen:
                rep.add(n)
            seen.add(key)
        return sorted(rep)

    def unnamed_pages(self):
        for n, ps in self.parts():
            if n == "(bez nazwy)":
                return ps
        return []

    # --- duplikaty ---
    def find_duplicates(self, small_images, threshold=1.5, progress=None):
        """small_images: {strona: mały obraz PIL}. Szuka stron identycznych z wcześniejszymi.
        Etap 1: szybkie porównanie miniatur. Etap 2: dokładne porównanie górnej części
        strony (tytuł i nazwa instrumentu) - partie o tych samych nutach, ale z inną
        nazwą (np. Trombone 3 / Trombone 4) nie są duplikatami."""
        import numpy as np
        arrs = {p: np.asarray(im.convert("L").resize((60, 85)), dtype=np.float32)
                for p, im in small_images.items()}
        detail = {}

        def top(p):
            if p not in detail:
                a = np.asarray(self.render(p, 0.6).convert("L"), dtype=np.float32)
                detail[p] = a[: int(a.shape[0] * 0.35)]
            return detail[p]

        self.dups = {}
        pages = sorted(arrs)
        for i, p in enumerate(pages):
            if progress:
                progress(i + 1, len(pages))
            for q in pages[:i]:
                if q in self.dups:
                    continue
                if float(np.abs(arrs[p] - arrs[q]).mean()) >= threshold:
                    continue
                a, b = top(p), top(q)
                if a.shape == b.shape and int((np.abs(a - b) > 100).sum()) <= 5:
                    self.dups[p] = q
                    break
        return self.dups

    # --- eksport ---
    def _write(self, parts, out_path):
        reader = pypdf.PdfReader(self.path)
        w = pypdf.PdfWriter()
        idx = 0
        for name, ps in parts:
            start = idx
            for p in ps:
                w.add_page(reader.pages[p - 1])
                idx += 1
            w.add_outline_item(name, start)
        with open(out_path, "wb") as f:
            w.write(f)
        return idx

    def export_ordered(self, out_path):
        return self._write(self.ordered_parts(), out_path)

    def export_pages(self, pages, out_path):
        """Wybrane strony (w kolejności numerów) jako jeden PDF, z zakładkami partii."""
        reader = pypdf.PdfReader(self.path)
        w = pypdf.PdfWriter()
        last = None
        for i, p in enumerate(sorted(set(pages))):
            w.add_page(reader.pages[p - 1])
            name, _ = self.part_of(p)
            if name and name != last:
                w.add_outline_item(name, i)
            last = name
        with open(out_path, "wb") as f:
            w.write(f)
        return len(w.pages)

    def export_matching(self, query, out_path):
        parts = [(n, ps) for n, ps in self.ordered_parts() if matches(n, query)]
        if not parts:
            return 0
        return self._write(parts, out_path)


def safe_name(s):
    return re.sub(r'[\\/:*?"<>|]+', "_", s).strip() or "partia"


def make_zip(files, zip_path, folder_in_zip=""):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, os.path.join(folder_in_zip, os.path.basename(f)))


# =====================================================================
# Automatyczne rozpoznawanie nazw partii (darmowy Tesseract OCR)
# =====================================================================
import shutil
import subprocess
import tempfile

# Ostrzejsze wzorce niż przy ręcznie wpisanych nazwach - OCR produkuje dużo śmieci,
# więc pomijamy bardzo krótkie skróty (dr, fl, cl...), które łatwo trafić przypadkiem.
_OCR_RULES = [
    (r"partytur|\bscore\b|conductor", 1),
    (r"bass\s*guitar|gitara\s*basow|\bebass\b|\bel\.?\s*bass\b|electric\s*bass", 64),
    (r"guitar|gitar|\bgtr\b|\bagit\b", 60),
    (r"piano|fortepian|\bpno\b|apiano|keyboard|celest|klawisz", 62),
    (r"\borgan\b|\borgany\b|hammond", 62.5),
    (r"accordion|akordeon", 63),
    (r"\bvocal|\bvoice\b|wokal|\bvoc\b", 10),
    (r"bass\s*clar|klarnet\s*basow", 23),
    (r"bass\s*(trombone|tbn|bone)|puzon\s*basow", 49),
    (r"tromb|\btbn\b|\btb\b(?=\s*\d)|\bbone\b(?=\s*\d)|puzon", 45),
    (r"soprano?\s*sax|\bsop\b|sopran", 24),
    (r"clarinet.{0,4}alto", 25.5),
    (r"\balto\b|alto\s*sax|altowy|sax\w*\s*alt\b|\bas\b(?=\s*[12])", 26),
    (r"\btenor\b|tenorowy|sax\w*\s*ten\b|\bten\.?\s*sax|\bts\b(?=\s*[12])", 30),
    (r"\bbari\b|baritone|barytone|barytonowy|bari\.?\s*sax|\bbs\b\s*sax", 34),
    (r"piccolo", 18),
    (r"\bflute\b|\bflet\b|\bfl\.?\s*$", 20),
    (r"\boboe\b|\boboj\b", 21),
    (r"clarinet|klarnet", 22),
    (r"bassoon|fagot", 23.5),
    (r"flugel|skrzydlowk", 40.6),
    (r"trumpet|tr[uv]mpet|\btpt\b|\btp\b(?=\s*\d)|trabka|trąbka|trabki", 40),
    (r"french\s*horn|\bhorn\b|waltorni", 38),
    (r"euphon|eufon", 49.5),
    (r"\btuba\b", 50),
    (r"kontrabas|contrabass|double\s*bass|\bbass\b(?!\s*(trombone|tbn|bone|clarinet))|\bbas\b", 64),
    (r"\bdrums?\b|\bdrumset\b|perkusja\b|\bdrum\s*set|\b[o0d]r[uvl]{1,2}ms\b", 66),
    (r"timpani|kotly", 69.5),
    (r"percussion|\bperc\b|perkusjonal|\bbells\b|triangle|glockenspiel|vibraphone|dzwonki|xylophone|marimba", 68),
    (r"\bharp\b|harfa", 69.8),
    (r"violoncello|\bcello\b|\bvcl\b|\bvc\b|wiolonczel", 76),
    (r"\bviola\b|\bvla\b|altowka|altówka", 74),
    (r"violin|\bvln\b|\bvl\b(?=\s*\d)|skrzypce", 70),
]
_NUMBERED = {26, 30, 40, 45, 70, 38, 22, 20}
_CANON = {1: "Partytura", 10: "Vocal", 18: "Piccolo", 20: "Flute", 21: "Oboe", 22: "Clarinet", 23: "Bass Clarinet",
          23.5: "Bassoon", 24: "Soprano Sax", 25.5: "Clarinet/Alto Sax", 26: "Alto Sax", 30: "Tenor Sax",
          34: "Baritone Sax", 38: "Horn", 40: "Trumpet", 40.6: "Flugelhorn", 45: "Trombone", 49: "Bass Trombone",
          49.5: "Euphonium", 50: "Tuba", 60: "Guitar", 62: "Piano", 62.5: "Organ", 63: "Accordion", 64: "Bass",
          66: "Drums", 68: "Percussion", 69.5: "Timpani", 69.8: "Harp", 70: "Violin", 74: "Viola", 76: "Cello"}
_ORD_RE = r"(1st|2nd|3rd|4th|1ST|2ND|3RD|4TH|ist|lst|2no|3ro|4rh)"


def find_tesseract():
    """Ścieżka do tesseract.exe albo None."""
    import sys
    if getattr(sys, "frozen", False):            # wersja zainstalowana (Windows setup.exe / Mac .app)
        here = os.path.dirname(sys.executable)
        for p in (os.path.join(here, "tesseract", "tesseract.exe"),
                  os.path.join(here, "tesseract", "tesseract"),
                  os.path.join(here, "..", "Resources", "tesseract", "tesseract")):
            if os.path.isfile(p):
                return os.path.normpath(p)
    p = shutil.which("tesseract")
    if p:
        return p
    cands = [os.path.expandvars(r"%LOCALAPPDATA%\Partytury\tesseract\tesseract.exe"),
             r"C:\Program Files\Tesseract-OCR\tesseract.exe",
             r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
             os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
             "/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"]
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def ocr_image(img, tesseract_path, psm=11):
    """Tekst z obrazu PIL (wywołuje tesseract.exe, bez okien konsoli)."""
    fd, tmp = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        img.save(tmp)
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
        env = None
        td = os.path.join(os.path.dirname(tesseract_path), "tessdata")
        if os.path.isdir(td):                          # dołączone dane języka (np. w wersji na Maca)
            env = dict(os.environ, TESSDATA_PREFIX=td)
        r = subprocess.run([tesseract_path, tmp, "stdout", "--psm", str(psm), "-l", "eng"],
                           capture_output=True, timeout=120, creationflags=flags, env=env)
        return r.stdout.decode("utf-8", "replace")
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _ord_number(s):
    s = s.lower()
    for k, v in (("1", 1), ("ist", 1), ("lst", 1), ("2", 2), ("3", 3), ("4", 4)):
        if s.startswith(k):
            return v
    return 0


_VOCAB = ["trumpet", "trombone", "saxophone", "baritone", "tenor", "alto", "soprano",
          "saksofon", "trabka", "puzon", "fortepian", "gitara", "perkusja", "skrzypce",
          "wiolonczela", "kontrabas", "klarnet", "waltornia", "horn", "oboe", "bassoon",
          "guitar", "piano", "drums", "bass", "vocal", "voice", "flute", "clarinet",
          "violin", "viola", "cello", "violoncello", "tuba", "percussion", "bells",
          "conductor", "score", "triangle"]


def _fix_words(low):
    """Poprawia słowa przekręcone przez OCR (np. 'teumpet' -> 'trumpet')."""
    import difflib

    def fix(m):
        w = m.group(0)
        if len(w) < 5 or w in _VOCAB:
            return w
        cut = 0.72 if len(w) >= 6 else 0.75
        c = [v for v in difflib.get_close_matches(w, _VOCAB, n=3, cutoff=cut) if v[0] == w[0]]
        return c[0] if c else w
    low = re.sub(r"\btp[l1i]\b", "tp 1", low)
    low = re.sub(r"\btb[hn]\b", "tb", low)
    return re.sub(r"[a-z]+", fix, low)


def detect_instrument(text, stop_words=()):
    """Z tekstu nagłówka strony zgaduje nazwę partii.
    Zwraca (nazwa albo None, liczba różnych grup instrumentów w tekście)."""
    found = []
    sections = set()
    for line in text.splitlines():
        low = fold(line)
        for w in stop_words:
            low = re.sub(r"\b%s\b" % re.escape(w), " " * len(w), low)
        if len(low.strip()) < 2:
            continue
        low = _fix_words(low)
        both_gp = re.search(_OCR_RULES[1][0], low) and re.search(_OCR_RULES[2][0], low)
        for pat, sec in _OCR_RULES:
            m = re.search(pat, low)
            if not m:
                continue
            sections.add(sec)
            name = _CANON[sec]
            if both_gp and sec in (60, 62):
                name = "Guitar/Piano"
            if sec in _NUMBERED:
                after = re.match(r"[\s.\-]*(?:in\s+[a-z]b?\s*)?(?:sax\w*\s*)?([1-4])(?!\d)", low[m.end():])
                before = re.search(_ORD_RE + r"[\s.]*(?:[a-z]b?\s+)?(?:\w+\s+)?$", low[:m.start()], re.I)
                n = int(after.group(1)) if after else (_ord_number(before.group(1)) if before else 0)
                if n:
                    name = f"{name} {n}"
            found.append(name)
            break
    if not found:
        return None, set()
    return found[0], set(found)


_TITLE_HINT = re.compile(r"arrang|\barr\b|words\s+and\s+music|music\s+by|\bmuz\.|opracow|"
                         r"recorded\s+by|composed|walrus|hal\s*leonard|publishing", re.I)


def is_title_page(text, title_words_list):
    """Pierwsza strona partii zwykle ma tytuł utworu i 'Arranged by'."""
    low = text.lower()
    if _TITLE_HINT.search(low):
        return True
    if title_words_list:
        hit = sum(1 for w in title_words_list if w in low)
        return hit >= max(2, (len(title_words_list) + 1) // 2)
    return False


def title_words(pdf_path):
    """Słowa z nazwy pliku (tytuł utworu) - nie mogą być brane za nazwę instrumentu,
    np. 'Bells' w 'Jingle Bells'."""
    base = os.path.splitext(os.path.basename(pdf_path))[0].lower()
    skip = {"instr", "lub", "the", "and", "do", "razem", "zaspiewania", "vocal", "solo", "zapasowy",
            "puzon", "basowy", "partie", "partytura", "pdf"}
    return [w for w in re.split(r"[^a-ząćęłńóśźż]+", base) if len(w) >= 3 and w not in skip]


def ocr_crops(project, page):
    """Dwa wycinki strony do OCR: nagłówek (tytuł, nazwa instrumentu) i lewy margines
    (nazwa instrumentu przy pierwszej pięciolinii)."""
    im = project.render(page, 2.0).convert("L")
    w, h = im.size
    if w > h * 1.15:            # strona pozioma (np. obrócona partytura)
        head = im.crop((0, 0, w, int(h * 0.45)))
    else:
        head = im.crop((0, 0, w, int(h * 0.33)))
    side = im.crop((0, int(h * 0.15), int(w * 0.24), int(h * 0.55)))
    return head, side


def recognize_texts(head_text, side_text, pdf_path):
    return analyze_page_texts(head_text, side_text, title_words(pdf_path))


UNKNOWN = "?"


_GROUPS = ("Alto Sax", "Tenor Sax", "Trumpet", "Trombone", "Violin")


def _split(name):
    m = re.match(r"(.*?)\s+([1-4])$", name or "")
    return (m.group(1), int(m.group(2))) if m else (name or "", 0)


def _fix_numbers(starts):
    """Numeracja w grupach (np. trąbki 1-4): OCR myli cyfry (1->7/4/L, 3->5/$),
    więc kolejne partie tej samej grupy dostają spójne numery 1, 2, 3, 4."""
    items = sorted(starts.items())
    i = 0
    while i < len(items):
        base, _ = _split(items[i][1])
        j = i
        while j + 1 < len(items) and _split(items[j + 1][1])[0] == base:
            j += 1
        k = j - i + 1
        if base in _GROUPS and 2 <= k <= 4:
            nums = [_split(items[t][1])[1] for t in range(i, j + 1)]
            # spróbuj tylko uzupełnić brakujące numery, zachowując odczytane
            filled, prev, ok = [], 0, True
            for idx, n in enumerate(nums):
                if n == 0:
                    n = prev + 1
                left = k - idx - 1
                if n <= prev or n + left > 4:
                    ok = False
                    break
                filled.append(n)
                prev = n
            if not ok:
                filled = list(range(1, k + 1))
            for t, n in zip(range(i, j + 1), filled):
                starts[items[t][0]] = f"{base} {n}"
        i = j + 1


def guess_starts(pages):
    """pages: {strona: (rozpoznana nazwa albo None, czy strona tytułowa, czy partytura)}.
    Zwraca {strona: nazwa} początków partii. Nierozpoznana partia dostaje nazwę '?'.
    Nowa partia zaczyna się na stronie tytułowej; nazwa odczytana na dalszych stronach
    tylko uzupełnia/poprawia nazwę bieżącej partii."""
    starts, cur_p, cur = {}, None, None
    for p in sorted(pages):
        name, title, score = pages[p]
        if score:
            if cur != "Partytura":
                starts[p] = cur = "Partytura"
                cur_p = p
            continue
        cb, cn = _split(cur)
        nb, nn = _split(name)
        if title and not (name and name == cur and nn):
            starts[p] = cur = name or UNKNOWN
            cur_p = p
            continue
        if not name:
            continue                                   # ciąg dalszy bieżącej partii
        if cur is None or cur == "Partytura" and nb != "Partytura":
            starts[p] = cur = name                     # pierwsza partia w pliku bez tytułu
            cur_p = p
        elif cur == UNKNOWN:
            starts[cur_p] = cur = name                 # uzupełnij nazwę ze strony 2.
        elif nb != cb:
            starts[p] = cur = name                     # inny instrument bez strony tytułowej
            cur_p = p
        elif nn and not cn:
            starts[cur_p] = cur = name                 # dopisz numer (np. Trumpet -> Trumpet 2)
    # nierozpoznane partie zaraz po "Trumpet 1" itp. -> Trumpet 2, 3, 4
    items = sorted(starts.items())
    for i, (p, n) in enumerate(items):
        m = re.match(r"(Alto Sax|Tenor Sax|Trumpet|Trombone|Violin) ([1-3])$", n)
        if not m:
            continue
        k = int(m.group(2))
        j = i + 1
        while j < len(items) and items[j][1] == UNKNOWN and k < 4:
            k += 1
            starts[items[j][0]] = f"{m.group(1)} {k}"
            items[j] = (items[j][0], starts[items[j][0]])
            j += 1
    _fix_numbers(starts)
    return starts

def analyze_page_texts(header_text, side_text, title_words_list):
    """Łączy odczyt nagłówka i lewego marginesu -> (nazwa, strona tytułowa?, partytura?)."""
    name, nsec = detect_instrument(header_text, title_words_list)
    name2, nsec2 = detect_instrument(side_text, title_words_list)
    if name is None or (name2 and name2.startswith(name) and len(name2) > len(name)):
        name = name2 or name
    score = bool(re.search(r"\bscore\b|conductor|partytura", header_text, re.I)) or len(nsec | nsec2) >= 4
    return name, is_title_page(header_text, title_words_list), score

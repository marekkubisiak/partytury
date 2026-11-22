"""Logika programu: opis partii w PDF, kolejność partytury, duplikaty, eksport."""
import json
import os
import re
import zipfile

import pypdf
import pypdfium2 as pdfium

# Lista podpowiedzi w kolejności partytury (można wpisać dowolną inną nazwę).
PART_NAMES = [
    "Okładka", "Partytura", "Vocal", "Flute", "Clarinet", "Soprano Sax",
    "Alto Sax 1", "Alto Sax 2", "Tenor Sax 1", "Tenor Sax 2", "Baritone Sax",
    "Trumpet 1", "Trumpet 2", "Trumpet 3", "Trumpet 4",
    "Trombone 1", "Trombone 2", "Trombone 3", "Trombone 4", "Bass Trombone", "Tuba",
    "Guitar", "Piano", "Bass", "Drums", "Percussion", "Bells",
    "Violin 1", "Violin 2", "Viola", "Cello", "Kontrabas", "Inne",
]

_ORDINALS = {"1st": 1, "2nd": 2, "3rd": 3, "4th": 4, "5th": 5,
             "i": 1, "ii": 2, "iii": 3, "iv": 4}

# (wzorzec, pozycja w partyturze) - sprawdzane po kolei, pierwszy pasujący wygrywa
_RULES = [
    (r"okład|oklad|cover|okładka", 0),
    (r"partytur|score|conductor|dyrygent", 1),
    (r"guit|gitar|\bgtr\b|\bgit\b|agit", 60),
    (r"piano|fortepian|pno|keyboard|keys|celest|apiano", 62),
    (r"voc|voice|wokal|śpiew|spiew|tekst|lyrics|chór|chor", 10),
    (r"\bsolo\b", 12),
    (r"sopr?an", 24),
    (r"clar.*alto", 25.5),
    (r"alto|\balt\b|altowy", 26),
    (r"tenor|\bten\b", 30),
    (r"bari|barit|baryton", 34),
    (r"flut|flet|piccolo|\bfl\b", 20),
    (r"clar|klarnet|\bcl\b", 22),
    (r"tr[uą]mp|trąbk|trabk|\btpt?\b|flugel|cornet", 40),
    (r"bass\s*(trombone|tbn|bone)|puzon\s*basowy|\bb\.?\s*tbn", 49),
    (r"tromb|\btbn?\b|\bbone\b|puzon", 45),
    (r"tuba", 50),
    (r"kontrabas|contrabass|double\s*bass|\bcb\b|ebass|el\.?\s*bass|\bbass\b|\bbas\b|bas\s*elektr", 64),
    (r"drum|perkusj|\bdr\b|\bdrs\b", 66),
    (r"perc|bells|dzwon|triang|trójk|trojk|vib|glock|marimb|timp|kotł", 68),
    (r"cell|vcl|wiolonczel", 76),
    (r"viola|\bvla\b|altówk|altowk", 74),
    (r"viol|vln|skrzyp", 70),
]

# Kategorie do wyodrębniania partii z wielu plików
CATEGORIES = {
    "Bas / kontrabas": 64,
    "Fortepian": 62,
    "Gitara": 60,
    "Perkusja": 66,
    "Wokal": 10,
    "Partytura": 1,
    "Trąbki (wszystkie)": 40,
    "Puzony (wszystkie)": 45,
}


def _number(name):
    n = name.lower()
    for w in re.findall(r"\b\w+\b", n):
        if w in _ORDINALS and w not in ("i",):
            return _ORDINALS[w]
    m = re.search(r"(?<!\d)([1-6])(?!\d)", n)
    return int(m.group(1)) if m else 0


def section(name):
    """Pozycja grupy instrumentów w partyturze (mniejsza = wyżej)."""
    n = name.lower()
    for pat, pos in _RULES:
        if re.search(pat, n):
            return pos
    return 90


def order_key(name):
    return (section(name), _number(name))


def matches(name, query):
    """Czy partia pasuje do kategorii (z CATEGORIES) lub wpisanego tekstu."""
    if query in CATEGORIES:
        sec = CATEGORIES[query]
        s = section(name)
        if sec == 45:
            return s in (45, 49)
        if s in (45, 49):          # np. "Bass Trombone" to nie bas
            return False
        n = name.lower()
        return s == sec or any(re.search(pat, n) for pat, pos in _RULES if pos == sec)
    return query.strip().lower() in name.lower()


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
            key = n.strip().lower()
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
    (r"guitar|gitar|\bgtr\b|\bagit\b", 60),
    (r"piano|fortepian|\bpno\b|apiano|keyboard|celest", 62),
    (r"\bvocal|\bvoice\b|wokal|\bvoc\b", 10),
    (r"soprano?\s*sax|\bsop\b|sopran", 24),
    (r"clarinet.{0,4}alto", 25.5),
    (r"\balto\b|alto\s*sax|\bas\b(?=\s*[12])", 26),
    (r"\btenor\b|\bten\.?\s*sax|\bts\b(?=\s*[12])", 30),
    (r"\bbari\b|baritone|barytone|bari\.?\s*sax|\bbs\b\s*sax", 34),
    (r"\bflute\b|\bflet\b|piccolo|\bfl\.?\s*$", 20),
    (r"clarinet|klarnet", 22),
    (r"trumpet|tr[uv]mpet|\btpt\b|\btp\b(?=\s*\d)|trąbk|flugel", 40),
    (r"bass\s*(trombone|tbn|bone)|puzon\s*basowy", 49),
    (r"trombone|tromb0ne|\btbn\b|\btb\b(?=\s*\d)|\bbone\b(?=\s*\d)|puzon", 45),
    (r"\btuba\b", 50),
    (r"kontrabas|contrabass|double\s*bass|\bebass\b|\bel\.?\s*bass\b|\bbass\b(?!\s*(trombone|tbn|bone|clarinet))|\bbas\b", 64),
    (r"\bdrums?\b|\bdrumset\b|perkusja|\bdrum\s*set|\b[o0d]r[uvl]{1,2}ms\b", 66),
    (r"percussion|\bperc\b|\bbells\b|triangle|glockenspiel|vibraphone|dzwonki", 68),
    (r"violoncello|\bcello\b|\bvcl\b|\bvc\b", 76),
    (r"\bviola\b|\bvla\b|altówka", 74),
    (r"violin|\bvln\b|\bvl\b(?=\s*\d)|skrzypce", 70),
]
_NUMBERED = {26, 30, 40, 45, 70}
_CANON = {1: "Partytura", 10: "Vocal", 20: "Flute", 22: "Clarinet", 24: "Soprano Sax",
          25.5: "Clarinet/Alto Sax", 26: "Alto Sax", 30: "Tenor Sax", 34: "Baritone Sax",
          40: "Trumpet", 45: "Trombone", 49: "Bass Trombone", 50: "Tuba", 60: "Guitar",
          62: "Piano", 64: "Bass", 66: "Drums", 68: "Percussion", 70: "Violin",
          74: "Viola", 76: "Cello", 28: "Saxophone"}
_ORD_RE = r"(1st|2nd|3rd|4th|1ST|2ND|3RD|4TH|ist|lst|2no|3ro|4rh)"


def find_tesseract():
    """Ścieżka do tesseract.exe albo None."""
    import sys
    if getattr(sys, "frozen", False):            # wersja zainstalowana z setup.exe
        p = os.path.join(os.path.dirname(sys.executable), "tesseract", "tesseract.exe")
        if os.path.isfile(p):
            return p
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
        r = subprocess.run([tesseract_path, tmp, "stdout", "--psm", str(psm), "-l", "eng"],
                           capture_output=True, timeout=120, creationflags=flags)
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
        low = " " + line.strip().lower() + " "
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

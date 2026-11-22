"""PartiMaster – Marek Kubisiak. Porządkowanie partii i partytur w PDF.

Jak używać:
 1. Otwórz PDF.
    Szybciej: „Rozpoznaj partie automatycznie” (potrzebny darmowy Tesseract OCR) –
    program sam znajdzie początki partii i spróbuje odczytać nazwy. Potem tylko
    przejrzyj zielone strony i popraw pomyłki oraz partie oznaczone „?”.
 2. Kliknij pierwszą stronę każdej partii i wybierz/wpisz nazwę instrumentu -> Enter.
    Kolejne strony należą do tej samej partii, aż do następnej oznaczonej strony.
 3. Duplikaty: program sam podpowiada identyczne strony (pomarańczowe), przycisk usuwa je.
    Dowolną stronę można usunąć/przywrócić klawiszem Delete.
 4. Zapisz uporządkowany PDF albo wyodrębnij partię (np. bas) - także z wielu plików naraz.
 5. Własny wybór stron: Ctrl+klik (Mac: ⌘+klik) dodaje stronę do zaznaczenia,
    Shift+klik zaznacza zakres, Ctrl+A wszystkie – potem „Zapisz zaznaczone strony”.
Opis partii zapisuje się automatycznie obok PDF-a (plik .partie.json).
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

try:                                    # motyw w stylu Windows 11
    import sv_ttk
except Exception:
    sv_ttk = None

from PIL import ImageTk

import partytury_core as core

IS_MAC = sys.platform == "darwin"

APP_NAME = "PartiMaster"
APP_AUTHOR = "Marek Kubisiak"
APP_VERSION = "1.5"
APP_TITLE = f"{APP_NAME} – {APP_AUTHOR}"

THUMB_SCALE = 0.25
THUMB_W = 150
COLS = 5

# kolory w stylu Windows 11
COL_START = "#0f7b0f"     # zielony (sukces)
COL_CONT = "#5c5c5c"      # szary tekst
COL_EXCL = "#c42b1c"      # czerwony (błąd)
COL_DUP = "#b35900"       # pomarańczowy (uwaga)
COL_SEL = "#005fb8"       # niebieski akcent Windows 11
BG = "#f3f3f3"            # tło obszaru miniatur
CARD = "#ffffff"
LINE = "#e0e0e0"
TEXT = "#1a1a1a"
FONT = "Segoe UI"         # zmieniane na Segoe UI Variable, jeśli jest w systemie
ACCENT = "TButton"        # styl przycisków głównych (Accent.TButton z motywem)

PALETTES = {
    "light": dict(COL_START="#0f7b0f", COL_CONT="#5c5c5c", COL_EXCL="#c42b1c", COL_DUP="#b35900",
                  COL_SEL="#005fb8", BG="#f3f3f3", CARD="#ffffff", LINE="#e0e0e0", TEXT="#1a1a1a"),
    "dark": dict(COL_START="#6ccb5f", COL_CONT="#a8a8a8", COL_EXCL="#ff99a4", COL_DUP="#f7b955",
                 COL_SEL="#60cdff", BG="#202020", CARD="#2b2b2b", LINE="#3d3d3d", TEXT="#ffffff"),
}
THEME = "light"


def app_data_dir():
    """Folder na ustawienia i dziennik: Windows %LOCALAPPDATA%\\Partytury,
    Mac ~/Library/Application Support/Partytury."""
    import tempfile
    if IS_MAC:
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    return os.path.join(base, "Partytury")


def _settings_path():
    return os.path.join(app_data_dir(), "ustawienia.json")


def load_settings():
    try:
        import json
        with open(_settings_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(**kw):
    try:
        import json
        st = load_settings()
        st.update(kw)
        os.makedirs(os.path.dirname(_settings_path()), exist_ok=True)
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=1)
    except Exception:
        pass


def set_palette(mode):
    """Ustawia kolory (jasne/ciemne) i motyw Sun Valley."""
    global THEME
    THEME = "dark" if mode == "dark" else "light"
    globals().update(PALETTES[THEME])
    if sv_ttk is not None:
        try:
            sv_ttk.set_theme(THEME)
        except Exception:
            pass


def apply_win11_look(root):
    """Motyw Sun Valley (wygląd Windows 11) + czcionka Segoe UI Variable."""
    global FONT, ACCENT
    try:
        fams = set(tkfont.families(root))
    except Exception:
        fams = set()
    if "Segoe UI Variable Text" in fams:
        FONT = "Segoe UI Variable Text"
    if IS_MAC:                                    # Mac: czcionka systemowa, rozmiary jak w Windows
        try:
            FONT = tkfont.nametofont("TkDefaultFont").actual()["family"]
        except Exception:
            FONT = "Helvetica Neue"
        try:
            root.tk.call("tk", "scaling", 1.3333)
        except Exception:
            pass
    if sv_ttk is not None:
        try:
            sv_ttk.set_theme("light")
            ACCENT = "Accent.TButton"
        except Exception:
            pass
    set_palette(load_settings().get("motyw", "light"))
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family=FONT, size=10)
        except Exception:
            pass
    try:
        root.configure(background=ttk.Style(root).lookup("TFrame", "background") or BG)
    except Exception:
        pass
    _dwm_round_corners(root)


def _dwm_round_corners(root):
    """Windows 11: zaokrąglone rogi okna i pasek tytułu w kolorze motywu."""
    if os.name != "nt":
        return
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        val = ctypes.c_int(2)      # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(val), ctypes.sizeof(val))
        dark = ctypes.c_int(1 if THEME == "dark" else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(dark), ctypes.sizeof(dark))
    except Exception:
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_win11_look(self)
        self.title(APP_TITLE)
        self.geometry("1350x880")
        ico = os.path.join(os.path.dirname(os.path.abspath(__file__)), "partytury.ico")
        if os.name == "nt" and os.path.exists(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass
        self.minsize(1000, 650)
        self.proj = None
        self.sel = None
        self.marked = set()          # strony zaznaczone do zapisu jako osobny PDF
        self.cells = {}
        self.thumb_imgs = {}
        self.small = {}
        self.preview_img = None
        self._render_queue = []
        self._ocr_running = False
        self._order = []
        self.drop_ok = False
        self._drop_procs = []
        self._build_ui()
        self.apply_theme()
        self._set_buttons()
        if IS_MAC:
            self._enable_drop()                # Mac: od razu, żeby przyjąć plik z Findera przy starcie
        else:
            self.after(400, self._enable_drop)     # dopiero gdy okno jest już na ekranie
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.open_pdf(sys.argv[1])

    # ------------------------------------------------------------- UI
    def _build_ui(self):
        top = ttk.Frame(self, padding=(10, 8))
        top.pack(fill="x")
        ttk.Button(top, text="📂 Otwórz PDF…", command=self.ask_open).pack(side="left")
        self.b_save = ttk.Button(top, text="💾 Zapisz uporządkowany PDF…", command=self.save_ordered)
        self.b_save.pack(side="left", padx=4)
        self.b_extract = ttk.Button(top, text="✂ Wyodrębnij partię…", command=self.extract_one)
        self.b_extract.pack(side="left", padx=4)
        self.b_auto = ttk.Button(top, text="🔍 Rozpoznaj partie automatycznie", command=self.auto_recognize,
                                 style=ACCENT)
        self.b_auto.pack(side="left", padx=4)
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(top, text="📚 Wiele plików: uporządkuj…", command=lambda: self.batch("order")).pack(side="left", padx=4)
        ttk.Button(top, text="📚 Wiele plików: wyodrębnij partię…", command=lambda: self.batch("extract")).pack(side="left", padx=4)
        ttk.Button(top, text="❓ Pomoc", command=self.help).pack(side="right")
        self.b_theme = ttk.Button(top, text="", command=self.toggle_theme)
        self.b_theme.pack(side="right", padx=4)

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)

        # lewa strona: miniatury
        left = ttk.Frame(body)
        self.canvas = tk.Canvas(left, background=BG, highlightthickness=0)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = tk.Frame(self.canvas, background=BG)
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.hint = tk.Label(self.grid_frame, text="", background=BG, foreground=COL_CONT,
                             font=(FONT, 16), padx=60, pady=120, justify="center")
        self.hint.pack()
        self.grid_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        body.add(left, weight=3)

        # prawa strona: podgląd + sterowanie
        right = ttk.Frame(body, padding=8)
        body.add(right, weight=2)
        self.info = ttk.Label(right, text="Otwórz plik PDF z partiami.", font=(FONT, 11, "bold"), wraplength=480)
        self.info.pack(anchor="w")
        self.preview = tk.Label(right, background=CARD, relief="flat", bd=0,
                                highlightthickness=1, highlightbackground=LINE)
        self.preview.pack(fill="x", pady=6)

        box = ttk.LabelFrame(right, text="Zaznaczona strona", padding=8)
        box.pack(fill="x", pady=4)
        ttk.Label(box, text="Nazwa partii zaczynającej się na tej stronie:").grid(row=0, column=0, columnspan=3, sticky="w")
        self.name_var = tk.StringVar()
        self.combo = ttk.Combobox(box, textvariable=self.name_var, values=core.PART_NAMES, width=30, font=(FONT, 11))
        self.combo.grid(row=1, column=0, sticky="we", pady=4)
        self.combo.bind("<Return>", lambda e: self.set_start())
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.set_start())
        self.b_start = ttk.Button(box, text="✔ Początek partii (Enter)", command=self.set_start, style=ACCENT)
        self.b_start.grid(row=1, column=1, padx=4)
        self.b_cont = ttk.Button(box, text="↳ To ciąg dalszy", command=self.clear_start)
        self.b_cont.grid(row=2, column=1, padx=4, sticky="we")
        self.b_excl = ttk.Button(box, text="🗑 Usuń / przywróć stronę (Delete)", command=self.toggle_excl)
        self.b_excl.grid(row=2, column=0, sticky="w", pady=2)
        box.columnconfigure(0, weight=1)

        boxm = ttk.LabelFrame(right, text="Wybrane strony → własny PDF", padding=8)
        boxm.pack(fill="x", pady=4)
        mod = "⌘" if IS_MAC else "Ctrl"
        self.mark_label = ttk.Label(boxm, wraplength=460,
                                    text=f"{mod}+klik – dodaj/odejmij stronę,  Shift+klik – zakres,  {mod}+A – wszystkie.")
        self.mark_label.pack(anchor="w")
        self.b_marked = ttk.Button(boxm, text="📄 Zapisz zaznaczone strony jako PDF…", command=self.save_marked)
        self.b_marked.pack(anchor="w", pady=(6, 0))

        box2 = ttk.LabelFrame(right, text="Duplikaty", padding=8)
        box2.pack(fill="x", pady=4)
        self.dup_label = ttk.Label(box2, text="—", wraplength=460)
        self.dup_label.pack(anchor="w")
        self.b_dups = ttk.Button(box2, text="🗑 Usuń wszystkie podpowiedziane duplikaty", command=self.exclude_dups)
        self.b_dups.pack(anchor="w", pady=4)

        box3 = ttk.LabelFrame(right, text="Kolejność po uporządkowaniu", padding=8)
        box3.pack(fill="both", expand=True, pady=4)
        self.order_list = tk.Listbox(box3, font=(FONT, 10), activestyle="none", relief="flat", bd=0,
                                     background=CARD, foreground=TEXT, selectbackground=COL_SEL,
                                     selectforeground="white", highlightthickness=1,
                                     highlightbackground=LINE, highlightcolor=COL_SEL)
        self.order_list.pack(fill="both", expand=True)
        self.order_list.bind("<<ListboxSelect>>", self._jump_from_list)
        self.warn = ttk.Label(right, text="", foreground=COL_EXCL, wraplength=480)
        self.warn.pack(anchor="w")

        self.status = ttk.Label(self, text="", anchor="w", padding=(10, 4), foreground=COL_CONT)
        self.status.pack(fill="x", side="bottom")
        ttk.Separator(self, orient="horizontal").pack(fill="x", side="bottom")

        for key, d in (("<Left>", -1), ("<Right>", 1), ("<Up>", -COLS), ("<Down>", COLS)):
            self.bind(key, lambda e, d=d: self._move(d, e))
        self.bind("<Delete>", lambda e: self.toggle_excl() if self.focus_get() is not self.combo else None)
        for k in (("<Command-a>", "<Command-A>") if IS_MAC else ("<Control-a>", "<Control-A>")):
            self.bind(k, self.select_all)
        if IS_MAC:                                # na Macu klawisz „delete” to BackSpace
            self.bind("<BackSpace>", lambda e: self.toggle_excl() if self.focus_get() is not self.combo else None)

    # ------------------------------------------------------------- przeciąganie plików
    def _enable_drop(self):
        """Przeciąganie PDF-ów na okno. W Windows: bezpośrednio przez system (WM_DROPFILES),
        w razie problemu: biblioteka tkinterdnd2. Bez obu program działa normalnie."""
        errors = []
        if IS_MAC:                     # upuszczenie na ikonę w Docku / „Otwórz za pomocą” w Finderze
            try:
                self.createcommand("::tk::mac::OpenDocument",
                                   lambda *files: self._open_dropped(list(files)))
            except Exception as ex:
                errors.append(f"Mac OpenDocument: {ex!r}")
        if os.name == "nt":
            try:
                self._win_drop_hook()
                self.drop_ok = True
            except Exception as ex:
                errors.append(f"Windows: {ex!r}")
        if not self.drop_ok:
            try:
                from tkinterdnd2 import TkinterDnD, DND_FILES
                TkinterDnD._require(self)
                for w in (self, self.canvas, self.grid_frame, self.preview, self.hint):
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind("<<Drop>>", self._on_tkdnd_drop)
                self.drop_ok = True
            except Exception as ex:
                errors.append(f"tkinterdnd2: {ex!r}")
        log("Przeciąganie: " + ("włączone" if self.drop_ok else "NIEDOSTĘPNE") +
            ("" if not errors else "  (" + "; ".join(errors) + ")"))
        try:
            if not self.proj:
                self.hint.configure(text=("Przeciągnij tutaj plik PDF\nalbo kliknij „Otwórz PDF…”"
                                          if self.drop_ok else "Kliknij „Otwórz PDF…”, żeby zacząć."))
        except Exception:
            pass

    def _win_drop_hook(self):
        """Przyjmowanie plików upuszczonych z Eksploratora Windows (jak w Notatniku)."""
        import ctypes
        from ctypes import wintypes
        user32, shell32 = ctypes.windll.user32, ctypes.windll.shell32
        LRESULT = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        user32.GetParent.restype = wintypes.HWND
        user32.GetParent.argtypes = [wintypes.HWND]
        user32.CallWindowProcW.restype = LRESULT
        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                                           wintypes.WPARAM, wintypes.LPARAM]
        set_proc = getattr(user32, "SetWindowLongPtrW", None) or user32.SetWindowLongW
        set_proc.restype = ctypes.c_void_p
        set_proc.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        shell32.DragFinish.argtypes = [ctypes.c_void_p]
        shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        WM_DROPFILES, GWLP_WNDPROC = 0x0233, -4
        self.update_idletasks()
        hwnds = []
        try:
            hwnds.append(int(self.wm_frame(), 16))       # właściwe okno Windows programu
        except Exception:
            pass
        inner = self.winfo_id()
        if inner not in hwnds:
            hwnds.append(inner)
        self._drop_procs = []
        for hwnd in hwnds:
            try:   # zezwól na upuszczanie także przy innych uprawnieniach okna
                f = user32.ChangeWindowMessageFilterEx
                f.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.DWORD, ctypes.c_void_p]
                for m in (WM_DROPFILES, 0x0049, 0x004A):
                    f(hwnd, m, 1, None)
            except Exception:
                pass
            shell32.DragAcceptFiles(hwnd, True)
            old = [None]

            def proc(hw, msg, wp, lp, old=old):
                if msg == WM_DROPFILES:
                    try:
                        n = shell32.DragQueryFileW(wp, 0xFFFFFFFF, None, 0)
                        files = []
                        for i in range(n):
                            ln = shell32.DragQueryFileW(wp, i, None, 0)
                            buf = ctypes.create_unicode_buffer(ln + 1)
                            shell32.DragQueryFileW(wp, i, buf, ln + 1)
                            files.append(buf.value)
                        shell32.DragFinish(wp)
                        self.after(10, lambda fs=files: self._open_dropped(fs))
                    except Exception as ex:
                        log(f"Błąd upuszczania: {ex!r}")
                    return 0
                return user32.CallWindowProcW(old[0], hw, msg, wp, lp)
            cb = WNDPROC(proc)
            old[0] = set_proc(hwnd, GWLP_WNDPROC, ctypes.cast(cb, ctypes.c_void_p))
            if old[0]:
                self._drop_procs.append(cb)      # trzymamy referencję, żeby nie zniknęła
        if not self._drop_procs:
            raise OSError("nie udało się podłączyć do okna")

    def _on_tkdnd_drop(self, event):
        self._open_dropped(list(self.tk.splitlist(event.data)))
        return event.action

    def _open_dropped(self, files):
        log(f"Upuszczono: {files}")
        pdfs = [f for f in files if f.lower().endswith(".pdf")]
        if not pdfs:
            messagebox.showinfo("Przeciąganie", "To nie jest plik PDF.")
            return
        self.open_pdf(pdfs[0])
        if len(pdfs) > 1:
            messagebox.showinfo("Przeciąganie",
                                f"Otwarto pierwszy z {len(pdfs)} plików: {os.path.basename(pdfs[0])}.\n"
                                "Żeby pracować na wielu plikach naraz, użyj przycisków „Wiele plików…”.")

    def _wheel(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None and w is not self.canvas and w is not self.grid_frame:
            if w is self.order_list:
                return
            w = w.master
        step = -e.delta if IS_MAC else int(-e.delta / 40)     # Mac: małe wartości delta
        if step:
            self.canvas.yview_scroll(step, "units")

    def _set_buttons(self):
        st = "normal" if self.proj else "disabled"
        for b in (self.b_save, self.b_extract, self.b_auto, self.b_start, self.b_cont, self.b_excl, self.b_dups,
                  self.b_marked):
            b.configure(state=st)
        if self.proj and not self.proj.dups:
            self.b_dups.configure(state="disabled")

    # ------------------------------------------------------------- otwieranie
    def ask_open(self):
        f = filedialog.askopenfilename(title="Wybierz PDF z partiami", filetypes=[("PDF", "*.pdf")])
        if f:
            self.open_pdf(f)

    def open_pdf(self, path):
        if self.proj:
            self.proj.close()
        try:
            self.proj = core.Project(path)
        except Exception as ex:
            messagebox.showerror("Błąd", f"Nie udało się otworzyć pliku:\n{ex}")
            return
        for w in self.grid_frame.winfo_children():
            w.destroy()
        self.cells, self.thumb_imgs, self.small = {}, {}, {}
        self.sel = None
        self.marked = set()
        self.title(f"{APP_TITLE}   |   {os.path.basename(path)}")
        for p in range(1, self.proj.n + 1):
            cell = tk.Frame(self.grid_frame, background=BG, bd=3, relief="flat", cursor="hand2")
            cell.grid(row=(p - 1) // COLS, column=(p - 1) % COLS, padx=4, pady=4, sticky="n")
            img = tk.Label(cell, text=f"str. {p}", width=20, height=10, background=CARD, foreground=COL_CONT)
            img.pack()
            cap = tk.Label(cell, text="", width=22, anchor="w", justify="left", background=BG,
                           font=(FONT, 9), wraplength=THUMB_W + 10)
            cap.pack(fill="x")
            for w in (cell, img, cap):
                w.bind("<Button-1>", lambda e, p=p: self.select(p))
                w.bind("<Shift-Button-1>", lambda e, p=p: self.select(p, "range"))
                for mk in (("<Command-Button-1>", "<Control-Button-1>") if IS_MAC else ("<Control-Button-1>",)):
                    w.bind(mk, lambda e, p=p: self.select(p, "toggle"))
                if self.drop_ok and not getattr(self, "_drop_procs", None):
                    try:
                        from tkinterdnd2 import DND_FILES
                        w.drop_target_register(DND_FILES)
                        w.dnd_bind("<<Drop>>", self._on_tkdnd_drop)
                    except Exception:
                        pass
            self.cells[p] = (cell, img, cap)
        self.canvas.yview_moveto(0)
        self._set_buttons()
        self.refresh()
        self.select(1)
        self._render_queue = list(range(1, self.proj.n + 1))
        self.after(10, self._render_next)

    def _render_next(self):
        if not self._render_queue or not self.proj:
            return
        p = self._render_queue.pop(0)
        try:
            im = self.proj.render(p, THUMB_SCALE)
            self.small[p] = im
            t = im.copy()
            t.thumbnail((THUMB_W, int(THUMB_W * 1.5)))
            ph = ImageTk.PhotoImage(t)
            self.thumb_imgs[p] = ph
            self.cells[p][1].configure(image=ph, width=t.width, height=t.height, text="")
        except Exception as ex:
            self.cells[p][1].configure(text=f"str. {p}\n(błąd podglądu)")
            print(ex)
        self.status.configure(text=f"Wczytywanie stron: {p}/{self.proj.n}")
        if self._render_queue:
            self.after(1, self._render_next)
        else:
            self.status.configure(text="Szukam duplikatów…")
            self.update_idletasks()
            self.proj.find_duplicates(self.small)
            self.status.configure(text=f"Gotowe. Stron: {self.proj.n}. "
                                       f"Opis zapisuje się automatycznie w: {os.path.basename(self.proj.json_path)}")
            self._set_buttons()
            self.refresh()

    # ------------------------------------------------------------- zaznaczanie
    def select(self, p, mode="single"):
        """mode: single – zwykłe kliknięcie, toggle – Ctrl/⌘+klik, range – Shift+klik."""
        if not self.proj or p < 1 or p > self.proj.n:
            return
        if mode == "toggle":
            if p in self.marked and len(self.marked) > 1:
                self.marked.discard(p)
            else:
                self.marked.add(p)
        elif mode == "range" and self.sel:
            a, b = sorted((self.sel, p))
            self.marked |= set(range(a, b + 1))
        else:
            self.marked = {p}
        self.sel = p
        self._update_marked()
        self.refresh_cells()
        name, is_start = self.proj.part_of(p)
        if is_start:
            self.name_var.set(name)
        else:
            self.name_var.set(self._suggest_name())
        self.show_preview()
        self._scroll_to(p)

    def _suggest_name(self):
        prev = [n for q, n in sorted(self.proj.starts.items()) if q < self.sel]
        return core.next_name(prev[-1]) if prev else ""

    def select_all(self, e=None):
        if not self.proj or self.focus_get() is self.combo:
            return
        self.marked = set(range(1, self.proj.n + 1))
        self._update_marked()
        self.refresh_cells()
        return "break"

    def _update_marked(self):
        mod = "⌘" if IS_MAC else "Ctrl"
        if len(self.marked) > 1:
            txt = (f"Zaznaczone: {pl(len(self.marked), 'strona', 'strony', 'stron')} "
                   f"({self._ranges(sorted(self.marked))}).  Zwykłe kliknięcie anuluje zaznaczenie.")
        else:
            txt = f"{mod}+klik – dodaj/odejmij stronę,  Shift+klik – zakres,  {mod}+A – wszystkie."
        self.mark_label.configure(text=txt)

    def save_marked(self):
        if not self.proj:
            return
        pages = sorted(self.marked or ({self.sel} if self.sel else set()))
        if not pages:
            messagebox.showinfo("Brak stron", "Kliknij strony po lewej (Ctrl+klik, Shift+klik), które mają trafić do pliku.")
            return
        base = os.path.splitext(os.path.basename(self.proj.path))[0]
        name, _ = self.proj.part_of(pages[0])
        sugg = f"{base}_{file_label(name)}" if name and not name.startswith(core.UNKNOWN) else f"{base}_strony"
        out = filedialog.asksaveasfilename(title=f"Zapisz {pl(len(pages), 'stronę', 'strony', 'stron')} jako PDF – wpisz nazwę",
                                           defaultextension=".pdf", initialdir=os.path.dirname(self.proj.path),
                                           initialfile=sugg + ".pdf", filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        if os.path.abspath(out) == os.path.abspath(self.proj.path):
            messagebox.showerror("Błąd", "Wybierz inną nazwę – nie nadpisuję oryginału.")
            return
        n = self.proj.export_pages(pages, out)
        messagebox.showinfo("Gotowe", f"Zapisano {pl(n, 'stronę', 'strony', 'stron')} ({self._ranges(pages)}):\n{out}")

    def _move(self, d, e):
        if self.focus_get() is self.combo or not self.proj:
            return
        self.select(max(1, min(self.proj.n, (self.sel or 1) + d)))

    def _scroll_to(self, p):
        self.update_idletasks()
        cell = self.cells[p][0]
        total = self.grid_frame.winfo_height()
        if total <= 0:
            return
        y0, y1 = cell.winfo_y(), cell.winfo_y() + cell.winfo_height()
        v0, v1 = self.canvas.yview()
        if y0 < v0 * total or y1 > v1 * total:
            self.canvas.yview_moveto(max(0, (y0 - 20) / total))

    def show_preview(self):
        p = self.sel
        try:
            im = self.proj.render(p, 1.0)
            w = 470
            im = im.resize((w, int(im.height * w / im.width)))
            im = im.crop((0, 0, w, min(im.height, int(w * 0.75))))
            self.preview_img = ImageTk.PhotoImage(im)
            self.preview.configure(image=self.preview_img)
        except Exception as ex:
            self.preview.configure(image="", text=str(ex))
        name, is_start = self.proj.part_of(p)
        txt = f"Strona {p} z {self.proj.n}"
        if p in self.proj.excluded:
            txt += "  –  USUNIĘTA"
        elif name:
            txt += f"  –  {name}" + ("" if is_start else " (ciąg dalszy)")
        if p in self.proj.dups:
            txt += f"\nWygląda jak kopia strony {self.proj.dups[p]}"
        self.info.configure(text=txt)

    # ------------------------------------------------------------- edycja
    def set_start(self):
        if not self.proj or not self.sel:
            return
        name = self.name_var.get().strip()
        if not name:
            messagebox.showinfo("Nazwa partii", "Wpisz albo wybierz z listy nazwę instrumentu.")
            return
        self.proj.starts[self.sel] = name
        self.proj.excluded.discard(self.sel)
        self._changed()

    def clear_start(self):
        if self.proj and self.sel in self.proj.starts:
            del self.proj.starts[self.sel]
            self._changed()

    def toggle_excl(self):
        if not self.proj or not self.sel:
            return
        pages = self.marked if len(self.marked) > 1 else {self.sel}
        if pages <= self.proj.excluded:          # wszystkie usunięte -> przywróć
            self.proj.excluded -= pages
        else:
            self.proj.excluded |= pages
        self._changed()

    def exclude_dups(self):
        if not self.proj or not self.proj.dups:
            return
        pages = sorted(self.proj.dups)
        if messagebox.askyesno("Duplikaty", f"Usunąć {pl(len(pages), 'stronę', 'strony', 'stron')}, które są kopiami wcześniejszych?\n"
                                            f"Strony: {self._ranges(pages)}\n\n(Można je potem przywrócić klawiszem Delete.)"):
            for p in pages:
                self.proj.excluded.add(p)
                self.proj.starts.pop(p, None)
            self._changed()

    def _changed(self):
        try:
            self.proj.save()
        except Exception as ex:
            messagebox.showwarning("Zapis opisu", f"Nie udało się zapisać pliku opisu:\n{ex}")
        self.refresh()
        self.show_preview()

    # ------------------------------------------------------------- odświeżanie
    def refresh(self):
        self.refresh_cells()
        if not self.proj:
            return
        self.order_list.delete(0, "end")
        self._order = self.proj.ordered_parts()
        for name, ps in self._order:
            self.order_list.insert("end", f"{name}   ({self._ranges(ps)})")
        d = self.proj.dups
        if d:
            active = [p for p in d if p not in self.proj.excluded]
            self.dup_label.configure(text=f"Znaleziono {pl(len(d), 'stronę identyczną', 'strony identyczne', 'stron identycznych')} z wcześniejszymi "
                                          f"(pomarańczowe): {self._ranges(sorted(d))}." +
                                     ("" if active else " Wszystkie są już usunięte."))
        else:
            self.dup_label.configure(text="Brak identycznych stron. Inne wersje tej samej partii "
                                          "(np. drugi skan) usuń ręcznie klawiszem Delete.")
        warns = []
        rep = self.proj.repeated_names()
        if rep:
            warns.append("Ta sama partia występuje kilka razy: " + ", ".join(rep) +
                         ". Jeśli to duplikat, usuń zbędne strony (Delete).")
        unk = [p for p, n in sorted(self.proj.starts.items()) if n.startswith(core.UNKNOWN)]
        if unk:
            warns.append(f"Nierozpoznane nazwy partii („?”) na stronach: {self._ranges(unk)} – "
                         "kliknij stronę i wpisz nazwę.")
        un = self.proj.unnamed_pages()
        if un and self.proj.starts:
            warns.append(f"Strony bez nazwy partii: {self._ranges(un)}.")
        self.warn.configure(text="\n".join(warns))
        self._set_buttons()

    # ------------------------------------------------------------- motyw
    def toggle_theme(self):
        self.apply_theme("light" if THEME == "dark" else "dark")
        save_settings(motyw=THEME)

    def apply_theme(self, mode=None):
        """Przełącza jasny/ciemny wygląd i przemalowuje zwykłe (nie-ttk) elementy okna."""
        if mode:
            set_palette(mode)
        self.b_theme.configure(text="☀ Jasny" if THEME == "dark" else "🌙 Ciemny")
        try:
            self.configure(background=ttk.Style(self).lookup("TFrame", "background") or BG)
        except Exception:
            pass
        for w, kw in ((self.canvas, dict(background=BG)), (self.grid_frame, dict(background=BG)),
                      (self.hint, dict(background=BG, foreground=COL_CONT)),
                      (self.preview, dict(background=CARD, highlightbackground=LINE)),
                      (self.order_list, dict(background=CARD, foreground=TEXT, selectbackground=COL_SEL,
                                             selectforeground=BG, highlightbackground=LINE,
                                             highlightcolor=COL_SEL)),
                      (self.warn, dict(foreground=COL_EXCL)), (self.status, dict(foreground=COL_CONT))):
            try:
                w.configure(**kw)
            except Exception:
                pass
        for cell, img, cap in self.cells.values():
            try:
                img.configure(background=CARD, foreground=COL_CONT)
                cap.configure(background=BG)
            except Exception:
                pass
        self.refresh_cells()
        _dwm_round_corners(self)

    def refresh_cells(self):
        if not self.proj:
            return
        for p, (cell, img, cap) in self.cells.items():
            name, is_start = self.proj.part_of(p)
            if p in self.proj.excluded:
                txt, col = f"{p}. ✖ USUNIĘTA", COL_EXCL
            elif is_start:
                txt, col = f"{p}. ▶ {name}", COL_START
            elif name:
                txt, col = f"{p}.   ↳ {name}", COL_CONT
            else:
                txt, col = f"{p}.  (bez nazwy)", COL_CONT
            if p in self.proj.dups and p not in self.proj.excluded:
                txt += f"\n⚠ kopia str. {self.proj.dups[p]}"
                col = COL_DUP
            if p in self.marked and len(self.marked) > 1:
                txt = "☑ " + txt
            cap.configure(text=txt, foreground=col,
                          font=(FONT, 9, "bold" if is_start or p in self.proj.excluded else "normal"))
            border = (COL_SEL if p == self.sel or (p in self.marked and len(self.marked) > 1)
                      else (COL_EXCL if p in self.proj.excluded else BG))
            cell.configure(background=border)

    def _jump_from_list(self, e):
        s = self.order_list.curselection()
        if s and self._order:
            self.select(self._order[s[0]][1][0])

    @staticmethod
    def _ranges(pages):
        out, i = [], 0
        while i < len(pages):
            j = i
            while j + 1 < len(pages) and pages[j + 1] == pages[j] + 1:
                j += 1
            out.append(str(pages[i]) if i == j else f"{pages[i]}–{pages[j]}")
            i = j + 1
        return ", ".join(out)

    # ------------------------------------------------------------- rozpoznawanie (OCR)
    def auto_recognize(self):
        if not self.proj or self._ocr_running:
            return
        tess = core.find_tesseract()
        if not tess:
            if messagebox.askyesno(
                    "Brak programu Tesseract",
                    "Do automatycznego rozpoznawania potrzebny jest darmowy program Tesseract OCR,\n"
                    "a nie udało się go znaleźć.\n\n"
                    "Najprościej: zainstaluj program jeszcze raz (Partytury-setup.exe).\n"
                    "Można też zainstalować Tesseract ręcznie.\n\nOtworzyć stronę z instalatorem Tesseract?"):
                import webbrowser
                webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")
            return
        if self.proj.starts and not messagebox.askyesno(
                "Rozpoznawanie", "Ten plik jest już (częściowo) opisany.\n"
                                 "Zastąpić opis wynikiem automatycznego rozpoznawania?"):
            return
        self._ocr_running = True
        self.b_auto.configure(state="disabled")
        self._ocr_tess = tess
        self._ocr_crops = {}
        self._ocr_todo = list(range(1, self.proj.n + 1))
        self.after(10, self._ocr_render_step)

    def _ocr_render_step(self):
        # wycinki renderujemy w głównym wątku (biblioteka PDF nie lubi wielu wątków naraz)
        for _ in range(3):
            if not self._ocr_todo:
                break
            p = self._ocr_todo.pop(0)
            self._ocr_crops[p] = core.ocr_crops(self.proj, p)
        done = len(self._ocr_crops)
        self.status.configure(text=f"Rozpoznawanie: przygotowuję strony {done}/{self.proj.n}…")
        if self._ocr_todo:
            self.after(1, self._ocr_render_step)
            return
        import threading
        self._ocr_results = {}
        threading.Thread(target=self._ocr_worker, daemon=True).start()
        self.after(300, self._ocr_poll)

    def _ocr_worker(self):
        from concurrent.futures import ThreadPoolExecutor

        def one(p):
            head, side = self._ocr_crops[p]
            try:
                return p, core.ocr_image(head, self._ocr_tess, 11), core.ocr_image(side, self._ocr_tess, 6)
            except Exception as ex:
                return p, "", ""
        workers = max(1, min(4, (os.cpu_count() or 2) - 1))
        with ThreadPoolExecutor(workers) as ex:
            for p, h, sd in ex.map(one, sorted(self._ocr_crops)):
                self._ocr_results[p] = (h, sd)

    def _ocr_poll(self):
        n = len(self._ocr_results)
        self.status.configure(text=f"Rozpoznawanie tekstu (Tesseract): {n}/{self.proj.n} stron…")
        if n < self.proj.n:
            self.after(300, self._ocr_poll)
            return
        pages = {p: core.recognize_texts(h, sd, self.proj.path) for p, (h, sd) in self._ocr_results.items()}
        self.proj.starts = core.guess_starts(pages)
        for p in list(self.proj.starts):
            if p in self.proj.excluded:
                del self.proj.starts[p]
        self._ocr_running = False
        self._ocr_crops = {}
        self._changed()
        unk = sum(1 for v in self.proj.starts.values() if v.startswith(core.UNKNOWN))
        self.status.configure(text=f"Rozpoznano {len(self.proj.starts)} partii. Sprawdź je – kliknij każdą zieloną stronę.")
        messagebox.showinfo(
            "Rozpoznawanie zakończone",
            f"Znaleziono {len(self.proj.starts)} partii"
            + (f", w tym {unk} bez odczytanej nazwy (oznaczone „?”)" if unk else "") + ".\n\n"
            "To jest PROPOZYCJA – OCR na skanach się myli. Przejrzyj zielone strony (początki partii)\n"
            "i popraw błędne nazwy. Lista po prawej pokazuje kolejność po uporządkowaniu.")

    # ------------------------------------------------------------- eksport
    def _check_ready(self, proj):
        if not proj.starts:
            messagebox.showinfo("Brak opisu", "Najpierw oznacz pierwsze strony partii (kliknij stronę, wybierz nazwę, Enter).")
            return False
        return True

    def save_ordered(self):
        if not self.proj or not self._check_ready(self.proj):
            return
        base = os.path.splitext(os.path.basename(self.proj.path))[0]
        out = filedialog.asksaveasfilename(title="Zapisz uporządkowany PDF", defaultextension=".pdf",
                                           initialdir=os.path.dirname(self.proj.path),
                                           initialfile=f"{base}_uporzadkowany.pdf", filetypes=[("PDF", "*.pdf")])
        if not out:
            return
        if os.path.abspath(out) == os.path.abspath(self.proj.path):
            messagebox.showerror("Błąd", "Wybierz inną nazwę – nie nadpisuję oryginału.")
            return
        n = self.proj.export_ordered(out)
        messagebox.showinfo("Gotowe", f"Zapisano {pl(n, 'stronę', 'strony', 'stron')} (z {self.proj.n}).\n{out}")

    def extract_one(self):
        if not self.proj or not self._check_ready(self.proj):
            return
        q = ask_part(self, "Wyodrębnij partię")
        if not q:
            return
        names = [n for n, _ in self.proj.ordered_parts() if core.matches(n, q)]
        if not names:
            messagebox.showinfo("Brak", f"W tym pliku nie ma partii pasującej do: {q}")
            return
        base = os.path.splitext(os.path.basename(self.proj.path))[0]
        out = filedialog.asksaveasfilename(title="Zapisz partię", defaultextension=".pdf",
                                           initialdir=os.path.dirname(self.proj.path),
                                           initialfile=f"{base}_{file_label(q)}.pdf",
                                           filetypes=[("PDF", "*.pdf")])
        if out:
            n = self.proj.export_matching(q, out)
            messagebox.showinfo("Gotowe", f"Zapisano {pl(n, 'stronę', 'strony', 'stron')}: {', '.join(names)}\n{out}")

    def batch(self, mode):
        files = filedialog.askopenfilenames(title="Wybierz pliki PDF (już opisane w programie)", filetypes=[("PDF", "*.pdf")])
        if not files:
            return
        files = sorted(files, key=natural_key)
        q = None
        if mode == "extract":
            q = ask_part(self, "Którą partię wyodrębnić ze wszystkich plików?")
            if not q:
                return
        outdir = filedialog.askdirectory(title="Folder, do którego zapisać wyniki")
        if not outdir:
            return
        made, report = [], []
        for f in files:
            name = os.path.splitext(os.path.basename(f))[0]
            try:
                pr = core.Project(f)
            except Exception as ex:
                report.append(f"✖ {name}: błąd ({ex})")
                continue
            if not pr.described:
                report.append(f"✖ {name}: plik nie jest opisany – otwórz go najpierw w programie")
                continue
            if mode == "order":
                out = os.path.join(outdir, f"{name}.pdf")
                if os.path.abspath(out) == os.path.abspath(f):
                    out = os.path.join(outdir, f"{name}_uporzadkowany.pdf")
                n = pr.export_ordered(out)
                rep = pr.repeated_names()
                report.append(f"✔ {name}: {pr.n} → {n} str." + (f"  (uwaga, powtórzone: {', '.join(rep)})" if rep else ""))
                made.append(out)
            else:
                out = os.path.join(outdir, f"{name}_{file_label(q)}.pdf")
                n = pr.export_matching(q, out)
                if n:
                    parts = [p for p, _ in pr.ordered_parts() if core.matches(p, q)]
                    report.append(f"✔ {name}: {n} str. ({', '.join(parts)})")
                    made.append(out)
                else:
                    report.append(f"✖ {name}: brak partii „{q}”")
        if made and messagebox.askyesno("Gotowe", f"Utworzono {pl(len(made), 'plik', 'pliki', 'plików')}.\nSpakować je też do pliku ZIP?"):
            label = "uporzadkowane" if mode == "order" else file_label(q)
            zp = os.path.join(outdir, f"Partie_{label}.zip")
            core.make_zip(made, zp, os.path.splitext(os.path.basename(zp))[0])
            report.append(f"\nZIP: {zp}")
        show_report(self, "Raport", "\n".join(report))

    def help(self):
        messagebox.showinfo(f"Pomoc – {APP_NAME}",
                            f"{APP_NAME} {APP_VERSION}\nAutor: {APP_AUTHOR}\n\n" + __doc__.split("\n", 1)[1])


def file_label(q):
    """Nazwa partii do nazwy pliku: 'Sax alt 1' -> 'Sax_alt_1', 'Bas / kontrabas' -> 'Bas_kontrabas'."""
    import re
    return re.sub(r"[^\w]+", "_", q.strip()).strip("_") or "partia"


def log(msg):
    """Dziennik programu (pomaga ustalić przyczynę problemów): %LOCALAPPDATA%\\Partytury\\partytury.log"""
    try:
        import datetime
        d = app_data_dir()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "partytury.log"), "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}  {msg}\n")
    except Exception:
        pass


def pl(n, one, few, many):
    """Polska odmiana: 1 strona, 2 strony, 5 stron."""
    if n == 1:
        return f"{n} {one}"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return f"{n} {few}"
    return f"{n} {many}"


def natural_key(path):
    import re
    s = os.path.basename(path)
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def _bg(win):
    """Tło okienka takie samo jak tło motywu."""
    try:
        win.configure(background=ttk.Style(win).lookup("TFrame", "background") or CARD)
    except Exception:
        pass


def ask_part(parent, title):
    """Okienko wyboru partii: kategoria z listy albo dowolny tekst."""
    win = tk.Toplevel(parent)
    win.title(title)
    _bg(win)
    win.transient(parent)
    win.grab_set()
    ttk.Label(win, text="Wybierz grupę z listy albo wpisz nazwę partii po polsku lub angielsku, "
                        "także skrótem – np. „Trumpet 1”, „Trąbka 1”, „Tr 1”, „Sax alt 2”, „AS 2”, "
                        "„Klarnet basowy”, „Bone 3”:",
              padding=10, wraplength=380).pack()
    var = tk.StringVar(value=list(core.CATEGORIES)[0])
    cb = ttk.Combobox(win, textvariable=var, values=list(core.CATEGORIES), width=32, font=(FONT, 11))
    cb.pack(padx=10)
    res = {"v": None}

    def ok(e=None):
        res["v"] = var.get().strip() or None
        win.destroy()
    ttk.Button(win, text="OK", command=ok, style=ACCENT, width=12).pack(pady=12)
    cb.bind("<Return>", ok)
    cb.focus_set()
    win.geometry(f"+{parent.winfo_rootx() + 200}+{parent.winfo_rooty() + 150}")
    parent.wait_window(win)
    return res["v"]


def show_report(parent, title, text):
    win = tk.Toplevel(parent)
    win.title(title)
    _bg(win)
    t = tk.Text(win, width=100, height=min(30, text.count("\n") + 3), font=(FONT, 10), relief="flat",
                bd=0, padx=10, pady=8, background=CARD, foreground=TEXT, insertbackground=TEXT,
                highlightthickness=1, highlightbackground=LINE)
    t.insert("1.0", text)
    t.configure(state="disabled")
    t.pack(padx=8, pady=8)
    ttk.Button(win, text="Zamknij", command=win.destroy).pack(pady=6)


def selftest(out):
    """Test dla serwera budującego: czy Tesseract jest dołączony i czyta tekst (bez okna)."""
    lines, ok = [], False
    try:
        from PIL import Image, ImageDraw, ImageFont
        tess = core.find_tesseract()
        lines.append(f"tesseract: {tess}")
        img = Image.new("RGB", (900, 200), "white")
        try:
            fnt = ImageFont.load_default(size=80)
        except TypeError:
            fnt = ImageFont.load_default()
        ImageDraw.Draw(img).text((40, 50), "TRUMPET 1", fill="black", font=fnt)
        txt = core.ocr_image(img, tess, psm=6) if tess else ""
        lines.append(f"ocr: {txt.strip()!r}")
        ok = "TRUMPET" in txt.upper()
        lines.append(f"sv_ttk: {sv_ttk is not None}")
    except Exception as ex:
        lines.append(f"blad: {ex!r}")
    lines.append("SELFTEST OK" if ok else "SELFTEST FAIL")
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        sys.exit(selftest(sys.argv[2]))
    App().mainloop()

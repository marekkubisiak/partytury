"""Porządkowanie partytur - program z oknem (Windows/Mac/Linux).

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
Opis partii zapisuje się automatycznie obok PDF-a (plik .partie.json).
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

import partytury_core as core

THUMB_SCALE = 0.25
THUMB_W = 150
COLS = 5

COL_START = "#1a7f37"
COL_CONT = "#555555"
COL_EXCL = "#c62828"
COL_DUP = "#e67e00"
COL_SEL = "#1565c0"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Porządkowanie partytur")
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
        self.cells = {}
        self.thumb_imgs = {}
        self.small = {}
        self.preview_img = None
        self._render_queue = []
        self._ocr_running = False
        self._order = []
        self._build_ui()
        self._set_buttons()
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.open_pdf(sys.argv[1])

    # ------------------------------------------------------------- UI
    def _build_ui(self):
        top = ttk.Frame(self, padding=6)
        top.pack(fill="x")
        ttk.Button(top, text="📂 Otwórz PDF…", command=self.ask_open).pack(side="left")
        self.b_save = ttk.Button(top, text="💾 Zapisz uporządkowany PDF…", command=self.save_ordered)
        self.b_save.pack(side="left", padx=4)
        self.b_extract = ttk.Button(top, text="✂ Wyodrębnij partię…", command=self.extract_one)
        self.b_extract.pack(side="left", padx=4)
        self.b_auto = ttk.Button(top, text="🔍 Rozpoznaj partie automatycznie", command=self.auto_recognize)
        self.b_auto.pack(side="left", padx=4)
        ttk.Separator(top, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(top, text="📚 Wiele plików: uporządkuj…", command=lambda: self.batch("order")).pack(side="left", padx=4)
        ttk.Button(top, text="📚 Wiele plików: wyodrębnij partię…", command=lambda: self.batch("extract")).pack(side="left", padx=4)
        ttk.Button(top, text="❓ Pomoc", command=self.help).pack(side="right")

        body = ttk.PanedWindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)

        # lewa strona: miniatury
        left = ttk.Frame(body)
        self.canvas = tk.Canvas(left, background="#e8e8e8", highlightthickness=0)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.grid_frame = tk.Frame(self.canvas, background="#e8e8e8")
        self.canvas.create_window((0, 0), window=self.grid_frame, anchor="nw")
        self.grid_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        body.add(left, weight=3)

        # prawa strona: podgląd + sterowanie
        right = ttk.Frame(body, padding=8)
        body.add(right, weight=2)
        self.info = ttk.Label(right, text="Otwórz plik PDF z partiami.", font=("Segoe UI", 11, "bold"), wraplength=480)
        self.info.pack(anchor="w")
        self.preview = tk.Label(right, background="white", relief="solid", bd=1)
        self.preview.pack(fill="x", pady=6)

        box = ttk.LabelFrame(right, text="Zaznaczona strona", padding=8)
        box.pack(fill="x", pady=4)
        ttk.Label(box, text="Nazwa partii zaczynającej się na tej stronie:").grid(row=0, column=0, columnspan=3, sticky="w")
        self.name_var = tk.StringVar()
        self.combo = ttk.Combobox(box, textvariable=self.name_var, values=core.PART_NAMES, width=30, font=("Segoe UI", 11))
        self.combo.grid(row=1, column=0, sticky="we", pady=4)
        self.combo.bind("<Return>", lambda e: self.set_start())
        self.combo.bind("<<ComboboxSelected>>", lambda e: self.set_start())
        self.b_start = ttk.Button(box, text="✔ Początek partii (Enter)", command=self.set_start)
        self.b_start.grid(row=1, column=1, padx=4)
        self.b_cont = ttk.Button(box, text="↳ To ciąg dalszy", command=self.clear_start)
        self.b_cont.grid(row=2, column=1, padx=4, sticky="we")
        self.b_excl = ttk.Button(box, text="🗑 Usuń / przywróć stronę (Delete)", command=self.toggle_excl)
        self.b_excl.grid(row=2, column=0, sticky="w", pady=2)
        box.columnconfigure(0, weight=1)

        box2 = ttk.LabelFrame(right, text="Duplikaty", padding=8)
        box2.pack(fill="x", pady=4)
        self.dup_label = ttk.Label(box2, text="—", wraplength=460)
        self.dup_label.pack(anchor="w")
        self.b_dups = ttk.Button(box2, text="🗑 Usuń wszystkie podpowiedziane duplikaty", command=self.exclude_dups)
        self.b_dups.pack(anchor="w", pady=4)

        box3 = ttk.LabelFrame(right, text="Kolejność po uporządkowaniu", padding=8)
        box3.pack(fill="both", expand=True, pady=4)
        self.order_list = tk.Listbox(box3, font=("Segoe UI", 10), activestyle="none")
        self.order_list.pack(fill="both", expand=True)
        self.order_list.bind("<<ListboxSelect>>", self._jump_from_list)
        self.warn = ttk.Label(right, text="", foreground=COL_EXCL, wraplength=480)
        self.warn.pack(anchor="w")

        self.status = ttk.Label(self, text="", relief="sunken", anchor="w", padding=(6, 2))
        self.status.pack(fill="x", side="bottom")

        for key, d in (("<Left>", -1), ("<Right>", 1), ("<Up>", -COLS), ("<Down>", COLS)):
            self.bind(key, lambda e, d=d: self._move(d, e))
        self.bind("<Delete>", lambda e: self.toggle_excl() if self.focus_get() is not self.combo else None)

    def _wheel(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None and w is not self.canvas and w is not self.grid_frame:
            if w is self.order_list:
                return
            w = w.master
        self.canvas.yview_scroll(int(-e.delta / 40), "units")

    def _set_buttons(self):
        st = "normal" if self.proj else "disabled"
        for b in (self.b_save, self.b_extract, self.b_auto, self.b_start, self.b_cont, self.b_excl, self.b_dups):
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
        self.title(f"Porządkowanie partytur – {os.path.basename(path)}")
        for p in range(1, self.proj.n + 1):
            cell = tk.Frame(self.grid_frame, background="#e8e8e8", bd=3, relief="flat", cursor="hand2")
            cell.grid(row=(p - 1) // COLS, column=(p - 1) % COLS, padx=4, pady=4, sticky="n")
            img = tk.Label(cell, text=f"str. {p}", width=20, height=10, background="white")
            img.pack()
            cap = tk.Label(cell, text="", width=22, anchor="w", justify="left", background="#e8e8e8",
                           font=("Segoe UI", 9), wraplength=THUMB_W + 10)
            cap.pack(fill="x")
            for w in (cell, img, cap):
                w.bind("<Button-1>", lambda e, p=p: self.select(p))
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
    def select(self, p):
        if not self.proj or p < 1 or p > self.proj.n:
            return
        self.sel = p
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
        if self.sel in self.proj.excluded:
            self.proj.excluded.discard(self.sel)
        else:
            self.proj.excluded.add(self.sel)
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
            cap.configure(text=txt, foreground=col,
                          font=("Segoe UI", 9, "bold" if is_start or p in self.proj.excluded else "normal"))
            border = COL_SEL if p == self.sel else (COL_EXCL if p in self.proj.excluded else "#e8e8e8")
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
                                           initialfile=f"{base}_{core.safe_name(q.split(' ')[0]).upper()}.pdf",
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
                out = os.path.join(outdir, f"{name}_{core.safe_name(q.split(' ')[0]).upper()}.pdf")
                n = pr.export_matching(q, out)
                if n:
                    parts = [p for p, _ in pr.ordered_parts() if core.matches(p, q)]
                    report.append(f"✔ {name}: {n} str. ({', '.join(parts)})")
                    made.append(out)
                else:
                    report.append(f"✖ {name}: brak partii „{q}”")
        if made and messagebox.askyesno("Gotowe", f"Utworzono {pl(len(made), 'plik', 'pliki', 'plików')}.\nSpakować je też do pliku ZIP?"):
            label = "uporzadkowane" if mode == "order" else core.safe_name(q.split(' ')[0])
            zp = os.path.join(outdir, f"Partie_{label}.zip")
            core.make_zip(made, zp, os.path.splitext(os.path.basename(zp))[0])
            report.append(f"\nZIP: {zp}")
        show_report(self, "Raport", "\n".join(report))

    def help(self):
        messagebox.showinfo("Pomoc", __doc__)


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


def ask_part(parent, title):
    """Okienko wyboru partii: kategoria z listy albo dowolny tekst."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.transient(parent)
    win.grab_set()
    ttk.Label(win, text="Wybierz kategorię albo wpisz fragment nazwy partii (np. „Tenor”, „Trumpet 1”):",
              padding=10, wraplength=380).pack()
    var = tk.StringVar(value=list(core.CATEGORIES)[0])
    cb = ttk.Combobox(win, textvariable=var, values=list(core.CATEGORIES), width=32, font=("Segoe UI", 11))
    cb.pack(padx=10)
    res = {"v": None}

    def ok(e=None):
        res["v"] = var.get().strip() or None
        win.destroy()
    ttk.Button(win, text="OK", command=ok).pack(pady=10)
    cb.bind("<Return>", ok)
    cb.focus_set()
    win.geometry(f"+{parent.winfo_rootx() + 200}+{parent.winfo_rooty() + 150}")
    parent.wait_window(win)
    return res["v"]


def show_report(parent, title, text):
    win = tk.Toplevel(parent)
    win.title(title)
    t = tk.Text(win, width=100, height=min(30, text.count("\n") + 3), font=("Segoe UI", 10))
    t.insert("1.0", text)
    t.configure(state="disabled")
    t.pack(padx=8, pady=8)
    ttk.Button(win, text="Zamknij", command=win.destroy).pack(pady=6)


if __name__ == "__main__":
    App().mainloop()

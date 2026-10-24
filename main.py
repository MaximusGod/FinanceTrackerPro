from datetime import datetime
from functools import lru_cache
import os
from pathlib import Path
import sys
import tempfile
from tkinter import messagebox
from typing import List, Optional, Tuple

# Garantisce una directory di cache valida per Matplotlib su ogni OS
if "MPLCONFIGDIR" not in os.environ:
    _temp_mpl = os.path.join(tempfile.gettempdir(), "matplotlib_financetracker")
    try:
        os.makedirs(_temp_mpl, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = _temp_mpl
    except Exception:
        pass

# Su Windows associa il processo a un AppID esplicito per la barra delle applicazioni
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("financetracker.pro.app")
    except Exception:
        pass

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from database import (
    add_transaction,
    delete_transaction,
    export_year_to_file,
    get_available_years,
    get_setting,
    get_transactions_by_year,
    init_db,
    set_setting,
)
from tracker import disegna_grafici_in_tempo_reale

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# DIZIONARIO DI TRADUZIONE MULTILINGUA
TRANSLATIONS = {
    "IT": {
        "year_label": "Anno:",
        "all_years": "Tutti",
        "export_btn": "Salva File",
        "balance_card": "SALDO ANNO",
        "income_card": "▲  ENTRATE TOTALI",
        "expense_card": "▼  USCITE TOTALI",
        "new_trans_title": "Nuovo Movimento",
        "expense_tab": "Uscita",
        "income_tab": "Entrata",
        "amount_lbl": "Importo (€)",
        "category_lbl": "Categoria",
        "date_lbl": "Data (YYYY-MM-DD)",
        "desc_lbl": "Descrizione / Note (opzionale)",
        "add_btn": "Aggiungi Movimento",
        "feed_title": "Movimenti",
        "filter_all": "Tutti",
        "filter_expenses": "Uscite",
        "filter_incomes": "Entrate",
        "charts_title": "Analisi Finanziaria in Tempo Reale",
        "live_lbl": "● LIVE",
        "no_data": "Nessuna transazione registrata.",
        "load_more": "Carica altri movimenti ({n} rimanenti)...",
        "confirm_del_title": "Elimina Movimento",
        "confirm_del_msg": "Sei sicuro di voler eliminare questa voce dallo storico?",
        "export_empty_title": "Nessun dato",
        "export_empty_msg": "Non ci sono transazioni da archiviare per l'anno {year}.",
        "export_success_title": "Archivio Salvato con Successo",
        "export_success_msg": "Tutte le transazioni dell'anno {year} sono state salvate nel file:\n\n{path}\n\nPuoi conservare questo file come backup permanente!",
        "err_amount": "Inserisci un importo numerico valido.",
        "err_amount_positive": "L'importo deve essere maggiore di zero.",
        "err_cat": "Specifica una categoria.",
        "err_date_format": "Data non valida. Usa il formato YYYY-MM-DD (es. 2026-10-17).",
        "err_date_range": "L'anno della data deve essere compreso tra 1900 e 2100.",
    },
    "EN": {
        "year_label": "Year:",
        "all_years": "All",
        "export_btn": "Save File",
        "balance_card": "YEAR BALANCE",
        "income_card": "▲  TOTAL INCOME",
        "expense_card": "▼  TOTAL EXPENSES",
        "new_trans_title": "New Transaction",
        "expense_tab": "Expense",
        "income_tab": "Income",
        "amount_lbl": "Amount (€)",
        "category_lbl": "Category",
        "date_lbl": "Date (YYYY-MM-DD)",
        "desc_lbl": "Description / Notes (optional)",
        "add_btn": "Add Transaction",
        "feed_title": "Transactions",
        "filter_all": "All",
        "filter_expenses": "Expenses",
        "filter_incomes": "Income",
        "charts_title": "Real-Time Financial Analysis",
        "live_lbl": "● LIVE",
        "no_data": "No transactions recorded.",
        "load_more": "Load more transactions ({n} remaining)...",
        "confirm_del_title": "Delete Transaction",
        "confirm_del_msg": "Are you sure you want to delete this entry?",
        "export_empty_title": "No Data",
        "export_empty_msg": "There are no transactions to archive for year {year}.",
        "export_success_title": "Archive Saved Successfully",
        "export_success_msg": "All transactions for year {year} were saved to:\n\n{path}\n\nYou can keep this file as a permanent backup!",
        "err_amount": "Please enter a valid numeric amount.",
        "err_amount_positive": "Amount must be greater than zero.",
        "err_cat": "Please specify a category.",
        "err_date_format": "Invalid date. Please use YYYY-MM-DD format (e.g. 2026-10-17).",
        "err_date_range": "Date year must be between 1900 and 2100.",
    },
}

CATEGORIE_SUGGERITE = {
    "IT": [
        "Spesa",
        "Stipendio",
        "Ristoranti & Bar",
        "Trasporti",
        "Casa & Affitto",
        "Utenze & Bollette",
        "Svago & Tempo Libero",
        "Salute & Benessere",
        "Shopping",
        "Altro",
    ],
    "EN": [
        "Groceries",
        "Salary",
        "Restaurants & Bars",
        "Transport",
        "Housing & Rent",
        "Utilities & Bills",
        "Leisure & Entertainment",
        "Health & Wellbeing",
        "Shopping",
        "Other",
    ],
}

ICON_KEYWORDS = [
    (("spesa", "supermercato", "alimentar", "grocer"), ""),
    (("stipendio", "lavoro", "fattura", "bonifico", "salary", "wage"), ""),
    (("ristorant", "bar", "pizza", "cena", "pranzo", "caff", "dining", "restaurant"), ""),
    (("trasport", "benzina", "carburante", "auto", "treno", "bus", "transport"), ""),
    (("casa", "affitto", "mutuo", "rent", "house", "housing"), ""),
    (("bollett", "luce", "gas", "internet", "utenze", "bills", "utilities"), ""),
    (("svago", "cinema", "hobby", "vacanz", "gioco", "entertainment", "leisure"), ""),
    (("salute", "farmacia", "medico", "visita", "health", "wellbeing"), ""),
    (("shopping", "abbigliamento", "vestit", "clothes"), ""),
]


@lru_cache(maxsize=256)
def ottieni_icona_categoria(categoria: str) -> str:
    """Restituisce l'icona appropriata per la categoria con memoization LRU ad alte prestazioni."""
    cat = categoria.lower()
    for parole, icona in ICON_KEYWORDS:
        if any(p in cat for p in parole):
            return icona
    return "" if ("entrata" in cat or "income" in cat or "guadagno" in cat) else ""


def find_asset(filename: str) -> Optional[Path]:
    """Cerca e trova un file di risorsa (es. icona) in modo affidabile su ogni OS e modalità di avvio."""
    candidates = []
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / filename)
        candidates.append(Path(sys.executable).resolve().parent / filename)
    candidates.append(Path(__file__).resolve().parent / filename)
    candidates.append(Path.cwd() / filename)

    for path in candidates:
        if path.is_file():
            return path
    return None


class MiaFinanza(ctk.CTk):

    def __init__(self):
        super().__init__()

        init_db()

        # Configurazione icona cross-platform (Windows, Linux, macOS)
        try:
            ico_path = find_asset("icon.ico")
            png_path = find_asset("icon.png")

            if sys.platform.startswith("win") and ico_path:
                self.iconbitmap(str(ico_path))
            elif png_path:
                from PIL import Image, ImageTk
                self._app_icon = ImageTk.PhotoImage(Image.open(str(png_path)))
                self.iconphoto(False, self._app_icon)
            elif ico_path:
                from PIL import Image, ImageTk
                self._app_icon = ImageTk.PhotoImage(Image.open(str(ico_path)))
                self.iconphoto(False, self._app_icon)
        except Exception:
            pass

        # Carica la lingua salvata o default "IT"
        self.lang = get_setting("language", "IT")

        self.title("Finance Tracker Pro")
        self.geometry("1150x960")
        self.minsize(980, 750)

        self.anno_selezionato = str(datetime.now().year)
        self.dati_transazioni: List[Tuple] = []
        self.filtro_corrente = "Tutti"
        self.limite_visibili = 50

        # Strutture per widget pooling (rendering istantaneo del feed senza distruzioni continue)
        self._card_pool: List[dict] = []
        self._empty_frame: Optional[ctk.CTkFrame] = None
        self._btn_mostra_altri: Optional[ctk.CTkButton] = None
        self._last_years_list: Optional[List[str]] = None

        # --- 1. BARRA SUPERIORE ---
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.top_bar.pack(fill="x", padx=25, pady=(15, 5))

        ctk.CTkLabel(
            self.top_bar,
            text="Finance Tracker Pro",
            font=("Arial", 18, "bold"),
        ).pack(side="left")

        self.box_anno_comandi = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.box_anno_comandi.pack(side="right")

        # Selettore Lingua
        self.scelta_lingua = ctk.CTkComboBox(
            self.box_anno_comandi,
            values=["IT", "EN"],
            width=95,
            height=32,
            font=("Arial", 12, "bold"),
            command=self.cambia_lingua,
        )
        self.scelta_lingua.set("IT" if self.lang == "IT" else "EN")
        self.scelta_lingua.pack(side="left", padx=(0, 12))

        self.lbl_anno_txt = ctk.CTkLabel(
            self.box_anno_comandi,
            text=self.t("year_label"),
            font=("Arial", 12, "bold"),
            text_color="#9ca3af",
        )
        self.lbl_anno_txt.pack(side="left", padx=(0, 6))

        self.scelta_anno = ctk.CTkComboBox(
            self.box_anno_comandi,
            values=[self.anno_selezionato, self.t("all_years")],
            width=110,
            height=32,
            font=("Arial", 12, "bold"),
            command=self.cambia_anno,
        )
        self.scelta_anno.set(self.anno_selezionato)
        self.scelta_anno.pack(side="left", padx=(0, 10))

        self.btn_esporta_archivio = ctk.CTkButton(
            self.box_anno_comandi,
            text=self.t("export_btn"),
            font=("Arial", 12, "bold"),
            height=32,
            width=150,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.esporta_archivio_anno,
        )
        self.btn_esporta_archivio.pack(side="left")

        # --- 2. KPI CARDS ---
        self.kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_container.pack(fill="x", padx=25, pady=(5, 8))
        self.kpi_container.grid_columnconfigure((0, 1, 2), weight=1, uniform="kpi")

        # Card 1: Saldo
        self.card_saldo = ctk.CTkFrame(
            self.kpi_container, corner_radius=12, fg_color=("#2b2d35", "#1f222a")
        )
        self.card_saldo.grid(row=0, column=0, padx=(0, 6), sticky="nsew")

        self.lbl_titolo_saldo = ctk.CTkLabel(
            self.card_saldo,
            text=self.t("balance_card"),
            font=("Arial", 11, "bold"),
            text_color="#9ca3af",
        )
        self.lbl_titolo_saldo.pack(anchor="w", padx=16, pady=(12, 2))

        self.lbl_valore_saldo = ctk.CTkLabel(
            self.card_saldo,
            text="€ 0.00",
            font=("Arial", 22, "bold"),
            text_color="#10b981",
        )
        self.lbl_valore_saldo.pack(anchor="w", padx=16, pady=(0, 12))

        # Card 2: Entrate
        self.card_entrate = ctk.CTkFrame(
            self.kpi_container, corner_radius=12, fg_color=("#2b2d35", "#1f222a")
        )
        self.card_entrate.grid(row=0, column=1, padx=3, sticky="nsew")

        self.lbl_titolo_entrate = ctk.CTkLabel(
            self.card_entrate,
            text=self.t("income_card"),
            font=("Arial", 11, "bold"),
            text_color="#9ca3af",
        )
        self.lbl_titolo_entrate.pack(anchor="w", padx=16, pady=(12, 2))

        self.lbl_valore_entrate = ctk.CTkLabel(
            self.card_entrate,
            text="+ € 0.00",
            font=("Arial", 20, "bold"),
            text_color="#10b981",
        )
        self.lbl_valore_entrate.pack(anchor="w", padx=16, pady=(0, 12))

        # Card 3: Uscite
        self.card_uscite = ctk.CTkFrame(
            self.kpi_container, corner_radius=12, fg_color=("#2b2d35", "#1f222a")
        )
        self.card_uscite.grid(row=0, column=2, padx=(6, 0), sticky="nsew")

        self.lbl_titolo_uscite = ctk.CTkLabel(
            self.card_uscite,
            text=self.t("expense_card"),
            font=("Arial", 11, "bold"),
            text_color="#9ca3af",
        )
        self.lbl_titolo_uscite.pack(anchor="w", padx=16, pady=(12, 2))

        self.lbl_valore_uscite = ctk.CTkLabel(
            self.card_uscite,
            text="- € 0.00",
            font=("Arial", 20, "bold"),
            text_color="#f43f5e",
        )
        self.lbl_valore_uscite.pack(anchor="w", padx=16, pady=(0, 12))

        # --- 3. ZONA CENTRALE ---
        self.blocco_principale = ctk.CTkFrame(self, fg_color="transparent")
        self.blocco_principale.pack(fill="both", expand=True, padx=25, pady=(5, 8))

        # FORM (SX)
        self.colonna_sx = ctk.CTkFrame(
            self.blocco_principale,
            width=350,
            corner_radius=14,
            fg_color=("#2b2d35", "#1f222a"),
        )
        self.colonna_sx.pack(side="left", fill="y", padx=(0, 12))

        self.lbl_form_title = ctk.CTkLabel(
            self.colonna_sx,
            text=self.t("new_trans_title"),
            font=("Arial", 15, "bold"),
        )
        self.lbl_form_title.pack(anchor="w", padx=18, pady=(12, 8))

        self.seg_tipo = ctk.CTkSegmentedButton(
            self.colonna_sx,
            values=[self.t("expense_tab"), self.t("income_tab")],
            selected_color="#ef4444",
            selected_hover_color="#dc2626",
            font=("Arial", 12, "bold"),
            command=self.cambia_colore_tipo,
        )
        self.seg_tipo.set(self.t("expense_tab"))
        self.seg_tipo.pack(fill="x", padx=18, pady=(0, 8))

        self.lbl_importo_txt = ctk.CTkLabel(
            self.colonna_sx, text=self.t("amount_lbl"), font=("Arial", 11), text_color="#9ca3af"
        )
        self.lbl_importo_txt.pack(anchor="w", padx=18)

        self.campo_quanto = ctk.CTkEntry(
            self.colonna_sx, placeholder_text="es. 49.90", font=("Arial", 13), height=32, corner_radius=8
        )
        self.campo_quanto.pack(fill="x", padx=18, pady=(1, 6))

        self.lbl_cat_txt = ctk.CTkLabel(
            self.colonna_sx, text=self.t("category_lbl"), font=("Arial", 11), text_color="#9ca3af"
        )
        self.lbl_cat_txt.pack(anchor="w", padx=18)

        cats_correnti = CATEGORIE_SUGGERITE.get(self.lang, CATEGORIE_SUGGERITE["IT"])
        self.campo_cat = ctk.CTkComboBox(
            self.colonna_sx, values=cats_correnti, font=("Arial", 12), height=32, corner_radius=8
        )
        self.campo_cat.set(cats_correnti[0])
        self.campo_cat.pack(fill="x", padx=18, pady=(1, 6))

        self.lbl_date_txt = ctk.CTkLabel(
            self.colonna_sx, text=self.t("date_lbl"), font=("Arial", 11), text_color="#9ca3af"
        )
        self.lbl_date_txt.pack(anchor="w", padx=18)

        self.campo_quando = ctk.CTkEntry(
            self.colonna_sx, font=("Arial", 12), height=32, corner_radius=8
        )
        self.campo_quando.insert(0, datetime.now().strftime("%Y-%m-%d"))
        self.campo_quando.pack(fill="x", padx=18, pady=(1, 6))

        self.lbl_desc_txt = ctk.CTkLabel(
            self.colonna_sx, text=self.t("desc_lbl"), font=("Arial", 11), text_color="#9ca3af"
        )
        self.lbl_desc_txt.pack(anchor="w", padx=18)

        self.campo_note = ctk.CTkEntry(
            self.colonna_sx, placeholder_text="es. Spesa settimanale", font=("Arial", 12), height=32, corner_radius=8
        )
        self.campo_note.pack(fill="x", padx=18, pady=(1, 10))

        self.btn_salva = ctk.CTkButton(
            self.colonna_sx,
            text=self.t("add_btn"),
            font=("Arial", 13, "bold"),
            height=38,
            corner_radius=8,
            fg_color="#10b981",
            hover_color="#059669",
            command=self.aggiungi_transazione,
        )
        self.btn_salva.pack(fill="x", padx=18, pady=(0, 12))

        # Scorciatoia rapida da tastiera: Invio salva il movimento da qualsiasi campo
        self.campo_quanto.bind("<Return>", lambda _e: self.aggiungi_transazione())
        self.campo_quando.bind("<Return>", lambda _e: self.aggiungi_transazione())
        self.campo_note.bind("<Return>", lambda _e: self.aggiungi_transazione())

        # FEED TRANSAZIONI (DX)
        self.colonna_dx = ctk.CTkFrame(
            self.blocco_principale, corner_radius=14, fg_color=("#2b2d35", "#1f222a")
        )
        self.colonna_dx.pack(side="right", fill="both", expand=True)

        self.header_feed = ctk.CTkFrame(self.colonna_dx, fg_color="transparent")
        self.header_feed.pack(fill="x", padx=18, pady=(12, 6))

        self.lbl_titolo_feed = ctk.CTkLabel(
            self.header_feed, text=self.t("feed_title"), font=("Arial", 15, "bold")
        )
        self.lbl_titolo_feed.pack(side="left")

        self.filtro_segmented = ctk.CTkSegmentedButton(
            self.header_feed,
            values=[self.t("filter_all"), self.t("filter_expenses"), self.t("filter_incomes")],
            font=("Arial", 11, "bold"),
            command=self.applica_filtro,
        )
        self.filtro_segmented.set(self.t("filter_all"))
        self.filtro_segmented.pack(side="right")

        self.feed_scrollable = ctk.CTkScrollableFrame(
            self.colonna_dx, fg_color="transparent", corner_radius=0
        )
        self.feed_scrollable.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # --- 4. GRAFICI ---
        self.blocco_grafici = ctk.CTkFrame(
            self, height=360, corner_radius=14, fg_color=("#2b2d35", "#1f222a")
        )
        self.blocco_grafici.pack(fill="x", padx=25, pady=(0, 15))
        self.blocco_grafici.pack_propagate(False)

        self.header_grafici = ctk.CTkFrame(self.blocco_grafici, fg_color="transparent")
        self.header_grafici.pack(fill="x", padx=18, pady=(10, 4))

        self.lbl_titolo_grafici = ctk.CTkLabel(
            self.header_grafici, text=self.t("charts_title"), font=("Arial", 14, "bold")
        )
        self.lbl_titolo_grafici.pack(side="left")

        self.lbl_live_badge = ctk.CTkLabel(
            self.header_grafici, text=self.t("live_lbl"), font=("Arial", 10, "bold"), text_color="#10b981"
        )
        self.lbl_live_badge.pack(side="right")

        # Inizializzazione diretta di Figure Matplotlib (senza pyplot state machine per massime prestazioni)
        self.figura = Figure(figsize=(11.5, 3.5), dpi=100)
        self.figura.patch.set_facecolor("#1f222a")
        self.ax_mese = self.figura.add_subplot(121)
        self.ax_giorno = self.figura.add_subplot(122)

        self.canvas_grafici = FigureCanvasTkAgg(self.figura, master=self.blocco_grafici)
        self.canvas_grafici.get_tk_widget().pack(fill="both", expand=True, padx=14, pady=(0, 10))

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_dati()

    def t(self, key: str) -> str:
        """Helper rapido per la traduzione con fallback immediato."""
        return TRANSLATIONS.get(self.lang, TRANSLATIONS["IT"]).get(key, key)

    def cambia_lingua(self, scelta: str) -> None:
        """Cambia dinamicamente la lingua dell'intera UI."""
        nuova_lang = "IT" if "IT" in scelta else "EN"
        if nuova_lang == self.lang:
            return

        self.lang = nuova_lang
        set_setting("language", nuova_lang)

        # Aggiorna elenco categorie suggerite
        nuove_cat = CATEGORIE_SUGGERITE.get(self.lang, CATEGORIE_SUGGERITE["IT"])
        self.campo_cat.configure(values=nuove_cat)
        self.campo_cat.set(nuove_cat[0])

        # Aggiorna etichette e testi dell'interfaccia
        self.lbl_anno_txt.configure(text=self.t("year_label"))
        self.btn_esporta_archivio.configure(text=self.t("export_btn"))
        self.lbl_titolo_saldo.configure(text=self.t("balance_card"))
        self.lbl_titolo_entrate.configure(text=self.t("income_card"))
        self.lbl_titolo_uscite.configure(text=self.t("expense_card"))
        self.lbl_form_title.configure(text=self.t("new_trans_title"))

        self.seg_tipo.configure(values=[self.t("expense_tab"), self.t("income_tab")])
        self.seg_tipo.set(self.t("expense_tab"))

        self.lbl_importo_txt.configure(text=self.t("amount_lbl"))
        self.lbl_cat_txt.configure(text=self.t("category_lbl"))
        self.lbl_date_txt.configure(text=self.t("date_lbl"))
        self.lbl_desc_txt.configure(text=self.t("desc_lbl"))
        self.btn_salva.configure(text=self.t("add_btn"))

        self.lbl_titolo_feed.configure(text=self.t("feed_title"))

        self.filtro_segmented.configure(
            values=[self.t("filter_all"), self.t("filter_expenses"), self.t("filter_incomes")]
        )
        self.filtro_segmented.set(self.t("filter_all"))
        self.filtro_corrente = "Tutti"

        self.lbl_titolo_grafici.configure(text=self.t("charts_title"))
        self.lbl_live_badge.configure(text=self.t("live_lbl"))

        self.refresh_dati()

    def on_close(self) -> None:
        """Rilascia le risorse e chiude la finestra in modo pulito."""
        try:
            self.figura.clear()
        except Exception:
            pass
        finally:
            self.destroy()

    def cambia_anno(self, nuovo_anno: str) -> None:
        self.anno_selezionato = nuovo_anno
        self.limite_visibili = 50
        self.refresh_dati()

    def esporta_archivio_anno(self) -> None:
        if not self.dati_transazioni:
            messagebox.showwarning(
                self.t("export_empty_title"),
                self.t("export_empty_msg").format(year=self.anno_selezionato),
            )
            return

        percorso_file = export_year_to_file(self.anno_selezionato)
        messagebox.showinfo(
            self.t("export_success_title"),
            self.t("export_success_msg").format(year=self.anno_selezionato, path=str(percorso_file)),
        )

    def cambia_colore_tipo(self, scelta: str) -> None:
        if scelta in ("Entrata", "Income"):
            self.seg_tipo.configure(selected_color="#10b981", selected_hover_color="#059669")
        else:
            self.seg_tipo.configure(selected_color="#ef4444", selected_hover_color="#dc2626")

    def applica_filtro(self, filtro: str) -> None:
        if filtro in ("Tutti", "All"):
            self.filtro_corrente = "Tutti"
        elif filtro in ("Uscite", "Expenses"):
            self.filtro_corrente = "Uscite"
        else:
            self.filtro_corrente = "Entrate"

        self.limite_visibili = 50
        self.renderizza_lista()

    def ricalcola_statistiche(self, lista_righe: List[Tuple]) -> None:
        """Calcola saldo, entrate e uscite in un unico passaggio O(N)."""
        entrate = 0.0
        uscite = 0.0
        for r in lista_righe:
            val = r[3]
            if r[2] == "entrata":
                entrate += val
            else:
                uscite += val
        saldo = entrate - uscite

        colore_saldo = "#10b981" if saldo >= 0 else "#f43f5e"
        self.lbl_valore_saldo.configure(text=f"€ {saldo:,.2f}", text_color=colore_saldo)
        self.lbl_valore_entrate.configure(text=f"+ € {entrate:,.2f}")
        self.lbl_valore_uscite.configure(text=f"- € {uscite:,.2f}")

    def aggiungi_transazione(self) -> None:
        """Valida e registra un nuovo movimento finanziario."""
        scelta_raw = self.seg_tipo.get().lower()
        tipo = "entrata" if ("entrata" in scelta_raw or "income" in scelta_raw) else "uscita"
        data = self.campo_quando.get().strip()
        cat = self.campo_cat.get().strip()
        note = self.campo_note.get().strip()

        categoria_pulita = (
            cat.split(" ", 1)[-1] if " " in cat and ord(cat[0]) > 255 else cat
        )

        try:
            valore_testo = self.campo_quanto.get().replace(",", ".").strip()
            importo = float(valore_testo)
            if importo <= 0:
                messagebox.showwarning("Warning", self.t("err_amount_positive"))
                return
        except ValueError:
            messagebox.showerror("Error", self.t("err_amount"))
            return

        if not cat:
            messagebox.showwarning("Warning", self.t("err_cat"))
            return

        # Validazione robusta formato data YYYY-MM-DD
        try:
            dt_val = datetime.strptime(data, "%Y-%m-%d")
            if not (1900 <= dt_val.year <= 2100):
                messagebox.showwarning("Warning", self.t("err_date_range"))
                return
        except ValueError:
            messagebox.showwarning("Warning", self.t("err_date_format"))
            return

        add_transaction(data, tipo, importo, categoria_pulita, note)

        self.campo_quanto.delete(0, "end")
        self.campo_note.delete(0, "end")

        anno_transazione = str(dt_val.year)
        if self.anno_selezionato not in ("Tutti", "All") and self.anno_selezionato != anno_transazione:
            self.anno_selezionato = anno_transazione
            self.scelta_anno.set(anno_transazione)

        self.refresh_dati()

    def cancella_transazione(self, id_transazione: int) -> None:
        if messagebox.askyesno(
            self.t("confirm_del_title"),
            self.t("confirm_del_msg"),
        ):
            delete_transaction(id_transazione)
            self.refresh_dati()

    def refresh_dati(self) -> None:
        """Ricarica i dati del DB, aggiorna i selettori e rinfresca la UI."""
        anni_db = get_available_years()
        anno_corrente = str(datetime.now().year)

        tutti_gli_anni = [anno_corrente]
        for a in anni_db:
            if a not in tutti_gli_anni:
                tutti_gli_anni.append(a)
        tutti_gli_anni.append(self.t("all_years"))

        # Aggiorna il dropdown anni solo se la lista è effettivamente cambiata
        if tutti_gli_anni != self._last_years_list:
            self._last_years_list = tutti_gli_anni
            self.scelta_anno.configure(values=tutti_gli_anni)
            self.scelta_anno.set(self.anno_selezionato)

        self.dati_transazioni = get_transactions_by_year(self.anno_selezionato)
        self.ricalcola_statistiche(self.dati_transazioni)
        self.renderizza_lista()

        disegna_grafici_in_tempo_reale(
            self.figura,
            self.ax_mese,
            self.ax_giorno,
            self.anno_selezionato,
            self.dati_transazioni,
            lang=self.lang,
        )
        # draw_idle() aggiorna la vista grafica senza bloccare il thread UI principale
        self.canvas_grafici.draw_idle()

    def mostra_altri(self) -> None:
        self.limite_visibili += 50
        self.renderizza_lista()

    def renderizza_lista(self) -> None:
        """Renderizza la lista movimenti con riciclo widget (pooling) ad altissime prestazioni."""
        if self.filtro_corrente == "Tutti":
            dati_filtrati = self.dati_transazioni
        elif self.filtro_corrente == "Entrate":
            dati_filtrati = [r for r in self.dati_transazioni if r[2] == "entrata"]
        else:
            dati_filtrati = [r for r in self.dati_transazioni if r[2] == "uscita"]

        # Rimuove temporaneamente il pulsante 'mostra altri' per preservare l'ordine corretto in basso
        if self._btn_mostra_altri is not None and self._btn_mostra_altri.winfo_ismapped():
            self._btn_mostra_altri.pack_forget()

        if not dati_filtrati:
            # Nasconde le card nel pool
            for item in self._card_pool:
                if item["packed"]:
                    item["frame"].pack_forget()
                    item["packed"] = False

            if self._empty_frame is None:
                self._empty_frame = ctk.CTkFrame(self.feed_scrollable, fg_color="transparent")
                self._empty_label = ctk.CTkLabel(
                    self._empty_frame,
                    text=self.t("no_data"),
                    font=("Arial", 13),
                    text_color="#9ca3af",
                )
                self._empty_label.pack(pady=(4, 0))

            self._empty_label.configure(text=self.t("no_data"))
            if not self._empty_frame.winfo_ismapped():
                self._empty_frame.pack(pady=35)
            return

        # Nasconde lo stato vuoto se presente
        if self._empty_frame is not None and self._empty_frame.winfo_ismapped():
            self._empty_frame.pack_forget()

        totale_filtrati = len(dati_filtrati)
        da_mostrare = dati_filtrati[::-1][: self.limite_visibili]

        for i, riga in enumerate(da_mostrare):
            id_db, data_str, tipo, amount, categoria, note = riga
            is_entrata = (tipo == "entrata")
            colore_importo = "#10b981" if is_entrata else "#f43f5e"
            segno = "+" if is_entrata else "-"
            icona = ottieni_icona_categoria(categoria)
            dettaglio = f"{data_str}  •  {note}" if note else data_str
            testo_importo = f"{segno} € {float(amount):,.2f}"

            if i < len(self._card_pool):
                # Riutilizzo istantaneo del widget esistente
                item = self._card_pool[i]
                item["badge"].configure(text=icona)
                item["lbl_cat"].configure(text=categoria)
                item["lbl_det"].configure(text=dettaglio)
                item["lbl_imp"].configure(text=testo_importo, text_color=colore_importo)
                item["btn_del"].configure(command=lambda tid=id_db: self.cancella_transazione(tid))

                if not item["packed"]:
                    item["frame"].pack(fill="x", pady=3, padx=4)
                    item["packed"] = True
            else:
                # Creazione nuovo widget nel pool solo se strettamente necessario
                card = ctk.CTkFrame(
                    self.feed_scrollable,
                    fg_color=("#374151", "#262932"),
                    corner_radius=10,
                )
                badge = ctk.CTkLabel(
                    card,
                    text=icona,
                    font=("Arial", 16),
                    width=34,
                    height=34,
                    corner_radius=8,
                    fg_color=("#4b5563", "#1b1d24"),
                )
                badge.pack(side="left", padx=(10, 8), pady=8)

                box_info = ctk.CTkFrame(card, fg_color="transparent")
                box_info.pack(side="left", fill="both", expand=True, pady=6)

                lbl_categoria = ctk.CTkLabel(
                    box_info,
                    text=categoria,
                    font=("Arial", 12, "bold"),
                    anchor="w",
                )
                lbl_categoria.pack(anchor="w")

                lbl_dettaglio = ctk.CTkLabel(
                    box_info,
                    text=dettaglio,
                    font=("Arial", 10),
                    text_color="#9ca3af",
                    anchor="w",
                )
                lbl_dettaglio.pack(anchor="w")

                btn_elimina = ctk.CTkButton(
                    card,
                    text="✕",
                    width=28,
                    height=28,
                    font=("Arial", 11),
                    fg_color="transparent",
                    hover_color="#ef4444",
                    text_color="#9ca3af",
                    corner_radius=6,
                    command=lambda tid=id_db: self.cancella_transazione(tid),
                )
                btn_elimina.pack(side="right", padx=(4, 10), pady=8)

                lbl_importo = ctk.CTkLabel(
                    card,
                    text=testo_importo,
                    font=("Arial", 12, "bold"),
                    text_color=colore_importo,
                )
                lbl_importo.pack(side="right", padx=(8, 4), pady=8)

                card.pack(fill="x", pady=3, padx=4)

                self._card_pool.append({
                    "frame": card,
                    "badge": badge,
                    "lbl_cat": lbl_categoria,
                    "lbl_det": lbl_dettaglio,
                    "btn_del": btn_elimina,
                    "lbl_imp": lbl_importo,
                    "packed": True,
                })

        # Nasconde eventuali card eccedenti nel pool
        for j in range(len(da_mostrare), len(self._card_pool)):
            item = self._card_pool[j]
            if item["packed"]:
                item["frame"].pack_forget()
                item["packed"] = False

        # Ripristina o nasconde il pulsante 'carica altri'
        if totale_filtrati > self.limite_visibili:
            rimanenti = totale_filtrati - self.limite_visibili
            if self._btn_mostra_altri is None:
                self._btn_mostra_altri = ctk.CTkButton(
                    self.feed_scrollable,
                    text="",
                    font=("Arial", 11, "bold"),
                    height=30,
                    fg_color="#374151",
                    hover_color="#4b5563",
                    command=self.mostra_altri,
                )
            self._btn_mostra_altri.configure(text=self.t("load_more").format(n=rimanenti))
            self._btn_mostra_altri.pack(fill="x", padx=20, pady=8)


if __name__ == "__main__":
    app = MiaFinanza()
    app.mainloop()

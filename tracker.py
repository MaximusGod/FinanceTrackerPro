

import os
from pathlib import Path
import tempfile
from typing import Optional, Tuple

# Garantisce una directory di cache valida per Matplotlib su ogni OS
if "MPLCONFIGDIR" not in os.environ:
    _temp_mpl = os.path.join(tempfile.gettempdir(), "matplotlib_financetracker")
    try:
        os.makedirs(_temp_mpl, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = _temp_mpl
    except Exception:
        pass

from matplotlib.ticker import FuncFormatter, MaxNLocator
import numpy as np
import pandas as pd

from database import get_transactions_by_year


def carica_dataframe(anno: Optional[str] = None, righe: Optional[list] = None) -> Optional[pd.DataFrame]:
    """Converte le righe delle transazioni in un DataFrame Pandas con tipi ottimizzati e parsing sicuro."""
    if righe is None:
        righe = get_transactions_by_year(anno)

    if not righe:
        return None

    df = pd.DataFrame(
        righe,
        columns=["id", "date", "type", "amount", "category", "description"],
    )
    # Parsing ISO rapido e sicuro con errors='coerce' per evitare crash su date anomale
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    df = df.dropna(subset=["date"])
    if df.empty:
        return None

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    return df


def elabora_statistiche(
    anno: Optional[str] = None, righe: Optional[list] = None
) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Calcola aggregazioni mensili e andamento giornaliero con operazioni vettoriali veloci."""
    df = carica_dataframe(anno, righe)
    if df is None or df.empty:
        return None, None

    is_entrata = df["type"] == "entrata"
    df["valore_netto"] = np.where(is_entrata, df["amount"], -df["amount"])
    df["entrata_val"] = np.where(is_entrata, df["amount"], 0.0)
    df["uscita_val"] = np.where(~is_entrata, df["amount"], 0.0)

    # 1. Statistiche mensili
    df["anno_mese"] = df["date"].dt.to_period("M")
    dati_mese = (
        df.groupby("anno_mese", observed=False)
        .agg(
            entrate=("entrata_val", "sum"),
            uscite=("uscita_val", "sum"),
            totale_netto=("valore_netto", "sum"),
        )
        .reset_index()
    )
    dati_mese["saldo_totale"] = dati_mese["totale_netto"].cumsum()
    dati_mese["etichetta_mese"] = dati_mese["anno_mese"].astype(str)

    # 2. Statistiche giornaliere (andamento progressivo)
    dati_giorno = (
        df.groupby("date", as_index=False, sort=True)["valore_netto"]
        .sum()
    )
    dati_giorno["anno_mese"] = dati_giorno["date"].dt.to_period("M")
    dati_giorno["saldo_progressivo"] = (
        dati_giorno.groupby("anno_mese", observed=False)["valore_netto"].cumsum()
    )

    if (anno in ("Tutti", "All") or anno is None) and dati_giorno["date"].dt.year.nunique() > 1:
        dati_giorno["etichetta_giorno"] = dati_giorno["date"].dt.strftime("%d/%m/%y")
    else:
        dati_giorno["etichetta_giorno"] = dati_giorno["date"].dt.strftime("%d/%m")

    return dati_mese, dati_giorno


def disegna_grafici_in_tempo_reale(
    figura, ax_mese, ax_giorno, anno: Optional[str] = None, righe: Optional[list] = None, lang: str = "IT"
) -> None:
    """Aggiorna i grafici in tempo reale riutilizzando i dati già in memoria e applicando la lingua."""
    dati_mese, dati_giorno = elabora_statistiche(anno, righe)

    ax_mese.clear()
    ax_giorno.clear()

    colore_bg = "#181a20"
    ax_mese.set_facecolor(colore_bg)
    ax_giorno.set_facecolor(colore_bg)

    # Traduzioni testi grafici
    txt_no_data = "Nessun dato registrato" if lang == "IT" else "No transactions recorded"
    lbl_income = "Entrate" if lang == "IT" else "Income"
    lbl_expenses = "Uscite" if lang == "IT" else "Expenses"
    lbl_balance = "Saldo Tot." if lang == "IT" else "Tot. Balance"
    lbl_month_balance = "Saldo Mese" if lang == "IT" else "Monthly Balance"
    titolo_m12 = "Entrate vs Uscite Mensili (ultimi 12 mesi)" if lang == "IT" else "Monthly Income vs Expenses (Last 12 Months)"
    titolo_m_base = "Entrate vs Uscite Mensili" if lang == "IT" else "Monthly Income vs Expenses"
    titolo_g_base = "Andamento Saldo Giornaliero" if lang == "IT" else "Daily Balance Trend"

    testo_anno = f" ({anno})" if anno and anno not in ("Tutti", "All") else ""

    if dati_mese is None or dati_mese.empty:
        for ax in (ax_mese, ax_giorno):
            ax.text(
                0.5,
                0.5,
                f"{txt_no_data}{testo_anno}",
                color="#6b7280",
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                transform=ax.transAxes,
            )
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
        figura.tight_layout(pad=2.2)
        return

    # 1. GRAFICO MENSILE
    if len(dati_mese) > 12:
        dati_mese_view = dati_mese.tail(12).reset_index(drop=True)
        titolo_mese = titolo_m12
    else:
        dati_mese_view = dati_mese
        titolo_mese = f"{titolo_m_base}{testo_anno}"

    x_labels_mese = dati_mese_view["etichetta_mese"]
    x_indices_mese = np.arange(len(x_labels_mese))
    width = 0.35

    ax_mese.bar(
        x_indices_mese - width / 2,
        dati_mese_view["entrate"],
        width=width,
        label=lbl_income,
        color="#10b981",
        alpha=0.88,
    )
    ax_mese.bar(
        x_indices_mese + width / 2,
        dati_mese_view["uscite"],
        width=width,
        label=lbl_expenses,
        color="#f43f5e",
        alpha=0.88,
    )

    ax_mese.plot(
        x_indices_mese,
        dati_mese_view["saldo_totale"],
        label=lbl_balance,
        color="#38bdf8",
        marker="o" if len(dati_mese_view) <= 12 else None,
        markersize=5,
        linewidth=2.2,
    )

    ax_mese.set_title(titolo_mese, color="white", fontsize=12, fontweight="bold", pad=10)
    ax_mese.set_xticks(x_indices_mese)
    ax_mese.set_xticklabels(x_labels_mese, color="#9ca3af", fontsize=10)
    ax_mese.set_ylabel("€", color="#9ca3af", fontsize=10)
    ax_mese.tick_params(colors="#9ca3af", labelsize=9)
    ax_mese.legend(facecolor="#262932", edgecolor="none", labelcolor="white", fontsize=9, loc="upper left")
    ax_mese.grid(True, color="#2b2d35", linestyle="--", alpha=0.6)

    # 2. GRAFICO GIORNALIERO
    n_punti = len(dati_giorno)
    x_indices_giorno = np.arange(n_punti)
    mostra_punti = n_punti <= 25

    ax_giorno.plot(
        x_indices_giorno,
        dati_giorno["saldo_progressivo"],
        color="#f59e0b",
        marker="o" if mostra_punti else None,
        markersize=4 if mostra_punti else 0,
        linewidth=2.0,
        label=lbl_month_balance,
    )
    ax_giorno.axhline(0, color="#4b5563", linestyle=":", linewidth=1.2)
    ax_giorno.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))

    # Formattazione data O(1) con tuple precalcolata per eliminare l'overhead di Pandas iloc
    etichette_rapide = tuple(dati_giorno["etichetta_giorno"])

    def formatta_data_scalabile(val, _):
        idx = int(round(val))
        if 0 <= idx < n_punti:
            return etichette_rapide[idx]
        return ""

    ax_giorno.xaxis.set_major_formatter(FuncFormatter(formatta_data_scalabile))

    ax_giorno.set_title(
        f"{titolo_g_base}{testo_anno}",
        color="white",
        fontsize=12,
        fontweight="bold",
        pad=10,
    )
    ax_giorno.set_ylabel("€", color="#9ca3af", fontsize=10)
    ax_giorno.tick_params(colors="#9ca3af", labelsize=9)
    ax_giorno.legend(facecolor="#262932", edgecolor="none", labelcolor="white", fontsize=9, loc="upper left")
    ax_giorno.grid(True, color="#2b2d35", linestyle="--", alpha=0.6)

    for ax in (ax_mese, ax_giorno):
        for spine in ax.spines.values():
            spine.set_color("#374151")

    figura.tight_layout(pad=2.2)
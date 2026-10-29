
import atexit
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, List, Optional, Tuple


def get_data_dir() -> Path:
    """Restituisce la directory corretta e persistente per DB e archivi su ogni OS.

    - macOS .app bundle: ~/Library/Application Support/FinanceTracker (permette scrittura)
    - PyInstaller standalone (Windows / Linux): directory dell'eseguibile
    - Sviluppo / Script locale: directory del file sorgente
    """
    if getattr(sys, "frozen", False):
        exe_path = Path(sys.executable).resolve()
      
        if sys.platform == "darwin" and ".app/Contents/MacOS" in str(exe_path):
            app_dir = Path.home() / "Library" / "Application Support" / "FinanceTracker"
            app_dir.mkdir(parents=True, exist_ok=True)
            return app_dir
        return exe_path.parent
    return Path(__file__).resolve().parent


BASE_DIR: Path = get_data_dir()
DB_NAME: Path = BASE_DIR / "finance.db"
ARCHIVI_DIR: Path = BASE_DIR / "archivi"


_conn: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Restituisce una connessione SQLite ottimizzata con Write-Ahead Logging e memory cache."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(
            str(DB_NAME),
            timeout=10.0,
            check_same_thread=False,
        )
      
        _conn.execute("PRAGMA journal_mode = WAL;")
        _conn.execute("PRAGMA synchronous = NORMAL;")
        _conn.execute("PRAGMA cache_size = -64000;")  
        _conn.execute("PRAGMA temp_store = MEMORY;")
        _conn.execute("PRAGMA mmap_size = 268435456;")  
    return _conn


def close_db() -> None:
    """Chiude in sicurezza la connessione al database all'uscita dall'applicazione."""
    global _conn
    if _conn is not None:
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None



atexit.register(close_db)


def init_db() -> None:
    """Inizializza le tabelle transactions e settings con indici ottimizzati."""
    conn = get_connection()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT CHECK(type IN ('entrata', 'uscita')) NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transactions_date_type ON transactions(date, type);"
        )
    
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)


def set_setting(key: str, value: Any) -> None:
    """Salva una preferenza di sistema in modo atomico."""
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )


def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Recupera una preferenza di sistema."""
    conn = get_connection()
    cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cursor.fetchone()
    return row[0] if row else default


def add_transaction(
    date_str: str,
    trans_type: str,
    amount: float,
    category: str,
    description: str = "",
) -> None:
    """Inserisce una nuova transazione nel database con commit atomico."""
    conn = get_connection()
    with conn:
        conn.execute(
            """
            INSERT INTO transactions (date, type, amount, category, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date_str, trans_type, amount, category, description),
        )


def delete_transaction(trans_id: int) -> None:
    """Elimina una transazione dato il suo ID."""
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))


def get_all_transactions() -> List[Tuple]:
    """Recupera tutte le transazioni ordinate per data crescente."""
    conn = get_connection()
    cursor = conn.execute(
        """
        SELECT id, date, type, amount, category, description
        FROM transactions
        ORDER BY date ASC, id ASC
        """
    )
    return cursor.fetchall()


def get_available_years() -> List[str]:
    """Restituisce gli anni distinti registrati nel database in ordine decrescente."""
    conn = get_connection()
    cursor = conn.execute(
        """
        SELECT DISTINCT SUBSTR(date, 1, 4) AS anno
        FROM transactions
        WHERE date IS NOT NULL AND length(date) >= 4
        ORDER BY anno DESC
        """
    )
    return [row[0] for row in cursor.fetchall() if row[0]]


def get_transactions_by_year(year: Optional[str] = None) -> List[Tuple]:
    """Recupera le transazioni per un anno specifico o tutte se year è None o 'Tutti' / 'All'."""
    if not year or year in ("Tutti", "All"):
        return get_all_transactions()

    conn = get_connection()
    cursor = conn.execute(
        """
        SELECT id, date, type, amount, category, description
        FROM transactions
        WHERE date LIKE ?
        ORDER BY date ASC, id ASC
        """,
        (f"{year}%",),
    )
    return cursor.fetchall()


def export_year_to_file(year: str) -> Path:
    """Esporta le transazioni dell'anno in un file JSON formattato dentro archivi/ in singolo passaggio."""
    righe = get_transactions_by_year(year)
    ARCHIVI_DIR.mkdir(parents=True, exist_ok=True)

    totale_entrate = 0.0
    totale_uscite = 0.0
    movimenti = []

    for r in righe:
        importo = float(r[3])
        if r[2] == "entrata":
            totale_entrate += importo
        else:
            totale_uscite += importo
        movimenti.append({
            "id": r[0],
            "data": r[1],
            "tipo": r[2],
            "importo": importo,
            "categoria": r[4],
            "note": r[5] or "",
        })

    nome_file = f"archivio_{year}.json" if year not in ("Tutti", "All") else "archivio_completo.json"
    destinazione = ARCHIVI_DIR / nome_file

    payload = {
        "anno": year,
        "data_esportazione": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "riepilogo": {
            "numero_transazioni": len(righe),
            "totale_entrate": round(totale_entrate, 2),
            "totale_uscite": round(totale_uscite, 2),
            "saldo_netto": round(totale_entrate - totale_uscite, 2),
        },
        "movimenti": movimenti,
    }

    with open(destinazione, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)

    return destinazione

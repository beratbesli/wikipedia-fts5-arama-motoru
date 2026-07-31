# AGENT.md - AI Agent Context & Engineering Guidelines

> **Target Audience:** AI Coding Assistants (Antigravity, Cursor, Claude, Copilot, GPT-4, etc.)  
> **Language:** English  
> **Project Name:** Wikipedia FTS5 Local Search Engine  

---

## 📌 Executive Summary

This repository implements a lightweight, high-performance **Local Full-Text Search Engine** in Python, leveraging **SQLite FTS5** and **BM25 Relevance Ranking** to search large text datasets (e.g., a ~2.2 GB Wikipedia dump file `wiki_temiz.txt`) in milliseconds.

The system is designed with **strict end-user experience standards**, **flexible multi-word query handling**, **MediaWiki wikitext sanitization**, and **automated background GitHub synchronization**.

---

## 🏗️ Architecture & File Structure

```
.
├── wiki_arama_motoru.py  # Main executable: DB setup, FTS5 engine, text cleaner, CLI & GitHub auto-sync
├── README.md             # End-user documentation (Turkish)
├── AGENT.md              # AI Agent context, architectural rules, and guidelines (English)
├── .gitignore            # Excludes large raw text dumps (*.txt) and SQLite database files (*.db)
├── wiki_fts.db           # SQLite database with FTS5 virtual table (Generated at runtime, ignored by Git)
└── wiki_temiz.txt        # Raw Wikipedia dataset dump (External source, ignored by Git)
```

---

## 🗄️ Database & Indexing Specifications

### 1. SQLite FTS5 Virtual Table Schema
The database uses an FTS5 virtual table named `makaleler`:
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS makaleler USING fts5(
    satir_id UNINDEXED, 
    metin, 
    tokenize='unicode61 remove_diacritics 0'
);
```
- `satir_id UNINDEXED`: Line number identifier stored without inverted index overhead.
- `metin`: Full text content of the article or paragraph.
- `tokenize='unicode61 remove_diacritics 0'`: Preserves Turkish characters (`ç, ğ, ı, ö, ş, ü, Ç, Ğ, İ, Ö, Ş, Ü`) accurately for exact and fuzzy matching.

### 2. Memory-Efficient Batch Insertion
- Function: `veritabani_kur(txt_dosyasi, db_dosyasi, max_satir, batch_size)`
- Reads `wiki_temiz.txt` line by line without loading the full file into RAM.
- Flushes records to SQLite in chunks of `batch_size=5000` via `cursor.executemany()`.
- Default sample limit: `max_satir=100000` (~260 MB indexing in ~19 seconds). Set `max_satir=None` to index the entire dataset (~2.2 GB).

---

## 🔍 Query Processing & Search Engine Logic

Search execution is handled by `esnek_arama(conn, sorgu_metni, limit)`:

### 1. Flexible Input Parsing
- Removes strict word count constraints (supports 1 word, $N$ non-adjacent words, or full sentences).
- Extracts clean unicode alphanumeric tokens via `re.findall(r'\w+', sorgu_metni.strip(), re.UNICODE)`.

### 2. Two-Stage Fallback Strategy

#### **Phase 1: Full Term Conjunction (`AND` Query - Position Independent)**
- Combines tokens using `AND` operator: `fts_sorgu_and = " AND ".join(kelimeler)`.
- Eliminates adjacency constraints: matches documents containing **all** specified terms regardless of their order, distance, or sentence structure.
- Ranks candidates using SQLite FTS5 built-in `BM25` algorithm (`ORDER BY rank`).

#### **Phase 2: Disjunctive Fallback (`OR` Query + BM25 Relevance Ranking)**
- Triggered automatically if Phase 1 returns zero results.
- Combines tokens using `OR` operator: `fts_sorgu_or = " OR ".join(kelimeler)`.
- Returns documents matching any of the query terms, ordered by `rank` (BM25 score) so articles containing the highest concentration of matched terms appear at the top.

---

## 🧹 MediaWiki & Wikitext Sanitization (`wiki_metni_sadelestir`)

The source text dataset contains raw MediaWiki wikitext markup. The internal helper `wiki_metni_sadelestir(metin)` cleans this noise before presentation:

1. **HTML Entity Unescaping**: Converts `&quot;` $\rightarrow$ `"`, `&lt;` $\rightarrow$ `<`, `&gt;` $\rightarrow$ `>`, `&amp;` $\rightarrow$ `&`.
2. **Reference Tag Stripping**: Removes `<ref ...> ... </ref>`, `<ref .../>`, and `&lt;ref&gt;`.
3. **Template & Infobox Cleaning**: Strips image parameters (`küçükresim|`, `upright=0.91|`, `sağ|`, `thumb|`) and infobox `key = value` structures (`doğum_tarihi =`, `ölüm_yeri =`).
4. **Link Normalization**: Converts `[[Internal Link|Display Text]]` $\rightarrow$ `Display Text` and `[[Internal Link]]` $\rightarrow$ `Internal Link`.
5. **Highlight Preservation**: Keeps FTS5 snippet term highlights formatted cleanly as `[MatchedTerm]`.

---

## 🖥️ User Interface & End-User Experience Rules

AI Agents modifying this repository **MUST** adhere to the following UI principles:

1. **Zero Technical Noise**:
   - **DO NOT** display raw database fields or developer jargon to the user (`satir_id`, `BM25 rank: -12.4`, `FTS5 MATCH`, SQL operational errors, raw wikitext syntax).
2. **Top-30 Summary List + Detail View Navigation**:
   - Present search results initially as a clean numbered list (`1.` to `30.`) displaying extracted article titles (`baslik_uydur()`).
   - Prompt the user to enter a result number (`1` to `30`) to inspect detailed information:
     - **Konu Başlığı** (Title)
     - **Eşleşme Durumu** (Friendly match description in Turkish)
     - **İçerik Özeti** (Highlighted 50-word snippet)
     - **Makaleden Geniş Metin** (Sanitized full article excerpt up to 1500 chars)
3. **Non-Blocking Control Flow**:
   - Users can view multiple detail views sequentially, enter `y` for a new search, or enter `q` to quit.

---

## 🔄 Automated Version Control & GitHub Sync (`otomatik_git_yedekle`)

To maintain the user's GitHub contribution activity grid (green squares):

- Function: `otomatik_git_yedekle()`
- Checks `git status --porcelain`. If modified files exist:
  1. Stages modified tracked files (`git add .`).
  2. Creates a commit: `git commit -m "Otomatik guncelleme: <YYYY-MM-DD HH:MM:SS>"`.
  3. Pushes changes asynchronously to `origin main` using `subprocess.Popen(["git", "push", "origin", "main"], ...)` to avoid blocking CLI interaction.
- Called automatically during script initialization and script exit.

**CRITICAL RULE FOR AI AGENTS:**  
Do **NOT** remove, disable, or break `otomatik_git_yedekle()`.

---

## 🚨 Guardrails for AI Agents

When editing or extending this codebase:

1. **Dependency Constraints**: Rely exclusively on standard Python 3 standard libraries (`sqlite3`, `re`, `time`, `os`, `html`, `subprocess`). Do not introduce third-party pip dependencies unless explicitly requested by the user.
2. **Git & Storage Safety**: Never alter `.gitignore` to track `.txt` or `.db` files. GitHub enforces a strict 100 MB per file limit.
3. **Character Encoding**: Ensure UTF-8 encoding is explicitly defined when handling files (`encoding="utf-8"`, `re.UNICODE`).

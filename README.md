<div align="center">

<img src="https://raw.githubusercontent.com/farheen-shaikh530/llm-abstain.v1/main/assets/Logo2.png" width="700"/>

<br><br>

<a href="https://llm-abstainv1-yqcecj8a6vdkkugbayf8sc.streamlit.app" target="_blank">
    <img alt="Live Demo" src="https://img.shields.io/badge/Live-Demo-4e6b99?style=for-the-badge">
</a>

<a href="https://github.com/farheen-shaikh530/llm-abstain.v1" target="_blank">
    <img alt="GitHub Repo" src="https://img.shields.io/badge/GitHub-Repository-black?style=for-the-badge&logo=github">
</a>

<img alt="Publication" src="https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python">

</div>


---

<details open>
<summary><b>📕 Table of Contents</b></summary>

- 🚀 [About ReleaseHub]
-  🎮 [Demo]
- 🌟 [Key Features]
- 🔎 [System Architecture]
- 🎬 [Get Started]
- 🔧 [Configurations]
- 📊 [Supported Queries]
- 📦 [Tech Stack]
- 📚 [Documentation]
- 📈 [Future Roadmap]

</details>

---

##  What is ReleaseHub?

ReleaseHub is Intelligent Release Note system an **evidence based data retrieval system** that enables users to retrieve the software release information upon on asked queries. The system verifies vendors, release information based on given dates, OS version against dates and other software related discussion information data from authoritative component feeds. 

</br>


## 🎮 Demo

---

## 🌟 Key Features

### 1️⃣ Prevents Wrong Version Deployments
Incorrect version information can break CI/CD pipelines or cause production outages. Eliminates deployment errors caused by incorrect release lookup.

- Returns only vendor-verified OS versions
- Matches exact brand names (no fuzzy guessing)
- Filters by release date when requested
- Abstains if data is missing


### 2️⃣ Stops AI Hallucination in Release Intelligence
Most AI systems fabricate version numbers when evidence is weak. Safe for enterprise environments where accuracy is critical.

- Uses deterministic filtering before any LLM involvement
- Never generates synthetic version values
- Validates LLM output against verified version strings
- Falls back to “I don’t know” when evidence is insufficient


### 3️⃣ Enables Security & Compliance Monitoring
Security teams must track OS releases for vulnerability exposure. Helps SOC teams verify patch timelines and update history.

- Filters by `versionTimestampLastUpdate`
- Supports date-specific queries (e.g., version on 2026-02-04)
- Compatible with CVE-linked OS feeds

### 4️⃣ Reduces Manual Release Lookup Overhead
Engineers often search across multiple sources to find release info. Saves engineering time and reduces operational friction.

- Aggregates OS component feeds
- Vendor list validation via `/api/c/names`
- TTL-based caching for fast response
- Single-query retrieval

---

## 🔧 Configuration

📡  API Endpoints

Defined configuration details inside `core/config.py`.

```API sources
os_api_base = "https://releasetrain.io/api/component"
reddit_api_base = "https://releasetrain.io/api/reddit"
vendor_api = "https://releasetrain.io/api/c/names"
```

Purpose:
-	vendor_api → Validates vendor existence before lookup
-	os_api_base → Retrieves OS version objects against vendor in vendor_api
-	reddit_api_base →  Discussion signals related to the OS and/or vendor

🗂  Cache Configuration

```
cache_dir = Path(__file__).resolve().parents[1] / ".live_cache"
rebuild_ttl_sec = 900
```

🔐  Environment Variables
```
export GOOGLE_API_KEY="API KEY HERE"
export GEMINI_MODEL="gemini-1.5-flash"
```

🧠  Vendor Validation Logic
Before querying data lakes, ReleaseHub verifies the vendor exists in below API:

```
/api/c/names
```

🔧 Configuration Behavior

- Normalized lowercase comparison for vendor detection  
- Longest-match resolution for multi-word vendors . Vendor list contains: slimbook and slimbook os

Example user query:
```
 Latest version for Slimbook OS
```

**Naive behavior (incorrect):**
- Matches `slimbook`
- Queries wrong dataset and may return incorrect version information

**Resolution:**
- Sorts vendor names by length (descending)
- Matches `slimbook os` (longest exact match)
-  Filters OS records only for the correct vendor, returns verified versionNumber

---

## 📊 Supported Queries

ReleaseHub supports deterministic, vendor-verified OS version retrieval queries. All queries must reference a vendor present in `/api/c/names`.

---

### 1️⃣ Latest OS Version

Retrieve the most recent version for a verified OS vendor.

**Example** :
Latest version for EN-OS

**Behavior**
- Validates vendor exists in official vendor list
- Fetches `/api/component?q=os`
- Filters by `versionProductBrand`
- Selects highest `versionTimestampLastUpdate`
- Returns only verified `versionNumber`

Version for EN-OS on 2026-01-01
**Behavior**
- Extracts ISO date from query
- Matches against:
  - `versionTimestampLastUpdate`
  - `versionReleaseDate`
- Returns version only if exact same-day match exists
- Otherwise → abstains

---

### 2️⃣  Multi-Word Vendor Handling

Handles vendors with multi-word names using longest-match resolution.

**Example** :
Latest version for Slimbook OS

**Behavior**
- Matches `slimbook os` (not `slimbook`)
- Prevents partial vendor collisions
- Ensures deterministic filtering

---

###  3️⃣ Security-Tagged OS Releases

Supports vendors whose releases include security metadata.

**Example** :
Latest version for WatchGuard Fireware OS

**Behavior**
- Filters correct multi-word vendor
- Reads classification metadata
- Returns verified version only

---

### 4️⃣  Abstention Scenarios

ReleaseHub abstains when:

- Vendor does not exist
- No OS record found
- Date does not match any release
- VersionNumber missing

---

### 5️⃣ Date-Specific Version

Retrieve the OS version released or updated on a specific date.

**Example** :
Version for EN-OS on 2026-01-01
**Behavior**
- Extracts ISO date from query
- Matches against:
  - `versionTimestampLastUpdate`
  - `versionReleaseDate`
- Returns version only if exact same-day match exists
- Otherwise → abstains

---


## 🖥 Local Installation

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/farheen-shaikh530/llm-abstain.v1.git
cd llm-abstain.v1
```
### 2️⃣ Create Virtual Environment (Recommended)
```
python3.11 -m venv .venv
source .venv/bin/activate   # macOS / Linux
```
Windows: .venv\Scripts\activate

3️⃣ Install Dependencies
```
pip install --upgrade pip
pip install -r requirements.txt

```

4️⃣ Configure LLM Formatting Layer
```
export GOOGLE_API_KEY="your_api_key_here"
export GEMINI_MODEL="gemini-1.5-flash"
```

5️⃣ Run the Application
```
streamlit run app.py
```



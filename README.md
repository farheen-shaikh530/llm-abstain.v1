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

- 🚀 [About ReleaseHub](#-about-releasehub)
- 🧠 [Problem It Solves](#-problem-it-solves)
- ⚙️ [How It Works](#️-how-it-works)
- 🔎 [Deterministic Retrieval Engine](#-deterministic-retrieval-engine)
- 🛡 [Abstention & Hallucination Control](#-abstention--hallucination-control)
- 📊 [Supported Queries](#-supported-queries)
- 🎮 [Live Demo](#-live-demo)
- 🏗 [System Design Overview](#-system-design-overview)
- 📦 [Tech Stack](#-tech-stack)
- 🔐 [Environment Variables](#-environment-variables)
- 📈 [Future Roadmap](#-future-roadmap)

</details>

---

## 📖 What is ReleaseHub?

ReleaseHub is Intelligent Release Note system an **evidence based data retrieval system** that enables users to retrieve the software release information upon on asked queries. The system verifies vendors, release information based on given dates, OS version against dates and other software related discussion information data from authoritative component feeds. 

</br>


## 🎮 Demo



---


## 🌟 Key Features

### 1️⃣ Prevents Wrong Version Deployments
Incorrect version information can break CI/CD pipelines or cause production outages.

ReleaseHub:
- Returns only vendor-verified OS versions
- Matches exact brand names (no fuzzy guessing)
- Filters by release date when requested
- Abstains if data is missing

➡️ Eliminates deployment errors caused by incorrect release lookup.

---

### 2️⃣ Stops AI Hallucination in Release Intelligence
Most AI systems fabricate version numbers when evidence is weak.

ReleaseHub:
- Uses deterministic filtering before any LLM involvement
- Never generates synthetic version values
- Validates LLM output against verified version strings
- Falls back to “I don’t know” when evidence is insufficient

➡️ Safe for enterprise environments where accuracy is critical.

---

### 3️⃣ Enables Security & Compliance Monitoring
Security teams must track OS releases for vulnerability exposure.

ReleaseHub:
- Filters by `versionTimestampLastUpdate`
- Supports date-specific queries (e.g., version on 2026-02-04)
- Compatible with CVE-linked OS feeds

➡️ Helps SOC teams verify patch timelines and update history.

---

### 4️⃣ Reduces Manual Release Lookup Overhead
Engineers often search across multiple sources to find release info.

ReleaseHub:
- Aggregates OS component feeds
- Vendor list validation via `/api/c/names`
- TTL-based caching for fast response
- Single-query retrieval

➡️ Saves engineering time and reduces operational friction.


---





# 🚀 ReleaseHub OS Intelligence  
### Vendor-Verified OS Version Retrieval System  

🔗 Live App: https://your-streamlit-url.streamlit.app  
📦 Repository: https://github.com/farheen-shaikh530/llm-abstain.v1  

---

## 📌 Overview

ReleaseHub OS Intelligence is a production-deployed Streamlit application that retrieves verified OS version information using deterministic filtering logic.

The system:

- Detects vendors strictly from a verified vendor registry (`/api/c/names`)
- Retrieves OS component metadata from `/api/component?q=os`
- Filters by:
  - `versionProductBrand`
  - `versionTimestampLastUpdate`
  - `versionReleaseDate`
- Returns the exact `versionNumber`
- Safely abstains when evidence is insufficient

This project demonstrates safe AI system design principles by eliminating hallucination risk and enforcing evidence-based retrieval.

---

## ⚙️ Tech Stack

- Python 3.11
- Streamlit
- Requests
- Deterministic filtering logic
- Optional Gemini formatting layer (strict validation mode)

Deployment:
- Streamlit Community Cloud

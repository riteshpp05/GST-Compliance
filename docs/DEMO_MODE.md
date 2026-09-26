# UC15 — Demo Mode & Synthetic Data Isolation Specification

## Overview

To prevent demo features or sample data from contaminating production environments, **UC15** strictly isolates demo operations behind explicit configuration flags and UI visual badges.

---

## 1. Demo Mode Configuration

Demo capabilities are enabled exclusively when:

```bash
DEMO_MODE=true
APP_ENV=demo  # or APP_ENV=development
```

In `APP_ENV=production` and `DEMO_MODE=false`:
- Automatic sample case seeding is **DISABLED**.
- Synthetic invoice fallback is **DISABLED**.
- Mock AI provider selection is **PROHIBITED**.

---

## 2. Visual Environment Badges & Labels

When operating under `DEMO_MODE=true` or `APP_ENV=demo`:
1. The UI displays an explicit header banner: **DEMO ENVIRONMENT (Synthetic Data)**.
2. AI Investigation displays explicit provider badges:
   - `AI Mode: LIVE` (Connected to live Gemini/OpenAI provider)
   - `AI Mode: DETERMINISTIC FALLBACK` (Using deterministic GST rule fallback)
   - `AI Mode: MOCK` (Using controlled test fixture mock response)

---

## 3. Explicit Seeding vs Production Finding Flow

- **Demo Environment Seeding:**
  Demo instances may be seeded using the explicit CLI seed command:
  ```bash
  python main.py --mock
  ```
- **Production Operational Flow:**
  In production, cases originate strictly via:
  `Raw ERP Transaction -> Gate Validation -> Compliance Finding -> Explicit Case Creation -> Human Review`.

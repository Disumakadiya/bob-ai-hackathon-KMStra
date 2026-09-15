# Mission Readiness & Predictive Maintenance Copilot

> Track D1

---

## 👥 Team

| Field | Value |
|---|---|
| **Team Name** | KMStra |
| **Track** | Defense & Aerospace |
| **Team Lead** | Disu Makadiya — disu.makadiya@gmail.com |
| **Members** | Vaibhavi Kariya, Pushti Kansara, Rutvi Shah |

---

## 🎯 Problem Statement

Maintenance and operations teams need to determine whether aircraft, vehicles, and other mission-critical equipment can meet an upcoming mission window. Sensor/HUMS data and maintenance history may contain early degradation signals, but those signals are difficult to connect to component risk, remaining useful life (RUL), mission timing, and maintenance priority. This project defines a copilot concept that turns those inputs into explainable readiness information without claiming validated operational results.

---

## 💡 Solution

The proposed Mission Readiness & Predictive Maintenance Copilot combines NASA C-MAPSS degradation/RUL data with clearly identified synthetic operational context such as asset metadata, maintenance history, and mission schedules. It is designed to use anomaly detection, component failure prediction, RUL prediction, SHAP explanations, and a mission-readiness prioritization layer. These are planned capabilities; this repository does not currently contain the implemented pipeline or validated model results.

---

## ✨ Key Features

- **Asset health and anomaly assessment**: Planned Isolation Forest signal for unusual sensor patterns
- **Component failure risk**: Planned XGBoost classifier for a defined future prediction horizon
- **RUL estimation**: Planned XGBoost regressor based initially on NASA C-MAPSS FD001
- **Explainable recommendations**: Planned SHAP explanations for risk and RUL drivers
- **Mission-aware prioritization**: Planned ranking using risk, RUL, criticality, urgency, and readiness impact

---

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Documentation / metadata** | Markdown, YAML |
| **Repository tooling present** | GitHub Actions validation workflow |
| **Development partner** | IBM Bob, used for planning and documentation workflow |
| **Planned analytical technologies** | Python, Pandas, NumPy, scikit-learn, XGBoost, SHAP |
| **Planned data** | NASA C-MAPSS; synthetic supporting operational context |

No application framework, database, API, dashboard, container, or ML dependency is implemented in this repository yet.

---

## 📁 Repository Structure

```
├── src/                  # All source code (including .env.example)
├── docs/                 # Written documentation
│   ├── problem-statement.md
│   ├── solution-overview.md
│   ├── architecture.md
│   └── setup-guide.md
├── demo/                 # Demo artifacts
│   ├── screenshots/      # App screenshots
│   └── demo-video-link.txt  # Link to demo video
├── presentation/         # Slide deck
├── .env.example          # Environment variable template (NEVER commit .env)
└── submission.yaml       # Structured submission metadata
```

---

## ⚡ How to Run

> There is no runnable application or dependency manifest in the current repository. See [`docs/setup-guide.md`](docs/setup-guide.md) for the documentation-stage status and future implementation prerequisites.

```bash
# No install or run command is available yet.
# The repository currently contains documentation and submission metadata only.
```

---

## 🖥️ Demo

| Artifact | Link |
|---|---|
| 📹 Demo Video | [See demo/demo-video-link.txt](demo/demo-video-link.txt) |
| 🌐 Live Demo | [See demo/live-demo-url.txt](demo/live-demo-url.txt) |
| 🖼️ Screenshots | [See demo/screenshots/](demo/screenshots/) |
| 📊 Presentation | [See presentation/slides.pdf](presentation/) |

---

## ⚠️ Known Limitations

1. **Simulated Data:** Models are trained on NASA C-MAPSS data, not real military aircraft telemetry.

2. **Fixed Sensor Schema:** Current models require the sensor structure used during training; different sensor configurations need adaptation or retraining.

3. **Distribution Shift:** Different operating conditions or sensor scales can affect prediction accuracy and anomaly detection.

4. **Decision Support Only:** Health, failure risk, and RUL are predictions; final maintenance and mission decisions remain with qualified personnel.

---

## 🏅 What We're Most Proud Of

The strongest aspect is the clear separation between real NASA C-MAPSS degradation/RUL data, synthetic operational context, and proposed mission-readiness logic. The design also keeps IBM Bob in its proper role as the AI development partner rather than misrepresenting it as the predictive model.

---

# Solution Overview: Mission Readiness & Predictive Maintenance Copilot

## What We Built

The proposed copilot is a decision-support layer for maintenance and operations
teams. It is intended to turn condition-monitoring signals and maintenance context
into an understandable assessment of mission readiness, likely failure risk,
remaining useful life, and maintenance priority. This repository documents the
concept; it does not contain the implementation.

## How It Works

1. Combine NASA C-MAPSS sensor/degradation and RUL information with clearly identified synthetic asset, maintenance, and mission context.
2. Preprocess time-ordered observations while preventing future failure or maintenance information from leaking into an earlier prediction.
3. Produce three planned analytical outputs: an Isolation Forest anomaly signal, an XGBoost component failure probability, and an XGBoost RUL estimate.
4. Use SHAP to describe the features that influenced risk and RUL outputs.
5. Combine model outputs with criticality, mission urgency, time to next mission, and maintenance history in a conceptual readiness and prioritization layer.

## Architecture Diagram

See [`architecture.md`](architecture.md) for the detailed proposed architecture.

```text
Sensor / HUMS data + maintenance history + asset and mission context
                              |
                       Preprocessing and validation
                              |
      Anomaly signal + component failure risk + RUL estimate
                              |
                     SHAP explanations and context
                              |
              Mission readiness and maintenance priority
```

## Key Design Decisions

| Decision                                 | Rationale                                                                                                                             |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Start with NASA C-MAPSS FD001            | It provides a simpler initial setting with one operating condition and one fault mode compared with the other subsets.                |
| Separate real and synthetic data         | C-MAPSS provides degradation/RUL information, while mission and business context must be represented separately and labeled honestly. |
| Explain outputs before prioritizing work | Maintenance users need reasons and contributing factors, not only uncontextualized model scores.                                      |

## IBM Technologies Used

IBM Bob is used as the AI development partner for requirements analysis,
repository planning, documentation, future development assistance, debugging,
testing, review, and validation. It is not the predictive model. No IBM runtime
or hosted inference service is implemented in the current repository.

- **IBM Bob:** Development partner used to shape and refine the proposed solution and its documentation.

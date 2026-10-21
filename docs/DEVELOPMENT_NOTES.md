# Development Notes: Design Decisions, Trade-Offs & Best Practices

## 1. Mathematical Recovery Formulation

In higher education institutions, students frequently ask two questions:
1. *"How many consecutive classes must I attend to get back to 75%?"*
2. *"How many more classes can I cut before I get debarred?"*

### Formula Derivation for Sessions Needed ($S$):
Let $P$ be attended sessions, $N$ be total held sessions, and $T \in (0, 1)$ be the target threshold.
If the student attends $S$ consecutive sessions:
$$\frac{P + S}{N + S} \ge T \implies P + S \ge T \cdot N + T \cdot S \implies S(1 - T) \ge T \cdot N - P \implies S \ge \frac{T \cdot N - P}{1 - T}$$
Taking the ceiling for discrete sessions:
$$S = \max\left(0, \left\lceil \frac{T \cdot N - P}{1 - T} \right\rceil\right)$$

### Formula Derivation for Maximum Permissible Absences ($M$):
If the student misses $M$ consecutive sessions while attending none:
$$\frac{P}{N + M} \ge T \implies P \ge T \cdot N + T \cdot M \implies T \cdot M \le P - T \cdot N \implies M \le \frac{P - T \cdot N}{T}$$
Taking the floor:
$$M = \max\left(0, \left\lfloor \frac{P - T \cdot N}{T} \right\rfloor\right)$$

---

## 2. Decision Tree vs. Rule-Based Baseline Trade-Off

- **Source of Truth:** Institutional bylaws require transparent, auditable rules for exam debarment. Academic decisions cannot rely on black-box probabilistic scores alone.
- **Architecture Strategy:** The primary risk engine is 100% deterministic and rule-based.
- **ML Extension:** A scikit-learn `DecisionTreeClassifier` is provided as an evaluable extension. It evaluates feature interactions such as absence velocity, consecutive absences, and prior leave behaviors. If scikit-learn or the model artifact is absent, the system falls back seamlessly to the deterministic rule engine without throwing runtime exceptions.

---

## 3. Spreadsheet Security: Formula Injection Mitigation

When exporting user-controlled content (such as student names, remarks, or course titles) into CSV or Excel files, malicious strings beginning with `=`, `+`, `-`, or `@` can be executed by spreadsheet applications (DDE / CSV Injection).
In `attendance/services/excel_service.py`, all dynamic strings pass through `sanitize_cell_value()`, which prepends a single quote (`'`) to neutralise formula interpretation.

---

## 4. Notification De-Duplication & Simulation Transparency

- To prevent parents from being spammed if a faculty member re-submits a period's attendance form, an idempotency marker `absence-rec-{record.id}` is verified before generating any alert.
- When live SMS/WhatsApp credentials are not configured in `.env`, the system explicitly records `status='SIMULATED'` in `NotificationDeliveryAttempt` rather than falsely claiming external delivery.

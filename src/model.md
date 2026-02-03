# Comprehensive Model Architecture Guide

This document details the architecture of the **Rational Speech Act (RSA)** model used to predict causal verb usage (*caused*, *enabled*, *allowed*, *made no difference*) in social-causation scenarios.

The model operates on a pipeline that transforms raw trial data into a high-dimensional semantic state, maps that state to verb "truthiness" probabilities, and finally computes pragmatic speaker probabilities.

---

## 1. High-Level Pipeline

1.  **Domain Inference**: We infer the semantic state of the world `(Changed, Aligned, WizardActed, Control, Necessity)` from raw trial data. This is the **Domain Model**.
2.  **Verb Classification**: An **Inertial Verb Classifier** assigns a "semantic truth value" (probability) to each verb based on the semantic state using probabilistic soft logic.
3.  **Literal Listener (L0)**: A listener infers the state of the world given an utterance, weighted by the verb's truth value and the prior probability of that state.
4.  **Pragmatic Speaker (S1)**: The speaker chooses a verb to maximize the L0 listener's probability of recovering the true world state, minimizing cost.

---

## 2. Semantic Domain State

For each trial, we compute a `DomainState` tuple consisting of five continuous scores (0.0 - 1.0). These represent the "ground truth" of the situation as perceived by the model.

### Core Variables

*   **`changed` (C)**: **Outcome Divergence**. To what degree did the actual outcome differ from the *inertial path* (what would have happened if the wizard did nothing/ignored the wizard)?
    *   $1.0$: Outcome is different from inertia.
    *   $0.0$: Outcome is the same as inertia.
*   **`aligned` (A)**: **Outcome Quality**. To what degree is the actual outcome aligned with the farmer/agent's preference (e.g., getting Apple or Gold)?
    *   $1.0$: Good outcome.
    *   $0.0$: Bad outcome.
*   **`wizard_acted` (V)**: **Intervention**. Did the wizard perform an action?
    *   $1.0$: Wizard intervened (e.g., removed rock, spoke).
    *   $0.0$: Wizard did nothing (or was ignored).
*   **`control`**: **Capacity**. Did the wizard have the *power* or *capacity* to influence the outcome, regardless of whether they actually did?
    *   $1.0$: Wizard has control (e.g., can remove rock, show sign, add fruit to basket).
    *   $0.0$: Wizard has no control (e.g., is ignored by the agent).
*   **`necessity`**: **Difference Making**. Did the wizard's choice (to act or not act) *actually* determine the outcome?
    *   $1.0$: The outcome depended on the wizard's choice (counterfactual dependence).
    *   $0.0$: The outcome would have been the same regardless of the wizard's choice.

---

## 3. Domain-Specific Implementations

The semantics are instantiated differently across domains.

### A. Physical Domain
*   **Context**: Wizard can add rock, remove rock, or do nothing. Actions depend on whether rock is initially presnet.
*   **Inference**: Bayesian inference estimates the farmer's preference $\theta$ (Apple vs Banana).
*   **Semantics**:
    *   `changed`: $1.0$ if Actual $\neq$ Inertial, else $0.0$.
    *   `aligned`: Probabilistic. $P(\text{Outcome} = \text{Preferred})$. Based on preference inference. 
    *   `wizard_acted`: $1.0$ if wizard places/removes rock, $0.0$ if "nothing".
    *   **`control`**: Always **1.0**. The wizard always has the ability to act in a way that could change the outcome.
    *   **`necessity`**: Check for counterfactual dependence.
        *   If Acted: `necessity = changed`. (Did my action change it vs inertia?)
        *   If Not Acted: We simulate the counterfactual: "What if I *had* acted?". If that counterfactual outcome differs from the actual outcome, `necessity = 1.0`.

### B. Belief Domain
*   **Context**: Wizard can show true sign, false sign, or do nothing. The farmer may listen or ignore.
*   **Semantics**:
    *   `changed`: Difference between actual outcome (Gold/Rocks) and inertial probability of Gold.
        - In "no belief" trials, the inertial probability of getting gold is 0.5. If the actual outcome is Gold (1.0), the change is $|1.0 - 0.5| = 0.5$.
    *   `aligned`: $1.0$ if Gold, $0.0$ if Rocks.
    *   `wizard_acted`: $1.0$ if wizard acts, $0.0$ if wizard does nothing OR farmer ignores.
    *   **`control`**: **Conditional**.
        *   If Farmer **Ignores**: $0.0$. (wizard has no capacity to influence).
        *   Else (if farmer listens, or wizard does nothing): $1.0$. 
    *   **`necessity`**:
        *   If Acted: `necessity = changed`.
        *   If Not Acted: If ignored, $0.0$. If listens (and wizard did nothing), $1.0$ (implied wizard *could* have spoken to change it).

### C. Preference Domain
*   **Context**: Comparison of expected vs actual choices.
*   **Semantics**:
    *   `changed`: $1.0$ if Actual Choice $\neq$ Expected Choice, else $0.0$.
    *   `aligned`: $1.0$ if Actual Choice == Expected Choice, else $0.0$.
    *   `wizard_acted`: $1.0$ if wizard intervenes (action type != 'nothing'), else $0.0$.
    *   `control`: **1.0** (wizard always has the capacity to act).
    *   `necessity`: Defaults to $1.0$ (assuming wizard has meaningful choice), or `changed` if acted.

---

## 4. Verb Classification (Linking Functions)

We map the `DomainState` $\{C, A, V, Control, Necessity\}$ to verb probabilities.

### Broad Semantics (Default)

| Verb | Formula | Intuition |
| :--- | :--- | :--- |
| **Caused** | $((C \cdot V) + (1-A)) \cdot Control \cdot Necessity$ | Active change OR Bad outcome. Gated by Control & Necessity. |
| **Enabled** | $C \cdot A \cdot V \cdot Control \cdot Necessity$ | Active change + Good outcome. Gated by Control & Necessity. |
| **Allowed** | $((1-V) + A) \cdot Control \cdot Necessity$ | Passive (omission) OR Good outcome. Gated by Control & Necessity. |
| **Made No Difference** | $1 - (C \cdot V)$ | The outcome did not change due to an action. |

*Note: The actual score is `Made No Difference = 1 - (Changed * Acted)`. The other three are multiplied by `Control * Necessity`. If Control or Necessity is 0, `Caused/Enabled/Allowed` become 0.*

### Normalization
Scores are normalized to sum to 1.0.
<!-- Scores are smoothed with $\epsilon=0.01$ and normalized to sum to 1.0. -->

---

## 5. RSA (Rational Speech Act)

The RSA framework models communication as recursive probabilistic inference between speakers and listeners.

### Notation

| Symbol | Name | Definition |
| :--- | :--- | :--- |
| $w$ | World state | The semantic state $(C, A, V, \text{Control}, \text{Necessity})$ |
| $u$ | Utterance | A causal verb: *caused*, *enabled*, *allowed*, *made no difference* |
| $P(u\|w)$ | Semantic truth | Probability that $u$ is true/appropriate in world $w$ (from Verb Classifier) |
| $P(w)$ | World prior | Prior over worlds (assumed uniform) |
| $P(u)$ | Verb marginal | How often $u$ is true across all worlds (see below) |

---

### Literal Speaker (S0)

The Literal Speaker chooses verbs based purely on semantic truth, without pragmatic reasoning:

$$P_{S0}(u|w) \propto P_{\text{sem}}(u|w)$$

This serves as a baseline to test if pragmatic reasoning adds predictive value.

---

### Literal Listener (L0)

The Literal Listener uses Bayes' rule to infer the world $w$ from an utterance $u$:

$$P_{L0}(w|u) = \frac{P(u|w) \cdot P(w)}{P(u)}$$

Where:
*   $P(u|w)$: Semantic probability (truthiness) from the Verb Classifier.
*   $P(w)$: Prior over worlds (assumed **uniform**).
*   $P(u)$: The **marginal probability** of the utterance, computed by marginalizing over worlds:

$$P(u) = \sum_w P(u|w) \cdot P(w)$$

<!-- > **Why marginalize over worlds?** $P(u)$ answers: "Across all possible world states, how often is this verb true?" A verb true in many worlds (high $P(u)$) is less informative than one true in few worlds (low $P(u)$). -->

---

### Pragmatic Speaker (S1)

The Pragmatic Speaker chooses $u$ to maximize the Listener's probability of recovering the true world $w$:

$$P_{S1}(u|w) \propto \exp\left(\alpha \cdot \left( \log P_{L0}(w|u) - \text{Cost}(u)\right)\right)$$

**Derivation of the $P(u|w)/P(u)$ term:**

Since we assume **uniform $P(w)$**, the prior becomes a constant and the L0 listener simplifies:

$$P_{L0}(w|u) \propto \frac{P(u|w)}{P(u)}$$

Substituting into the S1 formula:

$$P_{S1}(u|w) \propto \exp\left(\alpha \cdot \left(\ln \frac{P(u|w)}{P(u)} - \text{Cost}(u)\right)\right)$$

<!-- This is equivalent to **Pointwise Mutual Information (PMI)**: the ratio measures how much more likely $u$ is in *this* world compared to *any* world. High PMI → the verb is informative for this specific state. -->

**Components:**
*   $P(u|w)$: Semantic truth value from the Verb Classifier.
*   $P(u)$: Precomputed over a uniform grid of all 5 semantic variables.
*   $\text{Cost}(u)$: Optional **valence cost** — penalty if verb valence mismatches outcome (e.g., "caused" for a good outcome).

**Parameters:**
*   $\alpha$: Rationality parameter. Higher values → speaker more strongly prefers informative verbs.
*   `valence_cost`: Penalty magnitude for valence mismatches.


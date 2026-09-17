# FinPilot

**Financial Exception Intelligence for Transaction Review**

FinPilot is a Python-based financial exception intelligence system that helps finance teams turn fragmented transaction data into a structured, prioritized human-review workflow.

It ingests CSV/XLSX transaction files, maps source columns into a canonical schema, validates records, applies deterministic financial controls, and converts flagged transactions into reviewable exceptions with supporting evidence.

---

## Why FinPilot

Finance teams often review large transaction exports manually to identify unusual, duplicated, or financially significant transactions.

FinPilot reduces this manual effort by creating a repeatable exception-review workflow.

```text
CSV / XLSX
    ↓
Column Mapping
    ↓
Canonical Schema
    ↓
Validation
    ↓
SQLite Database
    ↓
Financial Controls
    ↓
Signals
    ↓
Exceptions
    ↓
Human Review
```

The goal is not to automatically decide whether a transaction is wrong.

Instead, FinPilot helps finance teams identify which transactions deserve attention first and provides evidence to support the review.

---

## V1 Features

FinPilot V1 currently supports:

- CSV file ingestion
- XLSX file ingestion
- source-to-canonical column mapping
- automatic mapping suggestions
- transaction validation
- SQLite transaction persistence
- configurable high-value thresholds
- duplicate-candidate detection
- standardized exception signals
- exception creation and prioritization
- evidence storage
- exception review queue
- status filtering
- priority filtering
- detailed exception investigation
- human review status updates
- Streamlit user interface
- automated Pytest coverage

---

## Multi-Client Data Mapping

Different companies may use different column names for their financial data.

For example, one company might provide:

```text
Document Number
Posting Date
Supplier
Gross Amount
Currency
```

while another company might provide:

```text
Transaction ID
Payment Date
Vendor Name
Payment Amount
Currency Code
```

FinPilot maps these different source formats into a standard internal structure.

Example:

```text
Document Number  → transaction_id
Posting Date     → date
Supplier         → vendor
Gross Amount     → amount
Currency         → currency
```

This allows the same FinPilot exception engine to process transaction exports from different organizations.

---

## Canonical Transaction Schema

FinPilot converts source data into a common internal transaction model.

### Core Required Fields

```text
transaction_id
date
amount
currency
```

These fields are required for a transaction to enter the trusted FinPilot transaction layer.

### Optional Fields

```text
description
vendor
transaction_type
category
department
```

Optional fields may still be required by individual financial controls.

For example:

```text
HIGH_VALUE
requires:
- amount
- currency
```

```text
DUPLICATE_CANDIDATE
requires:
- vendor
- date
- amount
```

This means a missing optional field does not automatically cause the entire dataset to fail.

---

## Current Financial Controls

### HIGH_VALUE

The `HIGH_VALUE` control identifies transactions that exceed a configurable threshold for their currency.

Example:

```text
Transaction Amount: SGD 15,000
Configured Threshold: SGD 10,000

Result:
HIGH_VALUE signal generated
```

Current V1 thresholds can be configured through the Streamlit interface.

Supported currencies currently include:

```text
SGD
USD
EUR
GBP
```

FinPilot does not automatically invent thresholds for unsupported currencies.

---

### DUPLICATE_CANDIDATE

The `DUPLICATE_CANDIDATE` control identifies transactions that may represent duplicated financial activity.

Transactions are compared using:

```text
vendor
date
amount
```

Example:

```text
Transaction A
Vendor: OfficeMart
Date: 2026-09-10
Amount: SGD 480

Transaction B
Vendor: OfficeMart
Date: 2026-09-10
Amount: SGD 480
```

Both transactions are flagged as duplicate candidates.

FinPilot does **not** automatically claim that they are confirmed duplicates.

Instead, both transactions are sent for human review.

---

## Exception Intelligence Model

FinPilot separates three important concepts.

### Transaction

The financial activity that occurred.

Example:

```text
Transaction ID: INV-1001
Vendor: AWS
Amount: SGD 15,000
```

### Signal

The reason FinPilot believes the transaction deserves attention.

Example:

```text
Signal Type: HIGH_VALUE
Severity: HIGH
Source: RULE
```

### Exception

The review case created for the finance user.

A single transaction can potentially have multiple supporting signals while remaining one reviewable exception.

Example:

```text
Transaction
    ↓
Exception
    ├── HIGH_VALUE
    ├── DUPLICATE_CANDIDATE
    └── Future ML anomaly signal
```

---

## Human-in-the-Loop Review

FinPilot is designed to support finance professionals rather than replace their judgment.

Each exception contains:

- transaction information
- priority
- current review status
- supporting signals
- explanation
- evidence
- control source

Available review statuses include:

```text
OPEN
NEEDS_INFO
CLEARED
CONFIRMED_ISSUE
```

Example workflow:

```text
OPEN
    ↓
Finance analyst investigates transaction
    ↓
Supporting evidence reviewed
    ↓
CLEARED

or

CONFIRMED_ISSUE

or

NEEDS_INFO
```

FinPilot therefore maintains human oversight over financial exception decisions.

---

## V1 Workflow

The complete V1 workflow is:

```text
Financial CSV / XLSX
        ↓
File Ingestion
        ↓
Source Column Detection
        ↓
Column Mapping
        ↓
FinPilot Canonical Schema
        ↓
Transaction Validation
        ↓
Trusted SQLite Storage
        ↓
Deterministic Financial Controls
        ↓
Standardized Signals
        ↓
Exception Creation
        ↓
Prioritized Review Queue
        ↓
Evidence Inspection
        ↓
Human Review Decision
```

---

## Example V1 Test

A company-style test dataset was created with non-FinPilot column names.

Source columns included:

```text
Document Number
Posting Date
Supplier
Gross Amount
Currency
Payment Description
Cost Center
```

FinPilot automatically mapped the source fields into its canonical schema.

The dataset contained:

```text
11 source transactions
11 valid transactions
0 invalid transactions
```

FinPilot detected:

```text
3 HIGH_VALUE signals
2 DUPLICATE_CANDIDATE signals
```

Result:

```text
5 signals
5 reviewable exceptions
```

These exceptions were then displayed in the Streamlit human-review queue.

---

## Controlled 1,000-Transaction Evaluation

The deterministic FinPilot V1 backend was also evaluated using a controlled synthetic Accounts Payable dataset containing:

```text
1,000 transactions
```

The dataset contained known injected V1 exception cases:

```text
30 HIGH_VALUE transactions
40 DUPLICATE_CANDIDATE transactions
```

The controlled benchmark produced:

```text
HIGH_VALUE
True Positives: 30
False Positives: 0
False Negatives: 0

DUPLICATE_CANDIDATE
True Positives: 40
False Positives: 0
False Negatives: 0
```

Overall controlled test:

```text
Expected V1 exceptions: 70
Detected V1 exceptions: 70
```

The pipeline was also executed a second time to test idempotency.

Second execution:

```text
New exceptions created: 0
New signals created: 0
```

This confirms that repeated execution does not duplicate previously stored exception records.

These results demonstrate implementation correctness on the controlled benchmark and should not be interpreted as real-world 100% anomaly-detection accuracy.

---

## Streamlit Interface

The FinPilot V1 application currently contains two main sections.

### Upload & Process

Users can:

1. Upload CSV/XLSX transaction files
2. Preview source data
3. Review automatic mapping suggestions
4. Confirm column mappings
5. Configure high-value thresholds
6. Run FinPilot analysis
7. View processing results
8. Review invalid transactions

Example output:

```text
Source Rows: 11
Valid: 11
Invalid: 0
Signals: 5
Exceptions: 5
```

---

### Exception Review

Users can view:

```text
Transactions
Exceptions
Open Exceptions
High-Priority Exceptions
```

The review queue displays information such as:

```text
Exception ID
Priority
Status
Transaction ID
Date
Vendor
Amount
Currency
Signal Type
```

Users can then inspect an individual exception and review its supporting evidence.

---

## Tech Stack

### Core

- Python
- Pandas
- SQLite

### Application

- Streamlit

### File Processing

- OpenPyXL

### Testing

- Pytest

### Planned V2 / V3

- NumPy
- scikit-learn
- Plotly
- Generative AI / LLM APIs

---

## Project Architecture

```text
Financial Sources
        ↓
src/ingestion.py
        ↓
src/mapping.py
        ↓
src/schema.py
        ↓
src/validation.py
        ↓
src/database.py
        ↓
src/controls.py
        ↓
src/exceptions.py
        ↓
src/review.py
        ↓
Streamlit app.py
```

The main orchestration layer is:

```text
src/pipeline.py
```

It connects:

```text
ingestion
→ mapping
→ validation
→ database
→ controls
→ exception persistence
```

---

## Project Structure

```text
finpilot/
│
├── app.py
├── requirements.txt
├── README.md
│
├── data/
│   ├── sample_transactions.csv
│   └── company_style_transactions.csv
│
├── docs/
│   ├── architecture.md
│   ├── exception_data_model.md
│   ├── financial_controls.md
│   └── transaction_schema.md
│
├── scripts/
│   ├── evaluate_v1_synthetic.py
│   └── profile_real_data.py
│
├── src/
│   ├── __init__.py
│   ├── controls.py
│   ├── database.py
│   ├── exceptions.py
│   ├── ingestion.py
│   ├── mapping.py
│   ├── pipeline.py
│   ├── review.py
│   ├── schema.py
│   └── validation.py
│
└── tests/
    ├── test_controls.py
    ├── test_database.py
    ├── test_exceptions.py
    ├── test_ingestion.py
    ├── test_integration.py
    ├── test_mapping.py
    ├── test_pipeline.py
    └── test_validation.py
```

---

## Automated Testing

FinPilot V1 currently has:

```text
56 passing automated tests
```

Test coverage includes:

- transaction validation
- required field handling
- invalid dates
- invalid amounts
- duplicate transaction IDs
- SQLite constraints
- foreign-key integrity
- transaction persistence
- exception persistence
- signal persistence
- evidence serialization
- idempotency
- HIGH_VALUE detection
- DUPLICATE_CANDIDATE detection
- missing-field handling
- control capability detection
- CSV ingestion
- XLSX ingestion
- automatic column mapping
- mapping validation
- full pipeline execution
- end-to-end integration

---

## Running FinPilot Locally

### 1. Activate the environment

```bash
conda activate finpilot
```

### 2. Run automated tests

```bash
pytest -q
```

Expected result:

```text
56 passed
```

### 3. Launch FinPilot

```bash
streamlit run app.py
```

Streamlit will provide a local URL, usually:

```text
http://localhost:8501
```

---

## Design Principles

FinPilot follows several important principles.

### Human Control

FinPilot prioritizes transactions for investigation but does not autonomously approve, reject, or accuse transactions of fraud.

### Traceability

Each exception contains supporting signals and evidence explaining why the transaction was flagged.

### Deterministic Before Probabilistic

FinPilot is being developed in stages:

```text
Deterministic Correctness
        ↓
Probabilistic Intelligence
        ↓
Generative Explanation
```

### Separation of Responsibilities

The intended architecture follows:

> **SQL retrieves, Python calculates, ML detects/predicts, LLM understands/orchestrates/explains.**

---

## Roadmap

### V1 — Deterministic Financial Exception Workflow

**Status: Complete**

Includes:

- ingestion
- schema mapping
- validation
- SQLite persistence
- financial controls
- standardized signals
- exceptions
- evidence
- review queue
- human status updates
- Streamlit UI
- automated testing

---

### V2 — ML Exception Intelligence

Planned capabilities include:

- contextual anomaly detection
- vendor-specific anomaly detection
- historical spending patterns
- abnormal transaction behavior
- confidence scoring
- materiality-aware prioritization
- rule vs ML benchmarking

Example:

```text
"This payment is unusually large compared with
this vendor's historical payment pattern."
```

rather than only:

```text
"This payment exceeds SGD 10,000."
```

---

### V3 — AI-Assisted Investigation

Planned capabilities include:

- grounded exception summaries
- evidence-based explanations
- investigation assistance
- transaction context synthesis
- human-review support

Example:

```text
This transaction is 3.8× higher than the vendor's
historical median and was also identified as a
duplicate candidate.

Review the invoice and payment reference before
clearing the exception.
```

The AI layer will assist investigation while deterministic calculations and structured data remain the source of truth.

---

## Product Direction

FinPilot is being developed as:

> **AI-Powered Financial Exception Intelligence**

The long-term objective is to convert fragmented financial transaction data into a prioritized human-review workflow using:

```text
Deterministic financial controls
        +
ML risk and anomaly detection
        +
Financial materiality
        +
AI-assisted investigation
        +
Human oversight
```

FinPilot is not intended to become:

- a general ERP
- an accounting platform
- a tax platform
- a payment processor
- a personal finance application
- an autonomous accounting agent

Its focus remains financial exception intelligence.

---

## Portfolio Positioning

FinPilot demonstrates practical experience with:

- Python development
- Pandas
- SQL / SQLite
- financial data processing
- data validation
- schema standardization
- exception management
- automated testing
- Streamlit
- system architecture
- product thinking
- financial controls
- human-in-the-loop workflow design
- future ML integration
- future Generative AI integration

---

## Current Status

**FinPilot V1 is functionally complete.**

The application can currently:

```text
Upload heterogeneous financial data
        ↓
Map fields
        ↓
Validate transactions
        ↓
Store trusted records
        ↓
Run deterministic financial controls
        ↓
Generate traceable exceptions
        ↓
Prioritize them for review
        ↓
Display supporting evidence
        ↓
Record a human review decision
```

Development will next move toward ML-based exception intelligence and AI-assisted investigation.
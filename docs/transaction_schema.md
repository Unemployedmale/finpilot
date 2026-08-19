# FinPilot Transaction Schema

## Required Fields

### transaction_id
Unique identifier for each transaction.

Rules:
- Required
- Must not be blank
- Must be unique

### date
Date on which the transaction occurred.

Rules:
- Required
- Must be convertible to a valid date
- Standard output format: YYYY-MM-DD

### description
Raw transaction description from the source system.

Rules:
- Required
- Must not be blank

### vendor
Vendor or customer associated with the transaction.

Rules:
- Required
- Must not be blank

### amount
Transaction monetary value.

Rules:
- Required
- Must be numeric
- Must be greater than 0

### transaction_type
Indicates whether the transaction represents revenue or an expense.

Allowed values:
- revenue
- expense

### category
Financial reporting category.

Rules:
- Required
- Must not be blank

### department
Internal department responsible for the transaction.

Rules:
- Required
- Must not be blank

### currency
ISO-style currency code.

Initial supported values:
- SGD
- USD
- EUR
- GBP

Rules:
- Required
- Convert to uppercase before validation
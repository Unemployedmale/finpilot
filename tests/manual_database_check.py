import pandas as pd

from src.database import (
    get_connection,
    initialize_database,
    save_transactions,
)
from src.validation import validate_transactions


df = pd.read_csv("data/sample_transactions.csv")

valid_df, invalid_df = validate_transactions(df)

initialize_database()

inserted_rows = save_transactions(valid_df)

print("Valid rows:", len(valid_df))
print("Invalid rows:", len(invalid_df))
print("Inserted rows:", inserted_rows)


with get_connection() as conn:
    stored_df = pd.read_sql_query(
        "SELECT * FROM transactions",
        conn,
    )


print("\nSTORED TRANSACTIONS")
print(stored_df.to_string(index=False))

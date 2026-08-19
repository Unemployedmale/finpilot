import pandas as pd

from src.validation import validate_transactions


df = pd.read_csv("data/bad_transactions.csv")

valid_df, invalid_df = validate_transactions(df)

print("Valid rows:", len(valid_df))
print("Invalid rows:", len(invalid_df))

print("\nINVALID TRANSACTIONS")
print(
    invalid_df[
        [
            "transaction_id",
            "date",
            "vendor",
            "amount",
            "transaction_type",
            "currency",
            "validation_errors",
        ]
    ].to_string(index=False)
)

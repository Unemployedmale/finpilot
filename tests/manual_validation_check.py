import pandas as pd

from src.validation import validate_transactions


df = pd.read_csv("data/sample_transactions.csv")

valid_df, invalid_df = validate_transactions(df)

print("Valid rows:", len(valid_df))
print("Invalid rows:", len(invalid_df))

print("\nVALID")
print(valid_df)

print("\nINVALID")
print(invalid_df)
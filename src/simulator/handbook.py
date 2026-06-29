"""
Transaction data simulator.

Faithful reproduction of the generator from:
  "Reproducible Machine Learning for Credit Card Fraud Detection - Practical
   Handbook", Chapter 3, Section 2 (Le Borgne, Siblini, Lebichot, Bontempi, ULB).
  https://fraud-detection-handbook.github.io/fraud-detection-handbook/
       Chapter_3_GettingStarted/SimulatedDataset.html

Produces three tables:
  * customer profiles  (id, location, spending mean/std, tx frequency)
  * terminal profiles  (id, location)
  * transactions       (id, datetime, customer, terminal, amount, fraud labels)
"""
import random
import numpy as np
import pandas as pd


def generate_customer_profiles_table(n_customers, random_state=0):
    np.random.seed(random_state)
    rows = []
    for customer_id in range(n_customers):
        x = np.random.uniform(0, 100)
        y = np.random.uniform(0, 100)
        mean_amount = np.random.uniform(5, 100)         # spending amount
        std_amount = mean_amount / 2
        mean_nb_tx_per_day = np.random.uniform(0, 4)    # spending frequency
        rows.append([customer_id, x, y, mean_amount, std_amount, mean_nb_tx_per_day])
    return pd.DataFrame(rows, columns=[
        "CUSTOMER_ID", "x_customer_id", "y_customer_id",
        "mean_amount", "std_amount", "mean_nb_tx_per_day"])


def generate_terminal_profiles_table(n_terminals, random_state=0):
    np.random.seed(random_state)
    rows = []
    for terminal_id in range(n_terminals):
        x = np.random.uniform(0, 100)
        y = np.random.uniform(0, 100)
        rows.append([terminal_id, x, y])
    return pd.DataFrame(rows, columns=[
        "TERMINAL_ID", "x_terminal_id", "y_terminal_id"])


def get_list_terminals_within_radius(customer_profile, x_y_terminals, r):
    """Terminals within radius r of the customer (geographic reachability)."""
    x_y_customer = customer_profile[["x_customer_id", "y_customer_id"]].values.astype(float)
    squared_diff = np.square(x_y_customer - x_y_terminals)
    dist = np.sqrt(np.sum(squared_diff, axis=1))
    return list(np.where(dist < r)[0])


def generate_transactions_table(customer_profile, start_date="2024-01-01", nb_days=10):
    customer_transactions = []
    random.seed(int(customer_profile.CUSTOMER_ID))
    np.random.seed(int(customer_profile.CUSTOMER_ID))

    for day in range(nb_days):
        nb_tx = np.random.poisson(customer_profile.mean_nb_tx_per_day)
        for _ in range(nb_tx):
            time_tx = int(np.random.normal(86400 / 2, 20000))   # seconds in the day
            if 0 < time_tx < 86400:
                amount = np.random.normal(customer_profile.mean_amount,
                                          customer_profile.std_amount)
                if amount < 0:
                    amount = np.random.uniform(0, customer_profile.mean_amount * 2)
                amount = np.round(amount, decimals=2)
                if len(customer_profile.available_terminals) > 0:
                    terminal_id = random.choice(customer_profile.available_terminals)
                    customer_transactions.append([
                        time_tx + day * 86400, day,
                        customer_profile.CUSTOMER_ID, terminal_id, amount])

    df = pd.DataFrame(customer_transactions, columns=[
        "TX_TIME_SECONDS", "TX_TIME_DAYS", "CUSTOMER_ID", "TERMINAL_ID", "TX_AMOUNT"])
    if len(df) > 0:
        df["TX_DATETIME"] = pd.to_datetime(df["TX_TIME_SECONDS"], unit="s", origin=start_date)
        df = df[["TX_DATETIME", "CUSTOMER_ID", "TERMINAL_ID",
                 "TX_AMOUNT", "TX_TIME_SECONDS", "TX_TIME_DAYS"]]
    return df


def add_frauds(customer_profiles_table, terminal_profiles_table, transactions_df):
    """Three fraud scenarios from the handbook."""
    transactions_df = transactions_df.copy()
    transactions_df["TX_FRAUD"] = 0
    transactions_df["TX_FRAUD_SCENARIO"] = 0
    if len(transactions_df) == 0:
        return transactions_df

    # Scenario 1: any amount > 220 is fraudulent.
    mask = transactions_df.TX_AMOUNT > 220
    transactions_df.loc[mask, "TX_FRAUD"] = 1
    transactions_df.loc[mask, "TX_FRAUD_SCENARIO"] = 1

    max_day = int(transactions_df.TX_TIME_DAYS.max())

    # Scenario 2: two terminals compromised for 28 days -> all their tx are fraud.
    for day in range(max_day + 1):
        compromised_terminals = terminal_profiles_table.TERMINAL_ID.sample(
            n=min(2, len(terminal_profiles_table)), random_state=day)
        comp = transactions_df[(transactions_df.TX_TIME_DAYS >= day) &
                               (transactions_df.TX_TIME_DAYS < day + 28) &
                               (transactions_df.TERMINAL_ID.isin(compromised_terminals))]
        transactions_df.loc[comp.index, "TX_FRAUD"] = 1
        transactions_df.loc[comp.index, "TX_FRAUD_SCENARIO"] = 2

    # Scenario 3: three customers compromised for 14 days; 1/3 of their tx have
    # the amount multiplied by 5 and are marked as fraud.
    for day in range(max_day + 1):
        compromised_customers = customer_profiles_table.CUSTOMER_ID.sample(
            n=min(3, len(customer_profiles_table)), random_state=day).values
        comp = transactions_df[(transactions_df.TX_TIME_DAYS >= day) &
                               (transactions_df.TX_TIME_DAYS < day + 14) &
                               (transactions_df.CUSTOMER_ID.isin(compromised_customers))]
        n = len(comp)
        if n > 0:
            idx = comp.sample(n=n // 3, random_state=day).index
            transactions_df.loc[idx, "TX_AMOUNT"] = transactions_df.loc[idx, "TX_AMOUNT"] * 5
            transactions_df.loc[idx, "TX_FRAUD"] = 1
            transactions_df.loc[idx, "TX_FRAUD_SCENARIO"] = 3

    return transactions_df

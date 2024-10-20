#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Oct 19 10:16:49 2024

@author: naomijohnson
"""

import pandas as pd
import os
import pytz

def clean_new_data(df, branch, source, last_update):
    
    source_settings = {
        'eBay': {
            'columns_to_keep': ['Payout date', 'Type', 'Order number', 'Buyer name', 'Gross transaction amount', 'Net amount'],
            'purchase_values': ['Order'],
            'refund_values': ['Refund'],
            'additional_processing': lambda df: df[(df['Gross transaction amount'] != '--') & (df['Payout date'] != '--')],
            'format_date_column': lambda df: pd.to_datetime(df['Payout Date'], format='%d-%b-%y').dt.date
        },
        'Shopify': {
            'columns_to_keep': ['Payout Date', 'Type', 'Order', 'Billing Name', 'Amount', 'Net'],
            'purchase_values': ['charge'],
            'refund_values': ['refund'],
            'additional_processing': lambda df: df.merge(
                pd.read_csv(f'new_data/{branch}_shopify_orders.csv').dropna(subset=['Total']).rename(columns={'Name': 'Order'})[['Order', 'Billing Name']],
                on='Order',
                how='left'
            ),
            'format_date_column': lambda df: pd.to_datetime(df['Payout Date']).dt.date
        },
        'PayPal': {
            'columns_to_keep': ['Date', 'Description', 'Invoice ID', 'Name', 'Gross', 'Net'],
            'purchase_values': ['Sale'],
            'refund_values': ['Refund'],
            'additional_processing': lambda df: df[~df['Description'].str.contains('Withdraw money', na=False)],
            'format_date_column': lambda df: pd.to_datetime(df['Payout Date'], format='%d/%m/%Y').dt.date
        }
    }
    
    settings = source_settings[source]
    
    if 'additional_processing' in settings:
        df = settings['additional_processing'](df)
        
    df = df[settings['columns_to_keep']]
    df.columns = ['Payout Date', 'Type', 'Description', 'Customer Name', 'Gross Amount', 'Net Amount']
    
    df.loc[:, 'Payout Date'] = settings['format_date_column'](df)
    if last_update is not None:
        df = df[(df['Payout Date'] > last_update)].sort_values(by='Payout Date').reset_index(drop=True)
    
    df['Type'] = df['Type'].apply(lambda x: 'Purchase' if x in settings['purchase_values'] else 'Refund' if x in settings['refund_values'] else 'Fee')
    df.loc[df['Type'] == 'Fee', 'Gross Amount'] = 0
    
    for col in ['Net Amount', 'Gross Amount']:
        df[col] = df[col].apply(lambda x: x.replace(',', '') if isinstance(x, str) else x).astype(float)
    
    df['Fee Amount'] = df['Net Amount'] - df['Gross Amount']
    df = df[['Payout Date', 'Type', 'Description', 'Customer Name', 'Gross Amount', 'Fee Amount', 'Net Amount']]

    return df 

def get_data():
    """
    Retrieves existing data from 'existing_data', processes new data from 'new_data',
    and updates the existing data with the new entries.

    Returns:
        dict: A dictionary containing updated data for each branch and source.
              Structure:
              {
                  index: (branch, source, DataFrame),
                  ...
              }
    """
    details = [
        ('Wunderlich', 'PayPal'),
        ('Wunderlich', 'Shopify'),
        ('Circa', 'PayPal'),
        ('Circa', 'eBay'),
        ('Circa', 'Shopify'),
    ]
    
    existing_data_folder = 'existing_data'  # Renamed from 'raw_data'
    new_data_folder = 'new_data'
    updated_data = {}

    for idx, (branch, source) in enumerate(details):
        filename = f"{branch}_{source}_Transactions.csv"
        existing_file_path = os.path.join(existing_data_folder, filename)  # Renamed
        new_file_path = os.path.join(new_data_folder, filename)

        # Initialize existing_df
        existing_df = None

        # Load existing data
        if os.path.exists(existing_file_path):
            try:
                existing_df = pd.read_csv(existing_file_path)
                existing_df['Payout Date'] = pd.to_datetime(existing_df['Payout Date'], errors='coerce').dt.date
                existing_df = existing_df.dropna(subset=['Payout Date'])
                last_update = existing_df['Payout Date'].max()
                print(f"{branch} {source} existing data loaded, last updated {last_update}.")
            except Exception as e:
                print(f"Error loading existing data for {branch} {source}: {e}")
                # If loading fails, treat as no existing data
                existing_df = None
        else:
            print(f"Warning: Existing data file not found for {branch} {source} at {existing_file_path}.")
            last_update = None

        # Load and process new data
        if os.path.exists(new_file_path):
            try:
                new_df = pd.read_csv(new_file_path)
                cleaned_new_df = clean_new_data(new_df, branch, source, last_update)

                if not cleaned_new_df.empty:
                    # Combine existing and new data
                    if existing_df is not None:
                        combined_df = pd.concat([existing_df, cleaned_new_df], ignore_index=True)
                    else:
                        combined_df = cleaned_new_df

                    # Save the combined data back to existing_data
                    combined_df.to_csv(existing_file_path, index=False)

                    # Update the dictionary without last_update
                    updated_data[idx] = (branch, source, combined_df)
                    print(f"{branch} {source} data updated with new entries.")
                else:
                    # No new data to add; keep existing data
                    if existing_df is not None:
                        updated_data[idx] = (branch, source, existing_df)
                        print(f"No new updates found for {branch} {source}.")
                    else:
                        updated_data[idx] = (branch, source, None)
                        print(f"No existing or new data found for {branch} {source}.")
                        
                # Delete the new data file after successful processing
                os.remove(new_file_path)
                print(f"[INFO] Deleted new data file for {branch} {source} at {new_file_path}.")

            except Exception as e:
                print(f"Error processing new data for {branch} {source}: {e}")
        else:
            print(f"Warning: New data file not found for {branch} {source} at {new_file_path}.")
            # If new data is not found, retain existing data
            if existing_df is not None:
                updated_data[idx] = (branch, source, existing_df)
            else:
                updated_data[idx] = (branch, source, None)

    return updated_data

updated_data = get_data()

    

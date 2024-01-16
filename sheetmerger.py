#!/bin/env python3

import pandas as pd

roster = pd.read_csv('roster.csv')
github = pd.read_csv('github_usernames.csv')

github.rename(columns={'WPI Email Address': 'Email'}, inplace=True)
github['Email'] = github['Email'].str.lower()
#github.drop(columns=['Timestamp', 'Name'], inplace=True)

print(roster.head())

roster['Email'] = roster.apply(lambda row: row['login_id'] + '@wpi.edu', axis=1)

print(github.head())
merged = roster.merge(github, on='Email', how='left')
print(merged.head())
merged = merged[['name', 'Email', 'GitHub Username', 'group_name']]
merged['Team'] = merged.apply(lambda row: int(''.join(filter(str.isdigit, row['group_name']))), axis=1)
print(merged.dropna())
print(len(merged.dropna()))
print('\n\n\n##### MISSING: #####\n')
print(merged.loc[merged.isnull().any(axis=1)])
print(len(merged.loc[merged.isnull().any(axis=1)]))

merged.to_csv('merged.csv')

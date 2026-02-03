import pandas as pd
import numpy as np
import os

def get_demographics():
    data_dir = "data"
    files = [
        "prolific_demographic_belief.csv",
        "prolific_demographic_physical.csv",
        "prolific_demographic_preference.csv"
    ]
    
    all_dfs = []
    for f in files:
        path = os.path.join(data_dir, f)
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Filter for approved participants
            df = df[df['Status'] == 'APPROVED']
            all_dfs.append(df)
        else:
            print(f"Warning: {path} not found.")
        
    # Combine data from all experiments
    combined_df = pd.concat(all_dfs, ignore_index=True)

    combined_df = combined_df.drop_duplicates(subset=['Participant id'])
    
    total_n = len(combined_df)
    
    # Age statistics
    combined_df['Age'] = pd.to_numeric(combined_df['Age'], errors='coerce')
    age_mean = combined_df['Age'].mean()
    age_sd = combined_df['Age'].std()
    age_min = combined_df['Age'].min()
    age_max = combined_df['Age'].max()
    
    # Sex distribution
    sex_counts = combined_df['Sex'].value_counts()
    sex_percentages = (sex_counts / total_n * 100).round(2)
    
    # Ethnicity distribution
    ethnicity_counts = combined_df['Ethnicity simplified'].value_counts()
    
    print("Participant Demographic Summary")
    print(f"Total N (Unique Approved Participants): {total_n}")
    print(f"Age: M = {age_mean:.2f}, SD = {age_sd:.2f}, Range = [{age_min}, {age_max}]")
    print("\nSex Distribution:")
    for sex, count in sex_counts.items():
        print(f"  {sex}: n = {count} ({sex_percentages[sex]}%)")
    
    print("\nEthnicity:")
    for eth, count in ethnicity_counts.items():
        print(f"  {eth}: n = {count}")
    print("---------------------------------------")

if __name__ == "__main__":
    get_demographics()

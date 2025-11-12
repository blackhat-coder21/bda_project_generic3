#data_preprocessor.py
import pandas as pd
from sklearn.preprocessing import LabelEncoder
import os

# Define file paths
DATA_FOLDER = 'data'
INPUT_FILE = os.path.join(DATA_FOLDER, 'city_day.csv')
OUTPUT_FILE = os.path.join(DATA_FOLDER, 'cleaned_aqi_data.csv')

# Define features (X) and target (y)
FEATURES = [
    'PM2.5', 'PM10', 'NO', 'NO2', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'Xylene'
]
TARGET = 'AQI_Bucket'

def preprocess_data():
    """
    Loads raw AQI data, cleans it, encodes the target, 
    and saves it to a new CSV for the producer.
    """
    print(f"Loading data from {INPUT_FILE}...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file not found at {INPUT_FILE}")
        print("Please place 'city_day.csv' in the 'data/' folder.")
        return

    df = pd.read_csv(INPUT_FILE)
    
    # Select only the columns we need
    columns_to_keep = FEATURES + [TARGET]
    df = df[columns_to_keep]

    # Drop rows with any missing values in our features or target
    initial_rows = len(df)
    df = df.dropna()
    cleaned_rows = len(df)
    print(f"Dropped {initial_rows - cleaned_rows} rows due to missing values.")

    # Encode the text target ('Good', 'Moderate') into numbers (0, 1)
    le = LabelEncoder()
    df[TARGET] = le.fit_transform(df[TARGET])
    
    print("Class Mapping:")
    for i, label in enumerate(le.classes_):
        print(f"  {i} -> {label}")

    # Save the cleaned data
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Data preprocessed and saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    preprocess_data()

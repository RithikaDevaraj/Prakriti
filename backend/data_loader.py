"""
Data Loader Module
Loads and preprocesses fertilizer dataset from CSV files
"""
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, Dict, Any
from sklearn.preprocessing import LabelEncoder, StandardScaler
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FertilizerDataLoader:
    """Load and preprocess fertilizer dataset"""
    
    def __init__(self, data_dir: str = "backend/data"):
        # Handle both absolute and relative paths
        data_path = Path(data_dir)
        if not data_path.is_absolute():
            # Try relative to current working directory
            if data_path.exists():
                self.data_dir = data_path
            else:
                # Try relative to project root (if running from backend/)
                project_root = Path(__file__).parent.parent
                alt_path = project_root / data_dir
                if alt_path.exists():
                    self.data_dir = alt_path
                else:
                    # Try just the data_dir name (if already in backend/)
                    simple_path = Path(__file__).parent / "data"
                    if simple_path.exists():
                        self.data_dir = simple_path
                    else:
                        self.data_dir = data_path
        else:
            self.data_dir = data_path
        self.label_encoders = {}
        self.target_encoder = None  # Encoder for target variable (Fertilizer_Name)
        self.feature_columns = []
        self.class_names = None  # Store original fertilizer names
        self.scaler = None  # For feature scaling
        
    def load_dataset(self, filename: str = "train.csv") -> pd.DataFrame:
        """Load dataset from CSV file"""
        try:
            # Try the requested filename first
            filepath = self.data_dir / filename
            if not filepath.exists():
                # Try alternative files in order of preference (larger datasets first)
                alt_files = ["train.csv", "Fertilizer Prediction (1).csv", "Fertilizer Prediction.csv"]
                for alt_file in alt_files:
                    if alt_file == filename:
                        continue  # Skip the one we already tried
                    alt_path = self.data_dir / alt_file
                    if alt_path.exists():
                        logger.info(f"Using alternative file: {alt_file}")
                        filepath = alt_path
                        break
                else:
                    # Last resort: try with absolute path resolution
                    project_root = Path(__file__).parent.parent
                    alt_path = project_root / "backend" / "data" / filename
                    if alt_path.exists():
                        logger.info(f"Using file from project root: {alt_path}")
                        filepath = alt_path
                    else:
                        raise FileNotFoundError(
                            f"Dataset file not found: {filename}. "
                            f"Checked in: {self.data_dir}. "
                            f"Available files: {list(self.data_dir.glob('*.csv')) if self.data_dir.exists() else 'Directory not found'}"
                        )
            
            df = pd.read_csv(filepath)
            logger.info(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns from {filepath.name}")
            return df
        
        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            raise
    
    def preprocess_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Preprocess data:
        - Handle missing values
        - Encode categorical variables
        - Normalize numeric features
        - Separate features and target
        """
        try:
            # Create a copy to avoid modifying original
            df_processed = df.copy()
            
            # Drop id column if present
            if 'id' in df_processed.columns:
                df_processed = df_processed.drop('id', axis=1)
            
            # Standardize column names (handle typos in original data)
            column_mapping = {
                'Temparature': 'Temperature',
                'Soil Type': 'Soil_Type',
                'Crop Type': 'Crop_Type',
                'Fertilizer Name': 'Fertilizer_Name',
                'Phosphorous': 'Phosphorus'  # Standardize spelling
            }
            df_processed.rename(columns=column_mapping, inplace=True)
            
            # Handle missing values
            numeric_cols = ['Temperature', 'Humidity', 'Moisture', 'Nitrogen', 'Potassium', 'Phosphorus']
            categorical_cols = ['Soil_Type', 'Crop_Type']
            
            # Fill numeric missing values with median
            for col in numeric_cols:
                if col in df_processed.columns:
                    if df_processed[col].isna().sum() > 0:
                        df_processed[col].fillna(df_processed[col].median(), inplace=True)
            
            # Fill categorical missing values with mode
            for col in categorical_cols:
                if col in df_processed.columns:
                    if df_processed[col].isna().sum() > 0:
                        df_processed[col].fillna(df_processed[col].mode()[0], inplace=True)
            
            # Encode categorical variables
            for col in categorical_cols:
                if col in df_processed.columns:
                    if col not in self.label_encoders:
                        self.label_encoders[col] = LabelEncoder()
                        df_processed[col] = self.label_encoders[col].fit_transform(df_processed[col])
                    else:
                        # For test data, transform using existing encoder
                        try:
                            df_processed[col] = self.label_encoders[col].transform(df_processed[col])
                        except ValueError:
                            # Handle unseen categories
                            unique_values = df_processed[col].unique()
                            known_values = self.label_encoders[col].classes_
                            for val in unique_values:
                                if val not in known_values:
                                    df_processed[col] = df_processed[col].replace(val, known_values[0])
                            df_processed[col] = self.label_encoders[col].transform(df_processed[col])
            
            # Separate features and target
            target_col = 'Fertilizer_Name'
            if target_col not in df_processed.columns:
                raise ValueError(f"Target column '{target_col}' not found in dataset")
            
            # Define base feature columns
            base_features = [col for col in df_processed.columns if col != target_col]
            
            # Feature engineering: Create interaction features and ratios
            df_features = df_processed[base_features].copy()
            
            # Add NPK ratio features if N, P, K are present
            if all(col in df_features.columns for col in ['Nitrogen', 'Phosphorus', 'Potassium']):
                df_features['NPK_Total'] = df_features['Nitrogen'] + df_features['Phosphorus'] + df_features['Potassium']
                df_features['N_P_Ratio'] = df_features['Nitrogen'] / (df_features['Phosphorus'] + 1e-6)
                df_features['N_K_Ratio'] = df_features['Nitrogen'] / (df_features['Potassium'] + 1e-6)
                df_features['P_K_Ratio'] = df_features['Phosphorus'] / (df_features['Potassium'] + 1e-6)
                logger.info("Added NPK interaction features")
            
            # Add climate interactions if available
            if 'Temperature' in df_features.columns and 'Humidity' in df_features.columns:
                df_features['Temp_Humidity'] = df_features['Temperature'] * df_features['Humidity'] / 100
                logger.info("Added climate interaction features")
            
            if 'Moisture' in df_features.columns and 'Humidity' in df_features.columns:
                df_features['Moisture_Humidity'] = df_features['Moisture'] * df_features['Humidity'] / 100
                logger.info("Added moisture-humidity interaction")
            
            # Scale numeric features
            numeric_feature_cols = [col for col in df_features.columns if col not in ['Soil_Type', 'Crop_Type']]
            if self.scaler is None:
                self.scaler = StandardScaler()
                df_features[numeric_feature_cols] = self.scaler.fit_transform(df_features[numeric_feature_cols])
                logger.info("Fitted StandardScaler on numeric features")
            else:
                df_features[numeric_feature_cols] = self.scaler.transform(df_features[numeric_feature_cols])
            
            # Update feature columns list
            self.feature_columns = list(df_features.columns)
            X = df_features
            y = df_processed[target_col]
            
            # Encode target variable (fertilizer names to numeric)
            if self.target_encoder is None:
                self.target_encoder = LabelEncoder()
                y_encoded = self.target_encoder.fit_transform(y)
                self.class_names = self.target_encoder.classes_
                logger.info(f"Target encoder created. Classes: {self.class_names}")
            else:
                y_encoded = self.target_encoder.transform(y)
            
            logger.info(f"Preprocessed data: {X.shape[0]} samples, {len(self.feature_columns)} features")
            logger.info(f"Features: {self.feature_columns}")
            logger.info(f"Target classes: {len(self.class_names)} unique fertilizers")
            
            return X, y_encoded
        
        except Exception as e:
            logger.error(f"Error preprocessing data: {e}")
            raise
    
    def get_feature_names(self) -> list:
        """Get list of feature column names"""
        return self.feature_columns.copy()
    
    def encode_categorical_input(self, soil_type: str, crop_type: str) -> Dict[str, int]:
        """Encode categorical inputs for prediction"""
        encoded = {}
        
        if 'Soil_Type' in self.label_encoders:
            try:
                encoded['Soil_Type'] = int(self.label_encoders['Soil_Type'].transform([soil_type])[0])
            except (ValueError, KeyError):
                # Use first class if unknown
                encoded['Soil_Type'] = 0
        
        if 'Crop_Type' in self.label_encoders:
            try:
                encoded['Crop_Type'] = int(self.label_encoders['Crop_Type'].transform([crop_type])[0])
            except (ValueError, KeyError):
                # Use first class if unknown
                encoded['Crop_Type'] = 0
        
        return encoded
    
    def decode_categorical_output(self, soil_type_encoded: int, crop_type_encoded: int) -> Tuple[str, str]:
        """Decode categorical outputs"""
        soil_type = self.label_encoders['Soil_Type'].inverse_transform([soil_type_encoded])[0] if 'Soil_Type' in self.label_encoders else "Unknown"
        crop_type = self.label_encoders['Crop_Type'].inverse_transform([crop_type_encoded])[0] if 'Crop_Type' in self.label_encoders else "Unknown"
        return soil_type, crop_type
    
    def decode_fertilizer_name(self, encoded_class: int) -> str:
        """Decode fertilizer name from encoded class"""
        if self.target_encoder:
            return self.target_encoder.inverse_transform([encoded_class])[0]
        return str(encoded_class)


import pandas as pd
import os

class CardRepository:
    def __init__(self, file_path='data1.csv'):
        self.file_path = file_path

    def load_all(self):
        if not os.path.exists(self.file_path):
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.file_path)
            df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
            
            # Normalización básica de esquema
            columnas_necesarias = ['name', 'set_name', 'rarity', 'type_line', 'cantidad', 'oracle_text', 'color_identity', 'mana_cost', 'power']
            for col in columnas_necesarias:
                if col not in df.columns:
                    df[col] = 0 if col == 'cantidad' else ""
            
            df['name'] = df['name'].astype(str).str.strip()
            df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
            df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
            
            return df
        except Exception:
            return pd.DataFrame()

    def save(self, df):
        df.to_csv(self.file_path, index=False)
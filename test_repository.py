import pytest
import pandas as pd
import os
from repository import CardRepository

def test_load_all_missing_file(tmp_path):
    # Probamos el comportamiento cuando el archivo no existe
    file = tmp_path / "missing.csv"
    repo = CardRepository(str(file))
    df = repo.load_all()
    assert df.empty

def test_save_and_load(tmp_path):
    # Probamos el ciclo de guardado y carga
    file = tmp_path / "test_data.csv"
    repo = CardRepository(str(file))
    df_to_save = pd.DataFrame([{'name': 'Test Card', 'cantidad': 1}])
    repo.save(df_to_save)
    
    df_loaded = repo.load_all()
    assert not df_loaded.empty
    # Verificamos que se normalizaron los nombres de las columnas
    assert 'name' in df_loaded.columns
    assert df_loaded.iloc[0]['name'] == 'Test Card'
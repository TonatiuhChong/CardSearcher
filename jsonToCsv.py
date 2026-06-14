import pandas as pd
import json
import os

# Configuración
input_file = 'default-cards-20260614090813.json'
output_file = 'data.csv'

# Columnas que realmente te interesan para tu buscador
columnas_interesantes = [
    'name', 
    'type_line', 
    'mana_cost', 
    'set_name', 
    'rarity', 
    'collector_number',
    'oracle_text',
    'color_identity',
    'digital'
]

def json_to_csv():
    print("Cargando archivo JSON... (esto puede tardar un poco)")
    
    # Abrir y cargar el JSON
    try:
        with open(input_file, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo '{input_file}'.")
        return
    except json.JSONDecodeError:
        print(f"❌ Error: El archivo '{input_file}' no es un JSON válido o está corrupto.")
        return
    
    # Convertir a DataFrame de Pandas
    df = pd.DataFrame(data)
    
    # Filtrar solo las columnas que queremos y eliminar duplicados internos del JSON
    columnas_finales = [col for col in columnas_interesantes if col in df.columns]
    df_json = df[columnas_finales].copy()
    if 'digital' in df_json.columns:
        df_json = df_json[df_json['digital'] == False]
    
    df_json = df_json.drop_duplicates(subset=['name', 'set_name'])
    
    # Verificar si el archivo CSV de salida ya existe
    file_exists = os.path.exists(output_file)
    df_existente = pd.DataFrame(columns=['name', 'set_name']) # DataFrame vacío por defecto

    if os.path.exists(output_file):
        print(f"El archivo {output_file} ya existe. Buscando cartas nuevas...")
        try:
            df_existente = pd.read_csv(output_file)
            # Asegurarse de que las columnas 'name' y 'set_name' existan para la fusión
            if 'name' not in df_existente.columns or 'set_name' not in df_existente.columns:
                print(f"⚠️ Advertencia: El archivo '{output_file}' no contiene las columnas 'name' y 'set_name' necesarias. Se tratará como un archivo nuevo.")
                file_exists = False # Tratar como nuevo si faltan columnas esenciales
                df_existente = pd.DataFrame(columns=['name', 'set_name'])
        except pd.errors.EmptyDataError:
            print(f"⚠️ Advertencia: El archivo '{output_file}' está vacío. Se tratará como un archivo nuevo.")
            file_exists = False
            df_existente = pd.DataFrame(columns=['name', 'set_name'])
        except Exception as e:
            print(f"❌ Error al leer el archivo '{output_file}': {e}. Se tratará como un archivo nuevo.")
            file_exists = False
            df_existente = pd.DataFrame(columns=['name', 'set_name'])
    else:
        print(f"El archivo {output_file} no existe. Creando base de datos...")

    # Comparamos por Nombre y Set para encontrar filas en JSON que no están en el CSV
    keys = ['name', 'set_name']
    df_nuevo = df_json.merge(df_existente[keys] if not df_existente.empty else pd.DataFrame(columns=keys),
                             on=keys,
                             how='left',
                             indicator=True)
    df_nuevo = df_nuevo[df_nuevo['_merge'] == 'left_only'].drop(columns=['_merge'])

    if not df_nuevo.empty:
        # Preparar columnas para que coincidan con la estructura esperada por app.py
        df_nuevo['name_clean'] = df_nuevo['name'].str.split(' // ').str[0].str.strip()
        df_nuevo['cantidad'] = 0
        
        # Columnas esperadas en el CSV final para el buscador y el generador de mazos
        expected_csv_columns = ['name_clean', 'name', 'set_name', 'rarity', 'type_line', 'cantidad', 'oracle_text', 'color_identity']
        
        # Añadir columnas faltantes a df_nuevo con valores por defecto si no están presentes
        for col in expected_csv_columns:
            if col not in df_nuevo.columns:
                if col == 'cantidad':
                    df_nuevo[col] = 0
                else:
                    df_nuevo[col] = '' # Valor por defecto para otras columnas

        # Reordenar columnas para que coincidan exactamente con la estructura de tu data.csv
        df_nuevo = df_nuevo[expected_csv_columns]

        print(f"Agregando {len(df_nuevo)} cartas nuevas a {output_file}...")
        df_nuevo.to_csv(output_file, mode='a', index=False, header=not file_exists, encoding='utf-8-sig')
    else:
        print("No se encontraron cartas nuevas para agregar.")
    
    print("¡Proceso completado!")

if __name__ == "__main__":
    json_to_csv()
    
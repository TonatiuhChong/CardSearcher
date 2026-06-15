import pandas as pd
import json
import os

# Configuración
input_file = 'default-cards-20260614090813.json'
output_file = 'data1.csv'

# Columnas que realmente te interesan para tu buscador
columnas_interesantes = [
    'name', 
    'layout',
    'type_line', 
    'mana_cost', 
    'set_name', 
    'rarity', 
    'collector_number',
    'oracle_text',
    'color_identity',
    'digital',
    'power',
    'toughness'
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
    
    # Intentar cargar cantidades existentes de data.csv o data1.csv para no perder tu progreso
    df_existente = pd.DataFrame(columns=['name', 'set_name', 'cantidad'])
    for f in ['data.csv', 'data1.csv']:
        if os.path.exists(f):
            try:
                temp_df = pd.read_csv(f)
                if 'name' in temp_df.columns and 'cantidad' in temp_df.columns:
                    df_existente = temp_df[['name', 'set_name', 'cantidad']]
                    print(f"ℹ️ Cargando cantidades desde '{f}'...")
                    break
            except:
                continue

    # Combinamos la info del JSON con las cantidades que ya tenías
    keys = ['name', 'set_name']
    df_final = df_json.merge(df_existente, on=keys, how='left')
    df_final['cantidad'] = df_final['cantidad'].fillna(0).astype(int)

    if not df_final.empty:
        # Preparar columnas finales
        df_final['name_clean'] = df_final['name'].str.split(' // ').str[0].str.strip()
        
        # Columnas esperadas en el CSV final para el buscador y el generador de mazos
        expected_csv_columns = ['name_clean', 'name', 'layout', 'set_name', 'rarity', 'type_line', 'cantidad', 'oracle_text', 'color_identity', 'mana_cost', 'power', 'toughness']
        
        # Añadir columnas faltantes con valores por defecto
        for col in expected_csv_columns:
            if col not in df_final.columns:
                if col == 'cantidad':
                    df_final[col] = 0
                elif col in ['power', 'toughness']:
                    df_final[col] = '0'
                else:
                    df_final[col] = ''

        # Reordenar columnas
        df_final = df_final[expected_csv_columns]

        print(f"💾 Guardando {len(df_final)} cartas en {output_file}...")
        df_final.to_csv(output_file, index=False, encoding='utf-8-sig')
    else:
        print("No se encontraron cartas para procesar.")
    
    print("¡Proceso completado!")

if __name__ == "__main__":
    json_to_csv()
    
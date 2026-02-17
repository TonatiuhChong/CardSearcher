import pandas as pd
import json

# Configuración
input_file = 'default-cards-20260215100746.json'
output_file = 'biblioteca_mtg.csv'

# Columnas que realmente te interesan para tu buscador
columnas_interesantes = [
    'name', 
    'type_line', 
    'mana_cost', 
    'set_name', 
    'rarity', 
    'collector_number',
    'oracle_text',
    'digital'
]

def json_to_csv():
    print("Cargando archivo JSON... (esto puede tardar un poco)")
    
    # Abrir y cargar el JSON
    with open(input_file, encoding='utf-8') as f:
        data = json.load(f)
    
    # Convertir a DataFrame de Pandas
    df = pd.DataFrame(data)
    
    # Filtrar solo las columnas que queremos para que Numbers no explote
    # Verificamos que las columnas existan en el archivo
    columnas_finales = [col for col in columnas_interesantes if col in df.columns]
    df_filtrado = df[columnas_finales]
    
    print(f"Guardando {len(df_filtrado)} cartas en {output_file}...")
    df_filtrado.to_csv(output_file, index=False, encoding='utf-8-sig')
    print("¡Listo! Ya puedes abrirlo en Numbers.")

if __name__ == "__main__":
    json_to_csv()
    
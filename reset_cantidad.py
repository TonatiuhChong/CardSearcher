import pandas as pd

def reset_stock():
    try:
        # Cargar el archivo
        df = pd.read_csv('data.csv')
        
        # Verificar si la columna existe antes de modificar
        if 'cantidad' in df.columns:
            df['cantidad'] = 0
            # Guardar los cambios sin índice
            df.to_csv('data.csv', index=False)
            print("✅ Éxito: Todas las cantidades se han reseteado a 0 en data.csv.")
        else:
            print("❌ Error: No se encontró la columna 'cantidad' en el archivo.")
            
    except FileNotFoundError:
        print("❌ Error: No se encontró el archivo 'data.csv'.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    reset_stock()
    
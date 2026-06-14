import streamlit as st
import pandas as pd
import urllib.parse
from fpdf import FPDF

# 1. Configuración de la página
st.set_page_config(page_title="MTG Collection Manager Pro", layout="wide")

# 2. Carga y Agrupación (Unifica duplicados de raíz)
@st.cache_data
def load_data_from_csv():
    try:
        df = pd.read_csv('data.csv')
        df.columns = [c.lower().strip().replace(' ', '_') for c in df.columns]
        
        # Asegurar que todas las columnas necesarias existan para evitar errores de carga y del generador
        columnas_necesarias = ['name', 'set_name', 'rarity', 'type_line', 'cantidad', 'oracle_text', 'color_identity']
        for col in columnas_necesarias:
            if col not in df.columns:
                if col == 'cantidad':
                    df[col] = 0
                else:
                    df[col] = ""

        df['name'] = df['name'].astype(str).str.strip()
        df['name_clean'] = df['name'].str.split(' // ').str[0].str.strip()
        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(0).astype(int)
        
        # Agrupamos por nombre único para evitar repetidos
        df = df.groupby('name_clean').agg({
            'name': 'first',
            'set_name': 'first',
            'rarity': 'first',
            'type_line': 'first',
            'cantidad': 'sum',
            'oracle_text': 'first',
            'color_identity': 'first'
        }).reset_index()
        
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar archivo: {e}")
        # Retornar un DataFrame con la estructura correcta pero vacío para evitar KeyErrors
        return pd.DataFrame(columns=['name_clean', 'name', 'set_name', 'rarity', 'type_line', 'cantidad', 'oracle_text', 'color_identity'])

# --- ESTADOS ---
if 'df' not in st.session_state:
    st.session_state.df = load_data_from_csv()
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "inicio"

# Si el DataFrame está vacío (error de carga o archivo inexistente)
if st.session_state.df.empty:
    st.warning("⚠️ La base de datos está vacía o no se encontró 'data.csv'. Por favor, ejecuta 'jsonToCsv.py' para generarla.")
    st.stop()

# --- FUNCIONES ---
def guardar_cambios():
    st.session_state.df.to_csv('data.csv', index=False)

def aplicar_filtros(df_input, nombre, tipo, rarezas, colecciones):
    df_res = df_input.copy()
    if nombre:
        df_res = df_res[df_res['name'].str.contains(nombre, case=False, na=False)]
    if tipo:
        df_res = df_res[df_res['type_line'].str.contains(tipo, case=False, na=False)]
    if rarezas:
        df_res = df_res[df_res['rarity'].isin(rarezas)]
    if colecciones:
        df_res = df_res[df_res['set_name'].isin(colecciones)]
    return df_res

def generar_pdf(df, titulo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"Wishlist MTG: {titulo}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(100, 10, "Nombre", 1); pdf.cell(60, 10, "Set", 1); pdf.cell(30, 10, "Cant.", 1, 1)
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        n = str(row['name']).encode('latin-1', 'ignore').decode('latin-1')[:45]
        s = str(row['set_name']).encode('latin-1', 'ignore').decode('latin-1')[:30]
        pdf.cell(100, 8, n, 1); pdf.cell(60, 8, s, 1); pdf.cell(30, 8, str(row['cantidad']), 1, 1)
    return bytes(pdf.output(dest='S'))

# --- SIDEBAR ---
st.sidebar.header("🔍 Filtros")
f_nombre = st.sidebar.text_input("Nombre de la carta")
f_tipo = st.sidebar.text_input("Tipo / Raza")
rareza_opciones = sorted(st.session_state.df['rarity'].unique().tolist())
f_rareza = st.sidebar.multiselect("Rareza", options=rareza_opciones)
set_opciones = sorted(st.session_state.df['set_name'].unique().tolist())
f_sets = st.sidebar.multiselect("Colecciones", options=set_opciones)

st.sidebar.divider()
if st.sidebar.button("📋 Ver Wishlist Completa", use_container_width=True):
    st.session_state.view_mode = "wishlist"
if st.sidebar.button("🚀 Buscador / Editor", use_container_width=True):
    st.session_state.view_mode = "search"
if st.sidebar.button("🪄 Generar Mazo Commander", use_container_width=True):
    st.session_state.view_mode = "deck"

# --- INTERFAZ ---
mode = st.session_state.view_mode

if mode == "wishlist":
    st.title("📋 Wishlist Visual Completa")
    df_f = aplicar_filtros(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
    df_wish = df_f[df_f['cantidad'] == 0]

    if not df_wish.empty:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.success(f"Mostrando **{len(df_wish)}** cartas faltantes.")
        with c2:
            pdf_bytes = generar_pdf(df_wish, "Faltantes")
            st.download_button("🖨️ Imprimir Lista Completa (PDF)", data=pdf_bytes, file_name="wishlist_completa.pdf", mime="application/pdf")

        st.divider()
        
        # --- GRID SIN LÍMITES ---
        # Usamos 5 columnas para que quepan más cartas visualmente
        num_cols = 5
        cols = st.columns(num_cols) 
        
        # Iteramos sobre TODA la lista (df_wish)
        for i, (idx_original, row) in enumerate(df_wish.iterrows()):
            with cols[i % num_cols]:
                with st.container(border=True):
                    n_u = urllib.parse.quote(row['name'])
                    # Cargamos las imágenes. Nota: Si son cientos, puede tardar un poco en renderizar el navegador
                    st.image(f"https://api.scryfall.com/cards/named?exact={n_u}&format=image")
                    st.caption(f"**{row['name']}**")
                    
                    if st.button(f"➕ Agregar", key=f"wish_{idx_original}", use_container_width=True):
                        st.session_state.df.at[idx_original, 'cantidad'] = 1
                        guardar_cambios()
                        st.toast(f"✅ {row['name']} añadida!")
                        st.rerun()
    else:
        st.info("No hay cartas faltantes con los filtros seleccionados.")

elif mode == "search":
    st.header("🔍 Buscador General")
    df_f = aplicar_filtros(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
    # En el buscador sí mantenemos un límite por página para edición rápida
    for idx, row in df_f.head(20).iterrows():
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 1])
            with c1:
                n_u = urllib.parse.quote(row['name'])
                st.image(f"https://api.scryfall.com/cards/named?exact={n_u}&format=image", width=120)
            with c2:
                st.subheader(row['name'])
                st.write(f"Stock actual: **{row['cantidad']}**")
            with c3:
                nuevo_val = st.number_input("Cantidad", min_value=0, value=int(row['cantidad']), key=f"edit_{idx}")
                if nuevo_val != row['cantidad']:
                    st.session_state.df.at[idx, 'cantidad'] = nuevo_val
                    guardar_cambios()
                    st.rerun()

elif mode == "deck":
    st.title("🪄 Generador de Mazo Commander (100 cartas)")
    st.write("Este generador selecciona las mejores cartas de tu base de datos basándose en los filtros actuales (ej. 'Angel') para armar un mazo de 100 cartas.")
    
    # --- LÓGICA ESTRATÉGICA DE CONSTRUCCIÓN ---
    import ast # Para convertir el string de color_identity a lista

    # 1. SELECCIÓN DEL COMANDANTE
    # Si el usuario escribió un nombre, intentamos buscar ese comandante específicamente
    if f_nombre:
        potential_commanders = st.session_state.df[
            (st.session_state.df['name'].str.contains(f_nombre, case=False, na=False)) &
            (st.session_state.df['type_line'].str.contains("Legendary Creature", case=False, na=False))
        ]
    else:
        # Si no hay nombre, aplicamos los filtros normales para sugerir uno
        df_f_cmd = aplicar_filtros(st.session_state.df, "", f_tipo, f_rareza, f_sets)
        potential_commanders = df_f_cmd[df_f_cmd['type_line'].str.contains("Legendary Creature", case=False, na=False)]
    
    if potential_commanders.empty:
        st.error("❌ No se encontró una Criatura Legendaria para ser el Comandante. Prueba escribiendo el nombre de una carta legendaria en el buscador.")
        st.stop()

    main_cmd = potential_commanders.iloc[0]

    # 2. DEFINICIÓN DEL TEMA Y EL POOL
    # Si el usuario especificó un tipo, ese es el tema. Si no, usamos el campo nombre como tema fallback.
    tema_mazo = f_tipo if f_tipo else f_nombre
    df_f = aplicar_filtros(st.session_state.df, "", tema_mazo, f_rareza, f_sets)
        
    if not df_f.empty:
        # Intentar parsear la identidad de color (viene como string "['W', 'U']")
        try:
            cmd_colors = ast.literal_eval(main_cmd['color_identity'])
        except:
            cmd_colors = [] # Fallback

        st.success(f"👑 **Comandante:** {main_cmd['name']} ({''.join(cmd_colors)})")

        # --- FILTRADO POR IDENTIDAD DE COLOR ---
        # Solo cartas que sus colores estén contenidos en la identidad del comandante
        def check_color(row_colors_str):
            try:
                row_colors = ast.literal_eval(row_colors_str)
                return all(c in cmd_colors for c in row_colors)
            except: return True

        pool = df_f[df_f['color_identity'].apply(check_color)].copy()
        
        lands = pool[pool['type_line'].str.contains("Land", case=False, na=False)]
        
        # 3. Resto del mazo (Hechizos/Criaturas)
        non_lands = pool[~pool['type_line'].str.contains("Land", case=False, na=False)].copy()

        # --- ANÁLISIS DE SINERGIA ---
        # Buscamos palabras clave en el texto del comandante para definir la estrategia
        estrategias = {
            "token": ["token", "create"],
            "counters": ["+1/+1", "counter", "proliferate"],
            "poison": ["poison", "toxic", "infect"],
            "sacrifice": ["sacrifice", "dies"],
            "lifegain": ["life", "gain"],
            "spellslinger": ["instant", "sorcery"]
        }
        
        cmd_text = str(main_cmd['oracle_text']).lower()
        keywords_interes = []
        for est, keys in estrategias.items():
            if any(k in cmd_text for k in keys):
                keywords_interes.extend(keys)

        # Calculamos score de sinergia
        def calcular_sinergia(text):
            text = str(text).lower()
            return sum(1 for k in keywords_interes if k in text)

        non_lands['sinergia'] = non_lands['oracle_text'].apply(calcular_sinergia)
        
        # Priorizamos: Sinergia > Rareza
        rarity_rank = {'mythic': 0, 'rare': 1, 'uncommon': 2, 'common': 3}
        non_lands['priority'] = non_lands['rarity'].str.lower().map(rarity_rank).fillna(4)
        non_lands = non_lands.sort_values(['sinergia', 'priority'], ascending=[False, True])

        deck_list = []
        deck_list.append(main_cmd.to_dict())

        # Paso B: Seleccionar tierras (Máximo 36)
        selected_lands = lands.head(36)
        deck_list.extend(selected_lands.to_dict('records'))
        
        # Paso C: Distribución equilibrada de hechizos
        # Definimos objetivos por categoría para un mazo sólido
        objetivos = {
            'Creature': 30,
            'Instant': 10,
            'Sorcery': 10,
            'Enchantment': 10,
            'Artifact': 3
        }
        
        nombres_en_mazo = {c['name_clean'] for c in deck_list}
        
        for tipo, meta in objetivos.items():
            # Filtramos cartas de este tipo que no estén ya en el mazo
            candidatos = non_lands[
                (non_lands['type_line'].str.contains(tipo, case=False, na=False)) & 
                (~non_lands['name_clean'].isin(nombres_en_mazo))
            ]
            seleccionadas = candidatos.head(meta)
            deck_list.extend(seleccionadas.to_dict('records'))
            nombres_en_mazo.update(seleccionadas['name_clean'].tolist())

        # Paso D: Relleno de seguridad (si faltan cartas para llegar a 100)
        faltantes = 100 - len(deck_list)
        if faltantes > 0:
            pool_restante = non_lands[~non_lands['name_clean'].isin(nombres_en_mazo)]
            deck_list.extend(pool_restante.head(faltantes).to_dict('records'))
        
        df_final_deck = pd.DataFrame(deck_list)
        
        st.info(f"✅ Mazo generado con **{len(df_final_deck)}** cartas respetando el equilibrio de tipos.")
        
        # Botón de impresión
        pdf_bytes = generar_pdf(df_final_deck, "Commander Decklist")
        st.download_button("🖨️ Descargar Decklist (PDF)", data=pdf_bytes, file_name="mazo_commander_sugerido.pdf", mime="application/pdf")

        # Grid Visual
        st.divider()
        grid_cols = st.columns(5)
        for i, card in enumerate(deck_list):
            with grid_cols[i % 5]:
                n_u = urllib.parse.quote(card['name'])
                st.image(f"https://api.scryfall.com/cards/named?exact={n_u}&format=image")
                st.caption(f"**{card['name']}**")
    else:
        st.error("No hay cartas suficientes con los filtros actuales para generar un mazo. Intenta buscar 'Angel' o 'Dragon' en el buscador.")
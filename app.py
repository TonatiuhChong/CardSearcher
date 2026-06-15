import streamlit as st
import urllib.parse
from fpdf import FPDF
from repository import CardRepository
from service import CardService

# 1. Configuración de la página
st.set_page_config(page_title="MTG Collection Manager Pro", layout="wide")

# 2. Inicialización de Capas
repo = CardRepository()
service = CardService()

# --- ESTADOS ---
if 'df' not in st.session_state:
    raw_df = repo.load_all()
    st.session_state.df = service.prepare_collection(raw_df)

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = "inicio"

# Si el DataFrame está vacío (error de carga o archivo inexistente)
if st.session_state.df.empty:
    st.warning("⚠️ La base de datos está vacía o no se encontró 'data1.csv'. Por favor, ejecuta 'jsonToCsv.py' para generarla.")
    st.stop()

# --- FUNCIONES ---
def guardar_cambios():
    repo.save(st.session_state.df)

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
    df_f = service.filter_cards(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
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
    df_f = service.filter_cards(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
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

    if st.button("🪄 Construir Mazo"):
        df_deck, status = service.generate_deck(st.session_state.df, f_nombre, f_tipo, f_rareza, f_sets)
        
        if df_deck is None:
            st.error(f"❌ {status}")
        else:
            st.success(f"✅ {status}")
            st.info(f"Mazo generado con **{len(df_deck)}** cartas.")
            
            pdf_bytes = generar_pdf(df_deck, "Commander Decklist")
            st.download_button("🖨️ Descargar PDF", data=pdf_bytes, file_name="mazo.pdf")

            grid_cols = st.columns(5)
            for i, (_, card) in enumerate(df_deck.iterrows()):
                with grid_cols[i % 5]:
                    n_u = urllib.parse.quote(card['name'])
                    st.image(f"https://api.scryfall.com/cards/named?exact={n_u}&format=image")
                    st.caption(f"**{card['name']}**")

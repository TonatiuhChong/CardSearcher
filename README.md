# 🎴 MTG Physical Collection Manager & Commander Builder

Este es un tablero interactivo profesional construido con **Streamlit** para gestionar inventarios de cartas físicas de Magic: The Gathering. El sistema está diseñado para entusiastas de Commander que desean organizar su colección y construir mazos estratégicos basados en sus cartas reales.

---

## ✨ Características Principales

### 📦 Gestión de Colección
*   **Buscador Avanzado:** Filtros dinámicos por nombre, tipo/raza, múltiples rarezas y expansiones.
*   **Gestión de Stock:** Edición rápida de cantidades. Las cantidades se preservan incluso al actualizar la base de datos de Scryfall.
*   **Visual Wishlist:** Identifica instantáneamente qué cartas te faltan según tus filtros actuales.

### 🪄 Generador de Mazos Commander (100 cartas)
*   **Construcción por Sinergia:** El algoritmo analiza el `oracle_text` del Comandante (Tokens, Contadores, Veneno, etc.) y prioriza cartas que apoyen esa estrategia.
*   **Identidad de Color Estricta:** Filtrado automático para asegurar que el mazo sea legal en Commander.
*   **Optimización de Curva:** Penalización inteligente para cartas de alto coste de maná para asegurar un mazo jugable.
*   **Prioridad de Inventario:** El sistema prioriza sugerirte cartas que **ya tienes en stock** (`cantidad > 0`).

### 🖼️ Interfaz Visual e Interactiva
*   **Flip de Cartas:** Soporte para cartas de doble cara (DFC, Transform, Aventuras) con vista frontal y trasera.
*   **Paginación Inteligente:** Navegación fluida de 20 en 20 cartas para evitar ralentizaciones.
*   **Cache Buster:** Botón de recarga individual para imágenes que no cargan correctamente.
*   **Exportación a PDF:** Genera listas de mazo o wishlists listas para imprimir.

---

## 🛠️ Arquitectura del Proyecto

El proyecto sigue una **Arquitectura por Capas** para facilitar el mantenimiento:

1.  **Capa de Presentación (`app.py`):** Interfaz de usuario pura con Streamlit.
2.  **Capa de Negocio (`service.py`):** Lógica de filtrado, reglas de Commander, cálculos de maná y algoritmos de construcción.
3.  **Capa de Datos (`repository.py`):** Persistencia, carga y normalización del archivo `data1.csv`.

---

## 🚀 Instalación y Configuración

### 1. Requisitos
*   Python 3.9 o superior.
*   Acceso a internet (para las imágenes vía Scryfall API).

### 2. Instalación de dependencias
```bash
pip install streamlit pandas fpdf2
```

### 3. Preparación de los datos (Scryfall)
1.  Descarga el archivo **Default Cards** (JSON) desde Scryfall Bulk Data.
2.  Colócalo en la carpeta raíz y actualiza el nombre del archivo en `jsonToCsv.py`.
3.  Ejecuta el script de sincronización:
    ```bash
    python jsonToCsv.py
    ```
    *Este script generará `data1.csv` extrayendo colores, texto, costes y poder de combate.*

### 4. Ejecutar la aplicación
```bash
streamlit run app.py
```

---

## 📊 Estructura de Datos

El archivo `data1.csv` requiere las siguientes columnas para el funcionamiento completo de todas las características:

| Columna | Descripción |
| :--- | :--- |
| `name` | Nombre completo de la carta. |
| `layout` | Tipo de diseño (normal, transform, etc) para el Flip. |
| `color_identity` | Colores legales de la carta. |
| `oracle_text` | Texto de habilidades para el motor de sinergia. |
| `mana_cost` / `mana_value` | Coste para el ordenamiento y la curva. |
| `cantidad` | Tu inventario físico personal. |

---

## 🛠️ Tecnologías Utilizadas

*   **Streamlit:** Framework para la UI web.
*   **Pandas:** Motor de procesamiento de datos.
*   **FPDF2:** Generación de reportes en PDF.
*   **Scryfall API:** Fuente de datos e imágenes en tiempo real.

---

## 📝 Notas de Versión
*   **v2.0:** Migración a arquitectura por capas y motor de sinergia para mazos.
*   **v1.5:** Implementación de Flip y Paginación.
*   **v1.0:** Versión inicial del buscador visual.

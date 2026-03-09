import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual de la web
st.set_page_config(page_title="Extractor Inteligente Honest", layout="wide")
st.title("📦 Extractor de Inventario Final")
st.markdown("Filtros avanzados con orden alfabético y limpieza de ceros.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Filtros")
proveedor = st.sidebar.text_input("Proveedor principal", "HONEST LAB")
palabras_extra_str = st.sidebar.text_input("Palabras clave en descripción", "STONE, TABLE")

st.sidebar.markdown("---")
st.sidebar.subheader("Ajustes de Columnas")
col_nombre = st.sidebar.number_input("Columna Nombre (Índice)", value=4)
col_cantidad = st.sidebar.number_input("Columna Cantidad (Índice)", value=10)
indices_extra_str = st.sidebar.text_input("Otras columnas (ej: 6, 7)", "6, 7")

st.sidebar.markdown("---")
agrupar = st.sidebar.checkbox("Agrupar y sumar iguales", value=True)
limpiar_num = st.sidebar.checkbox("Quitar números finales (01, 02...)", value=True)
orden_alfabetico = st.sidebar.checkbox("Ordenar alfabéticamente", value=True)

# --- PROCESAMIENTO ---
archivos_subidos = st.file_uploader("Sube aquí tus PDFs", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    indices_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    palabras_clave = [p.strip().upper() for p in palabras_extra_str.split(",") if p.strip()]
    datos_brutos = []

    with st.spinner('Procesando datos...'):
        for archivo in archivos_subidos:
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    tabla = pagina.extract_table()
                    if tabla:
                        for fila in tabla:
                            try:
                                nombre = str(fila[col_nombre]).replace('\n', ' ').strip()
                                fila_texto_completa = [str(celda).upper() for celda in fila if celda]
                                
                                coincide_proveedor = any(proveedor.upper() in t for t in fila_texto_completa) if proveedor else False
                                coincide_keyword = any(k in nombre.upper() for k in palabras_clave)

                                if coincide_proveedor or coincide_keyword:
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    
                                    # --- MEJORA 1: FILTRAR CANTIDADES 0 ---
                                    # Si la cantidad es 0, no lo añadimos a la lista inicial
                                    if qty > 0:
                                        extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in indices_extra]
                                        datos_brutos.append([nombre] + extras + [qty])
                            except:
                                continue

    if datos_brutos:
        nombres_col = ["Producto"] + [f"Info_{i}" for i in indices_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=nombres_col)

        if agrupar:
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            
            dict_agrup = {col: 'first' for col in df.columns if col != 'Producto'}
            dict_agrup['Cantidad'] = 'sum'
            df = df.groupby('Producto').agg(dict_agrup).reset_index()

        # --- MEJORA 2: ORDEN ALFABÉTICO ---
        if orden_alfabetico:
            df = df.sort_values(by='Producto', ascending=True)
        else:
            # Si no es alfabético, lo dejamos por cantidad (más a menos)
            df = df.sort_values(by='Cantidad', ascending=False)

        # Asegurar que cantidad sea la última columna
        cols = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
        df = df[cols]

        st.success(f"¡Hecho! Lista limpia y ordenada generada.")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Inventario Final (CSV)",
            data=csv,
            file_name=f"inventario_final.csv",
            mime='text/csv',
        )
    else:
        st.warning("No se encontraron elementos con cantidad mayor a cero que coincidan con los filtros.")

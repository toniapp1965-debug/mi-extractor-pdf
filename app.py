import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual de la web
st.set_page_config(page_title="Extractor de PDF Honest", layout="wide")
st.title("📦 Extractor de Inventario PDF")
st.markdown("Sube tu catálogo y genera la lista de cantidades automáticamente.")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Filtros")
proveedor = st.sidebar.text_input("Proveedor a buscar", "HONEST LAB")
col_nombre = st.sidebar.number_input("Columna Nombre (Índice)", value=4)
col_cantidad = st.sidebar.number_input("Columna Cantidad (Índice)", value=10)
indices_extra_str = st.sidebar.text_input("Columnas extra (ej: 6, 7)", "6, 7")

st.sidebar.markdown("---")
agrupar = st.sidebar.checkbox("Agrupar y sumar iguales", value=True)
limpiar_num = st.sidebar.checkbox("Quitar números finales (01, 02...)", value=True)

# --- SUBIDA DE ARCHIVO ---
archivo_subido = st.file_uploader("Sube aquí tu PDF", type="pdf")

if archivo_subido:
    indices_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    datos_brutos = []

    with st.spinner('Procesando PDF...'):
        with pdfplumber.open(archivo_subido) as pdf:
            for pagina in pdf.pages:
                tabla = pagina.extract_table()
                if tabla:
                    for fila in tabla:
                        # Buscamos al proveedor en la fila
                        fila_texto = [str(celda).upper() for celda in fila if celda]
                        if any(proveedor.upper() in texto for texto in fila_texto):
                            try:
                                nombre = str(fila[col_nombre]).replace('\n', ' ').strip()
                                qty_raw = str(fila[col_cantidad])
                                # Extraer solo los números de la cantidad
                                qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in indices_extra]
                                
                                # Orden: Nombre + Info Extra + Cantidad
                                datos_brutos.append([nombre] + extras + [qty])
                            except:
                                continue

    if datos_brutos:
        # Nombres de las columnas
        nombres_col = ["Producto"] + [f"Info_{i}" for i in indices_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=nombres_col)

        if agrupar:
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            
            # Sumar cantidades y mantener la primera info de las otras columnas
            dict_agrup = {col: 'first' for col in df.columns if col != 'Producto'}
            dict_agrup['Cantidad'] = 'sum'
            df = df.groupby('Producto').agg(dict_agrup).reset_index()
            
            # Asegurar que cantidad sea la última columna
            cols = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
            df = df[cols].sort_values(by='Cantidad', ascending=False)

        st.success(f"¡Hecho! Se han encontrado {len(df)} artículos.")
        st.dataframe(df, use_container_width=True)

        # Botón de descarga
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Descargar Excel (CSV)",
            data=csv,
            file_name=f"inventario_{proveedor.replace(' ','_')}.csv",
            mime='text/csv',
        )
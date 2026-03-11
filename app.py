import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual
st.set_page_config(page_title="Extractor Honest Avanzado", layout="wide")
st.title("📦 Extractor de Inventario Pro")
st.markdown("Filtros: HONEST (Todo) | Otros: Combinaciones de palabras separadas por ';' ")

# --- BARRA LATERAL ---
st.sidebar.header("Configuración de Filtros")
proveedor_fijo = st.sidebar.text_input("Proveedor a incluir siempre", "HONEST")

# Nueva explicación para los grupos de palabras
st.sidebar.markdown("**Keywords para otros proveedores:**")
palabras_extra_str = st.sidebar.text_input(
    "Usa ',' para 'Y' y ';' para 'O'", 
    "STONE, TABLE ; STONE, MESA"
)
st.sidebar.caption("Ejemplo: 'STONE, TABLE ; STONE, MESA' buscará ambas combinaciones.")

st.sidebar.markdown("---")
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
    idx_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    
    # PROCESAMOS LOS GRUPOS DE PALABRAS CLAVE
    # "STONE, TABLE ; STONE, MESA" -> [['STONE', 'TABLE'], ['STONE', 'MESA']]
    grupos_keywords = []
    for grupo in palabras_extra_str.split(";"):
        palabras = [p.strip().upper() for p in grupo.split(",") if p.strip()]
        if palabras:
            grupos_keywords.append(palabras)

    datos_brutos = []

    with st.spinner('Procesando datos...'):
        for archivo in archivos_subidos:
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    tabla = pagina.extract_table()
                    if tabla:
                        for fila in tabla:
                            try:
                                # 1. Búsqueda de Proveedor (Flexible en toda la fila)
                                fila_completa = " ".join([str(c) for c in fila if c]).upper()
                                es_honest = proveedor_fijo.upper() in fila_completa if proveedor_fijo else False
                                
                                # 2. Búsqueda de Combinaciones de Palabras (En el nombre)
                                nombre_prod = str(fila[col_nombre]).replace('\n', ' ').strip()
                                
                                coincide_algun_grupo = False
                                for grupo in grupos_keywords:
                                    # Verifica si TODAS las palabras del grupo están en el nombre
                                    if all(palabra in nombre_prod.upper() for palabra in grupo):
                                        coincide_algun_grupo = True
                                        break # Si ya coincide con un grupo, no hace falta mirar más

                                # FILTRO FINAL
                                if es_honest or coincide_algun_grupo:
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    
                                    if qty > 0:
                                        extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in idx_extra]
                                        datos_brutos.append([nombre_prod] + extras + [qty])
                            except:
                                continue

    if datos_brutos:
        columnas = ["Producto"] + [f"Info_{i}" for i in idx_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=columnas)

        if agrupar:
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            dict_agrup = {c: 'first' for c in df.columns if c != 'Producto'}
            dict_agrup['Cantidad'] = 'sum'
            df = df.groupby('Producto').agg(dict_agrup).reset_index()

        if orden_alfabetico:
            df = df.sort_values(by='Producto', ascending=True)
        else:
            df = df.sort_values(by='Cantidad', ascending=False)

        cols_final = [c for c in df.columns if c != 'Cantidad'] + ['Cantidad']
        df = df[cols_final]

        st.success(f"¡Análisis completado!")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar CSV", csv, "inventario_honest.csv", "text/csv")
    else:
        st.warning("No he encontrado nada. Prueba a cambiar los filtros.")

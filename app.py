import streamlit as st
import pdfplumber
import pandas as pd
import re

# Configuración visual
st.set_page_config(page_title="Extractor Honest Pro", layout="wide")
st.title("📦 Extractor de Inventario Pro")

# --- BARRA LATERAL ---
st.sidebar.header("1. Filtros de Búsqueda")
proveedor_fijo = st.sidebar.text_input("Proveedor a incluir siempre", "HONEST")
palabras_extra_str = st.sidebar.text_area(
    "Keywords (Otros proveedores)", 
    "STONE, TABLE ; STONE, MESA"
)

st.sidebar.markdown("---")
st.sidebar.header("2. Control de Agrupación")
agrupar = st.sidebar.checkbox("Activar agrupación inteligente", value=True)
limpiar_num = st.sidebar.checkbox("Quitar números finales (01, 02...)", value=True)
productos_para_sumar_total = st.sidebar.text_area(
    "Productos a SUMAR TOTALMENTE", 
    "BANCO NAGA"
)

st.sidebar.markdown("---")
st.sidebar.header("3. Ajustes de Columnas")
col_nombre = st.sidebar.number_input("Columna Nombre (Índice)", value=4)
col_cantidad = st.sidebar.number_input("Columna Cantidad (Índice)", value=10)
indices_extra_str = st.sidebar.text_input("Otras columnas (ej: 6, 7)", "6, 7")

st.sidebar.markdown("---")
st.sidebar.header("4. Orden del Listado")
# CAMBIO: Ahora es un selector con tres opciones
opcion_orden = st.sidebar.radio(
    "Selecciona el orden:",
    ("Orden original del PDF", "Alfabético (A-Z)", "Por cantidad (Mayor a menor)")
)

# --- PROCESAMIENTO ---
archivos_subidos = st.file_uploader("Sube aquí tus PDFs", type="pdf", accept_multiple_files=True)

if archivos_subidos:
    idx_extra = [int(i.strip()) for i in indices_extra_str.split(",") if i.strip()]
    lista_sumar_total = [s.strip().upper() for s in productos_para_sumar_total.split(",") if s.strip()]
    
    grupos_keywords = []
    for grupo in palabras_extra_str.split(";"):
        palabras = [p.strip().upper() for p in grupo.split(",") if p.strip()]
        if palabras:
            grupos_keywords.append(palabras)

    datos_brutos = []
    contador_posicion = 0 # Para recordar el orden original

    with st.spinner('Analizando PDFs...'):
        for archivo in archivos_subidos:
            with pdfplumber.open(archivo) as pdf:
                for pagina in pdf.pages:
                    tabla = pagina.extract_table()
                    if tabla:
                        for fila in tabla:
                            try:
                                texto_fila = " ".join([str(c) for c in fila if c]).upper()
                                nombre_prod = str(fila[col_nombre]).replace('\n', ' ').strip()
                                
                                es_honest = proveedor_fijo.upper() in texto_fila if proveedor_fijo else False
                                
                                coincide_keyword = False
                                for grupo in grupos_keywords:
                                    if all(p in nombre_prod.upper() for p in grupo):
                                        coincide_keyword = True
                                        break
                                
                                if es_honest or coincide_keyword:
                                    qty_raw = str(fila[col_cantidad])
                                    qty = int(''.join(filter(str.isdigit, qty_raw))) if any(c.isdigit() for c in qty_raw) else 0
                                    
                                    if qty > 0:
                                        contador_posicion += 1
                                        extras = [str(fila[i]).replace('\n', ' ').strip() if fila[i] else "" for i in idx_extra]
                                        # Guardamos la 'posicion' como primer elemento
                                        datos_brutos.append([contador_posicion, nombre_prod] + extras + [qty])
                            except:
                                continue

    if datos_brutos:
        # Añadimos 'Posicion' a las columnas
        columnas_nombres = ["Posicion", "Producto"] + [f"Info_{i}" for i in idx_extra] + ["Cantidad"]
        df = pd.DataFrame(datos_brutos, columns=columnas_nombres)

        if agrupar:
            if limpiar_num:
                df['Producto'] = df['Producto'].apply(lambda x: re.sub(r'\s*\d+\s*$', '', x))
            
            def aplicar_excepcion(row):
                if row['Producto'].upper() in lista_sumar_total:
                    for c in df.columns:
                        if "Info_" in c:
                            row[c] = "(Suma total)"
                return row
            df = df.apply(aplicar_excepcion, axis=1)
            
            # Agrupamos. Para la 'Posicion', nos quedamos con la mínima (la primera vez que apareció)
            columnas_agrupar = [c for c in df.columns if c not in ['Cantidad', 'Posicion']]
            df = df.groupby(columnas_agrupar).agg({'Cantidad': 'sum', 'Posicion': 'min'}).reset_index()

        # --- APLICAR EL ORDEN ELEGIDO ---
        if opcion_orden == "Orden original del PDF":
            df = df.sort_values(by='Posicion', ascending=True)
        elif opcion_orden == "Alfabético (A-Z)":
            df = df.sort_values(by='Producto', ascending=True)
        else:
            df = df.sort_values(by='Cantidad', ascending=False)

        # Quitamos la columna Posicion antes de mostrar/descargar para que no ensucie
        cols_final = [c for c in df.columns if c not in ['Cantidad', 'Posicion']] + ['Cantidad']
        df_mostrar = df[cols_final]

        st.success(f"¡Hecho! Listado generado.")
        st.dataframe(df_mostrar, use_container_width=True)

        csv = df_mostrar.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Inventario (CSV)", csv, "inventario.csv", "text/csv")
    else:
        st.warning("No se encontraron resultados.")

import streamlit as st
import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# Configuración visual estilo Notebook
st.set_page_config(page_title="Dynamic Pricing Analyzer", layout="wide")
st.title("01 Dynamic Pricing Analyzer")
st.markdown("---")

# 1. REQUISITOS DE COLUMNAS (Basado en el documento)
st.sidebar.header("Configuración de Datos")
st.sidebar.info("""
**Columnas Obligatorias:**
- sku, unidades, venta_neta, fecha [cite: 25, 26, 27, 28, 29]
""")

# 2. CARGA Y VALIDACIÓN
uploaded_file = st.file_uploader("Subir histórico de ventas (CSV o Excel)", type=["csv", "xlsx"])

if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # Validación estricta [cite: 40, 41]
    required = ['sku', 'unidades', 'venta_neta', 'fecha']
    if not all(col in df.columns for col in required):
        st.error("⚠️ El archivo no sirve para el análisis. Rectifique el nombre de las columnas: sku, unidades, venta_neta, fecha.")
        st.stop()

    # Cálculos iniciales [cite: 35, 59, 61, 64]
    df['precio'] = df['venta_neta'] / df['unidades']
    if 'costo' not in df.columns:
        st.warning("Falta columna 'costo'. Solo se simulará ingreso[cite: 36].")
        df['costo'] = 0

    # 3. DASHBOARD PRINCIPAL (Por SKU)
    sku_list = df['sku'].unique()
    selected_sku = st.selectbox("Seleccione un SKU para el análisis detallado", sku_list)
    sku_df = df[df['sku'] == selected_sku].copy()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Parámetros de Elasticidad")
        manual_e = st.number_input("Elasticidad Manual (0 para auto)", value=0.0)
        
        # Estimación Log-Log [cite: 37, 76]
        if manual_e == 0:
            try:
                y = np.log(sku_df['unidades'] + 1)
                x = np.log(sku_df['precio'])
                x = sm.add_constant(x)
                model = sm.OLS(y, x).fit()
                elasticity = model.params[1]
            except:
                elasticity = -0.01
        else:
            elasticity = manual_e

        # Clasificación [cite: 77, 78, 82, 83]
        if elasticity < -1: color, tipo = "green", "Elástico"
        elif -1 <= elasticity < 0: color, tipo = "blue", "Inelástico"
        else: color, tipo = "red", "Sospechoso/Positivo"
        
        st.metric("Elasticidad", f"{elasticity:.2f}", tipo)

    with col2:
        # Gráfica de Dispersión Precio vs Unidades (Del Notebook)
        fig, ax = plt.subplots()
        sns.regplot(data=sku_df, x='precio', y='unidades', ax=ax, color=color)
        ax.set_title(f"Relación Precio-Demanda: {selected_sku}")
        st.pyplot(fig)

    # 4. SIMULACIÓN DE ESCENARIOS [cite: 89, 90, 92, 93]
    st.markdown("---")
    st.subheader("Simulador de Escenarios y Promociones")
    
    p_base = sku_df['precio'].mean()
    u_base = sku_df['unidades'].sum()
    c_base = sku_df['costo'].mean()

    escenarios = {
        "-10%": 0.9, "-5%": 0.95, "Base": 1.0, "+5%": 1.05, "+10%": 1.1,
        "2x1": 0.5, "3x2": 0.66, "2do al 50%": 0.75 # Lógica de promos [cite: 16, 38]
    }

    sim_data = []
    for nombre, factor in escenarios.items():
        p_nuevo = p_base * factor
        # Fórmula del documento: u_base * (p_nuevo/p_base)^elasticidad
        u_sim = u_base * (factor**elasticity)
        i_sim = p_nuevo * u_sim
        m_sim = (p_nuevo - c_base) * u_sim
        
        sim_data.append({"Escenario": nombre, "Precio": p_nuevo, "Unidades": u_sim, "Ingreso": i_sim, "Margen": m_sim})

    df_sim = pd.DataFrame(sim_data)
    st.table(df_sim.style.highlight_max(axis=0, subset=['Ingreso', 'Margen'], color='lightgreen'))

    # 5. RECOMENDACIÓN FINAL [cite: 98, 109, 110, 111, 114]
    if elasticity < -1:
        rec = "Bajar precio / promover"
    elif -1 <= elasticity < 0:
        rec = "Subir precio"
    else:
        rec = "No recomendar / Revisar datos"
    
    st.success(f"**Recomendación Sugerida:** {rec}")

    # 6. EXPORTAR RESULTADOS [cite: 19, 131]
    csv = df_sim.to_csv(index=False).encode('utf-8')
    st.download_button("Descargar Análisis en CSV", csv, f"analisis_{selected_sku}.csv", "text/csv")
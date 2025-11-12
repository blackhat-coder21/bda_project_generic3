# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os
from collections import defaultdict

# --- Page Configuration ---
st.set_page_config(
    page_title="CapyMOA Real-Time Dashboard",
    page_icon="📊",
    layout="wide"
)

# --- File Paths ---
CLASSIFICATION_CSV = "metrics_classification.csv"
REGRESSION_CSV = "metrics_regression.csv"
CLASSIFICATION_DRIFT_CSV = "metrics_classification_drift.csv" # New file

# --- Caching ---
@st.cache_data(ttl=3)
def load_data(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_csv(file_path)
        if "instance" in df.columns:
            df = df.set_index("instance")
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna()
        return df
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return None

def get_learners_and_metrics(df):
    learners = set()
    metrics = set()
    for col in df.columns:
        parts = col.split('_', 1)
        if len(parts) == 2:
            learner, metric = parts[0], f"_{parts[1]}"
            learners.add(learner)
            metrics.add(metric)
    return sorted(list(learners)), sorted(list(metrics))

# --- Main Page ---
st.title("CapyMOA & Kafka: Real-Time Dashboard")
auto_refresh = st.sidebar.checkbox("Auto-refresh every 3s", value=True)

# --- NEW: Dashboard Mode Selector ---
st.sidebar.title("Dashboard Mode")
dashboard_mode = st.sidebar.radio(
    "Select a view",
    ("Live Monitoring", "Drift Comparison"),
    horizontal=True,
    label_visibility="collapsed"
)

if dashboard_mode == "Live Monitoring":
    # This is all your previous dashboard code
    st.sidebar.header("Monitoring Controls")
    task_type = st.sidebar.radio(
        "Select Task to Monitor",
        ("Classification", "Regression"),
        horizontal=True
    )
    file_path = CLASSIFICATION_CSV if task_type == "Classification" else REGRESSION_CSV
    st.header(f"Live {task_type} Monitoring")
    st.markdown(f"Monitoring metrics from **{file_path}**")
    
    df = load_data(file_path)

    if df is None:
        st.warning(f"Waiting for data... Please start your evaluator to create `{file_path}`.")
    elif df.empty:
        st.warning(f"File `{file_path}` is empty. Waiting for producer to send data...")
    else:
        learners, metrics = get_learners_and_metrics(df)
        if not learners or not metrics:
            st.error("Could not parse learners or metrics from the CSV.")
        else:
            # Comparative Plot
            st.sidebar.header("Comparative Plot")
            selected_metric = st.sidebar.selectbox("Select Metric to Compare", metrics, index=0)
            selected_learners = st.sidebar.multiselect("Select Learners to Compare", learners, default=learners)
            
            st.subheader("Learner Comparison")
            cols_to_plot = [f"{learner}{selected_metric}" for learner in selected_learners if f"{learner}{selected_metric}" in df.columns]
            if cols_to_plot:
                plot_df = df[cols_to_plot].copy()
                plot_df['instance'] = plot_df.index
                plot_df_melted = plot_df.melt('instance', var_name='Learner', value_name='Metric Value')
                plot_df_melted['Learner'] = plot_df_melted['Learner'].str.replace(selected_metric, "")
                
                fig_comp = px.line(plot_df_melted, x='instance', y='Metric Value', color='Learner', title=f"Comparison for {selected_metric}")
                st.plotly_chart(fig_comp, use_container_width=True)
            
            # Individual Plots
            st.subheader("Individual Learner Deep-Dive")
            tabs = st.tabs(learners)
            for i, learner in enumerate(learners):
                with tabs[i]:
                    learner_cols = [col for col in df.columns if col.startswith(learner)]
                    if learner_cols:
                        learner_df = df[learner_cols].copy()
                        learner_df['instance'] = learner_df.index
                        learner_df_melted = learner_df.melt('instance', var_name='Metric', value_name='Value')
                        learner_df_melted['Metric'] = learner_df_melted['Metric'].str.replace(f"{learner}_", "")
                        fig_indiv = px.line(learner_df_melted, x='instance', y='Value', color='Metric', title=f"All Metrics for {learner}")
                        st.plotly_chart(fig_indiv, use_container_width=True)

            # Raw Data
            st.subheader("Live Metric Log (Last 100 Instances)")
            st.dataframe(df.tail(100).sort_index(ascending=False))

# --- NEW: Drift Comparison Mode ---
elif dashboard_mode == "Drift Comparison":
    st.header("Drift vs. Normal Stream Comparison")
    st.markdown(f"Comparing **{CLASSIFICATION_CSV}** (Normal) vs. **{CLASSIFICATION_DRIFT_CSV}** (Drift)")

    # Load both datasets
    df_normal = load_data(CLASSIFICATION_CSV)
    df_drift = load_data(CLASSIFICATION_DRIFT_CSV)

    # Check if data is available
    if df_normal is None or df_drift is None:
        st.warning(f"Waiting for data... Please ensure both evaluators are running and producing:")
        st.markdown(f"* `{CLASSIFICATION_CSV}` (Normal Stream)")
        st.markdown(f"* `{CLASSIFICATION_DRIFT_CSV}` (Drift Stream)")
    elif df_normal.empty or df_drift.empty:
        st.warning("One or both streams are empty. Waiting for producers to send data...")
    else:
        # Get learners and metrics (assume they are the same)
        learners, metrics = get_learners_and_metrics(df_normal)
        
        if not learners or not metrics:
            st.error("Could not parse learners/metrics from `metrics_classification.csv`.")
        else:
            # Sidebar controls for comparison
            st.sidebar.header("Comparison Controls")
            selected_metric = st.sidebar.selectbox("Select Metric to Compare", metrics, index=0)
            selected_learners = st.sidebar.multiselect("Select Learners to Compare", learners, default=learners)

            if not selected_learners:
                st.warning("Please select at least one learner to compare.")
            else:
                # Prepare data for plotting
                all_plot_data = []
                for learner in selected_learners:
                    col_name = f"{learner}{selected_metric}"
                    if col_name in df_normal.columns and col_name in df_drift.columns:
                        # Get normal data
                        df_norm_learner = df_normal[[col_name]].copy()
                        df_norm_learner['instance'] = df_norm_learner.index
                        df_norm_learner['Stream'] = 'Normal'
                        df_norm_learner['Learner'] = learner
                        df_norm_learner = df_norm_learner.rename(columns={col_name: 'Value'})
                        
                        # Get drift data
                        df_drift_learner = df_drift[[col_name]].copy()
                        df_drift_learner['instance'] = df_drift_learner.index
                        df_drift_learner['Stream'] = 'Drift'
                        df_drift_learner['Learner'] = learner
                        df_drift_learner = df_drift_learner.rename(columns={col_name: 'Value'})
                        
                        all_plot_data.extend([df_norm_learner, df_drift_learner])

                if all_plot_data:
                    combined_df = pd.concat(all_plot_data)
                    
                    # --- The Magic Plot ---
                    # We use 'color' for the learner and 'line_dash' for the stream
                    fig_comp = px.line(
                        combined_df,
                        x='instance',
                        y='Value',
                        color='Learner',
                        line_dash='Stream', # This will make 'Normal' solid and 'Drift' dashed
                        title=f"Drift vs. Normal Comparison for {selected_metric.replace('_', ' ').strip().title()}",
                        labels={'Value': selected_metric.replace('_', ' ').strip().title()}
                    )
                    fig_comp.update_layout(legend_title="Legend")
                    st.plotly_chart(fig_comp, use_container_width=True)
                else:
                    st.error("No data found for the selected learner/metric combination.")

# --- Auto-Refresh Logic ---
if auto_refresh:
    time.sleep(3)
    st.rerun()

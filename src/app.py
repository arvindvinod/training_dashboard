import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# --- CONFIGURATION & THEMING ---
st.set_page_config(
    page_title="Multisport 70.3 & Recovery Dashboard",
    page_icon="🏊‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Styling
def inject_custom_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
        
        /* Font styling */
        html, body, [class*="css"], [class*="st-"] {
            font-family: 'Outfit', sans-serif;
        }
        
        /* Glassmorphic Metric Cards */
        .metric-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-align: center;
            height: 100%;
        }
        
        .metric-card:hover {
            transform: translateY(-4px);
            border-color: rgba(99, 102, 241, 0.4);
            box-shadow: 0 20px 25px -5px rgba(99, 102, 241, 0.15), 0 10px 10px -5px rgba(99, 102, 241, 0.1);
        }
        
        .metric-title {
            color: #94a3b8;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 6px;
        }
        
        .metric-value {
            font-size: 34px;
            font-weight: 700;
            margin-bottom: 4px;
            background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .metric-delta {
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
        }
        
        .delta-positive {
            color: #10b981;
        }
        
        .delta-negative {
            color: #ef4444;
        }
        
        .delta-neutral {
            color: #64748b;
        }
        
        /* Sport Badges */
        .sport-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge-swim { background-color: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.3); }
        .badge-bike { background-color: rgba(249, 115, 22, 0.15); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.3); }
        .badge-run { background-color: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
        .badge-strength { background-color: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
        .badge-yoga { background-color: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-other { background-color: rgba(100, 116, 139, 0.15); color: #94a3b8; border: 1px solid rgba(100, 116, 139, 0.3); }
        
        /* Banner Gradient */
        .header-gradient {
            background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 2.8rem;
            margin-bottom: 5px;
        }
        
        .header-subtext {
            color: #94a3b8;
            font-size: 1.1rem;
            margin-bottom: 25px;
        }

        /* Insight Card */
        .insight-card {
            background: rgba(30, 41, 59, 0.5);
            border-left: 5px solid #8b5cf6;
            border-radius: 8px;
            padding: 15px 20px;
            margin-bottom: 15px;
        }
        </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- HEADER ---
st.markdown("<h1 class='header-gradient'>🏊‍♂️ 70.3 Multisport & Recovery</h1>", unsafe_allow_html=True)
st.markdown("<p class='header-subtext'>Monitoring Swim, Bike, Run, Strength, and Yoga load to optimize your Half Ironman training journey.</p>", unsafe_allow_html=True)

# --- CREDENTIALS & SUPABASE INIT ---
intervals_id = os.getenv("INTERVALS_ATHLETE_ID", "")
intervals_key = os.getenv("INTERVALS_API_KEY", "")
supabase_url = os.getenv("SUPABASE_URL", "")
supabase_key = os.getenv("SUPABASE_KEY", "")

supabase: Client | None = None
if supabase_url and supabase_key:
    try:
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Error connecting to Supabase: {e}")

# --- INITIALIZE SESSION STATE ---
if "data_fetched" not in st.session_state:
    st.session_state.data_fetched = False
if "df_intervals" not in st.session_state:
    st.session_state.df_intervals = pd.DataFrame()
if "df_wellness" not in st.session_state:
    st.session_state.df_wellness = pd.DataFrame()

# --- SIDEBAR: CONFIGURATION ---
st.sidebar.header("🏁 70.3 Race Target")
race_name = st.sidebar.text_input("Target Race Name", "Ironman 70.3")
race_date = st.sidebar.date_input("Target Race Date", date.today() + timedelta(days=365))

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Settings")
days_to_pull = st.sidebar.slider("Days to Analyze", 7, 90, 30)

end_date = date.today()
start_date = end_date - timedelta(days=days_to_pull)

st.sidebar.markdown("---")
col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    if st.button("🔄 Reload App", use_container_width=True):
        st.cache_data.clear()
        st.session_state.data_fetched = False
        st.rerun()
with col_s2:
    sync_clicked = st.button("☁️ Sync Intervals", type="primary", use_container_width=True)

# --- CATEGORIZE ACTIVITIES ---
def categorize_activity(activity_type):
    t = str(activity_type).lower()
    if 'ride' in t or 'bike' in t or 'cycling' in t:
        return 'Bike'
    elif 'run' in t or 'jog' in t:
        return 'Run'
    elif 'swim' in t:
        return 'Swim'
    elif 'weight' in t or 'strength' in t or 'lift' in t or 'gym' in t:
        return 'Strength'
    elif 'yoga' in t or 'stretch' in t or 'pilates' in t:
        return 'Yoga'
    else:
        return 'Other'

# --- SYNC & LOAD LOGIC ---
def sync_data_to_supabase(athlete_id, api_key, start, end):
    if not supabase:
        st.error("Supabase client not initialized.")
        return
    
    # 1. Fetch & Sync Activities
    url_act = f"https://intervals.icu/api/v1/athlete/{athlete_id}/activities"
    params = {"oldest": start.isoformat(), "newest": end.isoformat()}
    res_act = requests.get(url_act, params=params, auth=("API_KEY", api_key))
    if res_act.status_code == 200:
        data_act = res_act.json()
        for act in data_act:
            # Map fields for Supabase
            record = {
                "id": str(act.get("id")),
                "date": act.get("start_date_local", "").split("T")[0] if act.get("start_date_local") else None,
                "category": categorize_activity(act.get("type", "")),
                "name": act.get("name"),
                "distance": act.get("distance"),
                "moving_time_mins": act.get("moving_time", 0) / 60.0 if act.get("moving_time") else 0.0,
                "tss": act.get("icu_training_load", 0.0),
                "avg_power": act.get("average_watts"),
                "avg_hr": act.get("average_heartrate"),
                "max_hr": act.get("max_heartrate"),
                "work_kj": act.get("kilojoules"),
                "elevation_gain_m": act.get("elevation_gain"),
                "raw_data": act
            }
            if record["date"]:
                supabase.table("activities").upsert(record).execute()
    else:
        st.error(f"Failed to fetch activities: {res_act.status_code}")

    # 2. Fetch & Sync Wellness
    url_well = f"https://intervals.icu/api/v1/athlete/{athlete_id}/wellness"
    res_well = requests.get(url_well, params=params, auth=("API_KEY", api_key))
    if res_well.status_code == 200:
        data_well = res_well.json()
        for well in data_well:
            record = {
                "date": well.get("id"),
                "ctl": well.get("ctl"),
                "atl": well.get("atl"),
                "form": well.get("form"),
                "resting_hr": well.get("restingHR"),
                "sleep_secs": well.get("sleepSecs"),
                "hrv": well.get("hrv"),
                "hrv_sdnn": well.get("hrvSDNN"),
                "weight": well.get("weight"),
                "raw_data": well
            }
            if record["date"]:
                supabase.table("wellness").upsert(record).execute()
    else:
        st.error(f"Failed to fetch wellness: {res_well.status_code}")
        
    st.success("Successfully synced with Intervals.icu!")

@st.cache_data(ttl=3600)
def load_data_from_supabase(start, end):
    if not supabase:
        return pd.DataFrame(), pd.DataFrame()
        
    # Fetch Activities
    try:
        res_act = supabase.table("activities").select("*").gte("date", start.isoformat()).lte("date", end.isoformat()).execute()
        df_act = pd.DataFrame(res_act.data)
        if not df_act.empty:
            df_act['date'] = pd.to_datetime(df_act['date']).dt.date
            df_act['distance'] = pd.to_numeric(df_act['distance'], errors='coerce')
            df_act['distance_formatted'] = df_act.apply(
                lambda row: row['distance'] / 1000.0 if row['category'] in ['Bike', 'Run', 'Other'] else row['distance'],
                axis=1
            )
            df_act['np'] = df_act['raw_data'].apply(lambda x: x.get('icu_weighted_avg_watts') if isinstance(x, dict) else None)
    except Exception as e:
        st.error(f"Error loading activities from Supabase: {e}")
        df_act = pd.DataFrame()
        
    # Fetch Wellness
    try:
        res_well = supabase.table("wellness").select("*").gte("date", start.isoformat()).lte("date", end.isoformat()).execute()
        df_well = pd.DataFrame(res_well.data)
        if not df_well.empty:
            df_well['date'] = pd.to_datetime(df_well['date']).dt.date
            df_well = df_well.sort_values('date')
            
            # Map DB columns to what dashboard expects
            mapping = {
                "resting_hr": "restingHR",
                "sleep_secs": "sleepSecs"
            }
            df_well = df_well.rename(columns=mapping)
            
            # Default missing
            for col in ['ctl', 'atl', 'form', 'restingHR', 'sleepSecs', 'hrv', 'weight']:
                if col not in df_well.columns:
                    df_well[col] = None
                    
            mask = df_well['form'].isna() & df_well['ctl'].notna() & df_well['atl'].notna()
            df_well.loc[mask, 'form'] = df_well.loc[mask, 'ctl'] - df_well.loc[mask, 'atl']
    except Exception as e:
        st.error(f"Error loading wellness from Supabase: {e}")
        df_well = pd.DataFrame()
        
    return df_act, df_well

# --- FETCH DATA TRIGGER ---
# --- FETCH & SYNC TRIGGER ---
if sync_clicked:
    if not (intervals_id and intervals_key):
        st.warning("Please configure Intervals credentials in .env to sync.")
    else:
        with st.spinner("Syncing data from Intervals to Supabase..."):
            sync_data_to_supabase(intervals_id, intervals_key, start_date, end_date)
            st.cache_data.clear() # Clear cache so it reloads fresh from DB
            st.rerun()

if not supabase_url:
    st.warning("Please configure SUPABASE_URL and SUPABASE_KEY in your .env file.")
else:
    with st.spinner("Loading data from Supabase..."):
        df_intervals, df_wellness = load_data_from_supabase(start_date, end_date)
        
        st.session_state.df_intervals = df_intervals
        st.session_state.df_wellness = df_wellness
        st.session_state.data_fetched = True

# --- RENDER DASHBOARD ---
if st.session_state.data_fetched:
    df_intervals = st.session_state.df_intervals
    df_wellness = st.session_state.df_wellness

    # Calculate latest metrics
    latest_ctl = df_wellness["ctl"].dropna().iloc[-1] if not df_wellness.empty and "ctl" in df_wellness.columns and not df_wellness["ctl"].dropna().empty else None
    latest_atl = df_wellness["atl"].dropna().iloc[-1] if not df_wellness.empty and "atl" in df_wellness.columns and not df_wellness["atl"].dropna().empty else None
    latest_form = df_wellness["form"].dropna().iloc[-1] if not df_wellness.empty and "form" in df_wellness.columns and not df_wellness["form"].dropna().empty else None
    latest_rhr = df_wellness["restingHR"].dropna().iloc[-1] if not df_wellness.empty and "restingHR" in df_wellness.columns and not df_wellness["restingHR"].dropna().empty else None
    
    sleep_series = df_wellness["sleepSecs"] / 3600.0 if not df_wellness.empty and "sleepSecs" in df_wellness.columns else pd.Series()
    latest_sleep = sleep_series.dropna().iloc[-1] if not sleep_series.dropna().empty else None
    latest_hrv = df_wellness["hrv"].dropna().iloc[-1] if not df_wellness.empty and "hrv" in df_wellness.columns and not df_wellness["hrv"].dropna().empty else None

    # Calculate 7-day Deltas
    def get_7day_delta(series):
        if len(series.dropna()) >= 8:
            clean = series.dropna()
            curr = clean.iloc[-1]
            prev = clean.iloc[-8]
            diff = curr - prev
            sign = "+" if diff >= 0 else ""
            delta_type = "positive" if diff >= 0 else "negative"
            return f"{sign}{diff:.1f}", delta_type
        return None, "neutral"
        
    def get_rhr_delta(series):
        if len(series.dropna()) >= 8:
            clean = series.dropna()
            curr = clean.iloc[-1]
            prev = clean.iloc[-8]
            diff = curr - prev
            sign = "+" if diff >= 0 else ""
            delta_type = "positive" if diff <= 0 else "negative"  # Lower RHR is good!
            return f"{sign}{diff:.0f} bpm", delta_type
        return None, "neutral"

    ctl_delta, ctl_type = get_7day_delta(df_wellness["ctl"]) if "ctl" in df_wellness.columns else (None, "neutral")
    atl_delta, atl_type = get_7day_delta(df_wellness["atl"]) if "atl" in df_wellness.columns else (None, "neutral")
    form_delta, form_type = get_7day_delta(df_wellness["form"]) if "form" in df_wellness.columns else (None, "neutral")
    
    rhr_delta, rhr_type = get_rhr_delta(df_wellness["restingHR"]) if "restingHR" in df_wellness.columns else (None, "neutral")
    sleep_delta, sleep_type = get_7day_delta(sleep_series) if not sleep_series.empty else (None, "neutral")
    hrv_delta, hrv_type = get_7day_delta(df_wellness["hrv"]) if "hrv" in df_wellness.columns else (None, "neutral")

    # Custom Card Renderer
    def render_metric_card(title, value, delta=None, delta_type="neutral", suffix="", format_str="{:.1f}"):
        d_class = "delta-neutral"
        d_symbol = "●"
        if delta_type == "positive":
            d_class = "delta-positive"
            d_symbol = "▲"
        elif delta_type == "negative":
            d_class = "delta-negative"
            d_symbol = "▼"
            
        delta_html = f"<div class='metric-delta {d_class}'><span>{d_symbol}</span> {delta} (7d)</div>" if delta else "<div class='metric-delta delta-neutral'>--</div>"
        
        if value is not None:
            try:
                val_str = format_str.format(value) + suffix
            except ValueError:
                val_str = str(value) + suffix
        else:
            val_str = "--"
            
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{title}</div>
                <div class="metric-value">{val_str}</div>
                {delta_html}
            </div>
        """, unsafe_allow_html=True)

    # --- TAB NAVIGATION ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏁 Overview & 70.3 Countdown", 
        "📈 Fitness Curves & TSS Load", 
        "🧘‍♂️ Recovery, Wellness & Yoga", 
        "🏊‍♂️ Multisport & Strength Log"
    ])
    
    # ==================== TAB 1: OVERVIEW & COUNTDOWN ====================
    with tab1:
        # Race Countdown Widget
        days_to_race = (race_date - date.today()).days
        weeks_to_race = max(0, days_to_race // 7)
        
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1d4ed8 0%, #7c3aed 100%); padding: 25px; border-radius: 16px; text-align: center; color: white; margin-bottom: 25px; box-shadow: 0 10px 25px -5px rgba(29, 78, 216, 0.3);">
                <h2 style="margin: 0; font-size: 22px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.95;">🏁 Goal Race: {race_name}</h2>
                <div style="font-size: 44px; font-weight: 800; margin: 12px 0; letter-spacing: -0.02em;">{days_to_race} Days / {weeks_to_race} Weeks to go</div>
                <div style="font-size: 14px; opacity: 0.85; font-weight: 500;">
                    Target Date: {race_date.strftime('%B %d, %Y')} | Power phase, aerobic volume, and core stability are your building blocks.
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Row 1: Metrics Grid
        col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)
        with col_m1:
            render_metric_card("Fitness (CTL)", latest_ctl, ctl_delta, ctl_type)
        with col_m2:
            render_metric_card("Fatigue (ATL)", latest_atl, atl_delta, atl_type)
        with col_m3:
            render_metric_card("Form (Balance)", latest_form, form_delta, form_type)
        with col_m4:
            render_metric_card("Resting HR", latest_rhr, rhr_delta, rhr_type, " bpm", format_str="{:.0f}")
        with col_m5:
            render_metric_card("Sleep Duration", latest_sleep, sleep_delta, sleep_type, " hrs")
        with col_m6:
            render_metric_card("HRV (rMSSD)", latest_hrv, hrv_delta, hrv_type, " ms", format_str="{:.0f}")
            
        st.markdown("---")
        
        # Row 2: Volume distribution & recommendation insights
        col_o1, col_o2 = st.columns([1, 1.2])
        
        with col_o1:
            st.markdown("### 📊 Weekly Training Volume")
            if not df_intervals.empty:
                # Group by category and compute hours
                df_vol = df_intervals.groupby('category').agg(
                    duration_hrs=('moving_time_mins', 'sum'),
                    tss_total=('tss', 'sum')
                ).reset_index()
                
                # Make sure all categories exist in df_vol to show color consistencies
                categories_list = ['Swim', 'Bike', 'Run', 'Strength', 'Yoga', 'Other']
                for cat in categories_list:
                    if cat not in df_vol['category'].values:
                        df_vol = pd.concat([df_vol, pd.DataFrame([{'category': cat, 'duration_hrs': 0.0, 'tss_total': 0.0}])], ignore_index=True)
                
                fig_pie = px.pie(
                    df_vol[df_vol['duration_hrs'] > 0], 
                    values='duration_hrs', 
                    names='category',
                    color='category',
                    color_discrete_map={
                        'Swim': '#0ea5e9',
                        'Bike': '#f97316',
                        'Run': '#ef4444',
                        'Strength': '#a855f7',
                        'Yoga': '#10b981',
                        'Other': '#64748b'
                    },
                    hole=0.4
                )
                fig_pie.update_layout(
                    template="plotly_dark",
                    height=280,
                    margin=dict(l=10, r=10, t=30, b=10),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No volume data found.")
                
        with col_o2:
            st.markdown("### 💡 Triathlete Recovery & Coaching Insights")
            
            # Generate insights
            insights = []
            
            # Form-based insights
            if latest_form is not None:
                if latest_form > 5:
                    insights.append("🌟 **Freshness Mode (Form > +5):** Your body has shed training load. Excellent timing for a high-intensity key brick workout (Bike-to-Run transition) or a critical swim speed test!")
                elif -10 <= latest_form <= 5:
                    insights.append("🚴‍♂️ **Optimal Training Balance (Form -10 to +5):** Ideal window for consistent base volume. Maintain the Swim, Bike, and Run splits while fitting in lifting.")
                elif -30 <= latest_form < -10:
                    insights.append("🔥 **Productive Overreaching (Form -30 to -10):** Fatigue is building. Focus heavily on recovery protocols (sleep and restorative yoga) to absorb the training block adaptation.")
                else:
                    insights.append("🛑 **Danger Zone (Form < -30):** Extreme fatigue. High risk of injury/burnout. Substantially reduce training load today. Do active recovery yoga instead of running.")
            
            # Wellness-based insights
            if "restingHR" in df_wellness.columns and latest_rhr is not None:
                rhr_avg = df_wellness["restingHR"].dropna().mean()
                if latest_rhr > rhr_avg + 3:
                    insights.append(f"⚠️ **Elevated Resting HR:** Today's RHR (**{latest_rhr:.0f} bpm**) is elevated. Your nervous system is under stress. Keep workouts in the aerobic zone (Zone 2) and prioritize rest.")
                    
            if "hrv" in df_wellness.columns and latest_hrv is not None:
                hrv_avg = df_wellness["hrv"].dropna().mean()
                if latest_hrv < hrv_avg - 4:
                    insights.append(f"🔋 **Suppressed HRV:** Autonomic nervous system recovery is low. Shift key workouts to a day when HRV rebounds.")
            
            # Multisport Balance check (last 7 days)
            if not df_intervals.empty:
                recent_7d = df_intervals[df_intervals['date'] >= (date.today() - timedelta(days=7))]
                
                # Check Yoga and Strength
                yoga_sessions = len(recent_7d[recent_7d['category'] == 'Yoga'])
                strength_sessions = len(recent_7d[recent_7d['category'] == 'Strength'])
                
                if yoga_sessions == 0:
                    insights.append("🧘‍♂️ **Yoga Check-in:** You haven't logged any yoga or stretching sessions in the last 7 days. Add a 15-minute recovery flow to loosen your calves, hips, and lower back.")
                if strength_sessions == 0:
                    insights.append("🏋️‍♂️ **Strength Training:** No strength sessions logged this week. Lifting is critical for glute/core power and preventing shoulder strain from swimming.")
                
                # Swim, Bike, Run proportion check
                sbr_dur = recent_7d[recent_7d['category'].isin(['Swim', 'Bike', 'Run'])].groupby('category')['moving_time_mins'].sum()
                total_sbr_dur = sbr_dur.sum()
                
                if total_sbr_dur > 0:
                    bike_pct = (sbr_dur.get('Bike', 0) / total_sbr_dur) * 100
                    run_pct = (sbr_dur.get('Run', 0) / total_sbr_dur) * 100
                    swim_pct = (sbr_dur.get('Swim', 0) / total_sbr_dur) * 100
                    
                    # Ideal triathlon volume guidelines (typically ~50% Bike, 30% Run, 20% Swim)
                    if bike_pct > 65:
                        insights.append(f"🚴‍♂️ **Cycling Dominance:** Cycling represented **{bike_pct:.0f}%** of your SBR duration this week. Ensure you aren't neglecting run volume or swim technique.")
                    if run_pct > 45:
                        insights.append(f"🏃‍♂️ **High Running Volume:** Running represents **{run_pct:.0f}%** of your volume. Runners preparing for 70.3 need to be careful to avoid high-impact joint stress—consider shifting some load to cycling.")
            
            if not insights:
                insights.append("✨ Keep logging your multisport workouts, strength, and yoga to populate your weekly 70.3 coach recommendations!")
                
            for ins in insights:
                st.markdown(f"<div class='insight-card'>{ins}</div>", unsafe_allow_html=True)

    # ==================== TAB 2: FITNESS & LOAD CURVES ====================
    with tab2:
        st.markdown("### Training Stress Balance (CTL / ATL / Form)")
        
        if not df_wellness.empty and "ctl" in df_wellness.columns:
            fig_curves = go.Figure()
            
            # CTL
            fig_curves.add_trace(go.Scatter(
                x=df_wellness['date'], y=df_wellness['ctl'],
                mode='lines',
                name='Fitness (CTL)',
                line=dict(color='#2563eb', width=3),
                hovertemplate='Fitness (CTL): %{y:.1f}<extra></extra>'
            ))
            
            # ATL
            fig_curves.add_trace(go.Scatter(
                x=df_wellness['date'], y=df_wellness['atl'],
                mode='lines',
                name='Fatigue (ATL)',
                line=dict(color='#dc2626', width=2, dash='dash'),
                hovertemplate='Fatigue (ATL): %{y:.1f}<extra></extra>'
            ))
            
            # Form (Balance)
            fig_curves.add_trace(go.Scatter(
                x=df_wellness['date'], y=df_wellness['form'],
                mode='lines',
                name='Form (Balance)',
                line=dict(color='#10b981', width=2),
                fill='tozeroy',
                fillcolor='rgba(16, 185, 129, 0.15)',
                hovertemplate='Form (Balance): %{y:.1f}<extra></extra>'
            ))
            
            fig_curves.update_layout(
                template="plotly_dark",
                hovermode="x unified",
                xaxis_title="Date",
                yaxis_title="Stress Value",
                height=450,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=20, r=20, t=60, b=20)
            )
            st.plotly_chart(fig_curves, use_container_width=True)
            
        # Daily TSS color-coded by sport
        if not df_intervals.empty and 'tss' in df_intervals.columns:
            st.markdown("### Daily Training Stress (TSS) by Sport Category")
            fig_tss = px.bar(
                df_intervals, x="date", y="tss",
                color="category",
                color_discrete_map={
                    'Swim': '#0ea5e9',
                    'Bike': '#f97316',
                    'Run': '#ef4444',
                    'Strength': '#a855f7',
                    'Yoga': '#10b981',
                    'Other': '#64748b'
                },
                labels={"date": "Date", "tss": "TSS Load", "category": "Sport"},
                category_orders={"category": ["Swim", "Bike", "Run", "Strength", "Yoga", "Other"]}
            )
            fig_tss.update_layout(
                template="plotly_dark",
                xaxis_title="Date",
                yaxis_title="TSS Contribution",
                height=350,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_tss, use_container_width=True)
        else:
            st.info("No workout loads found. Enter workouts with TSS or HR values in Intervals.icu to plot daily stress logs.")

    # ==================== TAB 3: RECOVERY, WELLNESS & YOGA ====================
    with tab3:
        st.markdown("### Recovery Analytics & Yoga Correlation")
        
        # Yoga Impact Analytics
        if not df_wellness.empty and not df_intervals.empty:
            # Find dates where a Yoga activity was logged
            yoga_dates = set(df_intervals[df_intervals['category'] == 'Yoga']['date'])
            total_yoga_days = len(yoga_dates)
            
            if total_yoga_days > 0:
                df_wellness['has_yoga'] = df_wellness['date'].apply(lambda d: d in yoga_dates)
                
                # Split wellness data
                df_yoga_days = df_wellness[df_wellness['has_yoga']]
                df_no_yoga_days = df_wellness[~df_wellness['has_yoga']]
                
                # Compute averages
                avg_hrv_yoga = df_yoga_days['hrv'].dropna().mean()
                avg_hrv_no_yoga = df_no_yoga_days['hrv'].dropna().mean()
                avg_rhr_yoga = df_yoga_days['restingHR'].dropna().mean()
                avg_rhr_no_yoga = df_no_yoga_days['restingHR'].dropna().mean()
                
                st.markdown(f"""
                    <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px; padding: 20px; margin-bottom: 25px;">
                        <h4 style="margin: 0 0 12px 0; color: #10b981; font-size: 16px;">🧘‍♂️ Yoga Practice Impact (Based on {total_yoga_days} logged sessions)</h4>
                        <p style="margin: 0; font-size: 14px; line-height: 1.5; color: #cbd5e1;">
                            Autonomic nervous system response (HRV) and cardiovascular recovery (Resting Heart Rate) compared on 
                            <strong>Yoga Days</strong> vs. <strong>Non-Yoga Days</strong>:
                        </p>
                        <div style="display: flex; gap: 40px; margin-top: 15px;">
                            <div>
                                <div style="font-size: 12px; text-transform: uppercase; color: #94a3b8; font-weight: 600;">Average HRV (rMSSD)</div>
                                <div style="font-size: 24px; font-weight: 700; color: white;">
                                    {f"{avg_hrv_yoga:.1f} ms" if pd.notna(avg_hrv_yoga) else "--"} 
                                    <span style="font-size: 13px; color: #10b981; font-weight: 600; margin-left: 8px;">
                                        (vs {f"{avg_hrv_no_yoga:.1f} ms" if pd.notna(avg_hrv_no_yoga) else "--"})
                                    </span>
                                </div>
                            </div>
                            <div>
                                <div style="font-size: 12px; text-transform: uppercase; color: #94a3b8; font-weight: 600;">Average Resting HR</div>
                                <div style="font-size: 24px; font-weight: 700; color: white;">
                                    {f"{avg_rhr_yoga:.0f} bpm" if pd.notna(avg_rhr_yoga) else "--"} 
                                    <span style="font-size: 13px; color: #10b981; font-weight: 600; margin-left: 8px;">
                                        (vs {f"{avg_rhr_no_yoga:.0f} bpm" if pd.notna(avg_rhr_no_yoga) else "--"})
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info("💡 Log Yoga sessions in Intervals.icu to analyze how stretching and mindfulness directly correlate with your resting heart rate and HRV.")

        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            # Resting Heart Rate Trend
            if "restingHR" in df_wellness.columns and not df_wellness["restingHR"].dropna().empty:
                fig_rhr = go.Figure()
                fig_rhr.add_trace(go.Scatter(
                    x=df_wellness['date'], y=df_wellness['restingHR'],
                    mode='lines+markers',
                    name='Resting HR',
                    line=dict(color='#ff7f0e', width=3),
                    hovertemplate='Resting HR: %{y:.0f} bpm<extra></extra>'
                ))
                
                rhr_avg = df_wellness["restingHR"].dropna().mean()
                fig_rhr.add_hline(
                    y=rhr_avg, 
                    line_dash="dash", 
                    line_color="#94a3b8",
                    annotation_text=f"Avg ({rhr_avg:.1f} bpm)", 
                    annotation_position="bottom right"
                )
                
                fig_rhr.update_layout(
                    template="plotly_dark",
                    title="Resting Heart Rate (RHR) Trend",
                    xaxis_title="Date",
                    yaxis_title="BPM",
                    height=350,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig_rhr, use_container_width=True)
            else:
                st.info("Resting heart rate data unavailable.")
                
        with col_g2:
            # HRV Trend
            if "hrv" in df_wellness.columns and not df_wellness["hrv"].dropna().empty:
                fig_hrv = go.Figure()
                fig_hrv.add_trace(go.Scatter(
                    x=df_wellness['date'], y=df_wellness['hrv'],
                    mode='lines+markers',
                    name='HRV (rMSSD)',
                    line=dict(color='#10b981', width=3),
                    hovertemplate='HRV: %{y:.0f} ms<extra></extra>'
                ))
                
                hrv_avg = df_wellness["hrv"].dropna().mean()
                fig_hrv.add_hline(
                    y=hrv_avg, 
                    line_dash="dash", 
                    line_color="#94a3b8",
                    annotation_text=f"Avg ({hrv_avg:.1f} ms)", 
                    annotation_position="bottom right"
                )
                
                fig_hrv.update_layout(
                    template="plotly_dark",
                    title="Heart Rate Variability (HRV) Trend",
                    xaxis_title="Date",
                    yaxis_title="rMSSD (ms)",
                    height=350,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig_hrv, use_container_width=True)
            else:
                st.info("Heart Rate Variability (HRV) data unavailable.")
        
        # Row 2: Sleep & Weight Tracker
        col_g3, col_g4 = st.columns(2)
        with col_g3:
            if "sleepSecs" in df_wellness.columns and not df_wellness["sleepSecs"].dropna().empty:
                fig_sleep = go.Figure()
                fig_sleep.add_trace(go.Bar(
                    x=df_wellness['date'], y=df_wellness['sleepSecs'] / 3600.0,
                    name='Sleep Duration',
                    marker_color="rgba(99, 102, 241, 0.5)",
                    hovertemplate='Sleep: %{y:.1f} hrs<extra></extra>'
                ))
                fig_sleep.update_layout(
                    template="plotly_dark",
                    title="Sleep Duration (Hours)",
                    xaxis_title="Date",
                    yaxis_title="Hours",
                    height=300,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig_sleep, use_container_width=True)
            else:
                st.info("Sleep data unavailable.")
                
        with col_g4:
            if "weight" in df_wellness.columns and not df_wellness["weight"].dropna().empty:
                fig_weight = go.Figure()
                fig_weight.add_trace(go.Scatter(
                    x=df_wellness['date'], y=df_wellness['weight'],
                    mode='lines+markers',
                    name='Weight',
                    line=dict(color='#06b6d4', width=2.5),
                    hovertemplate='Weight: %{y:.1f} kg<extra></extra>'
                ))
                fig_weight.update_layout(
                    template="plotly_dark",
                    title="Body Weight (kg) Tracker",
                    xaxis_title="Date",
                    yaxis_title="Weight (kg)",
                    height=300,
                    margin=dict(l=20, r=20, t=60, b=20)
                )
                st.plotly_chart(fig_weight, use_container_width=True)
            else:
                st.info("Weight tracking data unavailable.")

    # ==================== TAB 4: MULTISPORT & STRENGTH LOG ====================
    with tab4:
        st.markdown("### Multisport Training Metrics")
        
        if not df_intervals.empty:
            # Let's create columns for each major category of your priorities
            col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
            
            with col_s1:
                # 🏊‍♂️ SWIM
                swim_df = df_intervals[df_intervals['category'] == 'Swim']
                swim_sessions = len(swim_df)
                swim_dist_m = swim_df['distance'].sum() if 'distance' in swim_df.columns else 0.0
                swim_time_h = swim_df['moving_time_mins'].sum()
                
                st.markdown(f"""
                    <div style="background: rgba(14, 165, 233, 0.05); border: 1px solid rgba(14, 165, 233, 0.2); border-radius: 12px; padding: 15px; text-align: center;">
                        <h4 style="margin: 0; color: #38bdf8; font-size: 15px;">🏊‍♂️ Swimming</h4>
                        <div style="font-size: 24px; font-weight: 700; margin: 8px 0; color: white;">{swim_dist_m:,.0f} m</div>
                        <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                            {swim_sessions} Sessions | {swim_time_h:.1f} hrs
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
            with col_s2:
                # 🚴‍♂️ BIKE
                bike_df = df_intervals[df_intervals['category'] == 'Bike']
                bike_sessions = len(bike_df)
                bike_dist_km = bike_df['distance'].sum() / 1000.0 if 'distance' in bike_df.columns else 0.0
                bike_time_h = bike_df['moving_time_mins'].sum()
                
                st.markdown(f"""
                    <div style="background: rgba(249, 115, 22, 0.05); border: 1px solid rgba(249, 115, 22, 0.2); border-radius: 12px; padding: 15px; text-align: center;">
                        <h4 style="margin: 0; color: #fb923c; font-size: 15px;">🚴‍♂️ Cycling</h4>
                        <div style="font-size: 24px; font-weight: 700; margin: 8px 0; color: white;">{bike_dist_km:,.1f} km</div>
                        <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                            {bike_sessions} Sessions | {bike_time_h:.1f} hrs
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
            with col_s3:
                # 🏃‍♂️ RUN
                run_df = df_intervals[df_intervals['category'] == 'Run']
                run_sessions = len(run_df)
                run_dist_km = run_df['distance'].sum() / 1000.0 if 'distance' in run_df.columns else 0.0
                run_time_h = run_df['moving_time_mins'].sum()
                
                st.markdown(f"""
                    <div style="background: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 12px; padding: 15px; text-align: center;">
                        <h4 style="margin: 0; color: #f87171; font-size: 15px;">🏃‍♂️ Running</h4>
                        <div style="font-size: 24px; font-weight: 700; margin: 8px 0; color: white;">{run_dist_km:,.1f} km</div>
                        <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                            {run_sessions} Sessions | {run_time_h:.1f} hrs
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
            with col_s4:
                # 🏋️‍♂️ STRENGTH
                strength_df = df_intervals[df_intervals['category'] == 'Strength']
                strength_sessions = len(strength_df)
                strength_time_h = strength_df['moving_time_mins'].sum()
                
                st.markdown(f"""
                    <div style="background: rgba(168, 85, 247, 0.05); border: 1px solid rgba(168, 85, 247, 0.2); border-radius: 12px; padding: 15px; text-align: center;">
                        <h4 style="margin: 0; color: #c084fc; font-size: 15px;">🏋️‍♂️ Strength</h4>
                        <div style="font-size: 24px; font-weight: 700; margin: 8px 0; color: white;">{strength_sessions} Lifted</div>
                        <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                            {strength_time_h:.1f} Total Hours
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
            with col_s5:
                # 🧘‍♂️ YOGA
                yoga_df = df_intervals[df_intervals['category'] == 'Yoga']
                yoga_sessions = len(yoga_df)
                yoga_time_h = yoga_df['moving_time_mins'].sum()
                
                st.markdown(f"""
                    <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 12px; padding: 15px; text-align: center;">
                        <h4 style="margin: 0; color: #34d399; font-size: 15px;">🧘‍♂️ Yoga & Stretch</h4>
                        <div style="font-size: 24px; font-weight: 700; margin: 8px 0; color: white;">{yoga_sessions} Sessions</div>
                        <p style="margin: 0; font-size: 12px; color: #94a3b8;">
                            {yoga_time_h:.1f} Total Hours
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
            st.markdown("---")
            
            # Detailed Activity Log
            st.markdown("#### Complete Activity Log")
            
            # Format types using colored HTML badges
            def format_badge(val):
                if val == 'Swim': return '<span class="sport-badge badge-swim">🏊‍♂️ Swim</span>'
                elif val == 'Bike': return '<span class="sport-badge badge-bike">🚴‍♂️ Bike</span>'
                elif val == 'Run': return '<span class="sport-badge badge-run">🏃‍♂️ Run</span>'
                elif val == 'Strength': return '<span class="sport-badge badge-strength">🏋️‍♂️ Strength</span>'
                elif val == 'Yoga': return '<span class="sport-badge badge-yoga">🧘‍♂️ Yoga</span>'
                else: return '<span class="sport-badge badge-other">⚙️ Other</span>'

            # Apply conversions and mapping to table
            df_log = df_intervals.copy()
            
            # Formatted column values for displaying inside dataframe
            cols_to_format = {}
            for col, fmt in {
                'distance': '{:.1f} m',
                'distance_formatted': '{:.1f} km/m',
                'moving_time_mins': '{:.1f} hrs',
                'tss': '{:.0f}',
                'np': '{:.0f} W',
                'avg_power': '{:.0f} W',
                'avg_hr': '{:.0f} bpm',
                'max_hr': '{:.0f} bpm',
                'work_kj': '{:.0f} kJ',
                'elevation_gain_m': '{:.0f} m'
            }.items():
                if col in df_log.columns:
                    cols_to_format[col] = lambda x, f=fmt: f.format(x) if pd.notna(x) else "--"
                    
            # Order log chronologically descending
            df_log = df_log.sort_values("date", ascending=False)
            
            # Customize columns in order
            cols_show = ['date', 'category', 'name', 'moving_time_mins', 'distance', 'tss', 'avg_power', 'avg_hr']
            existing_show = [c for c in cols_show if c in df_log.columns]
            
            # Convert categories to badges and render via markdown/HTML if needed,
            # or just show them in the Streamlit dataframe
            st.dataframe(
                df_log[existing_show].style.format(cols_to_format),
                use_container_width=True
            )
        else:
            st.info("No activities found in this date range. Check your Intervals.icu ride, run, swim, and session logs.")
else:
    # Landing Page State (no credentials loaded yet)
    st.markdown("""
        <div style="background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 30px; text-align: center; margin-top: 40px;">
            <h3>🏊‍♂️ Dashboard State: Idle</h3>
            <p style="color: #94a3b8; max-width: 600px; margin: 10px auto;">
                Data is not loaded. Please configure your Intervals.icu credentials in the .env file.
            </p>
        </div>
    """, unsafe_allow_html=True)

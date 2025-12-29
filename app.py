import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.io.wavfile import write
from datetime import datetime
import io

# --- 1. 頁面全域設定 (模擬 App 沉浸感) ---
st.set_page_config(page_title="Rap Trainer", page_icon="🎤", layout="centered")

# 注入 CSS 樣式：隱藏多餘選單，放大 BPM 字體，模擬 App 介面
st.markdown("""
    <style>
    /* 隱藏 Streamlit 預設漢堡選單與 Footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 調整主要容器寬度，更像手機 App */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        max_width: 600px;
    }
    
    /* 讓 BPM 數字變得超大 (Soundbrenner 風格) */
    [data-testid="stMetricValue"] {
        font-size: 70px !important;
        font-weight: 700 !important;
        color: #00E676 !important; /* 螢光綠 */
        text-align: center !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 20px !important;
        text-align: center !important;
        color: #888888 !important;
    }
    
    /* 讓 Slider 看起來更寬 */
    .stSlider {
        padding-top: 20px;
        padding-bottom: 20px;
    }
    
    /* 按鈕樣式優化 */
    .stButton button {
        width: 100%;
        border-radius: 25px;
        height: 50px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心邏輯層 ---
class RapTrainerApp:
    def __init__(self):
        # 初始化：從零開始，不生成假數據
        if 'history' not in st.session_state:
            # 建立空的 DataFrame
            st.session_state.history = pd.DataFrame(columns=['Date', 'BPM', 'SPS', 'Focus', 'Duration'])
            
        self.target_bpm = 120 

    def calculate_sps(self, bpm, subdivision=4):
        return (bpm * subdivision) / 60

    def generate_metronome(self, bpm, duration_sec, ghost_mode=False):
        sample_rate = 44100
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
        audio_track = np.zeros_like(t)
        
        beat_interval = 60.0 / bpm
        samples_per_beat = int(sample_rate * beat_interval)
        
        # 製作聲音 (正弦波)
        def make_click(freq, dur=0.05):
            return 0.5 * np.sin(2 * np.pi * freq * np.linspace(0, dur, int(sample_rate * dur)))

        high_click = make_click(1200) # 強拍
        low_click = make_click(800)   # 弱拍
        
        total_samples = len(audio_track)
        current_sample = 0
        beat_count = 0
        bar_count = 1
        
        while current_sample < total_samples:
            # Ghost Mode: 每 4 小節，第 4 小節靜音
            is_ghost_bar = ghost_mode and (bar_count % 4 == 0)
            
            if not is_ghost_bar:
                click = high_click if beat_count % 4 == 0 else low_click
                if current_sample + len(click) < total_samples:
                    audio_track[current_sample:current_sample+len(click)] += click
            
            current_sample += samples_per_beat
            beat_count += 1
            if beat_count % 4 == 0:
                bar_count += 1
                
        audio_track = np.int16(audio_track * 32767)
        virtual_file = io.BytesIO()
        write(virtual_file, sample_rate, audio_track)
        return virtual_file

    def add_log(self, bpm, focus, duration):
        new_entry = pd.DataFrame([{
            'Date': datetime.now(),
            'BPM': bpm,
            'SPS': self.calculate_sps(bpm),
            'Focus': focus,
            'Duration': duration
        }])
        st.session_state.history = pd.concat([st.session_state.history, new_entry], ignore_index=True)

app = RapTrainerApp()

# --- 3. UI 介面層 (仿 Soundbrenner) ---

# 頂部：標題
st.markdown("<h2 style='text-align: center; color: white;'>Rap Trainer Pro</h2>", unsafe_allow_html=True)

# 核心控制區 (放在中間，方便拇指操作)
col_center = st.container()

with col_center:
    # 1. 巨大的 BPM 顯示
    # 這裡我們用 session_state 來記住 BPM，這樣滑桿和手動輸入可以同步
    if 'bpm' not in st.session_state:
        st.session_state.bpm = 85
        
    current_bpm = st.session_state.bpm
    sps = app.calculate_sps(current_bpm)
    
    # 顯示大數字 BPM
    st.metric(label="BPM (Beats Per Minute)", value=current_bpm, delta=f"{sps:.1f} SPS (音節/秒)")

    # 2. 滑桿 (模擬轉盤)
    new_bpm = st.slider("", 60, 160, current_bpm, key="bpm_slider", label_visibility="collapsed")
    if new_bpm != current_bpm:
        st.session_state.bpm = new_bpm
        st.rerun()

    # 3. 功能設定 (用 Expander 收納，保持介面乾淨)
    with st.expander("⚙️ 節拍設定 (Ghost Mode / 時長)"):
        duration = st.slider("練習時長 (秒)", 10, 300, 30)
        ghost_mode = st.toggle("👻 啟用 Ghost Mode (幽靈小節)")
        st.caption("Ghost Mode 會每 3 小節後靜音 1 小節，訓練你的內在時鐘。")

    # 4. 播放按鈕 (生成音頻)
    if st.button("▶️ 生成節拍音頻", type="primary"):
        audio_file = app.generate_metronome(current_bpm, duration, ghost_mode)
        st.audio(audio_file, format='audio/wav')
        
    st.markdown("---")

    # 5. 快速打卡區
    st.markdown("<h4 style='text-align: center;'>練習結束了嗎？</h4>", unsafe_allow_html=True)
    col_log1, col_log2 = st.columns([2, 1])
    with col_log1:
        focus = st.selectbox("本次重點", ["基礎律動", "咬字清晰度", "三連音 Flow", "快嘴衝刺", "Freestyle"], label_visibility="collapsed")
    with col_log2:
        if st.button("📝 打卡"):
            app.add_log(current_bpm, focus, duration)
            st.success("已記錄！")
            st.rerun()

# --- 4. 底部：數據概覽 (僅在有數據時顯示) ---
if not st.session_state.history.empty:
    st.markdown("---")
    st.markdown("<h3 style='text-align: center;'>近期表現</h3>", unsafe_allow_html=True)
    
    # 準備繪圖數據
    df = st.session_state.history
    
    # 使用 Matplotlib 繪製 Dark Mode 圖表
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(6, 3)) # 手機版圖表小一點
    
    # 因為是時間序列，我們只畫最後 10 筆以免太擠
    recent_df = df.tail(10).reset_index(drop=True)
    
    ax.plot(recent_df.index, recent_df['BPM'], color='#00E676', marker='o', linewidth=2, label='BPM')
    ax.axhline(y=120, color='#FF5252', linestyle='--', linewidth=1, label='目標 (120)')
    
    # 圖表美化
    ax.set_facecolor('#0e1117') # 配合 Streamlit 背景
    fig.patch.set_facecolor('#0e1117')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#444')
    ax.tick_params(colors='gray')
    ax.set_ylabel("BPM", color='gray')
    
    st.pyplot(fig)
    
    # 顯示簡單表格
    st.dataframe(
        recent_df[['Date', 'BPM', 'SPS', 'Focus']].sort_values(by='Date', ascending=False),
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("尚無記錄。點擊上方「打卡」按鈕開始你的第一筆訓練！")

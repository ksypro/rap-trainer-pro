import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.io.wavfile import write
from datetime import datetime, timedelta
import io

# --- 1. 設定頁面配置 (必須在第一行) ---
st.set_page_config(page_title="Rap Trainer Pro", page_icon="🎤", layout="wide")

# --- 2. 核心邏輯類別 (Backend Logic) ---
class RapTrainerApp:
    def __init__(self):
        # 模擬數據生成 (如果沒有歷史記錄)
        if 'history' not in st.session_state:
            dates = [datetime.now() - timedelta(days=i) for i in range(10, 0, -1)]
            data = {
                'Date': dates,
                'BPM': np.random.randint(75, 95, size=10).tolist(), # 模擬進步
                'SPS': [x * 4 / 60 for x in np.random.randint(75, 95, size=10)],
                'Focus': ['基礎', '三連音', '清晰度', '呼吸', '加速'] * 2
            }
            # 強制最後一次練習數據以便展示
            data['BPM'][-1] = 92
            st.session_state.history = pd.DataFrame(data)
            
        self.target_bpm = 120 # 快嘴目標

    def calculate_sps(self, bpm, subdivision=4):
        """計算每秒音節數 (SPS)"""
        return (bpm * subdivision) / 60

    def generate_metronome(self, bpm, duration_sec, ghost_mode=False):
        """
        生成節拍器音頻
        Ghost Mode: 每 4 個小節，第 4 小節靜音
        """
        sample_rate = 44100
        t = np.linspace(0, duration_sec, int(sample_rate * duration_sec), endpoint=False)
        
        # 基礎音頻軌道 (靜音)
        audio_track = np.zeros_like(t)
        
        # 計算參數
        beat_interval = 60.0 / bpm
        samples_per_beat = int(sample_rate * beat_interval)
        samples_per_bar = samples_per_beat * 4 # 假設 4/4 拍
        
        # 製作 "滴" (高頻) 和 "答" (低頻)
        def make_click(freq, dur=0.05):
            return 0.5 * np.sin(2 * np.pi * freq * np.linspace(0, dur, int(sample_rate * dur)))

        high_click = make_click(1200) # 第一拍
        low_click = make_click(800)   # 其他拍
        
        # 填充節拍
        total_samples = len(audio_track)
        current_sample = 0
        beat_count = 0
        bar_count = 1
        
        while current_sample < total_samples:
            # Ghost Mode 邏輯: 如果開啟，且是第 4 小節，則跳過聲音填充 (但時間繼續走)
            is_ghost_bar = ghost_mode and (bar_count % 4 == 0)
            
            if not is_ghost_bar:
                # 判斷是重拍還是弱拍
                click = high_click if beat_count % 4 == 0 else low_click
                
                # 確保不超出陣列範圍
                if current_sample + len(click) < total_samples:
                    audio_track[current_sample:current_sample+len(click)] += click
            
            # 更新計數
            current_sample += samples_per_beat
            beat_count += 1
            if beat_count % 4 == 0:
                bar_count += 1
                
        # 轉換為 16-bit PCM 格式以供播放
        audio_track = np.int16(audio_track * 32767)
        
        # 寫入 BytesIO 物件 (不存硬碟，直接在記憶體處理)
        virtual_file = io.BytesIO()
        write(virtual_file, sample_rate, audio_track)
        return virtual_file

    def add_log(self, bpm, focus):
        """新增練習記錄"""
        new_entry = {
            'Date': datetime.now(),
            'BPM': bpm,
            'SPS': self.calculate_sps(bpm),
            'Focus': focus
        }
        st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([new_entry])], ignore_index=True)

# --- 3. 初始化 App ---
app = RapTrainerApp()

# --- 4. 前端介面設計 (UI Layout) ---
st.title("🎤 Rap Trainer Pro")
st.markdown("### From Novice to Chopper | 你的快嘴訓練中心")

# 側邊欄：控制面板
with st.sidebar:
    st.header("🎛️ 節拍器設定")
    bpm_input = st.slider("BPM (速度)", 60, 160, 90)
    duration_input = st.slider("練習時長 (秒)", 10, 120, 30)
    ghost_mode = st.checkbox("👻 啟用 Ghost Mode (幽靈小節)", help="每 4 小節會靜音 1 小節，訓練內在節奏感")
    
    st.markdown("---")
    st.header("📝 練習打卡")
    focus_input = st.selectbox("今日重點", ["咬字清晰度", "三連音 Flow", "氣息控制", "雙倍速 (Double Time)", "Freestyle"])
    if st.button("✅ 完成練習並打卡"):
        app.add_log(bpm_input, focus_input)
        st.success(f"已記錄！BPM: {bpm_input} | 重點: {focus_input}")

# 主畫面：數據儀表板
col1, col2 = st.columns(2)

# 指標卡片
current_sps = app.calculate_sps(bpm_input)
with col1:
    st.metric(label="目前設定 BPM", value=bpm_input, delta=f"{bpm_input - 120} 與目標差距")
with col2:
    st.metric(label="預估語速 (SPS)", value=f"{current_sps:.1f} 音節/秒", help="以 16 分音符 (1/4) 計算")

# 音頻播放區
st.markdown("### 🎧 節拍器試聽")
if st.button("▶️ 生成並播放節拍"):
    audio_file = app.generate_metronome(bpm_input, duration_input, ghost_mode)
    st.audio(audio_file, format='audio/wav')
    if ghost_mode:
        st.info("👻 Ghost Mode 已啟用：注意聽，第 4 小節會消失，請保持你的 Rap 不斷！")

# 圖表區 (Matplotlib Dark Mode)
st.markdown("---")
st.markdown("### 📈 進步軌跡")

# 準備數據
df = st.session_state.history
fig, ax = plt.subplots(figsize=(10, 4))

# 設定 iOS Dark Mode 風格
plt.style.use('dark_background')
ax.set_facecolor('#1e1e1e')
fig.patch.set_facecolor('#0e1117')

# 畫圖
ax.plot(df['Date'], df['BPM'], color='#00ff41', marker='o', linewidth=2, label='你的進度')
ax.axhline(y=120, color='#ff0055', linestyle='--', linewidth=2, label='Chopper 目標 (120)')

# 裝飾
ax.set_title("BPM 成長曲線", color='white', fontsize=12)
ax.set_ylabel("BPM", color='gray')
ax.grid(color='#333333', linestyle=':', alpha=0.5)
ax.legend(facecolor='#1e1e1e', labelcolor='white')
plt.xticks(rotation=45, color='gray')
plt.yticks(color='gray')

# 在 Streamlit 中顯示圖表
st.pyplot(fig)

# 顯示最近記錄
with st.expander("查看詳細數據日誌"):
    st.dataframe(df.sort_values(by='Date', ascending=False).style.format({"BPM": "{:.0f}", "SPS": "{:.2f}"}))
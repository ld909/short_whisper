import subprocess
import os


def apply_audiobook_enhancement(
    input_file,
    output_file,
    eq_low_freq_hz=150,
    eq_low_gain_db=3,
    eq_low_q=1.0,
    comp_threshold_db=-18,
    comp_ratio=2.5,
    comp_attack_ms=5,
    comp_decay_ms=50,
    comp_makeup_db=2,
    vs_layout="5.1",
    vs_angle=25,
    sw_delay_ms=20,
    sw_feedback_pct=20,
    sw_crossfeed_pct=30,
    sw_drymix_pct=70,
    use_subtle_reverb=False,
    reverb_delay_ms=20,
    reverb_decay=0.1,
    reverb_wet_gain_db=-18,
):
    """
    Applies effects to an audiobook to simulate close-mic, wide, and surround sound.

    Args:
        input_file (str): Path to the input audio file (MP3 or WAV).
        output_file (str): Path to save the processed audio file.

        # Equalizer for Proximity Effect
        eq_low_freq_hz (float): Center frequency for low-frequency boost (e.g., 120-200 Hz).
        eq_low_gain_db (float): Gain for the low-frequency boost (e.g., 2-5 dB).
        eq_low_q (float): Q factor for the EQ band (e.g., 0.7-1.5).

        # Compressor for Intimacy and Clarity
        comp_threshold_db (float): Compressor threshold (e.g., -18 dBFS).
        comp_ratio (float): Compression ratio (e.g., 2:1 to 4:1).
        comp_attack_ms (float): Compressor attack time in ms (e.g., 3-10 ms).
        comp_decay_ms (float): Compressor decay (release) time in ms (e.g., 50-150 ms).
        comp_makeup_db (float): Makeup gain after compression (e.g., 0-4 dB).

        # Virtual Surround
        vs_layout (str): Virtual speaker layout (e.g., "5.1", "7.1", "stereo" for basic HRTF).
        vs_angle (float): Listener's angle relative to front-center (degrees, e.g., 20-35).

        # Stereo Widener (optional, virtualsurround might be enough)
        sw_delay_ms (float): Delay for widening effect (e.g., 15-30 ms).
        sw_feedback_pct (float): Feedback percentage (0-100).
        sw_crossfeed_pct (float): Crossfeed percentage (0-100).
        sw_drymix_pct (float): Percentage of dry (original stereo) signal (0-100). Wet is (100-drymix).

        # Subtle Reverb (use with extreme caution for audiobooks)
        use_subtle_reverb (bool): Whether to apply a very subtle reverb.
        reverb_delay_ms (float): Pre-delay for reverb (e.g., 10-30 ms).
        reverb_decay (float): Reverb decay factor (0-1, e.g., 0.1-0.3 for short ambience).
        reverb_wet_gain_db (float): Gain of the wet (reverberated) signal (e.g., -15 to -25 dB).
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return False

    filters = []

    # 1. Equalizer for proximity effect (low-frequency boost)
    #    Using 'superequalizer' for more precise Q control if needed, or 'equalizer'.
    #    For 'equalizer': f=freq:width_type=q:w=Q:g=gain
    filters.append(
        f"equalizer=f={eq_low_freq_hz}:width_type=q:w={eq_low_q}:g={eq_low_gain_db}"
    )

    # 2. Compressor for intimacy and to control dynamics
    #    Format: compand=attacks=A:decays=D:points=p1|p2|..:soft-knee=K:gain=G
    #    Points: in-level(dBFS)/out-level(dBFS)
    #    A simple setup for downward compression above threshold:
    #    -90/-90 (no change for very quiet sounds)
    #    threshold_db / (threshold_db + (target_loudness - threshold_db)/ratio)
    #    0 / (0 + (target_output_at_0dBFS_input - 0)/ratio)
    #    This example uses a more general compand string for voice:
    #    It sets up points for a compression curve.
    #    -90/-90 means anything below -90dB remains unchanged.
    #    comp_threshold_db / comp_threshold_db means no change up to the threshold.
    #    0 / ( (0 - comp_threshold_db) / comp_ratio + comp_threshold_db ) is output at 0dBFS input
    #    Example points for gentle compression: -90/-90|{comp_threshold_db}/{comp_threshold_db}|0/{(0-comp_threshold_db)/comp_ratio + comp_threshold_db}
    #    A more common compand setup for general voice:
    comp_points = f"-90/-90|{comp_threshold_db}/{comp_threshold_db}|0/{(0-comp_threshold_db)/comp_ratio + comp_threshold_db}"
    filters.append(
        f"compand=attacks={comp_attack_ms/1000}:decays={comp_decay_ms/1000}:points={comp_points}:soft-knee=6:gain={comp_makeup_db}"
    )

    # 3. Virtual Surround - 移除了不可用的virtualsurround滤镜
    # 如果音频是单声道，添加立体声转换
    filters.append("channelmap=stereo")

    # 4. Stereo Widener (apply after virtualsurround has created a stereo image)
    #    Parameters for stereowiden: delay, feedback, crossfeed, drymix
    #    drymix is 0-1, so convert percentage.
    filters.append(
        f"stereowiden=delay={sw_delay_ms}:feedback={sw_feedback_pct/100}:crossfeed={sw_crossfeed_pct/100}:drymix={sw_drymix_pct/100}"
    )

    # 5. Subtle Reverb (Optional and use with extreme caution)
    if use_subtle_reverb:
        # areverb parameters: delays, decay, decay_color, room_size, wet_gain, dry_gain, etc.
        # For a very short, almost imperceptible ambience:
        filters.append(
            f"areverb=delays={reverb_delay_ms/1000}:decay={reverb_decay}:wet_gain={reverb_wet_gain_db}:dry_gain=0"
        )  # dry_gain=0 because it's additive

    ffmpeg_filter_string = ",".join(filters)

    command = [
        "ffmpeg",
        "-i",
        input_file,
        "-af",
        ffmpeg_filter_string,
        "-y",  # Overwrite output file if it exists
        output_file,
    ]

    try:
        print(f"Processing '{input_file}' to '{output_file}'...")
        print(f"Applying FFmpeg filter chain: {ffmpeg_filter_string}")
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if process.stderr:
            print("FFmpeg output (stderr):\n", process.stderr)
        if process.stdout:  # Less common for ffmpeg to use stdout for progress
            print("FFmpeg output (stdout):\n", process.stdout)
        print(f"Successfully processed. Output saved to '{output_file}'")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during FFmpeg processing for '{input_file}':")
        print("Command:", " ".join(e.cmd))
        print("Return code:", e.returncode)
        if e.stdout:
            print("Stdout:", e.stdout)
        if e.stderr:
            print("Stderr:", e.stderr)
        return False
    except FileNotFoundError:
        print(
            "Error: FFmpeg command not found. Please ensure FFmpeg is installed and in your system's PATH."
        )
        return False


# --- Example Usage ---
input_audiobook = "./en-default.wav"  # <--- 替换为你的音频文件
output_enhanced_audiobook = "./en-default-enhanced.wav"

# 确保输入文件存在
if not os.path.exists(input_audiobook):
    print(f"错误: 示例输入文件 '{input_audiobook}' 未找到。")
    print("请将 'your_audiobook_segment.mp3' 替换为你的实际音频文件路径。")
    # 你可能需要创建一个虚拟文件用于测试，如果 pydub 已安装:
    # from pydub import AudioSegment
    # from pydub.generators import Sine
    # if not os.path.exists(input_audiobook) and input_audiobook == "your_audiobook_segment.mp3":
    #     AudioSegment.silent(duration=5000).overlay(Sine(440).to_audio_segment(duration=5000, volume=-12)).export(input_audiobook, format="mp3")
    #     print(f"创建了一个虚拟文件 '{input_audiobook}' 用于测试。")
else:
    print(f"准备处理文件: {input_audiobook}")
    success = apply_audiobook_enhancement(
        input_audiobook,
        output_enhanced_audiobook,
        # --- 你需要仔细调整这些参数！ ---
        # 近麦克风感 (EQ + Compression)
        eq_low_freq_hz=160,  # 提升的低频中心点 (Hz)
        eq_low_gain_db=3.5,  # 低频提升量 (dB)
        eq_low_q=1.2,  # EQ 带宽控制 (Q值)
        comp_threshold_db=-20,  # 压缩器阈值 (dBFS)
        comp_ratio=3.0,  # 压缩比 (例如 3:1)
        comp_attack_ms=5,  # 压缩启动时间 (ms)
        comp_decay_ms=80,  # 压缩释放时间 (ms)
        comp_makeup_db=2,  # 压缩后的补偿增益 (dB)
        # 环绕和宽度
        vs_layout="5.1",  # 虚拟环绕布局 ("stereo" 也可以试试，效果不同)
        vs_angle=30,  # 听者角度
        sw_delay_ms=25,  # 立体声扩展延迟
        sw_feedback_pct=15,
        sw_crossfeed_pct=25,
        sw_drymix_pct=65,  # 原始立体声信号比例 (dry/wet 平衡)
        # 极微弱混响 (默认关闭，如果开启，参数要非常非常小)
        use_subtle_reverb=False,  # 设置为 True 来启用，但要非常小心
        reverb_delay_ms=15,
        reverb_decay=0.08,  # 非常短的衰减
        reverb_wet_gain_db=-20,  # 非常低的混响音量
    )

    if success:
        print(f"增强处理完成。检查输出文件: {output_enhanced_audiobook}")
    else:
        print("增强处理失败。")

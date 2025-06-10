from pydub import AudioSegment
import os

def adjust_mp3_volume(input_mp3_path, output_mp3_path, gain_db):
    """
    调整 MP3 文件的音量。

    参数:
    input_mp3_path (str): 输入 MP3 文件的路径。
    output_mp3_path (str): 输出调整音量后 MP3 文件的路径。
    gain_db (float): 要增加的音量，单位是分贝 (dB)。
                     正值表示增大音量，负值表示减小音量。
    """
    try:
        # 检查输入文件是否存在
        if not os.path.exists(input_mp3_path):
            print(f"错误：输入文件 '{input_mp3_path}' 不存在。")
            return

        print(f"正在加载音频文件: {input_mp3_path} ...")
        # 从 MP3 文件加载音频
        audio = AudioSegment.from_mp3(input_mp3_path)

        # 调整音量
        # audio.dBFS 可以获取当前音频的平均响度（近似值，更准确的是峰值）
        # audio.max_dBFS 可以获取当前音频的峰值响度
        print(f"原始音频峰值响度: {audio.max_dBFS:.2f} dBFS")

        louder_audio = audio + gain_db # 或者使用 audio.apply_gain(gain_db)

        print(f"调整后音频峰值响度 (预计): {louder_audio.max_dBFS:.2f} dBFS")

        # 检查是否可能发生削波 (clipping)
        # 0 dBFS 是数字音频的最大可能响度，超过它就会发生削波，导致失真。
        # 最好让峰值保持在 0 dBFS 以下，例如 -0.5 dBFS 或 -1 dBFS。
        if louder_audio.max_dBFS > -0.1: # 给一点点余量
            print(f"警告：调整后的音频峰值响度为 {louder_audio.max_dBFS:.2f} dBFS，可能非常接近或超过 0 dBFS，有削波风险！")
            print("建议减小 gain_db 的值。")


        print(f"正在导出调整后的音频到: {output_mp3_path} ...")
        # 导出调整后的音频为 MP3
        # 可以指定比特率，例如 bitrate="192k"
        louder_audio.export(output_mp3_path, format="mp3")
        print("音量调整完成！")

    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        print("请确保 FFmpeg 已正确安装并已添加到系统 PATH 环境变量中。")

# --- 使用示例 ---
if __name__ == "__main__":
    # 设置你的文件路径和音量调整值
    input_file = "./11.mp3"  # <--- 修改这里：你的音量较小的MP3文件路径
    output_file = "./11_larger.mp3" # <--- 修改这里：输出文件的路径
    volume_increase_db = 6.0  # <--- 修改这里：你希望增加多少分贝 (例如 3dB, 6dB)

    # 确保路径中的反斜杠被正确处理，或者使用正斜杠
    # 例如 Windows: "C:\\Users\\YourName\\Music\\quieter.mp3"
    # 或者: "C:/Users/YourName/Music/quieter.mp3"

    # --- 自动标准化到一个目标峰值 (更推荐的方法) ---
    # 如果你想将音频标准化到一个特定的峰值响度，而不是简单地增加固定dB
    # 例如，将峰值响度标准化到 -1.0 dBFS (避免削波)
    try:
        print(f"尝试标准化 '{input_file}'...")
        song_to_normalize = AudioSegment.from_mp3(input_file)
        target_peak_dbfs = 2     # 目标峰值响度，-1.0 dBFS 是一个安全的值
        
        # 计算需要增加的dB值
        change_in_dbfs = target_peak_dbfs - song_to_normalize.max_dBFS
        
        print(f"当前峰值: {song_to_normalize.max_dBFS:.2f} dBFS")
        print(f"目标峰值: {target_peak_dbfs:.2f} dBFS")
        print(f"需要调整: {change_in_dbfs:.2f} dB")

        if change_in_dbfs > 0: # 只有当需要增大音量时才调整
            normalized_song = song_to_normalize.apply_gain(change_in_dbfs)
            output_normalized_file = "./11_normalized_2.mp3" # <--- 修改这里
            normalized_song.export(output_normalized_file, format="mp3")
            print(f"已将 '{input_file}' 标准化到峰值 {target_peak_dbfs} dBFS, 输出到 '{output_normalized_file}'")
            print(f"标准化后音频峰值: {normalized_song.max_dBFS:.2f} dBFS")
        else:
            print(f"音频 '{input_file}' 已经足够响亮或比目标更响，无需调整。")

    except Exception as e:
        print(f"标准化过程中发生错误: {e}")
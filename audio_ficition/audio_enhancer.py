#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import numpy as np
import soundfile as sf
from scipy.io import wavfile
from pydub import AudioSegment
import os
import tempfile
import time

class AudioEnhancer:
    def __init__(self, 
                 rms_peak=0.2,
                 attack_ms=25.0,
                 release_ms=100.0,
                 threshold_db=-11.0,
                 ratio=4.0,
                 knee_db=5.0,
                 makeup_gain_db=7.0):
        """
        初始化音频增强器参数
        
        参数:
            rms_peak (float): RMS/peak比例
            attack_ms (float): 压缩器响应时间(毫秒)
            release_ms (float): 压缩器释放时间(毫秒)
            threshold_db (float): 压缩阈值(dB)
            ratio (float): 压缩比
            knee_db (float): 拐点半径(dB)
            makeup_gain_db (float): 补偿增益(dB)
        """
        self.rms_peak = rms_peak
        self.attack_ms = attack_ms / 1000.0  # 转换为秒
        self.release_ms = release_ms / 1000.0  # 转换为秒
        self.threshold_db = threshold_db
        self.threshold = 10 ** (threshold_db / 20)
        self.ratio = ratio
        self.knee_db = knee_db
        self.knee_width = 2 * knee_db
        self.makeup_gain_db = makeup_gain_db
        self.makeup_gain = 10 ** (makeup_gain_db / 20)
        
    def _convert_to_mono_if_needed(self, audio_data):
        """如果是立体声，转换为单声道"""
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            return np.mean(audio_data, axis=1)
        return audio_data
    
    def _db_to_linear(self, db):
        """将dB值转换为线性值"""
        return 10 ** (db / 20)
    
    def _linear_to_db(self, linear):
        """将线性值转换为dB值"""
        return 20 * np.log10(max(linear, 1e-5))
    
    def _apply_compression(self, audio_data, sample_rate):
        """应用动态压缩"""
        # 确保音频是单声道的
        mono_audio = self._convert_to_mono_if_needed(audio_data)
        
        # 计算包络
        attack_samples = int(self.attack_ms * sample_rate)
        release_samples = int(self.release_ms * sample_rate)
        
        # 初始化增益跟踪
        gain_reduction = np.zeros_like(mono_audio, dtype=np.float32)
        
        # 计算每个样本的增益衰减
        for i in range(len(mono_audio)):
            # 获取当前样本电平(绝对值)
            level = abs(mono_audio[i])
            level_db = self._linear_to_db(level)
            
            # 检查是否超过阈值
            if level_db > self.threshold_db:
                # 计算拐点压缩
                if level_db <= self.threshold_db + self.knee_db:
                    # 在拐点区域内的软压缩
                    knee_factor = (level_db - self.threshold_db + self.knee_db/2) / self.knee_width
                    gain_reduction_db = ((self.ratio - 1) * knee_factor**2 * self.knee_width/2)
                else:
                    # 超过拐点的硬压缩
                    gain_reduction_db = (level_db - self.threshold_db) * (1 - 1/self.ratio)
                
                target_gain = self._db_to_linear(-gain_reduction_db)
            else:
                target_gain = 1.0
            
            # 应用时间常数 (attack/release)
            if i > 0:
                if target_gain < gain_reduction[i-1]:  # 需要更多压缩 (攻击阶段)
                    coeff = np.exp(-1 / (attack_samples))
                    gain_reduction[i] = coeff * gain_reduction[i-1] + (1 - coeff) * target_gain
                else:  # 需要减少压缩 (释放阶段)
                    coeff = np.exp(-1 / (release_samples))
                    gain_reduction[i] = coeff * gain_reduction[i-1] + (1 - coeff) * target_gain
            else:
                gain_reduction[i] = target_gain
        
        # 应用补偿增益
        compressed_audio = mono_audio * gain_reduction * self.makeup_gain
        
        # 规范化为[-1, 1]范围
        max_val = np.max(np.abs(compressed_audio))
        if max_val > 1.0:
            compressed_audio = compressed_audio / max_val * self.rms_peak
        
        return compressed_audio
    
    def process_file(self, input_file, output_file):
        """处理音频文件"""
        print(f"处理文件: {input_file}")
        
        # 检查文件扩展名
        _, ext = os.path.splitext(input_file)
        ext = ext.lower()
        
        if ext == '.mp3':
            # 将MP3转换为临时WAV文件
            temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_wav.close()
            
            audio = AudioSegment.from_mp3(input_file)
            audio.export(temp_wav.name, format="wav")
            
            # 读取WAV文件
            sample_rate, audio_data = wavfile.read(temp_wav.name)
            
            # 转换为浮点数范围[-1, 1]
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483648.0
            
            # 删除临时WAV文件
            os.unlink(temp_wav.name)
            
        elif ext == '.wav':
            # 直接读取WAV文件
            sample_rate, audio_data = wavfile.read(input_file)
            
            # 转换为浮点数范围[-1, 1]
            if audio_data.dtype == np.int16:
                audio_data = audio_data.astype(np.float32) / 32768.0
            elif audio_data.dtype == np.int32:
                audio_data = audio_data.astype(np.float32) / 2147483648.0
                
        else:
            raise ValueError(f"不支持的文件格式: {ext}. 请使用MP3或WAV文件。")
        
        # 应用音频处理
        enhanced_audio = self._apply_compression(audio_data, sample_rate)
        
        # 保存为临时WAV文件
        temp_output = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_output.close()
        
        # 确保enhanced_audio是浮点数范围[-1, 1]
        sf.write(temp_output.name, enhanced_audio, sample_rate)
        
        # 转换为MP3
        wav_audio = AudioSegment.from_wav(temp_output.name)
        wav_audio.export(output_file, format="mp3")
        
        # 删除临时文件
        os.unlink(temp_output.name)
        
        print(f"增强的音频已保存至: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='音频增强工具')
    parser.add_argument('input_file', help='输入音频文件路径 (MP3或WAV)')
    parser.add_argument('output_file', help='输出音频文件路径 (MP3)')
    parser.add_argument('--rms-peak', type=float, default=0.2, help='RMS/peak比例 (默认: 0.2)')
    parser.add_argument('--attack', type=float, default=25.0, help='攻击时间(毫秒) (默认: 25.0)')
    parser.add_argument('--release', type=float, default=100.0, help='释放时间(毫秒) (默认: 100.0)')
    parser.add_argument('--threshold', type=float, default=-11.0, help='阈值(dB) (默认: -11.0)')
    parser.add_argument('--ratio', type=float, default=4.0, help='压缩比 (默认: 4.0)')
    parser.add_argument('--knee', type=float, default=5.0, help='拐点半径(dB) (默认: 5.0)')
    parser.add_argument('--makeup-gain', type=float, default=7.0, help='补偿增益(dB) (默认: 7.0)')
    
    args = parser.parse_args()
    
    enhancer = AudioEnhancer(
        rms_peak=args.rms_peak,
        attack_ms=args.attack,
        release_ms=args.release,
        threshold_db=args.threshold,
        ratio=args.ratio,
        knee_db=args.knee,
        makeup_gain_db=args.makeup_gain
    )
    
    start_time = time.time()
    enhancer.process_file(args.input_file, args.output_file)
    end_time = time.time()
    
    print(f"处理时间: {end_time - start_time:.2f} 秒")

if __name__ == "__main__":
    main() 
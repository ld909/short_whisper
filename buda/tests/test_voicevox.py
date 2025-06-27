#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VOICEVOX 测试脚本
用于调用 VOICEVOX 生成测试 MP3 文件

依赖:
- voicevox-client
- pydub (用于音频转换)
- ffmpeg (音频处理后端)

使用方法:
1. 启动 VOICEVOX Engine (通过 Docker 或直接运行)
2. 运行此脚本测试语音合成
"""

import os
import sys
import asyncio
import argparse
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("voicevox_test.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """检查必要的依赖是否已安装"""
    logger.info("检查依赖...")

    missing_deps = []

    # 检查 voicevox-client
    try:
        import voicevox

        logger.info("✅ voicevox-client 已安装")
    except ImportError:
        missing_deps.append("voicevox-client")
        logger.error("❌ voicevox-client 未安装")

    # 检查 pydub
    try:
        from pydub import AudioSegment

        logger.info("✅ pydub 已安装")
    except ImportError:
        missing_deps.append("pydub")
        logger.error("❌ pydub 未安装")

    # 检查 ffmpeg
    try:
        from pydub.utils import which

        if which("ffmpeg"):
            logger.info("✅ ffmpeg 已安装")
        else:
            missing_deps.append("ffmpeg")
            logger.error("❌ ffmpeg 未安装或不在 PATH 中")
    except Exception:
        missing_deps.append("ffmpeg")
        logger.error("❌ 无法检查 ffmpeg")

    if missing_deps:
        logger.error(f"缺少依赖: {', '.join(missing_deps)}")
        logger.info("安装命令:")
        if "voicevox-client" in missing_deps:
            logger.info("  pip install voicevox-client")
        if "pydub" in missing_deps:
            logger.info("  pip install pydub")
        if "ffmpeg" in missing_deps:
            logger.info("  # 安装 ffmpeg:")
            logger.info("  # macOS: brew install ffmpeg")
            logger.info("  # Ubuntu: sudo apt-get install ffmpeg")
        return False

    return True


async def check_voicevox_engine(host: str = "localhost", port: int = 50021):
    """检查 VOICEVOX Engine 是否运行"""
    logger.info(f"检查 VOICEVOX Engine 连接 ({host}:{port})...")

    try:
        import voicevox

        async with voicevox.Client(f"http://{host}:{port}") as client:
            # 检查服务器状态
            version = await client.fetch_engine_version()
            logger.info(f"✅ VOICEVOX Engine 已连接, 版本: {version}")
            return True

    except Exception as e:
        logger.error(f"❌ 无法连接到 VOICEVOX Engine: {e}")
        logger.info("请确保 VOICEVOX Engine 正在运行:")
        logger.info("  Docker 启动命令:")
        logger.info(
            "  docker run -d --rm -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest"
        )
        return False


async def get_speakers(host: str = "localhost", port: int = 50021):
    """获取可用的说话人列表"""
    try:
        import voicevox

        async with voicevox.Client(f"http://{host}:{port}") as client:
            speakers = await client.fetch_speakers()

            logger.info("可用说话人:")
            for speaker in speakers:
                logger.info(f"  ID: {speaker.speaker_uuid}, 名称: {speaker.name}")
                for style in speaker.styles:
                    logger.info(f"    风格 ID: {style.id}, 名称: {style.name}")

            return speakers

    except Exception as e:
        logger.error(f"获取说话人列表失败: {e}")
        return []


async def synthesize_speech(
    text: str,
    speaker_id: int = 1,
    output_path: str = "test_voice.wav",
    host: str = "localhost",
    port: int = 50021,
    speed_scale: float = 1.0,
    pitch_scale: float = 0.0,
    intonation_scale: float = 1.0,
    volume_scale: float = 1.0,
):
    """合成语音"""
    logger.info(f"开始合成语音: '{text}'")
    logger.info(f"说话人ID: {speaker_id}")
    logger.info(f"输出文件: {output_path}")

    try:
        import voicevox

        async with voicevox.Client(f"http://{host}:{port}") as client:
            # 创建音频查询
            audio_query = await client.create_audio_query(text, speaker=speaker_id)

            # 设置参数
            audio_query.speed_scale = speed_scale
            audio_query.pitch_scale = pitch_scale
            audio_query.intonation_scale = intonation_scale
            audio_query.volume_scale = volume_scale

            logger.info(
                f"音频参数: 语速={speed_scale}, 音调={pitch_scale}, 语调={intonation_scale}, 音量={volume_scale}"
            )

            # 合成语音
            audio_data = await audio_query.synthesis(speaker=speaker_id)

            # 保存 WAV 文件
            with open(output_path, "wb") as f:
                f.write(audio_data)

            logger.info(f"✅ WAV 文件已保存: {output_path}")
            return True

    except Exception as e:
        logger.error(f"❌ 语音合成失败: {e}")
        return False


def convert_wav_to_mp3(wav_path: str, mp3_path: str, bitrate: str = "128k"):
    """将 WAV 文件转换为 MP3"""
    logger.info(f"转换 WAV 到 MP3: {wav_path} -> {mp3_path}")

    try:
        from pydub import AudioSegment

        # 加载 WAV 文件
        audio = AudioSegment.from_wav(wav_path)

        # 导出为 MP3
        audio.export(mp3_path, format="mp3", bitrate=bitrate)

        logger.info(f"✅ MP3 文件已保存: {mp3_path} (比特率: {bitrate})")
        return True

    except Exception as e:
        logger.error(f"❌ WAV 转 MP3 失败: {e}")
        return False


async def test_voice_synthesis(
    text: str = "こんにちは！これはVOICEVOXのテストです。",
    speaker_id: int = 1,
    output_dir: str = "output",
    filename: str = "test_voice",
    convert_to_mp3: bool = True,
    host: str = "localhost",
    port: int = 50021,
    **synthesis_params,
):
    """测试语音合成完整流程"""
    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # 文件路径
    wav_file = output_path / f"{filename}.wav"
    mp3_file = output_path / f"{filename}.mp3"

    # 合成语音
    success = await synthesize_speech(
        text=text,
        speaker_id=speaker_id,
        output_path=str(wav_file),
        host=host,
        port=port,
        **synthesis_params,
    )

    if not success:
        return False

    # 转换为 MP3
    if convert_to_mp3:
        success = convert_wav_to_mp3(str(wav_file), str(mp3_file))
        if success:
            # 保留原始 WAV 文件以供参考
            logger.info("保留原始 WAV 文件以供参考")

    return success


async def test_multiple_voices(
    tests: List[tuple],
    output_dir: str = "output",
    host: str = "localhost",
    port: int = 50021,
):
    """测试多种声音和文本"""
    logger.info("开始批量测试...")

    for i, (text, speaker_id, description) in enumerate(tests):
        logger.info(f"\n--- 测试 {i+1}/{len(tests)}: {description} ---")

        filename = f"test_voice_{i+1:02d}_speaker_{speaker_id}"

        success = await test_voice_synthesis(
            text=text,
            speaker_id=speaker_id,
            output_dir=output_dir,
            filename=filename,
            host=host,
            port=port,
        )

        if success:
            logger.info(f"✅ 测试 {i+1} 完成")
        else:
            logger.error(f"❌ 测试 {i+1} 失败")


async def main():
    parser = argparse.ArgumentParser(description="VOICEVOX 测试脚本")
    parser.add_argument(
        "--text",
        "-t",
        default="こんにちは！これはVOICEVOXのテストです。",
        help="要合成的文本",
    )
    parser.add_argument("--speaker", "-s", type=int, default=1, help="说话人ID")
    parser.add_argument("--output-dir", "-o", default="output", help="输出目录")
    parser.add_argument(
        "--filename", "-f", default="test_voice", help="输出文件名(不含扩展名)"
    )
    parser.add_argument("--host", default="localhost", help="VOICEVOX Engine 主机")
    parser.add_argument("--port", type=int, default=50021, help="VOICEVOX Engine 端口")
    parser.add_argument("--no-mp3", action="store_true", help="不转换为MP3")
    parser.add_argument("--speed", type=float, default=1.0, help="语速 (0.5-2.0)")
    parser.add_argument("--pitch", type=float, default=0.0, help="音调 (-0.15-0.15)")
    parser.add_argument("--intonation", type=float, default=1.0, help="语调 (0.0-2.0)")
    parser.add_argument("--volume", type=float, default=1.0, help="音量 (0.0-2.0)")
    parser.add_argument("--check-only", action="store_true", help="仅检查环境和连接")
    parser.add_argument("--list-speakers", action="store_true", help="列出可用说话人")
    parser.add_argument("--test-batch", action="store_true", help="批量测试多种声音")

    args = parser.parse_args()

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 检查 VOICEVOX Engine 连接
    if not await check_voicevox_engine(args.host, args.port):
        sys.exit(1)

    # 仅检查环境
    if args.check_only:
        logger.info("✅ 环境检查完成，一切正常！")
        return

    # 列出说话人
    if args.list_speakers:
        await get_speakers(args.host, args.port)
        return

    # 批量测试
    if args.test_batch:
        test_cases = [
            ("こんにちは、世界！", 1, "四国めたん（ノーマル）"),
            ("こんにちは、世界！", 2, "四国めたん（あまあま）"),
            ("Hello, World! This is a test.", 3, "四国めたん（ツンツン）"),
            ("今日はいい天気ですね。", 8, "春日部つむぎ（ノーマル）"),
            ("ありがとうございます！", 9, "波音リツ（ノーマル）"),
        ]
        await test_multiple_voices(test_cases, args.output_dir, args.host, args.port)
        return

    # 单个测试
    success = await test_voice_synthesis(
        text=args.text,
        speaker_id=args.speaker,
        output_dir=args.output_dir,
        filename=args.filename,
        convert_to_mp3=not args.no_mp3,
        host=args.host,
        port=args.port,
        speed_scale=args.speed,
        pitch_scale=args.pitch,
        intonation_scale=args.intonation,
        volume_scale=args.volume,
    )

    if success:
        logger.info("🎉 测试完成！")
    else:
        logger.error("❌ 测试失败！")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"程序出错: {e}")
        sys.exit(1)

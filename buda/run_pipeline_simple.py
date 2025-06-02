#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版材料生成管道脚本 - 增强版
支持conda环境、环境变量检查、参数传递等功能
"""

import subprocess
import sys
import os
import platform
import time


def get_required_conda_env():
    """根据操作系统返回所需的conda环境名称"""
    if platform.system() == "Darwin":  # macOS
        return "buda"
    else:  # Linux/Windows
        return "audio"


def check_conda_environment():
    """检查并激活conda环境"""
    print("🔍 检查conda环境...")

    # 获取当前系统所需的环境
    required_env = get_required_conda_env()
    print(f"📋 当前系统({platform.system()})需要的环境: {required_env}")

    # 检查是否在conda环境中
    if "CONDA_DEFAULT_ENV" in os.environ:
        current_env = os.environ["CONDA_DEFAULT_ENV"]
        print(f"✅ 当前conda环境: {current_env}")

        # 检查是否是所需环境
        if current_env != required_env:
            print(f"⚠️  当前环境是 {current_env}，需要切换到 {required_env} 环境")
            return False
        return True
    else:
        print("❌ 未检测到conda环境")
        return False


def get_conda_python_path():
    """获取conda环境中的python路径"""
    try:
        # 尝试获取当前conda环境的python路径
        result = subprocess.run(["which", "python"], capture_output=True, text=True)
        if result.returncode == 0:
            python_path = result.stdout.strip()
            if (
                "conda" in python_path
                or "miniconda" in python_path
                or "anaconda" in python_path
            ):
                print(f"🐍 使用conda python: {python_path}")
                return python_path

        # 备用方案：直接使用python命令
        return "python"
    except:
        return "python"


def check_environment_variables():
    """检查必要的环境变量"""
    print("🔑 检查环境变量...")

    required_vars = {
        "UNI_API_KEY": "用于字幕处理和翻译",
        "DASHSCOPE_API_KEY": "用于阿里云服务（可选）",
    }

    missing_vars = []
    for var, description in required_vars.items():
        if not os.getenv(var):
            missing_vars.append(f"  - {var}: {description}")
        else:
            print(f"✅ {var}: 已设置")

    if missing_vars:
        print("⚠️  以下环境变量未设置:")
        for var in missing_vars:
            print(var)
        print("\n设置方法:")
        print("export UNI_API_KEY=你的密钥")
        print("export DASHSCOPE_API_KEY=你的密钥")
        print("\n⚠️  警告: 部分环境变量未设置，某些脚本可能会失败")
        print("💡 程序将自动继续执行...")

    return True


def check_dependencies():
    """检查必要的依赖包"""
    print("🔧 检查必要的依赖包...")

    dependencies = {"edge-tts": "用于生成多语种MP3音频文件"}

    missing_deps = []
    for dep, description in dependencies.items():
        try:
            # 尝试运行命令检查是否安装
            result = subprocess.run([dep, "--help"], capture_output=True, text=True)
            if result.returncode in [0, 2]:  # 0=成功, 2=参数错误但命令存在
                print(f"✅ {dep}: 已安装")
            else:
                missing_deps.append(f"  - {dep}: {description}")
        except FileNotFoundError:
            missing_deps.append(f"  - {dep}: {description}")

    if missing_deps:
        print("❌ 以下依赖包未安装:")
        for dep in missing_deps:
            print(dep)
        print("\n安装方法:")
        print("pip install edge-tts")
        print("💡 程序将自动安装缺失的依赖...")

        try:
            print("正在安装 edge-tts...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "edge-tts"], check=True
            )
            print("✅ 依赖安装完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 依赖安装失败: {e}")
            print("⚠️  警告: 某些脚本可能会失败，程序将继续执行...")
            return True  # 即使安装失败也继续执行

    return True


def run_script_with_conda(script_name, description, args=None, conda_env=None):
    """使用conda环境运行脚本"""
    print(f"\n正在运行: {script_name} - {description}")
    print("-" * 50)

    # 如果没有指定环境，使用系统默认环境
    if conda_env is None:
        conda_env = get_required_conda_env()

    # 检查脚本是否存在
    if not os.path.exists(script_name):
        print(f"❌ 错误: 脚本文件 {script_name} 不存在")
        return False

    try:
        # 构建conda运行命令
        if platform.system() == "Windows":
            # Windows系统
            conda_cmd = f"conda activate {conda_env} && python {script_name}"
            if args:
                conda_cmd += f" {args}"
            cmd = ["cmd", "/c", conda_cmd]
        else:
            # Linux/Mac系统
            python_path = get_conda_python_path()
            cmd = [python_path, script_name]
            if args:
                if isinstance(args, list):
                    cmd.extend(args)
                else:
                    cmd.extend(args.split())

        print(f"🚀 执行命令: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

        # 设置环境变量，确保conda环境正确
        env = os.environ.copy()
        if "CONDA_DEFAULT_ENV" not in env:
            env["CONDA_DEFAULT_ENV"] = conda_env

        # 运行脚本
        result = subprocess.run(
            cmd,
            check=True,
            cwd=os.getcwd(),
            env=env,
            text=True,
            capture_output=False,  # 保持输出到控制台
        )

        print(f"✅ 完成: {description}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 失败: {description} (错误代码: {e.returncode})")
        print("可能的原因:")
        print("  - 脚本内部错误")
        print("  - 缺少必要的参数")
        print("  - 环境变量未设置")
        print("  - 依赖文件不存在")
        return False
    except Exception as e:
        print(f"❌ 异常: {description} - {str(e)}")
        return False


def get_default_topic():
    """获取默认的topic参数"""
    # 可以从环境变量或配置文件读取，这里使用默认值
    return "code"


def main():
    """主函数 - 按顺序执行所有脚本"""

    print("🚀 启动材料生成管道...")
    print("=" * 60)

    # 确保在正确的目录下运行（buda目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"🔧 工作目录: {os.getcwd()}")

    # 检查conda环境
    if not check_conda_environment():
        required_env = get_required_conda_env()
        print(f"\n❗ 请先激活conda {required_env}环境:")
        print(f"conda activate {required_env}")
        print("然后重新运行此脚本")
        return

    # 检查环境变量
    if not check_environment_variables():
        print("❌ 环境变量检查失败，脚本退出")
        return

    # 检查必要的依赖包
    if not check_dependencies():
        print("❌ 依赖包检查失败，脚本退出")
        return

    # 获取默认topic
    default_topic = get_default_topic()
    print(f"📝 使用默认topic: {default_topic}")

    print("\n🚀 开始执行材料生成管道...")

    # 脚本执行顺序和参数配置
    scripts = []

    # 根据操作系统决定是否包含mp3toscripts_faster.py
    if platform.system() != "Darwin":  # 非macOS系统才执行
        scripts.append(
            ("mp3toscripts_faster.py", "1. 生成原始 srt 文件", [default_topic])
        )
        print("📋 检测到非macOS系统，将执行mp3toscripts_faster.py")
    else:
        print("📋 检测到macOS系统，跳过mp3toscripts_faster.py（需要显卡支持）")

    # 添加其他脚本
    scripts.extend(
        [
            ("fix_tyro.py", "2. 生成修复的中文 srt 文件", ["-a", "uni"]),
            ("split_sentences_zh_srt.py", "2.1. 对中文进行分句得到分句后的txt", []),
            ("translate_srt_zh_multi.py", "3. 得到不同语种的 txt", []),
            ("generate_mp3_clips.py", "4.1. 生成多语种 mp3 clips (第1次)", ["-b", "5"]),
            ("generate_mp3_clips.py", "4.2. 生成多语种 mp3 clips (第2次)", ["-b", "3"]),
            ("generate_mp3_clips.py", "4.3. 生成多语种 mp3 clips (第3次)", ["-b", "2"]),
            (
                "check_and_regenerate_mp3.py",
                "4.4. 检查mp3进度，删除坏mp3，重新生成对应mp3 clip",
                [],
            ),
            ("generate_subtitles.py", "5. 得到不同语言对应 srt 字幕", []),
            ("merge_mp3.py", "6. 把 mp3 clips 合成为一个 mp3", []),
            ("merge_mp3.py", "6.1 再跑一次，把 mp3 clips 合成为一个 mp3", []),
            ("merge_mp4_clips_by_audio_duration.py", "7. 生成无声且无字幕的 mp4", []),
            ("add_subtitles_to_mp4.py", "8. 给无声的 mp4 增加字幕", []),
            ("merge_mp4_mp3.py", "9. 给mp4添加音频", []),
            (
                "title_translator_multi_lang.py",
                "10.1. 生成多语言标题翻译结果",
                ["-l", "English", "Korean"],
            ),
            ("shorten_titles_multi_lang.py", "10.2. 生成简化多语种标题", []),
            ("generate_key_phrases.py", "11. 生成多语种的封面关键词和简化标题", []),
            (
                "generate_multilingual_thumbnails.py",
                "12. 生成多语种封面",
                ["--font_size", "80", "--no_stroke"],
            ),
            ("generate_multi_lang_descriptions.py", "13. 生成多语种视频描述", []),
        ]
    )

    # 在开始之前检查所有脚本是否存在
    print("🔍 检查所有脚本文件是否存在...")
    missing_scripts = []
    for script_name, _, _ in scripts:
        if not os.path.exists(script_name):
            missing_scripts.append(script_name)

    if missing_scripts:
        print("❌ 以下脚本文件不存在:")
        for script in missing_scripts:
            print(f"   - {script}")
        print("请确保所有脚本文件都在当前目录下")
        return

    print("✅ 所有脚本文件检查完毕")

    success_count = 0
    failed_scripts = []
    start_time = time.time()

    for i, (script_name, description, args) in enumerate(scripts, 1):
        print(f"\n📍 执行进度: {i}/{len(scripts)}")
        print(f"⏰ 已用时: {time.time() - start_time:.1f}秒")

        if run_script_with_conda(script_name, description, args):
            success_count += 1
        else:
            failed_scripts.append((script_name, description))
            # 脚本失败，立即停止整个程序
            print(
                f"\n❌ 脚本 {script_name} 执行失败，由于每一步都依赖上一步的完成，程序将停止执行"
            )
            break

    # 计算总用时
    total_time = time.time() - start_time

    print(f"\n🎯 管道执行完成！")
    print("=" * 60)
    print(f"⏰ 总用时: {total_time:.1f}秒 ({total_time/60:.1f}分钟)")
    print(f"📊 总脚本数: {len(scripts)}")
    print(f"✅ 成功执行: {success_count}")
    print(f"❌ 执行失败: {len(failed_scripts)}")
    print(f"📈 成功率: {success_count/len(scripts)*100:.1f}%")

    if success_count == len(scripts):
        print("🎉 所有脚本都成功执行！")
    else:
        print(
            f"⚠️  管道在第 {success_count + 1} 步失败，共有 {len(scripts) - success_count} 个脚本未执行"
        )

        if failed_scripts:
            print("\n❌ 失败的脚本:")
            for script_name, description in failed_scripts:
                print(f"   - {script_name}: {description}")

            required_env = get_required_conda_env()
            print("\n💡 故障排除建议:")
            print(f"1. 检查conda环境是否正确激活: conda activate {required_env}")
            print("2. 检查环境变量是否设置: echo $UNI_API_KEY")
            print("3. 检查输入文件和目录是否存在")
            print("4. 查看上面的详细错误信息")
            print("5. 修复问题后，请重新运行完整的管道")
            print("\n⚠️  注意: 由于每一步都依赖前一步的结果，建议从头开始重新运行管道")


if __name__ == "__main__":
    main()

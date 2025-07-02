#!/usr/bin/env python3
"""
====================================================================
                    视频生成脚本 - Wan2GP自动化工具
====================================================================

功能描述:
    本脚本用于自动化Wan2GP视频生成流程，将亮度增强处理后的封面图片批量转换为5秒短视频。
    支持多主题并行处理，采用轮询方式确保公平处理每个主题的图片。

支持主题:
    - scifi      (科幻)
    - thriller   (惊悚)
    - horror     (恐怖)
    - fantasy    (奇幻)
    - romance    (浪漫)

====================================================================
输入要求:
====================================================================

前置条件:
1. 必须先运行 lighten_cover_images.py 生成增亮图片
2. Wan2GP环境已正确安装并配置
3. 已安装playwright: pip install playwright && playwright install chromium

输入文件结构:
    {audio_base_path}/{theme}/lighten_images/
    ├── 1.png          # 故事1的增亮封面图片
    ├── 2.png          # 故事2的增亮封面图片
    ├── 3.png          # 故事3的增亮封面图片
    └── ...

路径配置 (自动检测):
    - Intel Mac:      /Volumes/dhl/audio/{theme}/lighten_images/
    - Apple Silicon:  /Users/donghaoliu/Documents/audio/{theme}/lighten_images/
    - Ubuntu/Linux:   /mnt/dhl/audio/{theme}/lighten_images/

====================================================================
输出说明:
====================================================================

实际输出:
    生成的5秒MP4视频将保存到 Wan2GP 的默认输出目录:
    /home/dhl/Documents/Wan2GP/outputs/
    ├── [随机UUID].mp4      # Wan2GP生成的视频文件
    ├── [随机UUID].mp4      # 需要通过match_mp4_covers.py匹配
    ├── [随机UUID].mp4      # 才能对应到具体故事索引
    └── ...

后续处理:
    由于Wan2GP生成的视频文件名为随机UUID，需要运行 match_mp4_covers.py
    进行图片匹配，将视频复制到最终目录:
    {audio_base_path}/{theme}/starting_mp4/
    ├── 1.mp4          # 故事1的5秒视频（匹配后）
    ├── 2.mp4          # 故事2的5秒视频（匹配后）
    ├── 3.mp4          # 故事3的5秒视频（匹配后）
    └── ...

视频规格:
    - 时长: 5秒
    - 格式: MP4
    - 质量: 高清 (由LTX Video 0.9.7 Distilled 13B模型生成)
    - 内容: 基于输入图片的动态视频效果

====================================================================
使用方法:
====================================================================

基本用法:
    python gen_video_5s.py                           # 处理所有主题
    python gen_video_5s.py --theme scifi             # 只处理scifi主题
    python gen_video_5s.py --theme thriller horror   # 处理thriller和horror主题
    python gen_video_5s.py --list-themes             # 显示支持的主题列表

参数说明:
    --theme THEME [THEME ...]    指定要处理的主题，可多选
    --list-themes               显示支持的主题列表并退出

工作流程:
1. 脚本启动Wan2GP的conda环境
2. 自动打开浏览器连接到Gradio界面 (http://localhost:7860)
3. 选择LTX Video 0.9.7 Distilled 13B模型
4. 逐个上传增亮图片并添加到生成队列
5. 视频在后台自动生成，保存到 /home/dhl/Documents/Wan2GP/outputs/
6. 需要手动运行 match_mp4_covers.py 进行视频匹配和重命名

====================================================================
重要说明:
====================================================================

智能跳过:
    - 自动检测已存在的MP4文件，避免重复生成
    - 只处理缺失MP4的图片，提高效率

多主题处理:
    - 采用轮询方式：每轮各主题处理一张图片
    - 确保资源公平分配，避免单个主题阻塞其他主题

错误处理:
    - 自动排除Mac系统文件 (.DS_Store等)
    - 处理失败的图片会被跳过，不影响其他图片处理
    - 详细的日志输出便于问题诊断

注意事项:
    - 首次运行可能需要较长时间加载模型
    - 浏览器会保持运行状态，可实时查看生成进度
    - 按Ctrl+C可安全退出程序
    - 生成过程中请勿关闭浏览器窗口
    - 生成完成后需要运行 match_mp4_covers.py 进行视频匹配

====================================================================
"""

import subprocess
import time
import sys
import os
import glob
import re
import argparse
import platform
from playwright.sync_api import sync_playwright


def get_base_audio_path():
    """根据系统类型获取音频文件基础路径"""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":  # macOS
        if machine == "x86_64":  # Intel Mac
            return "/Volumes/dhl/audio"
        else:  # Apple Silicon (arm64)
            return "/Users/donghaoliu/Documents/audio"
    else:  # Linux/Ubuntu
        return "/mnt/dhl/audio"


def get_supported_themes():
    """获取支持的主题列表"""
    return ["scifi", "thriller", "horror", "fantasy", "romance"]


def run_command(command, cwd=None, shell=True):
    """执行shell命令"""
    try:
        result = subprocess.run(
            command, shell=shell, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"命令执行失败: {e}")
        print(f"错误输出: {e.stderr}")
        return None


def countdown_timer(seconds):
    """倒计时函数，在终端显示倒计时"""
    for i in range(seconds, 0, -1):
        print(f"\r等待中... {i}秒", end="", flush=True)
        time.sleep(1)
    print(f"\r等待完成！{' ' * 20}")


def get_upscaled_images(theme):
    """获取已处理的超分图片列表"""
    base_path = get_base_audio_path()
    output_dir = os.path.join(base_path, theme, "cover_img_large")

    if not os.path.exists(output_dir):
        print(f"超分图片目录不存在: {output_dir}")
        return {}

    image_files = glob.glob(os.path.join(output_dir, "*.png"))
    images = {}

    for file_path in image_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的meta文件（如.DS_Store等）
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.png", basename)
        if match:
            story_index = int(match.group(1))
            images[story_index] = file_path

    return images


def get_existing_mp4s(theme):
    """获取已存在的MP4文件列表"""
    base_path = get_base_audio_path()
    mp4_dir = os.path.join(base_path, theme, "starting_mp4")

    if not os.path.exists(mp4_dir):
        return set()

    existing_files = glob.glob(os.path.join(mp4_dir, "*.mp4"))
    existing_indices = set()

    for file_path in existing_files:
        basename = os.path.basename(file_path)
        # 排除以点开头的meta文件
        if basename.startswith("."):
            continue
        match = re.match(r"(\d+)\.mp4", basename)
        if match:
            existing_indices.add(int(match.group(1)))

    return existing_indices


def collect_all_images_to_process(themes):
    """收集所有主题的待处理图片信息"""
    all_theme_images = {}

    for theme in themes:
        # 获取超分图片列表
        upscaled_images = get_upscaled_images(theme)
        if not upscaled_images:
            print(f"⚠️ 主题 {theme} 未找到超分图片，跳过")
            continue

        # 获取已存在的MP4文件
        existing_mp4s = get_existing_mp4s(theme)

        # 过滤需要处理的图片
        images_to_process = {}
        for story_index, image_path in upscaled_images.items():
            if story_index not in existing_mp4s:
                images_to_process[story_index] = image_path

        if images_to_process:
            all_theme_images[theme] = images_to_process
            print(f"📂 主题 {theme}: 找到 {len(images_to_process)} 张图片需要处理")
            print(f"   故事索引: {sorted(images_to_process.keys())}")
        else:
            print(f"✅ 主题 {theme}: 所有图片对应的MP4都已存在，无需处理")

    return all_theme_images


def process_single_image(page, theme, story_index, image_path, is_first_image=False):
    """处理单张图片"""
    try:
        print(f"🖼️ 处理图片: 主题 {theme}, 故事 {story_index}")
        print(f"   图片路径: {image_path}")

        # 上传图片
        print("📤 上传图片...")
        # 通过包含特定label文本的容器来精准定位
        upload_block = page.locator(
            'div:has(label:has-text("Images as starting points for new videos"))'
        )
        # 在该容器内找到file input
        file_input = upload_block.locator(
            'input[data-testid="file-upload"][type="file"]'
        ).first
        file_input.set_input_files(image_path)
        time.sleep(2.5)  # 等待2.5秒

        # 点击生成按钮
        print("🎬 点击生成按钮...")
        try:
            # 尝试点击第一个按钮
            generate_btn = page.locator('button:has-text("Add New Prompt To Queue")')
            if generate_btn.count() > 0 and generate_btn.is_visible():
                generate_btn.click()
                print("✅ 点击了 'Add New Prompt To Queue' 按钮")
            else:
                # 尝试点击Generate按钮，排除隐藏的按钮
                generate_btn = page.locator(
                    'button:has-text("Generate"):not(.hidden)'
                ).first
                if generate_btn.count() > 0 and generate_btn.is_visible():
                    generate_btn.click()
                    print("✅ 点击了 'Generate' 按钮")
                else:
                    # 如果上面的不行，尝试通过ID定位
                    generate_btn = page.locator("#component-182")
                    if generate_btn.count() > 0 and generate_btn.is_visible():
                        generate_btn.click()
                        print("✅ 点击了 Generate 按钮 (通过ID)")
                    else:
                        print("❌ 未找到生成按钮")
                        return False
        except Exception as e:
            print(f"❌ 点击生成按钮失败: {e}")
            return False

        time.sleep(2)  # 等待2秒

        # 清理图像（除非是所有图片的最后一张）
        print("🧹 清理图像...")
        try:
            if is_first_image:
                # 第一张图片：两步清理
                print("第一张图片，执行两步清理...")
                # 第一步：点击预览容器的Close按钮
                preview_container = page.locator("button.preview.svelte-842rpi")
                close_btn = preview_container.locator(
                    'button[aria-label="Close"][title="Close"]'
                )
                if close_btn.count() > 0 and close_btn.is_visible():
                    close_btn.click()
                    print("✅ 第一步清理完成")
                    time.sleep(1)  # 等待1秒

                    # 第二步：点击最终的清理按钮
                    final_clear_btn = page.locator(
                        "#component-40 > div.gallery-container > div > div.icon-button-wrapper.top-panel.hide-top-corner.svelte-1jx2rq3 > button"
                    )
                    if final_clear_btn.count() > 0 and final_clear_btn.is_visible():
                        final_clear_btn.click()
                        print("✅ 图片清理完成")
                    else:
                        print("⚠️ 未找到最终清理按钮")
                else:
                    print("⚠️ 未找到关闭按钮")
            else:
                # 非第一张图片：直接一步清理
                print("非第一张图片，执行一步清理...")
                final_clear_btn = page.locator(
                    "#component-40 > div.gallery-container > div > div.icon-button-wrapper.top-panel.hide-top-corner.svelte-1jx2rq3 > button"
                )
                if final_clear_btn.count() > 0 and final_clear_btn.is_visible():
                    final_clear_btn.click()
                    print("✅ 图片清理完成")
                else:
                    print("⚠️ 未找到清理按钮")
        except Exception as e:
            print(f"⚠️ 清理图像失败: {e}")

        time.sleep(2)  # 等待2秒
        return True

    except Exception as e:
        print(f"❌ 处理图片失败: {e}")
        return False


def process_all_themes(page, themes):
    """处理所有主题 - 采用轮询方式"""
    print(f"🎯 开始处理 {len(themes)} 个主题: {', '.join(themes)}")
    print("🔄 采用轮询方式：每轮所有主题各处理一张图片")

    # 1. 先选择模型（只需要做一次）
    print("\n🎯 步骤1: 选择模型...")
    try:
        # 先定位到大元素
        model_list_container = page.locator("#model_list")

        # 在大元素内部找到input
        dropdown_input = model_list_container.locator(
            'input[role="listbox"][aria-label="Dropdown"]'
        )

        # 点击激活下拉框
        dropdown_input.click()
        time.sleep(1)

        # 清空占位符内容
        dropdown_input.press("Control+a")  # 全选
        dropdown_input.press("Delete")  # 删除
        time.sleep(0.5)

        # 输入模型名称
        dropdown_input.fill("LTX Video 0.9.7 Distilled 13B")
        time.sleep(0.5)

        # 按两次回车
        page.keyboard.press("Enter")
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(1)

        print("✅ 模型选择完成")
    except Exception as e:
        print(f"❌ 模型选择失败: {e}")
        return [], themes

    # 2. 收集所有主题的待处理图片
    print(f"\n🎯 步骤2: 收集各主题待处理图片...")
    all_theme_images = collect_all_images_to_process(themes)

    if not all_theme_images:
        print("✅ 所有主题都无需处理图片")
        return [], []

    # 3. 计算需要多少轮处理
    max_images = max(len(images) for images in all_theme_images.values())
    print(f"\n🎯 步骤3: 开始轮询处理，共需 {max_images} 轮")
    print(
        f"📊 各主题图片数量: {', '.join([f'{theme}({len(images)})' for theme, images in all_theme_images.items()])}"
    )

    success_themes = set()
    failed_themes = set()
    processed_count = {}  # 记录每个主题已处理的图片数量

    # 初始化已处理数量
    for theme in all_theme_images.keys():
        processed_count[theme] = 0

    # 4. 开始轮询处理
    is_first_image_overall = True  # 标记是否是整个流程的第一张图片

    for round_num in range(1, max_images + 1):
        print(f"\n{'='*60}")
        print(f"🔄 第 {round_num}/{max_images} 轮处理")
        print(f"{'='*60}")

        round_processed = 0

        for theme in sorted(all_theme_images.keys()):
            images = all_theme_images[theme]
            sorted_indices = sorted(images.keys())

            # 检查该主题在这一轮是否还有图片要处理
            if processed_count[theme] < len(sorted_indices):
                story_index = sorted_indices[processed_count[theme]]
                image_path = images[story_index]

                print(
                    f"\n📂 主题 {theme} - 第 {processed_count[theme] + 1}/{len(sorted_indices)} 张图片"
                )

                # 处理图片
                success = process_single_image(
                    page,
                    theme,
                    story_index,
                    image_path,
                    is_first_image=is_first_image_overall,
                )

                if success:
                    processed_count[theme] += 1
                    round_processed += 1

                    # 检查该主题是否完成
                    if processed_count[theme] == len(sorted_indices):
                        success_themes.add(theme)
                        print(f"🎉 主题 {theme} 全部完成！")
                else:
                    failed_themes.add(theme)
                    print(f"❌ 主题 {theme} 图片 {story_index} 处理失败")

                is_first_image_overall = False

                # 主题间添加短暂间隔
                if round_processed < sum(
                    1
                    for t in all_theme_images.keys()
                    if processed_count[t] < len(all_theme_images[t])
                ):
                    time.sleep(1)
            else:
                print(f"✅ 主题 {theme} 已完成，跳过")

        # 轮次间添加间隔
        if round_num < max_images:
            print(f"\n⏳ 第 {round_num} 轮完成，等待3秒后进入下一轮...")
            time.sleep(3)

    # 5. 输出总结
    print(f"\n{'='*60}")
    print("🎊 轮询处理完成！")

    completed_themes = list(success_themes)
    skipped_or_failed = []

    # 处理未在待处理列表中的主题（即本来就无需处理的主题）
    for theme in themes:
        if theme not in all_theme_images:
            completed_themes.append(theme)  # 无需处理也算完成

    # 添加失败的主题到跳过列表
    skipped_or_failed.extend(failed_themes)

    print(f"✅ 成功完成: {len(completed_themes)} 个主题")
    if completed_themes:
        print(f"   - {', '.join(completed_themes)}")

    if skipped_or_failed:
        print(f"⚠️  跳过/失败: {len(skipped_or_failed)} 个主题")
        print(f"   - {', '.join(skipped_or_failed)}")

    # 统计总处理数量
    total_processed = sum(processed_count.values())
    print(f"📊 总共处理图片: {total_processed} 张")
    print("📹 队列中的视频将自动生成，请在浏览器中查看进度")
    print(f"{'='*60}")

    return completed_themes, skipped_or_failed


def automate_video_generation(page, theme):
    """自动化视频生成流程 - 单主题版本（保留以兼容单主题调用）"""
    try:
        print(f"开始自动化视频生成流程 - 主题: {theme}")

        # 获取超分图片列表
        upscaled_images = get_upscaled_images(theme)
        if not upscaled_images:
            print(f"❌ 主题 {theme} 未找到超分图片，请先运行upscale_cover_images.py")
            return False

        # 获取已存在的MP4文件
        existing_mp4s = get_existing_mp4s(theme)

        # 过滤需要处理的图片
        images_to_process = {}
        for story_index, image_path in upscaled_images.items():
            if story_index not in existing_mp4s:
                images_to_process[story_index] = image_path

        if not images_to_process:
            print(f"✅ 主题 {theme} 所有图片对应的MP4都已存在，无需处理")
            return True

        print(f"主题 {theme} 找到 {len(images_to_process)} 张图片需要生成视频")
        print(f"故事索引: {sorted(images_to_process.keys())}")

        # 1. 选择模型
        print("🎯 步骤1: 选择模型...")

        # 先定位到大元素
        model_list_container = page.locator("#model_list")

        # 在大元素内部找到input
        dropdown_input = model_list_container.locator(
            'input[role="listbox"][aria-label="Dropdown"]'
        )

        # 点击激活下拉框
        dropdown_input.click()
        time.sleep(1)

        # 清空占位符内容
        dropdown_input.press("Control+a")  # 全选
        dropdown_input.press("Delete")  # 删除
        time.sleep(0.5)

        # 输入模型名称
        dropdown_input.fill("LTX Video 0.9.7 Distilled 13B")
        time.sleep(0.5)

        # 按两次回车
        page.keyboard.press("Enter")
        time.sleep(0.5)
        page.keyboard.press("Enter")
        time.sleep(1)

        print("✅ 模型选择完成")

        # 2. 逐个处理图片
        for i, (story_index, image_path) in enumerate(
            sorted(images_to_process.items())
        ):
            is_last_image = i == len(images_to_process) - 1
            success = process_single_image(
                page, theme, story_index, image_path, is_first_image=(i == 0)
            )

            if not success:
                print(f"❌ 图片 {story_index} 处理失败，继续下一张")
                continue

            # 如果不是最后一张图片，添加间隔
            if not is_last_image:
                time.sleep(2)

        print(
            f"\n🎉 主题 {theme} 自动化流程完成！共处理了 {len(images_to_process)} 张图片"
        )
        return True

    except Exception as e:
        print(f"❌ 主题 {theme} 自动化流程出错: {e}")
        import traceback

        traceback.print_exc()
        return False


def activate_conda_and_run():
    """激活conda环境并运行命令"""
    # 目标目录
    target_dir = "/home/dhl/Documents/Wan2GP"

    # 检查目录是否存在
    if not os.path.exists(target_dir):
        print(f"错误: 目录 {target_dir} 不存在！")
        return False, None

    print(f"切换到目录: {target_dir}")

    # 检查wgp.py文件是否存在
    wgp_file = os.path.join(target_dir, "wgp.py")
    if not os.path.exists(wgp_file):
        print(f"错误: 文件 {wgp_file} 不存在！")
        return False, None

    print(f"确认文件存在: {wgp_file}")

    # 先检测conda路径
    conda_paths = [
        "~/miniconda3/etc/profile.d/conda.sh",
        "~/anaconda3/etc/profile.d/conda.sh",
        "~/miniforge3/etc/profile.d/conda.sh",
        "/opt/conda/etc/profile.d/conda.sh",
        "/usr/local/miniconda3/etc/profile.d/conda.sh",
        "/usr/local/anaconda3/etc/profile.d/conda.sh",
    ]

    conda_init_path = None
    for path in conda_paths:
        expanded_path = os.path.expanduser(path)
        if os.path.exists(expanded_path):
            conda_init_path = path
            print(f"找到conda初始化脚本: {conda_init_path}")
            break

    if conda_init_path is None:
        print("未找到conda初始化脚本，尝试直接使用conda命令...")
        # 构建不依赖conda.sh的命令
        command = f"""
        cd {target_dir} && \
        echo "=== 当前目录: $(pwd) ===" && \
        echo "=== 检查conda命令 ===" && \
        which conda && \
        conda --version && \
        echo "=== 激活环境 ===" && \
        conda run -n wan2gp python --version && \
        echo "=== 检查wgp.py文件 ===" && \
        ls -la wgp.py && \
        echo "=== 开始运行命令 ===" && \
        conda run -n wan2gp python wgp.py --i2v
        """
    else:
        # 构建使用conda.sh的命令
        command = f"""
        cd {target_dir} && \
        source {conda_init_path} && \
        conda activate wan2gp && \
        echo "=== conda环境已激活: wan2gp ===" && \
        echo "当前conda环境: $CONDA_DEFAULT_ENV" && \
        echo "当前目录: $(pwd)" && \
        echo "检查Python版本:" && \
        python --version && \
        echo "检查wgp.py文件:" && \
        ls -la wgp.py && \
        echo "=== 开始运行命令 ===" && \
        python wgp.py --i2v
        """

    print("激活conda环境: wan2gp")
    print("检查环境和文件...")

    # 在后台启动进程，保持运行
    process = subprocess.Popen(
        command,
        shell=True,
        executable="/bin/bash",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # 将stderr重定向到stdout
        text=True,
        bufsize=1,
        universal_newlines=True,
    )

    print("已启动命令，等待输出...")

    # 读取前几行输出来检查是否成功启动
    output_lines = []
    try:
        import select
        import time

        for i in range(15):  # 尝试读取前15行输出
            # 使用非阻塞方式读取，避免卡死
            ready, _, _ = select.select([process.stdout], [], [], 2)  # 2秒超时
            if ready:
                line = process.stdout.readline()
                if line:
                    print(f"输出: {line.strip()}")
                    output_lines.append(line.strip())
                else:
                    break
            else:
                print(f"第{i+1}次读取超时，检查进程状态...")
                if process.poll() is not None:
                    print("进程已结束")
                    break
                else:
                    print("进程仍在运行，可能正在加载...")

                    # 如果已经读到了"开始运行命令"，说明可能在加载模型
                    if any("开始运行命令" in line for line in output_lines):
                        print("检测到命令开始执行，可能正在加载模型，跳出读取循环...")
                        break
    except ImportError:
        print("select模块不可用，使用简化版本...")
        # 降级方案：只读取几行然后继续
        for i in range(5):
            try:
                line = process.stdout.readline()
                if line:
                    print(f"输出: {line.strip()}")
                    output_lines.append(line.strip())
                else:
                    break
            except:
                break
    except Exception as e:
        print(f"读取输出时出错: {e}")

    # 检查进程是否还在运行
    if process.poll() is None:
        print("✓ 进程正在运行中")
        print("进程可能正在加载模型或初始化Gradio...")
    else:
        print("✗ 进程已停止，返回码:", process.returncode)
        # 读取剩余输出
        try:
            remaining_output, error_output = process.communicate(timeout=5)
            if remaining_output:
                print("完整输出:")
                print(remaining_output)
            if error_output:
                print("错误输出:")
                print(error_output)
        except:
            pass
        return False, None

    print("等待15秒让Gradio应用完全启动...")
    print("（模型加载可能需要较长时间）")
    # 15秒倒计时，给Gradio更多时间启动
    countdown_timer(15)

    # 再次检查进程状态
    if process.poll() is None:
        print("✓ 进程仍在运行，Gradio应该已启动")
        return True, process
    else:
        print("✗ 进程在启动过程中停止了")
        return False, None


def open_browser(gradio_process, themes):
    """使用playwright打开浏览器"""
    try:
        print("正在启动浏览器...")
        with sync_playwright() as p:
            # 启动Chrome浏览器
            browser = p.chromium.launch(
                headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"]
            )

            # 创建新页面
            page = browser.new_page()

            # 导航到指定URL
            url = "http://localhost:7860/"
            print(f"正在打开: {url}")

            try:
                page.goto(url, timeout=15000)  # 15秒超时
                print("浏览器已成功打开！")
                print("开始自动化流程...")

                # 开始自动化视频生成流程
                if len(themes) == 1:
                    # 单主题：使用原有的单主题处理方式
                    print("🎯 单主题模式")
                    success = automate_video_generation(page, themes[0])
                    success_themes = [themes[0]] if success else []
                    skipped_themes = [] if success else [themes[0]]
                else:
                    # 多主题：使用轮询方式
                    print("🎯 多主题轮询模式")
                    success_themes, skipped_themes = process_all_themes(page, themes)

                print("\n🎊 所有任务已加入队列！")
                print("🌟 浏览器将保持运行，您可以在页面中查看视频生成进度")
                print("🔄 视频将在后台自动生成，无需人工干预")
                print("⏹️  如需退出程序，请按 Ctrl+C")
                print("=" * 60)

                # 保持浏览器打开状态，直到用户手动关闭
                try:
                    while True:
                        time.sleep(10)  # 每10秒检查一次
                        # 检查Gradio进程是否还在运行
                        if gradio_process.poll() is not None:
                            print("⚠️  警告：Gradio进程已停止运行！")
                            print("浏览器将在5秒后自动关闭...")
                            time.sleep(5)
                            break
                except KeyboardInterrupt:
                    print("\n👋 用户手动退出，正在关闭浏览器...")

            except Exception as e:
                print(f"无法连接到 {url}: {e}")
                print("请确保服务正在运行...")
                print("可能需要等待更长时间让Gradio启动...")
                time.sleep(5)  # 等待5秒后关闭

            browser.close()

    except Exception as e:
        print(f"启动浏览器失败: {e}")
        print("请确保已安装playwright: pip install playwright")
        print("并运行: playwright install chromium")
    finally:
        # 确保关闭Gradio进程
        if gradio_process and gradio_process.poll() is None:
            print("正在关闭Gradio进程...")
            gradio_process.terminate()
            time.sleep(2)
            if gradio_process.poll() is None:
                gradio_process.kill()
            print("Gradio进程已关闭")


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="视频生成脚本 - 自动化Wan2GP视频生成流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python gen_video_5s.py                    # 运行所有主题
  python gen_video_5s.py --theme scifi      # 只运行scifi主题
  python gen_video_5s.py --theme thriller horror  # 运行thriller和horror主题
  python gen_video_5s.py --list-themes      # 显示支持的主题列表

支持的主题: scifi, thriller, horror, fantasy, romance
        """,
    )

    parser.add_argument(
        "--theme",
        nargs="*",
        choices=get_supported_themes(),
        help="要处理的主题，可以指定多个。不指定则处理所有主题",
    )

    parser.add_argument(
        "--list-themes", action="store_true", help="显示支持的主题列表并退出"
    )

    return parser.parse_args()


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()

    # 如果只是列出主题，直接返回
    if args.list_themes:
        print("支持的主题:")
        for theme in get_supported_themes():
            print(f"  - {theme}")
        return

    # 确定要处理的主题
    if args.theme:
        themes = args.theme
    else:
        themes = get_supported_themes()

    print("=" * 50)
    print("视频生成脚本启动")
    print("=" * 50)
    print(f"🎯 计划处理的主题: {', '.join(themes)}")
    print(f"📁 音频基础路径: {get_base_audio_path()}")
    print("=" * 50)

    gradio_process = None

    try:
        # 步骤1: 激活conda环境并运行命令
        success, gradio_process = activate_conda_and_run()
        if not success:
            print("环境激活失败，退出脚本")
            return

        # 步骤2: 打开浏览器
        open_browser(gradio_process, themes)

    except KeyboardInterrupt:
        print("\n\n👋 脚本被用户中断")
    except Exception as e:
        print(f"❌ 发生错误: {e}")
    finally:
        # 确保Gradio进程被正确关闭
        if gradio_process and gradio_process.poll() is None:
            print("🧹 清理：关闭Gradio进程...")
            gradio_process.terminate()
            time.sleep(2)
            if gradio_process.poll() is None:
                gradio_process.kill()
            print("✅ Gradio进程已关闭")
        print("🎯 脚本执行完毕")


if __name__ == "__main__":
    main()

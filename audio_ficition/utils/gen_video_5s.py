#!/usr/bin/env python3
"""
视频生成脚本 - 自动化Wan2GP视频生成流程
"""

import subprocess
import time
import sys
import os
import glob
import re
from playwright.sync_api import sync_playwright


def run_command(command, cwd=None, shell=True):
    """执行shell命令"""
    try:
        result = subprocess.run(
            command, 
            shell=shell, 
            cwd=cwd, 
            capture_output=True, 
            text=True,
            check=True
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


def get_upscaled_images():
    """获取已处理的超分图片列表"""
    output_dir = "/mnt/dhl/audio/scifi/cover_img_large"
    
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


def get_existing_mp4s():
    """获取已存在的MP4文件列表"""
    mp4_dir = "/mnt/dhl/audio/scifi/starting_mp4"
    
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


def automate_video_generation(page):
    """自动化视频生成流程"""
    try:
        print("开始自动化视频生成流程...")
        
        # 获取超分图片列表
        upscaled_images = get_upscaled_images()
        if not upscaled_images:
            print("❌ 未找到超分图片，请先运行upscale_cover_images.py")
            return
            
        # 获取已存在的MP4文件
        existing_mp4s = get_existing_mp4s()
        
        # 过滤需要处理的图片
        images_to_process = {}
        for story_index, image_path in upscaled_images.items():
            if story_index not in existing_mp4s:
                images_to_process[story_index] = image_path
                
        if not images_to_process:
            print("✅ 所有图片对应的MP4都已存在，无需处理")
            return
            
        print(f"找到 {len(images_to_process)} 张图片需要生成视频")
        print(f"故事索引: {sorted(images_to_process.keys())}")
        
        # 1. 选择模型
        print("🎯 步骤1: 选择模型...")
        
        # 先定位到大元素
        model_list_container = page.locator('#model_list')
        
        # 在大元素内部找到input
        dropdown_input = model_list_container.locator('input[role="listbox"][aria-label="Dropdown"]')
        
        # 点击激活下拉框
        dropdown_input.click()
        time.sleep(1)
        
        # 清空占位符内容
        dropdown_input.press("Control+a")  # 全选
        dropdown_input.press("Delete")     # 删除
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
        for i, (story_index, image_path) in enumerate(sorted(images_to_process.items())):
            print(f"\n🖼️ 处理图片 {i+1}/{len(images_to_process)}: 故事 {story_index}")
            print(f"图片路径: {image_path}")
            
            # 上传图片
            print("📤 上传图片...")
            # 通过包含特定label文本的容器来精准定位
            upload_block = page.locator('div:has(label:has-text("Images as starting points for new videos"))')
            # 在该容器内找到file input
            file_input = upload_block.locator('input[data-testid="file-upload"][type="file"]').first
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
                    generate_btn = page.locator('button:has-text("Generate"):not(.hidden)').first
                    if generate_btn.count() > 0 and generate_btn.is_visible():
                        generate_btn.click()
                        print("✅ 点击了 'Generate' 按钮")
                    else:
                        # 如果上面的不行，尝试通过ID定位
                        generate_btn = page.locator('#component-182')
                        if generate_btn.count() > 0 and generate_btn.is_visible():
                            generate_btn.click()
                            print("✅ 点击了 Generate 按钮 (通过ID)")
                        else:
                            print("❌ 未找到生成按钮")
                            continue
            except Exception as e:
                print(f"❌ 点击生成按钮失败: {e}")
                continue
                
            time.sleep(2)  # 等待2秒
            
            # 如果不是最后一张图片，清理图像
            if i < len(images_to_process) - 1:
                print("🧹 清理图像...")
                try:
                    if i == 0:
                        # 第一张图片：两步清理
                        print("第一张图片，执行两步清理...")
                        # 第一步：点击预览容器的Close按钮
                        preview_container = page.locator('button.preview.svelte-842rpi')
                        close_btn = preview_container.locator('button[aria-label="Close"][title="Close"]')
                        if close_btn.count() > 0 and close_btn.is_visible():
                            close_btn.click()
                            print("✅ 第一步清理完成")
                            time.sleep(1)  # 等待1秒
                            
                            # 第二步：点击最终的清理按钮
                            final_clear_btn = page.locator('#component-40 > div.gallery-container > div > div.icon-button-wrapper.top-panel.hide-top-corner.svelte-1jx2rq3 > button')
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
                        final_clear_btn = page.locator('#component-40 > div.gallery-container > div > div.icon-button-wrapper.top-panel.hide-top-corner.svelte-1jx2rq3 > button')
                        if final_clear_btn.count() > 0 and final_clear_btn.is_visible():
                            final_clear_btn.click()
                            print("✅ 图片清理完成")
                        else:
                            print("⚠️ 未找到清理按钮")
                except Exception as e:
                    print(f"⚠️ 清理图像失败: {e}")
                    
                time.sleep(2)  # 等待2秒
        
        print(f"\n🎉 自动化流程完成！共处理了 {len(images_to_process)} 张图片")
        print("✅ 所有图片已成功加入视频生成队列！")
        print("📹 队列中的视频将自动生成，请在浏览器中查看进度")
        
    except Exception as e:
        print(f"❌ 自动化流程出错: {e}")
        import traceback
        traceback.print_exc()


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
        "/usr/local/anaconda3/etc/profile.d/conda.sh"
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
        universal_newlines=True
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


def open_browser(gradio_process):
    """使用playwright打开浏览器"""
    try:
        print("正在启动浏览器...")
        with sync_playwright() as p:
            # 启动Chrome浏览器
            browser = p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
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
                automate_video_generation(page)
                
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


def main():
    """主函数"""
    print("=" * 50)
    print("视频生成脚本启动")
    print("=" * 50)
    
    gradio_process = None
    
    try:
        # 步骤1: 激活conda环境并运行命令
        success, gradio_process = activate_conda_and_run()
        if not success:
            print("环境激活失败，退出脚本")
            return
        
        # 步骤2: 打开浏览器
        open_browser(gradio_process)
        
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
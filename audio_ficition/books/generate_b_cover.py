#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文书籍B站封面生成器

功能说明：
1. 生成中文书籍的4:3比例B站封面
2. 使用bg.jpg作为背景底图
3. 读取书的封面，进行适当缩放后放在底图的左边（最大宽度不超过底图的60%）
4. 保证封面完整不溢出，封面左边和底图左边重合
5. 支持断点续传，自动跳过已生成的封面
6. 自动排除Mac系统产生的点开头文件

输入文件：
• 背景图片：audio_ficition/books/assets/bg.jpg
• 书籍封面：
  - Intel Mac: /Volumes/dhl/audio/books/zh/thumbnails_large/{uuid}.png
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/zh/thumbnails_large/{uuid}.png
  - Linux: /mnt/dhl/audio/books/zh/thumbnails_large/{uuid}.png

输出文件：
• B站封面：
  - Intel Mac: /Volumes/dhl/audio/books/zh/b_cover/{uuid}.png
  - Apple Silicon: /Users/donghaoliu/Documents/audio/books/zh/b_cover/{uuid}.png
  - Linux: /mnt/dhl/audio/books/zh/b_cover/{uuid}.png

使用方法：
python generate_b_cover.py                    # 生成所有B站封面
python generate_b_cover.py --count 10         # 生成10个封面
python generate_b_cover.py --force            # 强制重新生成
python generate_b_cover.py --uuid abc123      # 生成指定UUID
python generate_b_cover.py --preview          # 预览模式
python generate_b_cover.py --debug            # 调试模式

技术规格：
• 输出尺寸：4:3比例（推荐1920x1440或1280x960）
• 背景图片：拉伸至目标尺寸
• 书籍封面：保持原始比例，缩放适配左侧区域（最大60%宽度，左边贴边）
• 图片格式：PNG（保持透明度支持）
"""

import os
import sys
import argparse
import platform
import glob
import re
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Tuple, List

# 导入PIL进行图像处理
try:
    from PIL import Image, ImageOps
except ImportError:
    print("❌ 缺少依赖模块，请安装: pip install Pillow")
    sys.exit(1)


def get_base_media_path():
    """根据系统类型返回基础媒体路径（与generate_youtube_descriptions.py保持一致）"""
    system = platform.system()

    if system == "Linux":  # Ubuntu/Linux
        return "/mnt/dhl/audio"
    elif system == "Darwin":  # macOS
        machine = platform.machine().lower()
        processor = platform.processor().lower()
        # Apple Silicon (M芯片)
        is_apple_silicon = (
            machine == "arm64"
            or "arm" in machine
            or "apple" in processor
            or "m1" in processor
            or "m2" in processor
            or "m3" in processor
        )
        if is_apple_silicon:
            return "/Users/donghaoliu/Documents/audio"
        else:
            # Intel Mac
            return "/Volumes/dhl/audio"
    else:
        # 默认使用环境变量或默认路径
        return os.environ.get("AUDIO_BASE_DIR", "/Users/donghaoliu/Documents/audio")


class BCoverGenerator:
    """B站封面生成器"""

    def __init__(self, debug=False):
        self.debug = debug
        self.base_media_path = get_base_media_path()
        self.books_base_path = os.path.join(self.base_media_path, "books", "zh")
        
        # 输入目录
        self.thumbnails_dir = os.path.join(self.books_base_path, "thumbnails_large")
        
        # 输出目录
        self.b_cover_dir = os.path.join(self.books_base_path, "b_cover")
        
        # 背景图片路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.bg_image_path = os.path.join(script_dir, "assets", "bg.jpg")
        
        # B站封面规格（4:3比例）
        self.target_width = 1920
        self.target_height = 1440  # 4:3比例
        
        # 左侧书籍封面区域配置
        self.cover_area_width = int(self.target_width * 0.6)  # 左侧60%用于书籍封面
        self.cover_padding = 20  # 封面边距（只用于上下边距）
        
        # 创建输出目录
        os.makedirs(self.b_cover_dir, exist_ok=True)
        
        print(f"📁 基础路径: {self.base_media_path}")
        print(f"📁 封面输入目录: {self.thumbnails_dir}")
        print(f"📁 B站封面输出目录: {self.b_cover_dir}")
        print(f"🖼️  背景图片: {self.bg_image_path}")
        print(f"📐 输出尺寸: {self.target_width}x{self.target_height} (4:3)")

    def get_available_thumbnails(self) -> List[Tuple[str, str]]:
        """
        获取所有可用的书籍封面文件
        
        Returns:
            List[Tuple[str, str]]: [(封面路径, UUID), ...]
        """
        if not os.path.exists(self.thumbnails_dir):
            print(f"❌ 封面目录不存在: {self.thumbnails_dir}")
            return []
        
        # 查找所有PNG文件
        thumbnail_files = glob.glob(os.path.join(self.thumbnails_dir, "*.png"))
        
        available_thumbnails = []
        skipped_files = []
        
        for thumbnail_path in thumbnail_files:
            basename = os.path.basename(thumbnail_path)
            
            # 排除以点开头的文件（Mac系统文件）
            if basename.startswith("."):
                skipped_files.append(basename)
                continue
            
            # 提取UUID
            if basename.endswith(".png"):
                uuid_val = basename[:-4]
                
                # 验证文件是否有效
                try:
                    file_size = os.path.getsize(thumbnail_path)
                    if file_size > 1024:  # 至少1KB
                        available_thumbnails.append((thumbnail_path, uuid_val))
                        if self.debug:
                            print(f"✅ 发现封面: {uuid_val}")
                    else:
                        if self.debug:
                            print(f"⚠️ 封面文件过小，跳过: {uuid_val}")
                except Exception as e:
                    if self.debug:
                        print(f"⚠️ 检查封面文件失败 {thumbnail_path}: {e}")
        
        if skipped_files:
            print(f"🚫 跳过 {len(skipped_files)} 个Mac系统文件")
        
        # 按UUID排序
        available_thumbnails.sort(key=lambda x: x[1])
        print(f"📊 找到 {len(available_thumbnails)} 个有效的书籍封面")
        return available_thumbnails

    def get_existing_b_covers(self) -> set:
        """
        获取已存在的B站封面
        
        Returns:
            set: 已存在封面的UUID集合
        """
        existing_uuids = set()
        
        if os.path.exists(self.b_cover_dir):
            b_cover_files = glob.glob(os.path.join(self.b_cover_dir, "*.png"))
            
            for b_cover_file in b_cover_files:
                basename = os.path.basename(b_cover_file)
                # 排除以点开头的文件
                if basename.startswith("."):
                    continue
                
                if basename.endswith(".png"):
                    uuid_val = basename[:-4]
                    try:
                        # 验证文件大小
                        if os.path.getsize(b_cover_file) > 1024:
                            existing_uuids.add(uuid_val)
                            if self.debug:
                                print(f"✅ 发现现有B站封面: {uuid_val}")
                    except:
                        if self.debug:
                            print(f"⚠️ 检查B站封面失败: {uuid_val}")
        
        print(f"📊 找到 {len(existing_uuids)} 个已存在的B站封面")
        return existing_uuids

    def create_b_cover(self, thumbnail_path: str, uuid: str) -> bool:
        """
        生成单个B站封面
        
        Args:
            thumbnail_path: 书籍封面路径
            uuid: 书籍UUID
            
        Returns:
            bool: 是否成功生成
        """
        try:
            print(f"🎨 正在生成 {uuid} 的B站封面...")
            
            # 检查背景图片是否存在
            if not os.path.exists(self.bg_image_path):
                print(f"❌ 背景图片不存在: {self.bg_image_path}")
                return False
            
            # 检查书籍封面是否存在
            if not os.path.exists(thumbnail_path):
                print(f"❌ 书籍封面不存在: {thumbnail_path}")
                return False
            
            # 打开背景图片
            try:
                bg_image = Image.open(self.bg_image_path)
                if self.debug:
                    print(f"📷 背景图片尺寸: {bg_image.size}")
            except Exception as e:
                print(f"❌ 打开背景图片失败: {e}")
                return False
            
            # 打开书籍封面
            try:
                book_cover = Image.open(thumbnail_path)
                if self.debug:
                    print(f"📚 书籍封面尺寸: {book_cover.size}")
            except Exception as e:
                print(f"❌ 打开书籍封面失败: {e}")
                return False
            
            # 创建目标画布（4:3比例）
            canvas = Image.new("RGB", (self.target_width, self.target_height), (255, 255, 255))
            
            # 1. 将背景图片拉伸到目标尺寸
            bg_resized = bg_image.resize((self.target_width, self.target_height), Image.Resampling.LANCZOS)
            canvas.paste(bg_resized, (0, 0))
            if self.debug:
                print(f"✅ 背景图片已拉伸到 {self.target_width}x{self.target_height}")
            
            # 2. 处理书籍封面 - 保持比例缩放到左侧区域
            # 计算左侧区域的可用空间（宽度不减去左右padding，因为要贴左边）
            available_width = self.cover_area_width
            available_height = self.target_height - (self.cover_padding * 2)
            
            # 计算书籍封面的缩放比例（保持原始比例）
            book_width, book_height = book_cover.size
            scale_width = available_width / book_width
            scale_height = available_height / book_height
            scale_factor = min(scale_width, scale_height)  # 选择较小的缩放比例确保不溢出
            
            # 计算缩放后的尺寸
            scaled_width = int(book_width * scale_factor)
            scaled_height = int(book_height * scale_factor)
            
            # 缩放书籍封面
            book_cover_scaled = book_cover.resize((scaled_width, scaled_height), Image.Resampling.LANCZOS)
            
            # 计算书籍封面的位置（左边贴边，垂直居中）
            book_x = 0  # 左边与底图左边重合
            book_y = (self.target_height - scaled_height) // 2  # 垂直居中
            
            # 将书籍封面粘贴到画布上
            canvas.paste(book_cover_scaled, (book_x, book_y))
            
            if self.debug:
                print(f"📐 书籍封面缩放: {book_width}x{book_height} -> {scaled_width}x{scaled_height}")
                print(f"📍 书籍封面位置: ({book_x}, {book_y}) [左边贴边]")
                print(f"🔢 缩放比例: {scale_factor:.3f}")
                print(f"📏 可用区域: {available_width}x{available_height} (宽度={self.target_width*0.6:.0f}px, 60%)")
            
            # 保存B站封面
            output_path = os.path.join(self.b_cover_dir, f"{uuid}.png")
            canvas.save(output_path, "PNG", quality=95)
            
            # 验证文件是否成功保存
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                print(f"💾 B站封面已保存: {output_path}")
                print(f"📊 文件大小: {file_size / 1024:.1f} KB")
                return True
            else:
                print(f"❌ 文件保存后未找到: {output_path}")
                return False
                
        except Exception as e:
            print(f"❌ 生成B站封面失败 {uuid}: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False

    def process_covers(self, max_count=None, force=False, target_uuid=None, preview=False):
        """
        批量处理B站封面生成
        
        Args:
            max_count: 最大处理数量
            force: 是否强制重新生成
            target_uuid: 指定处理的UUID
            preview: 是否为预览模式
        """
        print("🎨 B站封面生成器")
        print(f"📁 封面输入目录: {self.thumbnails_dir}")
        print(f"📁 输出目录: {self.b_cover_dir}")
        print(f"📐 输出尺寸: {self.target_width}x{self.target_height} (4:3)")
        
        # 获取可用的书籍封面
        available_thumbnails = self.get_available_thumbnails()
        if not available_thumbnails:
            print("❌ 没有找到可用的书籍封面")
            print("💡 请确保运行 upscale_book_thumbnails.py 生成超分封面")
            return {"total_targets": 0, "successful": 0, "failed": 0, "skipped": 0}
        
        # 如果指定了特定UUID
        if target_uuid:
            target_thumbnails = [(path, uuid) for path, uuid in available_thumbnails if uuid == target_uuid]
            if target_thumbnails:
                available_thumbnails = target_thumbnails
                print(f"🎯 处理指定UUID: {target_uuid}")
            else:
                print(f"❌ 未找到指定的UUID: {target_uuid}")
                return {"total_targets": 0, "successful": 0, "failed": 0, "skipped": 0}
        
        # 获取已存在的B站封面
        existing_b_covers = self.get_existing_b_covers()
        
        # 筛选需要处理的文件
        covers_to_process = []
        skipped_count = 0
        
        for thumbnail_path, uuid in available_thumbnails:
            if force or uuid not in existing_b_covers:
                covers_to_process.append((thumbnail_path, uuid))
            else:
                skipped_count += 1
                if self.debug:
                    print(f"⏭️ 跳过已存在的B站封面: {uuid}")
        
        # 限制处理数量
        if max_count and len(covers_to_process) > max_count:
            covers_to_process = covers_to_process[:max_count]
        
        if not covers_to_process:
            print("🎉 所有B站封面都已生成完成！")
            return {
                "total_targets": 0,
                "successful": 0, 
                "failed": 0,
                "skipped": len(available_thumbnails)
            }
        
        print(f"\n📊 处理统计:")
        print(f"可处理封面: {len(available_thumbnails)}")
        print(f"已有B站封面: {len(existing_b_covers)}")
        print(f"需要处理: {len(covers_to_process)}")
        print(f"跳过数量: {skipped_count}")
        
        # 预览模式
        if preview:
            print(f"\n📋 预览模式 - 将要处理的封面:")
            for i, (thumbnail_path, uuid) in enumerate(covers_to_process, 1):
                output_path = os.path.join(self.b_cover_dir, f"{uuid}.png")
                print(f"  {i:2d}. UUID: {uuid}")
                print(f"      输入: {thumbnail_path}")
                print(f"      输出: {output_path}")
            return {
                "total_targets": len(covers_to_process),
                "successful": 0,
                "failed": 0,
                "skipped": skipped_count,
                "preview": len(covers_to_process)
            }
        
        # 开始处理
        success_count = 0
        failed_count = 0
        
        with tqdm(total=len(covers_to_process), desc="🎨 生成B站封面") as pbar:
            for thumbnail_path, uuid in covers_to_process:
                try:
                    print(f"\n=== 处理 {uuid} ===")
                    
                    if self.create_b_cover(thumbnail_path, uuid):
                        success_count += 1
                        print(f"✅ {uuid} 处理成功")
                    else:
                        failed_count += 1
                        print(f"❌ {uuid} 处理失败")
                        
                except KeyboardInterrupt:
                    print("⏹️ 用户中断，程序停止")
                    break
                except Exception as e:
                    print(f"❌ 处理 {uuid} 时出错: {e}")
                    failed_count += 1
                
                pbar.update(1)
        
        # 最终统计
        print(f"\n🎯 B站封面生成完成!")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(f"📊 成功率: {success_count/(success_count+failed_count)*100:.1f}%" 
              if (success_count + failed_count) > 0 else "N/A")
        
        return {
            "total_targets": len(covers_to_process),
            "successful": success_count,
            "failed": failed_count,
            "skipped": skipped_count
        }

    def check_status(self):
        """检查当前状态"""
        print("📊 当前状态检查")
        print(f"📁 基础路径: {self.base_media_path}")
        print(f"🖼️  背景图片: {'存在' if os.path.exists(self.bg_image_path) else '不存在'}")
        
        available_thumbnails = self.get_available_thumbnails()
        existing_b_covers = self.get_existing_b_covers()
        
        print(f"📚 可用书籍封面: {len(available_thumbnails)}")
        print(f"🎨 已生成B站封面: {len(existing_b_covers)}")
        
        # 计算待处理数量
        thumbnail_uuids = {uuid for _, uuid in available_thumbnails}
        pending_count = len(thumbnail_uuids - existing_b_covers)
        print(f"⏳ 待处理数量: {pending_count}")
        
        if pending_count > 0:
            print("\n📋 待处理示例 (前5个):")
            pending_uuids = list(thumbnail_uuids - existing_b_covers)
            for i, uuid in enumerate(sorted(pending_uuids)[:5]):
                print(f"   {i+1}. {uuid}")
            if len(pending_uuids) > 5:
                print(f"   ... 还有 {len(pending_uuids) - 5} 个")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🎨 中文书籍B站封面生成器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python generate_b_cover.py                  # 生成所有B站封面
  python generate_b_cover.py --count 10       # 生成10个封面
  python generate_b_cover.py --force          # 强制重新生成
  python generate_b_cover.py --uuid abc123    # 生成指定UUID
  python generate_b_cover.py --preview        # 预览模式
  python generate_b_cover.py --debug          # 调试模式
  python generate_b_cover.py --status         # 检查状态

注意:
- 自动支持Mac、Linux系统的路径配置
- 需要先运行 upscale_book_thumbnails.py 生成超分封面
- 输出为4:3比例的B站封面图片
        """
    )
    
    parser.add_argument("--count", "-c", type=int, help="要处理的封面数量（默认处理所有）")
    parser.add_argument("--force", "-f", action="store_true", help="强制重新生成已存在的封面")
    parser.add_argument("--uuid", "-u", help="只处理指定UUID的书籍")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    parser.add_argument("--preview", "-p", action="store_true", help="预览模式，只显示会处理哪些文件")
    parser.add_argument("--status", "-s", action="store_true", help="检查当前处理状态")
    
    args = parser.parse_args()
    
    # 创建生成器实例
    generator = BCoverGenerator(debug=args.debug)
    
    print("🎨 中文书籍B站封面生成器")
    print("=" * 50)
    
    # 状态检查模式
    if args.status:
        generator.check_status()
        return
    
    # 处理封面生成
    try:
        stats = generator.process_covers(
            max_count=args.count,
            force=args.force,
            target_uuid=args.uuid,
            preview=args.preview
        )
        
        print(f"\n📊 处理完成统计:")
        print(f"  🎯 目标文件: {stats.get('total_targets', 0)} 个")
        print(f"  ✅ 成功生成: {stats.get('successful', 0)} 个")
        print(f"  ❌ 生成失败: {stats.get('failed', 0)} 个")
        print(f"  ⏭️ 跳过处理: {stats.get('skipped', 0)} 个")
        
        if args.preview:
            print(f"  👁️  预览文件: {stats.get('preview', 0)} 个")
        
        if stats.get('total_targets', 0) > 0 and not args.preview:
            success_rate = stats.get('successful', 0) / stats.get('total_targets', 1) * 100
            print(f"  📈 成功率: {success_rate:.1f}%")
            
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断处理")
    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main() 
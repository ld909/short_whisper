#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文年份表述修正脚本 - refine_chinese_year_chunks.py

功能说明：
1. 读取 chunk_book_summaries.py 生成的中文chunk文件
2. 使用 Google Gemini AI 修正其中不符合中文朗读习惯的年份表述  
3. 将修正后的内容保存到新的目录结构中
4. 支持断点续传，跳过已处理的文件
5. 自动排除Mac系统产生的点开头文件

输入: /home/dhl/Documents/book/zh-before-refine/{uuid}/{chunk_index}.txt
输出: /home/dhl/Documents/book/zh-after-refine/{uuid}/{chunk_index}.txt
"""

import os
import sys
import time
import argparse
import glob
from tqdm import tqdm

# 导入Google Gemini相关模块
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ 缺少依赖模块，请安装: pip install google-genai")
    sys.exit(1)


def setup_gemini_client():
    """设置Google Gemini客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")
    if not api_key:
        print("❌ 错误: 未找到API密钥")
        print("请设置环境变量UNI_API_KEY")
        sys.exit(1)

    try:
        client = genai.Client(
            http_options=types.HttpOptions(base_url="https://api.uniapi.io/gemini"),
            api_key=api_key,
        )
        return client
    except Exception as e:
        print(f"❌ 初始化Gemini客户端时出错: {e}")
        sys.exit(1)


class ChineseYearRefiner:
    """中文年份表述修正器"""

    def __init__(self, debug=False):
        self.debug = debug
        self.input_base_dir = "/home/dhl/Documents/book/zh-before-refine"
        self.output_base_dir = "/home/dhl/Documents/book/zh-after-refine"
        
        # 确保输出目录存在
        os.makedirs(self.output_base_dir, exist_ok=True)

        # 设置系统提示词
        self.system_instruction = [
            "你是一个中文年份表述修正助手。你的任务是检查我提供的文本，并仅对其中不符合中文朗读习惯的年份表述进行修正。请严格遵守以下规则：",
            "年份修正：将一百一十这类读法修正为一一零的逐字读法。例如，公元一百一十年应修正为公元一一零年；两千零二十五年应修正为二零二五年。",
            "保留原文：除了修正年份的中文写法，不要修改、增添或删除文本中的任何其他内容。",
            "使用中文数字：修正后的年份必须使用中文数字（如：一、二、三、零），不得使用阿拉伯数字（如：1、2、3、0）。",
            "非年份数字：如果文本中的中文数字不是年份，请勿修改。",
            "无修改时的返回值：如果提供的文本中没有需要修正的年份，请直接返回数字111，不要返回任何其他内容。",
            "直接输出：直接返回修正后的完整文本或111，不要包含任何解释或说明。"
        ]

        # 设置Gemini客户端
        self.client = setup_gemini_client()
        print(f"📁 输入目录: {self.input_base_dir}")
        print(f"📁 输出目录: {self.output_base_dir}")

    def get_available_uuid_dirs(self):
        """获取所有可用的UUID目录"""
        uuid_dirs = {}
        if not os.path.exists(self.input_base_dir):
            print(f"❌ 输入目录不存在: {self.input_base_dir}")
            return uuid_dirs

        for item in os.listdir(self.input_base_dir):
            # 排除以点开头的文件（Mac系统文件）
            if item.startswith("."):
                continue

            item_path = os.path.join(self.input_base_dir, item)
            if os.path.isdir(item_path):
                # 简单验证UUID格式（36字符，包含4个连字符）
                if len(item) == 36 and item.count("-") == 4:
                    uuid_dirs[item] = item_path
                    if self.debug:
                        print(f"✅ 发现UUID目录: {item}")

        print(f"📁 找到 {len(uuid_dirs)} 个UUID目录")
        return uuid_dirs

    def get_chunk_files_in_uuid(self, uuid_val, uuid_path):
        """获取指定UUID目录下的所有chunk文件"""
        chunk_files = {}
        chunk_pattern = os.path.join(uuid_path, "*.txt")
        txt_files = glob.glob(chunk_pattern)

        for file_path in txt_files:
            basename = os.path.basename(file_path)
            # 排除以点开头的文件
            if basename.startswith("."):
                continue

            if basename.endswith(".txt"):
                chunk_index = basename[:-4]
                try:
                    # 验证chunk_index是数字
                    int(chunk_index)
                    chunk_files[chunk_index] = file_path
                    if self.debug:
                        print(f"  ✅ 发现chunk文件: {chunk_index}.txt")
                except ValueError:
                    if self.debug:
                        print(f"  ⚠️ 跳过非数字文件名: {basename}")

        return chunk_files

    def get_all_chunk_files(self):
        """获取所有可处理的chunk文件"""
        all_chunks = {}
        uuid_dirs = self.get_available_uuid_dirs()

        for uuid_val, uuid_path in uuid_dirs.items():
            chunk_files = self.get_chunk_files_in_uuid(uuid_val, uuid_path)
            if chunk_files:
                all_chunks[uuid_val] = chunk_files
                if self.debug:
                    print(f"📁 UUID {uuid_val}: {len(chunk_files)} 个chunk文件")

        total_chunks = sum(len(chunks) for chunks in all_chunks.values())
        print(f"📊 总共找到 {total_chunks} 个chunk文件在 {len(all_chunks)} 个UUID目录中")
        return all_chunks

    def get_existing_output_files(self):
        """获取已存在的输出文件"""
        existing_files = set()
        if not os.path.exists(self.output_base_dir):
            return existing_files

        for uuid_dir in os.listdir(self.output_base_dir):
            # 排除点文件
            if uuid_dir.startswith("."):
                continue

            uuid_path = os.path.join(self.output_base_dir, uuid_dir)
            if os.path.isdir(uuid_path):
                for file_name in os.listdir(uuid_path):
                    if file_name.startswith("."):
                        continue
                    if file_name.endswith(".txt"):
                        chunk_index = file_name[:-4]
                        try:
                            int(chunk_index)  # 验证是数字
                            file_key = f"{uuid_dir}/{chunk_index}"
                            existing_files.add(file_key)
                            if self.debug:
                                print(f"✅ 发现已存在文件: {file_key}")
                        except ValueError:
                            continue

        print(f"📊 找到 {len(existing_files)} 个已处理的文件")
        return existing_files

    def refine_text_with_gemini(self, text_content, uuid_val, chunk_index, max_retries=3):
        """使用Google Gemini修正文本中的年份表述"""
        if not text_content.strip():
            print(f"⚠️ 警告: {uuid_val}/{chunk_index} 内容为空，跳过处理")
            return text_content

        budget = 512  # Thinking budget for Gemini

        for attempt in range(max_retries):
            try:
                print(f"🤖 正在修正 {uuid_val}/{chunk_index} 的年份表述... (尝试 {attempt+1}/{max_retries})")

                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=text_content,
                    config=types.GenerateContentConfig(
                        system_instruction=self.system_instruction,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=budget, include_thoughts=True
                        ),
                    ),
                )

                result = response.text.strip()

                # 检查返回结果
                if result == "111":
                    # 无需修改，返回原文
                    print(f"✅ {uuid_val}/{chunk_index} 无需修正年份")
                    return text_content
                elif result and len(result) > 10:  # 确保生成了有意义的内容
                    print(f"✅ {uuid_val}/{chunk_index} 年份修正完成")
                    # 显示修正前后对比
                    if result != text_content:
                        print(f"📝 修正了年份表述 (长度: {len(text_content)} → {len(result)})")
                    return result
                else:
                    print(f"⚠️ 返回内容异常，重试... (结果: {result[:50]}...)")
                    continue

            except Exception as e:
                print(f"❌ 修正年份表述出错 (尝试 {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    retry_delay = (attempt + 1) * 3
                    print(f"⏳ 等待{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ 达到最大重试次数 ({max_retries})，返回原文")
                    return text_content

        return text_content

    def save_refined_chunk(self, uuid_val, chunk_index, refined_content):
        """保存修正后的chunk文件"""
        if not refined_content or not refined_content.strip():
            print(f"⚠️ 警告: {uuid_val}/{chunk_index} 修正后内容为空，跳过保存")
            return False

        # 创建UUID目录
        uuid_output_dir = os.path.join(self.output_base_dir, uuid_val)
        os.makedirs(uuid_output_dir, exist_ok=True)

        # 保存文件
        output_file_path = os.path.join(uuid_output_dir, f"{chunk_index}.txt")

        try:
            with open(output_file_path, "w", encoding="utf-8") as f:
                f.write(refined_content)

            # 验证文件是否成功写入
            if os.path.exists(output_file_path):
                file_size = os.path.getsize(output_file_path)
                print(f"💾 已保存到: {output_file_path} (大小: {file_size} 字节)")
                return True
            else:
                print(f"❌ 文件保存后未找到: {output_file_path}")
                return False

        except Exception as e:
            print(f"❌ 保存文件到 {output_file_path} 时出错: {e}")
            return False

    def get_all_chunk_files(self):
        """获取所有可处理的chunk文件"""
        all_chunks = {}
        uuid_dirs = self.get_available_uuid_dirs()

        for uuid_val, uuid_path in uuid_dirs.items():
            chunk_files = self.get_chunk_files_in_uuid(uuid_val, uuid_path)
            if chunk_files:
                all_chunks[uuid_val] = chunk_files
                if self.debug:
                    print(f"📁 UUID {uuid_val}: {len(chunk_files)} 个chunk文件")

        total_chunks = sum(len(chunks) for chunks in all_chunks.values())
        print(f"📊 总共找到 {total_chunks} 个chunk文件在 {len(all_chunks)} 个UUID目录中")
        return all_chunks

    def get_existing_output_files(self):
        """获取已存在的输出文件"""
        existing_files = set()
        if not os.path.exists(self.output_base_dir):
            return existing_files

        for uuid_dir in os.listdir(self.output_base_dir):
            # 排除点文件
            if uuid_dir.startswith("."):
                continue

            uuid_path = os.path.join(self.output_base_dir, uuid_dir)
            if os.path.isdir(uuid_path):
                for file_name in os.listdir(uuid_path):
                    if file_name.startswith("."):
                        continue
                    if file_name.endswith(".txt"):
                        chunk_index = file_name[:-4]
                        try:
                            int(chunk_index)  # 验证是数字
                            file_key = f"{uuid_dir}/{chunk_index}"
                            existing_files.add(file_key)
                            if self.debug:
                                print(f"✅ 发现已存在文件: {file_key}")
                        except ValueError:
                            continue

        print(f"📊 找到 {len(existing_files)} 个已处理的文件")
        return existing_files

    def process_chunks(self, max_count=None, force=False, target_uuid=None, preview_mode=False):
        """批量处理chunk文件，修正年份表述"""
        print("🔧 中文年份表述修正器")
        print(f"📁 输入目录: {self.input_base_dir}")
        print(f"📁 输出目录: {self.output_base_dir}")

        # 获取所有chunk文件
        all_chunks = self.get_all_chunk_files()
        if not all_chunks:
            print("❌ 没有找到可处理的chunk文件")
            print("💡 请确保运行 chunk_book_summaries.py --lang zh 生成中文chunk文件")
            return {"total_targets": 0, "successful": 0, "failed": 0, "skipped": 0}

        # 如果指定了特定UUID
        if target_uuid:
            if target_uuid in all_chunks:
                all_chunks = {target_uuid: all_chunks[target_uuid]}
                print(f"🎯 处理指定UUID: {target_uuid}")
            else:
                print(f"❌ 未找到指定的UUID: {target_uuid}")
                return {"total_targets": 0, "successful": 0, "failed": 0, "skipped": 0}

        # 获取已存在的输出文件
        existing_files = self.get_existing_output_files()

        # 构建需要处理的文件列表
        files_to_process = []
        for uuid_val, chunk_files in all_chunks.items():
            for chunk_index, input_file_path in chunk_files.items():
                file_key = f"{uuid_val}/{chunk_index}"
                
                if force or file_key not in existing_files:
                    files_to_process.append({
                        'uuid': uuid_val,
                        'chunk_index': chunk_index,
                        'input_path': input_file_path,
                        'file_key': file_key
                    })
                elif self.debug:
                    print(f"⏭️ 跳过已存在的文件: {file_key}")

        # 限制处理数量
        if max_count and len(files_to_process) > max_count:
            # 按UUID和chunk_index排序，保证处理顺序一致
            files_to_process.sort(key=lambda x: (x['uuid'], int(x['chunk_index'])))
            files_to_process = files_to_process[:max_count]

        if not files_to_process:
            print("🎉 所有chunk文件的年份表述都已修正完成！")
            total_files = sum(len(chunks) for chunks in all_chunks.values())
            return {
                "total_targets": 0,
                "successful": 0,
                "failed": 0,
                "skipped": total_files,
            }

        print(f"\n📊 处理统计:")
        total_files = sum(len(chunks) for chunks in all_chunks.values())
        print(f"总chunk文件: {total_files}")
        print(f"已处理文件: {len(existing_files)}")
        print(f"需要处理: {len(files_to_process)}")

        # 预览模式
        if preview_mode:
            print(f"\n📋 预览模式 - 将要处理的文件 (前10个):")
            for i, file_info in enumerate(files_to_process[:10]):
                print(f"  {i+1:2d}. {file_info['file_key']}")
                print(f"      输入: {file_info['input_path']}")
                output_path = os.path.join(self.output_base_dir, file_info['uuid'], f"{file_info['chunk_index']}.txt")
                print(f"      输出: {output_path}")
            if len(files_to_process) > 10:
                print(f"  ... 还有 {len(files_to_process) - 10} 个文件")
            return {
                "total_targets": 0,
                "successful": 0,
                "failed": 0,
                "preview": len(files_to_process),
            }

        # 开始处理
        success_count = 0
        failed_count = 0

        with tqdm(total=len(files_to_process), desc="🔧 修正年份表述") as pbar:
            for file_info in files_to_process:
                try:
                    uuid_val = file_info['uuid']
                    chunk_index = file_info['chunk_index']
                    input_path = file_info['input_path']

                    print(f"\n=== 处理 {uuid_val}/{chunk_index} ===")

                    # 读取原始内容
                    try:
                        with open(input_path, "r", encoding="utf-8") as f:
                            original_content = f.read()
                    except Exception as e:
                        print(f"❌ 读取文件失败 {input_path}: {e}")
                        failed_count += 1
                        pbar.update(1)
                        continue

                    print(f"📄 原始内容长度: {len(original_content)} 字符")

                    # 使用Gemini修正年份表述
                    refined_content = self.refine_text_with_gemini(
                        original_content, uuid_val, chunk_index
                    )

                    if refined_content:
                        # 保存修正后的内容
                        if self.save_refined_chunk(uuid_val, chunk_index, refined_content):
                            success_count += 1
                            print(f"✅ {uuid_val}/{chunk_index} 处理成功")
                            
                            # 显示修正差异（如果有）
                            if refined_content != original_content:
                                print(f"📝 内容已修正 (长度变化: {len(original_content)} → {len(refined_content)})")
                            else:
                                print(f"📝 内容无变化（无需修正年份）")
                        else:
                            failed_count += 1
                            print(f"❌ {uuid_val}/{chunk_index} 保存失败")
                    else:
                        failed_count += 1
                        print(f"❌ {uuid_val}/{chunk_index} 修正失败")

                except KeyboardInterrupt:
                    print("⏹️ 用户中断，程序停止")
                    break
                except Exception as e:
                    print(f"❌ 处理 {file_info['file_key']} 时出错: {e}")
                    failed_count += 1

                pbar.update(1)

                # API调用间隔，避免请求过快
                if file_info != files_to_process[-1]:  # 不是最后一个
                    time.sleep(1)

        # 最终统计
        print(f"\n🎯 年份表述修正完成!")
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {failed_count}")
        print(
            f"📊 成功率: {success_count/(success_count+failed_count)*100:.1f}%"
            if (success_count + failed_count) > 0
            else "N/A"
        )

        # 返回统计信息
        return {
            "total_targets": len(files_to_process),
            "successful": success_count,
            "failed": failed_count,
            "skipped": total_files - len(files_to_process),
        }

    def check_status(self):
        """检查当前状态"""
        print("📊 当前状态检查")
        print(f"📁 输入目录: {self.input_base_dir}")
        print(f"📁 输出目录: {self.output_base_dir}")

        all_chunks = self.get_all_chunk_files()
        existing_files = self.get_existing_output_files()

        total_files = sum(len(chunks) for chunks in all_chunks.values())
        processed_files = len(existing_files)
        pending_files = total_files - processed_files

        print(f"📁 UUID目录数量: {len(all_chunks)}")
        print(f"📄 总chunk文件: {total_files}")
        print(f"✅ 已处理文件: {processed_files}")
        print(f"⏳ 待处理文件: {pending_files}")

        if pending_files > 0:
            print(f"\n📈 处理进度: {processed_files}/{total_files} ({processed_files/total_files*100:.1f}%)")

        # 显示每个UUID的处理状态
        if all_chunks:
            print(f"\n📋 各UUID处理状态:")
            for uuid_val, chunk_files in sorted(all_chunks.items()):
                total_chunks = len(chunk_files)
                processed_chunks = sum(1 for chunk_index in chunk_files.keys() 
                                     if f"{uuid_val}/{chunk_index}" in existing_files)
                print(f"  {uuid_val}: {processed_chunks}/{total_chunks} ({processed_chunks/total_chunks*100:.0f}%)")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🔧 中文年份表述修正器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python refine_chinese_year_chunks.py                     # 处理所有文件
  python refine_chinese_year_chunks.py --count 50          # 处理50个文件
  python refine_chinese_year_chunks.py --force             # 强制重新处理
  python refine_chinese_year_chunks.py --uuid abc123       # 处理指定UUID
  python refine_chinese_year_chunks.py --preview           # 预览模式
  python refine_chinese_year_chunks.py --status            # 检查状态

注意:
- 需要设置环境变量 UNI_API_KEY
- 确保已运行 chunk_book_summaries.py --lang zh 生成中文chunk文件

系统提示词功能:
- 修正年份表述: 将"一百一十年"修正为"一一零年"
- 保留原文: 除年份外不修改任何其他内容
- 无需修改时: LLM返回"111"，脚本保持原文不变
        """,
    )
    
    parser.add_argument("--count", "-c", type=int, help="要处理的文件数量（默认处理所有）")
    parser.add_argument("--force", "-f", action="store_true", help="强制重新处理已存在的文件")
    parser.add_argument("--uuid", "-u", help="只处理指定UUID的文件")
    parser.add_argument("--debug", "-d", action="store_true", help="启用调试模式")
    parser.add_argument("--status", "-s", action="store_true", help="检查当前处理状态")
    parser.add_argument("--preview", "-p", action="store_true", help="预览模式，只显示会处理哪些文件")

    args = parser.parse_args()

    # 创建修正器实例
    refiner = ChineseYearRefiner(debug=args.debug)

    print("🔧 中文年份表述修正器")
    print("=" * 50)

    # 状态检查模式
    if args.status:
        refiner.check_status()
        return

    # 处理chunk文件
    try:
        stats = refiner.process_chunks(
            max_count=args.count, 
            force=args.force, 
            target_uuid=args.uuid,
            preview_mode=args.preview
        )

        print(f"\n📊 处理完成统计:")
        if args.preview:
            print(f"  📋 预览文件: {stats.get('preview', 0)} 个")
        else:
            print(f"  🎯 目标文件: {stats.get('total_targets', 0)} 个")
            print(f"  ✅ 成功修正: {stats.get('successful', 0)} 个")
            print(f"  ❌ 修正失败: {stats.get('failed', 0)} 个")
            print(f"  ⏭️ 跳过处理: {stats.get('skipped', 0)} 个")

            if stats.get("total_targets", 0) > 0:
                success_rate = (
                    stats.get("successful", 0) / stats.get("total_targets", 1) * 100
                )
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
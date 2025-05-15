#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
多语言视频标题简化工具

功能说明:
此脚本用于将视频标题简化为更具吸引力的短标题，支持多种语言（英语、日语、越南语、韩语）。
使用OpenAI API通过uniapi.io进行处理，特别针对简化标题优化，支持并发处理和断点续传。

输入目录:
- 标题文件：[媒体路径]/buda_videos_youtube/multi_lang_txt/[频道名称]/[语言代码]/[视频名].txt (第一行为标题)

输出目录:
- 简化标题: [媒体路径]/buda_videos_youtube/title_shorten_multi_lang/[频道名称]/[语言代码]/[视频名].txt

使用方法:
1. 基本使用: python shorten_titles_multi_lang.py
2. 指定目标语言: python shorten_titles_multi_lang.py -l en ja
3. 强制重新生成: python shorten_titles_multi_lang.py -f
4. 设置并发数: python shorten_titles_multi_lang.py -w 5
5. 单视频处理: python shorten_titles_multi_lang.py -s 频道名/视频名

注意:
- 需要设置环境变量UNI_API_KEY以提供OpenAI API密钥，或在.env文件中设置
- 脚本支持断点续传，中断后可从上次停止的位置继续处理
"""

import os
import argparse
import platform
import concurrent.futures
import sys
from tqdm import tqdm
from openai import OpenAI
try:
    from dotenv import load_dotenv
    # 尝试加载.env文件中的环境变量
    load_dotenv()
except ImportError:
    print("提示: 如需使用.env文件，请安装python-dotenv: pip install python-dotenv")

def get_base_path():
    """根据操作系统类型返回对应的基础路径"""
    if platform.system() == "Darwin":  # macOS
        return "/Volumes/dhl/buda_videos_youtube"
    else:  # 默认为Linux/Ubuntu
        return "/media/dhl/buda_videos_youtube"

# 定义全局路径变量
BASE_PATH = get_base_path()
# 输入多语言TXT目录
INPUT_TXT_PATH = os.path.join(BASE_PATH, "multi_lang_txt")
# 输出简化标题目录
OUTPUT_TITLE_PATH = os.path.join(BASE_PATH, "title_shorten_multi_lang")
# 支持的语言代码
SUPPORTED_LANGUAGES = ["en", "ja", "vi", "ko"]
# 语言代码到完整语言名称的映射
LANGUAGE_NAMES = {"en": "English", "ja": "Japanese", "vi": "Vietnamese", "ko": "Korean"}

def setup_openai_client():
    """设置OpenAI客户端并验证API密钥"""
    api_key = os.environ.get("UNI_API_KEY")

    if not api_key:
        print("错误: 未找到OpenAI API密钥")
        print("请设置环境变量UNI_API_KEY或在.env文件中提供API密钥")
        print("例如: 在.env文件中添加 UNI_API_KEY='your-api-key'")
        print("或者: export UNI_API_KEY='your-api-key'")
        sys.exit(1)

    try:
        client = OpenAI(base_url="https://api.uniapi.io/v1", api_key=api_key)
        return client
    except Exception as e:
        print(f"初始化OpenAI客户端时出错: {e}")
        sys.exit(1)

def get_original_title(channel, video_name, language):
    """获取原始标题"""
    # 构建输入文件路径
    input_file_path = os.path.join(INPUT_TXT_PATH, channel, language, f"{video_name}.txt")
    
    if not os.path.exists(input_file_path):
        print(f"输入文件不存在: {input_file_path}")
        return None
    
    try:
        with open(input_file_path, "r", encoding="utf-8") as f:
            # 读取第一行作为标题
            lines = f.readlines()
            if not lines:
                print(f"文件为空: {input_file_path}")
                return None
            
            title = lines[0].strip()
            return title
    except Exception as e:
        print(f"读取原始标题时出错: {e}")
        return None

def shorten_title(title, language, client, max_retries=3):
    """使用OpenAI API简化标题"""
    if not title:
        return None
    
    language_name = LANGUAGE_NAMES.get(language, "English")
    
    system_prompt = f"""
你是一个短视频营销大师，能够将一个长标题变成非常有吸引力的短标题，同时满足：
1, 吸引观众点击，新标题足够吸引人
2,使用{language_name}返回结果
3,总长度length,在90以内
4,言简意赅，直切主题
直接返回你简化后对应{language_name}的结果，不要带任何其他内容。
"""
    
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="gpt-4.1-mini",
                max_tokens=200,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": title}
                ]
            )
            
            result = completion.choices[0].message.content.strip()
            
            # 确保结果不超过90个字符
            if len(result) > 90:
                print(f"警告: 生成的标题超过90个字符，长度为{len(result)}字符，尝试截断")
                result = result[:90]
            
            return result
        except Exception as e:
            print(f"简化标题出错 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("等待2秒后重试...")
                import time
                time.sleep(2)  # 添加延迟，避免过快请求
    
    print(f"达到最大重试次数 ({max_retries})，返回原标题")
    return title

def process_title(channel, video_name, language, client, force=False):
    """处理单个视频标题"""
    # 构建输出文件路径
    output_dir = os.path.join(OUTPUT_TITLE_PATH, channel, language)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    output_file = os.path.join(output_dir, f"{video_name}.txt")
    
    # 如果输出文件已存在且不强制重新生成，则跳过
    if os.path.exists(output_file) and not force:
        print(f"输出文件已存在，跳过: {output_file}")
        return True
    
    # 获取原始标题
    original_title = get_original_title(channel, video_name, language)
    if not original_title:
        print(f"无法获取原始标题，跳过: {channel}/{video_name}/{language}")
        return False
    
    print(f"处理视频: {video_name}, 语言: {language}")
    print(f"原始标题: {original_title}")
    
    # 简化标题
    shortened_title = shorten_title(original_title, language, client)
    if not shortened_title:
        print(f"简化标题失败，跳过: {channel}/{video_name}/{language}")
        return False
    
    print(f"简化标题: {shortened_title}")
    
    # 保存简化标题
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(shortened_title)
        
        print(f"成功保存简化标题: {output_file}")
        return True
    except Exception as e:
        print(f"保存简化标题时出错: {e}")
        return False

def process_video_all_languages(channel, video_name, languages, client, force=False):
    """处理一个视频的所有语言版本"""
    success_count = 0
    
    for language in languages:
        if process_title(channel, video_name, language, client, force):
            success_count += 1
    
    return success_count

def process_all_channels(languages=None, force=False, max_workers=3, client=None):
    """处理所有频道的所有视频"""
    if languages is None:
        languages = SUPPORTED_LANGUAGES
    
    # 验证语言是否支持
    for lang in languages[:]:  # 创建一个副本以便在迭代时修改
        if lang not in SUPPORTED_LANGUAGES:
            print(f"警告: 不支持的语言 {lang}，将被忽略")
            languages.remove(lang)
    
    if not languages:
        print("错误: 没有指定任何有效的语言")
        return
    
    # 检查输入路径是否存在
    if not os.path.exists(INPUT_TXT_PATH):
        print(f"错误: 输入路径不存在: {INPUT_TXT_PATH}")
        return
    
    # 获取所有频道目录
    channels = [d for d in os.listdir(INPUT_TXT_PATH) 
               if os.path.isdir(os.path.join(INPUT_TXT_PATH, d))]
    
    if not channels:
        print(f"在 {INPUT_TXT_PATH} 中未找到任何频道目录")
        return
    
    print(f"找到 {len(channels)} 个频道目录")
    
    # 处理每个频道
    for channel in channels:
        channel_path = os.path.join(INPUT_TXT_PATH, channel)
        print(f"\n处理频道: {channel}")
        
        # 创建任务列表
        tasks = []
        
        # 获取当前频道下的所有语言目录
        lang_dirs = [d for d in os.listdir(channel_path)
                    if os.path.isdir(os.path.join(channel_path, d)) and d in languages]
        
        if not lang_dirs:
            print(f"在频道 {channel} 中未找到任何支持的语言目录")
            continue
        
        # 获取所有视频名称
        all_videos = set()
        for lang in lang_dirs:
            lang_path = os.path.join(channel_path, lang)
            videos = [
                f[:-4]  # 去除.txt后缀
                for f in os.listdir(lang_path)
                if f.endswith(".txt") and os.path.isfile(os.path.join(lang_path, f))
            ]
            all_videos.update(videos)
        
        print(f"找到 {len(all_videos)} 个视频")
        
        # 添加任务
        for video_name in all_videos:
            for lang in lang_dirs:
                # 检查该语言下是否有对应的TXT文件
                txt_path = os.path.join(channel_path, lang, f"{video_name}.txt")
                if not os.path.exists(txt_path):
                    continue
                
                # 构建输出文件路径
                output_dir = os.path.join(OUTPUT_TITLE_PATH, channel, lang)
                output_file = os.path.join(output_dir, f"{video_name}.txt")
                
                # 如果输出文件已存在且不强制重新生成，则跳过
                if os.path.exists(output_file) and not force:
                    continue
                
                # 添加任务
                tasks.append((channel, video_name, lang))
        
        print(f"找到 {len(tasks)} 个待处理任务")
        
        # 并发处理任务
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_title, channel, video_name, language, client, force): 
                (channel, video_name, language)
                for channel, video_name, language in tasks
            }
            
            for future in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc=f"处理 {channel} 频道",
            ):
                channel, video_name, language = futures[future]
                try:
                    success = future.result()
                    if success:
                        print(f"成功处理 {channel}/{video_name}/{language}")
                    else:
                        print(f"处理失败 {channel}/{video_name}/{language}")
                except Exception as e:
                    print(f"处理 {channel}/{video_name}/{language} 时出错: {e}")

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="生成多语言简化视频标题")
    
    # 添加命令行参数
    parser.add_argument(
        "-l",
        "--languages",
        nargs="+",
        choices=SUPPORTED_LANGUAGES,
        default=SUPPORTED_LANGUAGES,
        help=f"目标语言列表 (默认: {' '.join(SUPPORTED_LANGUAGES)})",
    )
    parser.add_argument(
        "-f", "--force", action="store_true", help="强制重新生成，即使输出文件已存在"
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=3, help="并发处理的工作线程数，默认为3"
    )
    parser.add_argument(
        "-s", "--single", type=str, help="只处理指定的单个视频，格式: 频道名/视频名"
    )
    
    # 解析命令行参数
    args = parser.parse_args()
    
    # 设置OpenAI客户端
    client = setup_openai_client()
    
    # 处理单个视频模式
    if args.single:
        if "/" not in args.single:
            print("错误: 单个视频参数格式应为 '频道名/视频名'")
            return
        
        channel, video_name = args.single.split("/", 1)
        
        print(f"处理单个视频: {channel}/{video_name}")
        success_count = process_video_all_languages(channel, video_name, args.languages, client, args.force)
        
        print(f"处理完成，成功生成 {success_count}/{len(args.languages)} 个语言版本")
    else:
        # 处理所有频道和视频
        process_all_channels(args.languages, args.force, args.workers, client)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文年份表述修正测试脚本 - test_year_refiner.py

功能说明：
1. 随机生成包含错误中文年份表述的测试句子
2. 使用 ChineseYearRefiner 类进行修正测试
3. 显示修正前后的对比结果
4. 验证修正功能是否正常工作
"""

import os
import sys
import random
import argparse
from typing import List, Dict

# 添加当前目录到path，以便导入refine_chinese_year_chunks模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from refine_chinese_year_chunks import ChineseYearRefiner, setup_gemini_client
except ImportError as e:
    print(f"❌ 导入模块失败: {e}")
    print("请确保 refine_chinese_year_chunks.py 在同一目录下")
    sys.exit(1)


class YearRefinerTester:
    """中文年份表述修正测试器"""
    
    def __init__(self, debug=False):
        self.debug = debug
        
        # 初始化年份修正器
        try:
            self.refiner = ChineseYearRefiner(debug=debug)
            print("✅ 年份修正器初始化成功")
        except Exception as e:
            print(f"❌ 年份修正器初始化失败: {e}")
            sys.exit(1)
            
        # 错误年份写法模板
        self.wrong_year_patterns = [
            "一百一十",      # 110
            "一百二十",      # 120
            "一百五十",      # 150
            "二百",          # 200
            "二百五十",      # 250
            "三百",          # 300
            "四百",          # 400
            "五百",          # 500
            "六百",          # 600
            "七百",          # 700
            "八百",          # 800
            "九百",          # 900
            "一千",          # 1000
            "一千二百",      # 1200
            "一千五百",      # 1500
            "一千八百",      # 1800
            "一千九百",      # 1900
            "两千",          # 2000
            "两千零五",      # 2005
            "两千零十",      # 2010
            "两千零二十",    # 2020
            "两千零二十五",  # 2025
        ]
        
        # 正确年份写法对应表（用于验证）
        self.correct_year_mapping = {
            "一百一十": "一一零",
            "一百二十": "一二零", 
            "一百五十": "一五零",
            "二百": "二零零",
            "二百五十": "二五零",
            "三百": "三零零",
            "四百": "四零零",
            "五百": "五零零",
            "六百": "六零零",
            "七百": "七零零",
            "八百": "八零零",
            "九百": "九零零",
            "一千": "一零零零",
            "一千二百": "一二零零",
            "一千五百": "一五零零",
            "一千八百": "一八零零",
            "一千九百": "一九零零",
            "两千": "二零零零",
            "两千零五": "二零零五",
            "两千零十": "二零一零",
            "两千零二十": "二零二零",
            "两千零二十五": "二零二五",
        }
        
        # 句子模板
        self.sentence_templates = [
            "在公元{year}年，中国发生了重大历史事件。",
            "据史书记载，{year}年是一个重要的转折点。",
            "这位皇帝在{year}年登基，开创了新的王朝。",
            "考古发现表明，{year}年左右这里曾经是繁荣的城市。",
            "历史学家认为{year}年是这个朝代的鼎盛时期。",
            "文献显示，{year}年发生了著名的农民起义。",
            "根据古籍记录，{year}年出现了罕见的天文现象。",
            "这座寺庙建于{year}年，至今已有悠久的历史。",
            "诗人李白在{year}年写下了这首著名的诗篇。",
            "科举制度在{year}年得到了重要的改革。",
            "据传说，{year}年这里发生了神奇的故事。",
            "史学家将{year}年定为这一历史时期的开端。",
        ]
        
        # 非年份的中文数字（不应该被修改）
        self.non_year_numbers = [
            "三个苹果",
            "五本书", 
            "八只猫",
            "十二个月",
            "二十四小时",
            "三十六计",
            "七十二变",
            "九十九个问题",
        ]

    def generate_test_sentences(self, count: int = None) -> List[str]:
        """生成测试句子"""
        if count is None:
            count = random.randint(3, 5)
            
        sentences = []
        
        for _ in range(count):
            # 随机选择一个错误年份写法
            wrong_year = random.choice(self.wrong_year_patterns)
            
            # 随机选择一个句子模板
            template = random.choice(self.sentence_templates)
            
            # 生成句子
            sentence = template.format(year=wrong_year)
            sentences.append(sentence)
            
        return sentences

    def generate_mixed_content(self) -> str:
        """生成包含年份和非年份数字的混合内容"""
        content_parts = []
        
        # 添加一些包含年份的句子
        year_sentences = self.generate_test_sentences(2)
        content_parts.extend(year_sentences)
        
        # 添加一些包含非年份数字的句子
        non_year_sentences = [
            f"这个故事讲述了{random.choice(self.non_year_numbers)}的传说。",
            f"古代的工匠用了{random.choice(self.non_year_numbers)}完成这项工程。"
        ]
        content_parts.extend(non_year_sentences)
        
        # 随机打乱顺序
        random.shuffle(content_parts)
        
        return "\n".join(content_parts)

    def test_single_refinement(self, test_content: str, test_id: str = "1") -> Dict:
        """测试单个文本的年份修正"""
        print(f"\n=== 测试 {test_id} ===")
        print(f"📝 原始内容:")
        print(f"   {test_content}")
        
        try:
            # 使用修正器处理文本
            refined_content = self.refiner.refine_text_with_gemini(
                test_content, 
                f"test_{test_id}", 
                "chunk_1"
            )
            
            # 分析结果
            result = {
                "original": test_content,
                "refined": refined_content,
                "changed": refined_content != test_content,
                "success": True,
                "error": None
            }
            
            print(f"🔧 修正结果:")
            if result["changed"]:
                print(f"   {refined_content}")
                print(f"✅ 内容已修正")
                
                # 检查是否正确修正
                self.analyze_changes(test_content, refined_content)
            else:
                print(f"   {refined_content}")
                print(f"ℹ️ 内容无变化（可能无需修正）")
                
            return result
            
        except Exception as e:
            print(f"❌ 修正失败: {e}")
            return {
                "original": test_content,
                "refined": None,
                "changed": False,
                "success": False,
                "error": str(e)
            }

    def analyze_changes(self, original: str, refined: str):
        """分析修正前后的变化"""
        print(f"\n📊 变化分析:")
        
        # 检查是否包含已知的错误年份模式
        found_patterns = []
        for wrong_pattern in self.wrong_year_patterns:
            if wrong_pattern in original:
                found_patterns.append(wrong_pattern)
                correct_pattern = self.correct_year_mapping.get(wrong_pattern, "未知")
                
                if correct_pattern in refined:
                    print(f"   ✅ {wrong_pattern} → {correct_pattern} (正确修正)")
                elif wrong_pattern in refined:
                    print(f"   ❌ {wrong_pattern} → 未修正")
                else:
                    print(f"   ⚠️ {wrong_pattern} → 可能修正但格式不在预期范围内")
        
        if not found_patterns:
            print(f"   ℹ️ 未发现预定义的错误年份模式")
            
        # 检查长度变化
        len_diff = len(refined) - len(original)
        if len_diff != 0:
            print(f"   📏 长度变化: {len(original)} → {len(refined)} (差异: {len_diff:+d})")

    def run_batch_test(self, test_count: int = 5):
        """运行批量测试"""
        print(f"🧪 开始批量测试 (共 {test_count} 轮)")
        print("=" * 60)
        
        all_results = []
        success_count = 0
        changed_count = 0
        
        for i in range(test_count):
            # 生成测试内容
            if i % 3 == 0:  # 每3轮中有1轮使用混合内容
                test_content = self.generate_mixed_content()
            else:
                test_sentences = self.generate_test_sentences()
                test_content = "\n".join(test_sentences)
            
            # 执行测试
            result = self.test_single_refinement(test_content, str(i + 1))
            all_results.append(result)
            
            if result["success"]:
                success_count += 1
                if result["changed"]:
                    changed_count += 1
        
        # 输出总体统计
        print(f"\n" + "=" * 60)
        print(f"🎯 测试完成统计:")
        print(f"   📊 总测试数: {test_count}")
        print(f"   ✅ 成功执行: {success_count}")
        print(f"   🔧 内容修正: {changed_count}")
        print(f"   ❌ 执行失败: {test_count - success_count}")
        
        if success_count > 0:
            success_rate = success_count / test_count * 100
            change_rate = changed_count / success_count * 100
            print(f"   📈 成功率: {success_rate:.1f}%")
            print(f"   📝 修正率: {change_rate:.1f}%")
        
        return all_results

    def test_specific_cases(self):
        """测试特定的边界情况"""
        print(f"\n🔍 特定案例测试")
        print("=" * 40)
        
        test_cases = [
            {
                "name": "纯年份句子",
                "content": "这件事发生在公元一千八百年左右。"
            },
            {
                "name": "多个年份",
                "content": "从一千年到两千年，历史跨越了一千年的时光。"
            },
            {
                "name": "年份与非年份混合",
                "content": "在一千二百年，这位皇帝用了三年时间统一了五个国家。"
            },
            {
                "name": "无年份内容",
                "content": "这个故事讲述了三个勇士和七把神剑的传说。"
            },
            {
                "name": "空内容",
                "content": ""
            },
            {
                "name": "纯标点符号",
                "content": "。，！？；："
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\n--- {test_case['name']} ---")
            result = self.test_single_refinement(
                test_case["content"], 
                f"case_{i+1}"
            )


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="🧪 中文年份表述修正测试器",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
使用示例:
  python test_year_refiner.py                      # 运行默认测试
  python test_year_refiner.py --count 10           # 运行10轮测试
  python test_year_refiner.py --specific           # 运行特定案例测试
  python test_year_refiner.py --debug              # 启用调试模式

注意:
- 需要设置环境变量 UNI_API_KEY
- 确保 refine_chinese_year_chunks.py 在同一目录
        """
    )
    
    parser.add_argument(
        "--count", "-c", 
        type=int, 
        default=5, 
        help="测试轮数（默认5轮）"
    )
    
    parser.add_argument(
        "--specific", "-s", 
        action="store_true", 
        help="运行特定边界案例测试"
    )
    
    parser.add_argument(
        "--debug", "-d", 
        action="store_true", 
        help="启用调试模式"
    )

    args = parser.parse_args()

    # 创建测试器
    try:
        tester = YearRefinerTester(debug=args.debug)
    except Exception as e:
        print(f"❌ 测试器初始化失败: {e}")
        return

    print("🧪 中文年份表述修正测试器")
    print("=" * 50)

    try:
        # 运行批量测试
        if not args.specific:
            tester.run_batch_test(args.count)
        
        # 运行特定案例测试
        if args.specific or args.count <= 3:
            tester.test_specific_cases()

    except KeyboardInterrupt:
        print("\n⏹️ 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()

    print("\n🏁 测试完成")


if __name__ == "__main__":
    main() 
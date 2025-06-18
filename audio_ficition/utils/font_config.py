#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一字体配置文件 - Sci-Fi风格字体设置

此配置文件确保所有主题（scifi, thriller, horror, fantasy, romance）
都使用相同的字体设计，保持视觉风格的一致性。

主要特点：
- 使用 Oxanium 字体系列（专为科幻风格设计）
- 统一的字体粗细、大小、颜色设置
- 支持多种字体权重选择
- 自动回退机制

字体设计理念：
Oxanium字体具有现代、科技感强的特点，非常适合：
- 科幻主题（原生匹配）
- 惊悚主题（增强未来感和紧张感）
- 奇幻主题（提供现代魔法科技感）
- 浪漫主题（现代都市浪漫风格）
- 恐怖主题（冷酷科技恐怖风格）
"""

import os
import platform
from typing import Dict, Tuple, Optional

# ============================================================================
# 统一字体配置 - 所有主题通用
# ============================================================================

# 🎨 Sci-Fi统一字体设置
UNIFIED_FONT_CONFIG = {
    # 字体基础设置
    "font_family": "Oxanium",
    "font_dir": "font/en/",  # 相对于utils目录的路径
    
    # 默认字体设置（推荐用于所有主题）
    "default_weight": "semi-bold",  # 半粗体，适中且现代感强
    "default_size": 50,             # 适合高清视频的字体大小
    "default_color": "FFFFFF",      # 纯白色，在深色背景上清晰可见
    
    # 描边设置（增强可读性）
    "outline_color": "000000",      # 黑色描边
    "outline_width": 2,             # 适中的描边宽度
    
    # 布局设置
    "margin_v": 20,                 # 底部边距
    "alignment": 2,                 # 底部居中对齐
    
    # 特效设置
    "fade_in_ms": 200,              # 淡入时间（毫秒）
    "fade_out_ms": 200,             # 淡出时间（毫秒）
}

# 🎯 字体权重映射 - Oxanium系列
OXANIUM_FONT_MAPPING = {
    # 字符串映射
    "extra-light": ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
    "light": ("Oxanium-Light.ttf", "Oxanium Light"),
    "normal": ("Oxanium-Regular.ttf", "Oxanium Regular"),
    "regular": ("Oxanium-Regular.ttf", "Oxanium Regular"),
    "medium": ("Oxanium-Medium.ttf", "Oxanium Medium"),
    "semi-bold": ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),  # 🌟 推荐默认
    "bold": ("Oxanium-Bold.ttf", "Oxanium Bold"),
    "extra-bold": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    "black": ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
}

# 数字权重映射（100-900）
OXANIUM_WEIGHT_MAPPING = {
    100: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
    200: ("Oxanium-ExtraLight.ttf", "Oxanium ExtraLight"),
    300: ("Oxanium-Light.ttf", "Oxanium Light"),
    400: ("Oxanium-Regular.ttf", "Oxanium Regular"),
    500: ("Oxanium-Medium.ttf", "Oxanium Medium"),
    600: ("Oxanium-SemiBold.ttf", "Oxanium SemiBold"),  # 🌟 默认
    700: ("Oxanium-Bold.ttf", "Oxanium Bold"),
    800: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
    900: ("Oxanium-ExtraBold.ttf", "Oxanium ExtraBold"),
}

# 🎬 主题特定微调（保持Oxanium基础，细微调整）
THEME_FONT_VARIATIONS = {
    "scifi": {
        "description": "科幻主题 - Oxanium原生适配",
        "weight": "semi-bold",
        "size": 50,
        "color": "FFFFFF",
        "outline_width": 2,
        "style_notes": "现代科技感，清晰锐利"
    },
    "thriller": {
        "description": "惊悚主题 - 增强紧张感",
        "weight": "semi-bold",
        "size": 50,
        "color": "FFFFFF",
        "outline_width": 2,
        "style_notes": "保持科技感，增强未来惊悚氛围"
    },
    "horror": {
        "description": "恐怖主题 - 冷酷科技恐怖",
        "weight": "semi-bold",
        "size": 50,
        "color": "FFFFFF",
        "outline_width": 2,
        "style_notes": "现代恐怖，科技冷酷感"
    },
    "fantasy": {
        "description": "奇幻主题 - 现代魔法科技",
        "weight": "semi-bold",
        "size": 50,
        "color": "FFFFFF",
        "outline_width": 2,
        "style_notes": "未来奇幻，科技魔法融合"
    },
    "romance": {
        "description": "浪漫主题 - 现代都市浪漫",
        "weight": "semi-bold",
        "size": 50,
        "color": "FFFFFF",
        "outline_width": 2,
        "style_notes": "现代浪漫，都市科技感"
    }
}

# ============================================================================
# 字体选择和配置函数
# ============================================================================

def get_unified_font_config(theme: str = None) -> Dict:
    """
    获取统一的字体配置
    
    Args:
        theme: 主题名称（可选），用于获取主题特定的微调
        
    Returns:
        Dict: 字体配置字典
    """
    config = UNIFIED_FONT_CONFIG.copy()
    
    # 如果指定了主题，应用主题微调
    if theme and theme in THEME_FONT_VARIATIONS:
        theme_config = THEME_FONT_VARIATIONS[theme]
        config.update({
            "weight": theme_config["weight"],
            "size": theme_config["size"],
            "color": theme_config["color"],
            "outline_width": theme_config["outline_width"]
        })
        print(f"🎨 {theme} 主题字体配置: {theme_config['description']}")
        print(f"   风格说明: {theme_config['style_notes']}")
    
    return config

def select_oxanium_font_by_weight(font_weight, font_dir: str = "font/en/") -> Tuple[str, str]:
    """
    根据字体粗细选择对应的Oxanium字体文件
    
    Args:
        font_weight: 字体粗细，可以是字符串或数字(100-900)
        font_dir: 字体文件目录
        
    Returns:
        Tuple: (font_file_path, font_display_name)
    """
    # 根据类型选择字体
    if isinstance(font_weight, str):
        font_key = font_weight.lower().replace("_", "-")
        if font_key in OXANIUM_FONT_MAPPING:
            font_file, font_name = OXANIUM_FONT_MAPPING[font_key]
        else:
            # 默认使用semi-bold
            font_file, font_name = OXANIUM_FONT_MAPPING["semi-bold"]
            print(f"⚠️  未知的字体粗细 '{font_weight}'，使用默认 Semi-Bold")
    elif isinstance(font_weight, int):
        # 找到最接近的权重
        closest_weight = min(OXANIUM_WEIGHT_MAPPING.keys(), 
                           key=lambda x: abs(x - font_weight))
        font_file, font_name = OXANIUM_WEIGHT_MAPPING[closest_weight]
        if font_weight != closest_weight:
            print(f"📊 字体权重 {font_weight} 映射到最接近的 {closest_weight}")
    else:
        # 默认使用semi-bold
        font_file, font_name = OXANIUM_FONT_MAPPING["semi-bold"]
        print(f"⚠️  无效的字体粗细类型，使用默认 Semi-Bold")
    
    font_path = os.path.join(font_dir, font_file)
    
    # 检查文件是否存在
    if not os.path.exists(font_path):
        print(f"⚠️  字体文件不存在 {font_path}，使用可变字体")
        font_path = os.path.join(font_dir, "Oxanium-VariableFont_wght.ttf")
        font_name = "Oxanium"
    
    return font_path, font_name

def get_font_dir_path(base_dir: str = None) -> str:
    """
    获取字体目录的绝对路径
    
    Args:
        base_dir: 基础目录，如果为None则自动检测
        
    Returns:
        str: 字体目录路径
    """
    if base_dir is None:
        # 自动检测当前脚本位置
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = current_dir
    
    font_dir = os.path.join(base_dir, UNIFIED_FONT_CONFIG["font_dir"])
    
    if not os.path.exists(font_dir):
        print(f"⚠️  字体目录不存在: {font_dir}")
        # 尝试相对路径
        relative_font_dir = UNIFIED_FONT_CONFIG["font_dir"]
        if os.path.exists(relative_font_dir):
            return relative_font_dir
    
    return font_dir

def validate_font_installation() -> bool:
    """
    验证Oxanium字体是否正确安装
    
    Returns:
        bool: 字体是否完整安装
    """
    font_dir = get_font_dir_path()
    missing_fonts = []
    
    print("🔍 检查Oxanium字体安装情况...")
    
    for weight, (font_file, font_name) in OXANIUM_FONT_MAPPING.items():
        font_path = os.path.join(font_dir, font_file)
        if os.path.exists(font_path):
            print(f"✅ {font_name}: {font_file}")
        else:
            missing_fonts.append((weight, font_file))
            print(f"❌ {font_name}: {font_file} (缺失)")
    
    if missing_fonts:
        print(f"\n⚠️  发现 {len(missing_fonts)} 个缺失的字体文件")
        print(f"📁 字体目录: {font_dir}")
        return False
    else:
        print(f"\n✅ 所有Oxanium字体文件完整！")
        print(f"📁 字体目录: {font_dir}")
        return True

def print_theme_font_summary():
    """打印所有主题的字体配置摘要"""
    print("\n🎨 所有主题统一字体配置摘要")
    print("=" * 60)
    print(f"字体家族: {UNIFIED_FONT_CONFIG['font_family']}")
    print(f"默认权重: {UNIFIED_FONT_CONFIG['default_weight']}")
    print(f"默认大小: {UNIFIED_FONT_CONFIG['default_size']}")
    print(f"默认颜色: #{UNIFIED_FONT_CONFIG['default_color']}")
    print(f"描边设置: {UNIFIED_FONT_CONFIG['outline_width']}px #{UNIFIED_FONT_CONFIG['outline_color']}")
    
    print("\n📋 各主题配置详情:")
    for theme, config in THEME_FONT_VARIATIONS.items():
        print(f"  🎬 {theme.upper():8} - {config['description']}")
        print(f"      {config['style_notes']}")

# ============================================================================
# 主函数（用于测试和验证）
# ============================================================================

def main():
    """主函数 - 用于测试和验证字体配置"""
    print("🎨 Sci-Fi统一字体配置系统")
    print("=" * 50)
    
    # 验证字体安装
    validate_font_installation()
    
    # 显示配置摘要
    print_theme_font_summary()
    
    # 测试字体选择
    print("\n🧪 字体选择测试:")
    test_weights = ["semi-bold", "bold", 600, 700]
    
    for weight in test_weights:
        font_path, font_name = select_oxanium_font_by_weight(weight)
        print(f"   {weight} -> {font_name}")
    
    print("\n✅ 字体配置验证完成！")

if __name__ == "__main__":
    main() 
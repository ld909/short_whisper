#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建📚 emoji风格的书籍图标PNG文件
"""

from PIL import Image, ImageDraw


def create_book_emoji_icon(size=64, output_path="book_emoji.png"):
    """
    创建📚 emoji风格的书籍图标

    Args:
        size: 图标大小（正方形）
        output_path: 输出路径
    """
    # 创建透明背景图片
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 📚 emoji通常是多本书叠放的样子
    margin = size // 10
    book_width = size - margin * 2
    book_height = int(book_width * 0.7)  # 书籍比较宽扁

    # 绘制三本叠放的书
    colors = [
        (0, 255, 0, 255),  # 绿色（匹配文字）
        (0, 200, 255, 255),  # 蓝色
        (255, 150, 0, 255),  # 橙色
    ]

    # 计算每本书的偏移
    book_offset = size // 16
    start_x = margin
    start_y = margin + book_offset

    # 从后往前绘制书籍（叠放效果）
    for i in range(3):
        x = start_x + i * book_offset
        y = start_y - i * book_offset
        color = colors[i]

        # 绘制书籍主体
        draw.rectangle(
            [x, y, x + book_width - i * book_offset, y + book_height - i * book_offset],
            fill=color,
            outline=(0, 0, 0, 100),
        )

        # 绘制书脊
        spine_width = (book_width - i * book_offset) // 8
        draw.rectangle(
            [x, y, x + spine_width, y + book_height - i * book_offset],
            fill=(color[0] // 2, color[1] // 2, color[2] // 2, 255),
        )

        # 绘制书页线条（只在可见部分）
        if i < 2:  # 只在前两本书上绘制线条
            line_margin = spine_width + 2
            line_spacing = max(2, (book_height - i * book_offset) // 8)
            for j in range(2):
                line_y = y + (book_height - i * book_offset) // 3 + j * line_spacing
                if line_y < y + book_height - i * book_offset - 2:
                    draw.line(
                        [
                            x + line_margin,
                            line_y,
                            x + book_width - i * book_offset - 2,
                            line_y,
                        ],
                        fill=(255, 255, 255, 150),
                        width=max(1, size // 64),
                    )

    # 保存图标
    img.save(output_path, "PNG")
    print(f"✅ 📚 emoji风格图标已创建: {output_path}")
    print(f"📐 图标大小: {size}x{size} pixels")


if __name__ == "__main__":
    # 创建📚 emoji风格图标
    sizes = [16, 24, 32, 48, 64, 96]
    for size in sizes:
        output_name = f"book_emoji_{size}.png"
        create_book_emoji_icon(size, output_name)

    # 创建默认图标，覆盖之前的book_icon.png
    create_book_emoji_icon(48, "book_icon.png")  # 默认使用48px，比之前小
    print("\n🎉 �� emoji风格图标创建完成!")

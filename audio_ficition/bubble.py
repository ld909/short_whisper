import cv2
import numpy as np
from PIL import Image, ImageDraw # Pillow库，用于绘制带透明度的图形
import random
import math  # 用于更高级的数学运算

class Bubble:
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.reset() # 初始化时调用reset来设置初始属性

    def reset(self):
        """重置泡泡到随机位置，并赋予新的随机属性"""
        # 随机位置策略 - 从四面八方生成泡泡
        random_start = random.random()
        if random_start < 0.25:  # 从底部
            self.x = random.randint(0, self.screen_width)
            self.y = self.screen_height + random.randint(20, 100)
        elif random_start < 0.5:  # 从顶部
            self.x = random.randint(0, self.screen_width)
            self.y = -random.randint(20, 100)
        elif random_start < 0.75:  # 从左侧
            self.x = -random.randint(20, 100)
            self.y = random.randint(0, self.screen_height)
        else:  # 从右侧
            self.x = self.screen_width + random.randint(20, 100)
            self.y = random.randint(0, self.screen_height)

        # 更小的泡泡尺寸
        self.radius = random.randint(8, 45)  # 稍微增加最大尺寸
        
        # 材质属性
        self.material = random.choice(['glass', 'crystal', 'soap', 'gel'])
        
        # 彩色泡泡基础颜色 (更丰富的颜色选择)
        if self.material == 'glass':
            # 玻璃质感 - 淡蓝、淡绿等透明感强的色调
            color_scheme = random.choice([
                (180, 220, 240),  # 浅蓝玻璃色
                (200, 240, 230),  # 浅绿玻璃色
                (220, 220, 240),  # 淡紫玻璃色
                (230, 240, 250),  # 白玻璃色
            ])
        elif self.material == 'crystal':
            # 水晶质感 - 更鲜艳的颜色
            color_scheme = random.choice([
                (160, 200, 250),  # 蓝水晶
                (250, 180, 220),  # 粉水晶
                (180, 250, 200),  # 绿水晶
                (250, 240, 180),  # 黄水晶
                (230, 180, 250),  # 紫水晶
            ])
        elif self.material == 'soap':
            # 肥皂泡质感 - 彩虹色
            color_scheme = random.choice([
                (255, 220, 240),  # 粉红肥皂泡
                (220, 240, 255),  # 蓝肥皂泡
                (240, 255, 220),  # 绿肥皂泡
                (255, 240, 220),  # 橙肥皂泡
            ])
        else:  # 'gel'
            # 凝胶质感 - 更饱和的颜色
            color_scheme = random.choice([
                (100, 200, 255),  # 蓝凝胶
                (255, 150, 200),  # 粉凝胶
                (150, 255, 180),  # 绿凝胶
                (255, 200, 100),  # 橙凝胶
            ])
        
        # 基本透明度策略
        if self.material == 'glass':
            self.alpha = random.randint(120, 180)  # 玻璃更透明
        elif self.material == 'crystal':
            self.alpha = random.randint(140, 200)  # 水晶较不透明
        elif self.material == 'soap':
            self.alpha = random.randint(100, 150)  # 肥皂泡较透明
        else:  # 'gel'
            self.alpha = random.randint(150, 210)  # 凝胶较不透明
            
        self.base_color = color_scheme
        
        # 随机调整移动速度和方向
        direction = random.random()
        if direction < 0.25:  # 主要向上移动
            self.dx = random.uniform(-0.3, 0.3)
            self.dy = random.uniform(-0.6, -0.2)
        elif direction < 0.5:  # 主要向下移动
            self.dx = random.uniform(-0.3, 0.3)
            self.dy = random.uniform(0.2, 0.6)
        elif direction < 0.75:  # 主要向左移动
            self.dx = random.uniform(-0.6, -0.2)
            self.dy = random.uniform(-0.3, 0.3)
        else:  # 主要向右移动
            self.dx = random.uniform(0.2, 0.6)
            self.dy = random.uniform(-0.3, 0.3)
            
        # 3D效果高级参数
        self.light_source_x = random.uniform(-1.0, 1.0)  # 光源X位置 (-1到1)
        self.light_source_y = random.uniform(-1.0, 1.0)  # 光源Y位置 (-1到1)
        self.light_source_z = random.uniform(0.5, 2.0)   # 光源Z位置 (正值表示在观察者前方)
        self.light_intensity = random.uniform(0.7, 0.95)  # 光照强度
        self.specular_power = random.uniform(3.0, 8.0)    # 高光锐度
        
        # 透明度渐变控制
        self.transparency_gradient = random.uniform(0.5, 0.9)
        
        # 彩虹效果初始化
        self.has_rainbow = random.random() < 0.3
        self.rainbow_intensity = random.uniform(0.1, 0.3)
        self.rainbow_width = random.uniform(0.1, 0.3)
        self.rainbow_offset = random.uniform(0, 6.28)
        
        # 泡泡材质特效
        self.has_inner_glow = random.random() < 0.95
        self.has_outer_rim = True  # 总是有边缘
        self.has_highlight = True  # 总是有高光
        
        # 多层光晕参数 - 增加更多层
        self.num_halos = random.randint(4, 7)  # 更多层光晕
        
        # 基于材质调整光晕属性
        if self.material == 'glass':
            # 玻璃 - 锐利清晰的光晕
            self.halo_alpha_factors = [0.9 * ((i+1) / self.num_halos) for i in range(self.num_halos)]
            self.halo_radius_factors = [1.02 + (i * 0.04) for i in range(self.num_halos)]
        elif self.material == 'crystal':
            # 水晶 - 多层次锐利光晕
            self.halo_alpha_factors = [0.85 * ((i+0.5) / self.num_halos) for i in range(self.num_halos)]
            self.halo_radius_factors = [1.025 + (i * 0.045) for i in range(self.num_halos)]
        elif self.material == 'soap':
            # 肥皂泡 - 彩虹色柔和光晕
            self.halo_alpha_factors = [0.75 * ((i+1.5) / self.num_halos) for i in range(self.num_halos)]
            self.halo_radius_factors = [1.03 + (i * 0.055) for i in range(self.num_halos)]
        else:  # 'gel'
            # 凝胶 - 密集光晕
            self.halo_alpha_factors = [0.95 * ((i+0.8) / self.num_halos) for i in range(self.num_halos)]
            self.halo_radius_factors = [1.015 + (i * 0.035) for i in range(self.num_halos)]
        
        # 增强脉动效果
        self.pulsate = random.random() < 0.8
        self.pulse_speed = random.uniform(0.005, 0.02)  # 更缓慢的脉动
        self.pulse_amount = random.uniform(0.02, 0.06)  # 更微妙的脉动
        self.pulse_phase = random.uniform(0, 6.28)
        
        # 增强质感的纹理效果 - 确保所有属性总是被初始化
        self.has_texture = random.random() < 0.4
        self.texture_type = random.choice(['noise', 'ripple', 'swirl'])
        self.texture_intensity = random.uniform(0.05, 0.15)
        self.texture_scale = random.uniform(1.0, 3.0)
        self.texture_speed = random.uniform(0.001, 0.005)
        self.texture_phase = random.uniform(0, 6.28)
        
        # 3D反光点设置 - 更先进的设置
        self.num_highlights = random.randint(2, 4)
        self.highlights = []
        
        # 主要高光 (通常位于泡泡上方偏左或偏右)
        main_highlight = {
            'offset_x': -self.radius * random.uniform(0.2, 0.4) * np.sign(self.light_source_x),
            'offset_y': -self.radius * random.uniform(0.2, 0.4) * np.sign(self.light_source_y),
            'radius': self.radius * random.uniform(0.15, 0.25),
            'intensity': random.uniform(0.9, 1.0),
            'blur': random.uniform(0.5, 1.0)  # 高光的模糊度
        }
        self.highlights.append(main_highlight)
        
        # 次要高光
        for _ in range(self.num_highlights - 1):
            # 根据主光源位置计算次要高光的位置
            angle = random.uniform(0, 6.28)
            distance = random.uniform(0.2, 0.7)
            secondary_highlight = {
                'offset_x': self.radius * distance * np.cos(angle),
                'offset_y': self.radius * distance * np.sin(angle),
                'radius': self.radius * random.uniform(0.05, 0.15),
                'intensity': random.uniform(0.6, 0.85),
                'blur': random.uniform(1.0, 2.0)  # 次要高光更模糊
            }
            self.highlights.append(secondary_highlight)
            
        # 边缘反射光参数 - 更精确控制
        self.rim_light_width = random.uniform(0.01, 0.04)
        self.rim_light_intensity = random.uniform(0.75, 0.95)
        self.rim_light_falloff = random.uniform(1.5, 3.0)  # 边缘光衰减速度

    def update(self):
        """更新泡泡的位置和效果"""
        self.x += self.dx
        self.y += self.dy
        
        # 脉动效果
        if self.pulsate:
            self.pulse_phase += self.pulse_speed
            if self.pulse_phase > 6.28:  # 2π
                self.pulse_phase -= 6.28
        
        # 更新纹理动画
        if self.has_texture:
            self.texture_phase += self.texture_speed
            if self.texture_phase > 6.28:
                self.texture_phase -= 6.28
                
        # 更新彩虹效果
        if self.has_rainbow:
            self.rainbow_offset += 0.01
            if self.rainbow_offset > 6.28:
                self.rainbow_offset -= 6.28
        
        # 重置超出屏幕的泡泡
        if ((self.dx < 0 and self.x + self.radius < 0) or
            (self.dx > 0 and self.x - self.radius > self.screen_width) or
            (self.dy < 0 and self.y + self.radius < 0) or
            (self.dy > 0 and self.y - self.radius > self.screen_height)):
            self.reset()

    def _calculate_bubble_texture(self, x, y, r, phase):
        """计算泡泡纹理在指定点的强度"""
        if not self.has_texture:
            return 0.0
            
        # 归一化坐标
        nx = (x - self.x) / r
        ny = (y - self.y) / r
        dist = np.sqrt(nx*nx + ny*ny)
        
        if self.texture_type == 'noise':
            # 简单随机噪声纹理
            angle = np.arctan2(ny, nx) * self.texture_scale + phase
            return self.texture_intensity * (0.5 + 0.5 * np.sin(angle * 8.0))
        elif self.texture_type == 'ripple':
            # 同心圆纹理
            return self.texture_intensity * (0.5 + 0.5 * np.sin(dist * 10.0 * self.texture_scale + phase))
        else:  # 'swirl'
            # 螺旋纹理
            angle = np.arctan2(ny, nx) + dist * 3.0 * self.texture_scale
            return self.texture_intensity * (0.5 + 0.5 * np.sin(angle * 4.0 + phase))

    def _calculate_rainbow_effect(self, radius_ratio, angle):
        """计算彩虹效果的RGB调整值"""
        if not self.has_rainbow:
            return (0, 0, 0)
        
        # 彩虹效果随角度和半径变化
        hue = (angle + self.rainbow_offset) % 6.28 / 6.28
        
        # 只在特定环状区域显示彩虹效果
        rainbow_center = 0.85  # 彩虹中心位置 (相对于半径)
        distance = abs(radius_ratio - rainbow_center)
        
        if distance > self.rainbow_width:
            return (0, 0, 0)
        
        # 彩虹强度随距离中心距离变化
        intensity = (1.0 - distance / self.rainbow_width) * self.rainbow_intensity
        
        # 将HSV转换为RGB增益
        h = hue * 6.0
        i = int(h)
        f = h - i
        p = 0
        q = (1 - f) * 255 * intensity
        t = f * 255 * intensity
        
        if i == 0:
            return (0, t, -q)
        elif i == 1:
            return (-q, 0, t)
        elif i == 2:
            return (t, -q, 0)
        elif i == 3:
            return (0, t, -q)
        elif i == 4:
            return (-q, 0, t)
        else:
            return (t, -q, 0)

    def draw(self, image_draw):
        """在Pillow ImageDraw对象上绘制超真实3D科幻梦幻泡泡"""
        try:
            # 计算当前实际半径 (如果有脉动效果)
            current_radius = self.radius
            if self.pulsate:
                pulse_factor = 1.0 + self.pulse_amount * np.sin(self.pulse_phase)
                current_radius = int(max(1, self.radius * pulse_factor))
            
            # 创建临时图层用于复杂光学效果
            temp_size = int(current_radius * 2.5)
            temp_x_offset = int(self.x - temp_size/2)
            temp_y_offset = int(self.y - temp_size/2)
            
            # 1. 绘制外部多层光晕 (从外到内)
            for i in range(self.num_halos - 1, -1, -1):
                halo_radius = int(current_radius * self.halo_radius_factors[i])
                base_halo_alpha = int(self.alpha * self.halo_alpha_factors[i])
                
                # 计算基于位置的光晕强度变化
                # 光源的方向影响光晕的强度分布
                for angle_deg in range(0, 360, 5):  # 每5度采样一次
                    angle_rad = np.radians(angle_deg)
                    
                    # 计算当前角度的点相对于光源的位置
                    dx = np.cos(angle_rad)
                    dy = np.sin(angle_rad)
                    
                    # 计算该点接收到的光照强度
                    light_dot = dx * self.light_source_x + dy * self.light_source_y
                    light_factor = 0.5 + 0.5 * light_dot  # 从0.0到1.0映射
                    
                    # 应用特定于材质的光晕效果
                    if self.material == 'glass':
                        # 玻璃的锐利光晕
                        light_factor = max(0.01, light_factor) ** 0.7  # 提高对比度，确保非负
                    elif self.material == 'crystal':
                        # 水晶的棱角光晕
                        light_factor = 0.4 + 0.6 * light_factor
                        if angle_deg % 45 < 10:  # 每45度增强一次，模拟棱角
                            light_factor *= 1.3
                    elif self.material == 'soap':
                        # 肥皂泡的均匀光晕
                        light_factor = 0.7 + 0.3 * light_factor
                    else:  # 'gel'
                        # 凝胶的集中光晕
                        light_factor = max(0.01, light_factor) ** 1.5  # 降低对比度，确保非负
                    
                    # 安全限制：确保值在有效范围内
                    light_factor = max(0.0, min(1.0, light_factor))
                    
                    # 计算当前光晕点的透明度
                    halo_alpha = int(base_halo_alpha * light_factor)
                    
                    # 计算彩虹效果的色彩调整
                    radius_ratio = i / self.num_halos
                    rainbow_adjust = self._calculate_rainbow_effect(radius_ratio, angle_rad)
                    
                    # 计算当前角度的颜色 (基础颜色 + 光照影响 + 彩虹效果)
                    base_r, base_g, base_b = self.base_color
                    
                    # 根据距离中心的远近，计算颜色渐变
                    gradient_factor = i / self.num_halos
                    
                    # 特定于材质的颜色处理
                    if self.material == 'glass':
                        # 玻璃 - 向白色渐变
                        r = int(base_r + (255 - base_r) * gradient_factor * 0.5)
                        g = int(base_g + (255 - base_g) * gradient_factor * 0.5)
                        b = int(base_b + (255 - base_b) * gradient_factor * 0.5)
                    elif self.material == 'crystal':
                        # 水晶 - 保持鲜艳并略微向白色渐变
                        r = int(base_r + (255 - base_r) * gradient_factor * 0.3)
                        g = int(base_g + (255 - base_g) * gradient_factor * 0.3)
                        b = int(base_b + (255 - base_b) * gradient_factor * 0.3)
                    elif self.material == 'soap':
                        # 肥皂泡 - 彩虹色渐变
                        r = int(base_r * (1.0 - gradient_factor * 0.5) + 200 * gradient_factor * 0.5)
                        g = int(base_g * (1.0 - gradient_factor * 0.5) + 200 * gradient_factor * 0.5)
                        b = int(base_b * (1.0 - gradient_factor * 0.5) + 240 * gradient_factor * 0.5)
                    else:  # 'gel'
                        # 凝胶 - 保持饱和度并加强亮度
                        r = int(min(base_r * (1.0 + gradient_factor * 0.4), 255))
                        g = int(min(base_g * (1.0 + gradient_factor * 0.4), 255))
                        b = int(min(base_b * (1.0 + gradient_factor * 0.4), 255))
                    
                    # 应用彩虹调整
                    r = max(0, min(255, r + int(rainbow_adjust[0])))
                    g = max(0, min(255, g + int(rainbow_adjust[1])))
                    b = max(0, min(255, b + int(rainbow_adjust[2])))
                    
                    # 创建带透明度的颜色
                    halo_color = (r, g, b, halo_alpha)
                    
                    # 为当前角度绘制光晕点
                    x = self.x + halo_radius * np.cos(angle_rad)
                    y = self.y + halo_radius * np.sin(angle_rad)
                    
                    point_size = max(1, int(current_radius / 20))
                    point_bbox = [
                        int(x - point_size/2), int(y - point_size/2),
                        int(x + point_size/2), int(y + point_size/2)
                    ]
                    
                    # 为高性能，每5度画一个点，而不是连续的圆
                    image_draw.ellipse(point_bbox, fill=halo_color, outline=None)
                
            # 2. 绘制3D泡泡主体
            # 使用径向渐变和光照模型模拟3D效果
            for r in range(current_radius, 0, -max(1, current_radius // 20)):
                # 计算当前半径比例
                radius_ratio = r / current_radius
                
                # 基于材质的透明度计算
                if self.material == 'glass':
                    # 玻璃 - 边缘较不透明，中心较透明
                    alpha_factor = 0.5 + 0.7 * (1.0 - radius_ratio) ** 2
                elif self.material == 'crystal':
                    # 水晶 - 较为均匀的透明度
                    alpha_factor = 0.7 + 0.4 * (1.0 - radius_ratio)
                elif self.material == 'soap':
                    # 肥皂泡 - 非常透明
                    alpha_factor = 0.3 + 0.5 * (1.0 - radius_ratio) ** 3
                else:  # 'gel'
                    # 凝胶 - 中心不透明，边缘透明
                    alpha_factor = 0.8 * (1.0 - radius_ratio ** 0.8)
                
                base_alpha = int(max(0, min(255, self.alpha * alpha_factor)))
                
                # 计算光照效果
                for angle_deg in range(0, 360, 5):
                    angle_rad = np.radians(angle_deg)
                    
                    # 计算该点相对于光源的位置
                    dx = radius_ratio * np.cos(angle_rad)
                    dy = radius_ratio * np.sin(angle_rad)
                    
                    # 计算纹理效果
                    x = self.x + r * np.cos(angle_rad)
                    y = self.y + r * np.sin(angle_rad)
                    texture_value = self._calculate_bubble_texture(x, y, current_radius, self.texture_phase)
                    
                    # 计算光照强度 (简化的Phong照明模型)
                    # 环境光照分量
                    ambient = 0.2
                    
                    # 漫反射分量
                    light_dot = dx * self.light_source_x + dy * self.light_source_y
                    diffuse = max(0, 0.5 * light_dot)
                    
                    # 镜面反射分量 (观察者位于Z轴)
                    view_vector = (0, 0, 1)  # 假设观察者直视屏幕
                    reflection_vector = (-dx, -dy, 0)  # 简化的反射向量
                    spec_dot = max(0, view_vector[2])  # 简化的高光计算
                    specular = pow(spec_dot, self.specular_power) * self.light_intensity
                    
                    # 合并所有光照分量
                    light_factor = min(1.0, ambient + diffuse + specular + texture_value)
                    
                    # 计算彩虹效果
                    rainbow_adjust = self._calculate_rainbow_effect(radius_ratio, angle_rad)
                    
                    # 根据光照和材质计算最终颜色
                    base_r, base_g, base_b = self.base_color
                    
                    # 应用光照效果
                    r = int(min(base_r * light_factor, 255))
                    g = int(min(base_g * light_factor, 255))
                    b = int(min(base_b * light_factor, 255))
                    
                    # 应用彩虹效果
                    r = max(0, min(255, r + int(rainbow_adjust[0])))
                    g = max(0, min(255, g + int(rainbow_adjust[1])))
                    b = max(0, min(255, b + int(rainbow_adjust[2])))
                    
                    # 最终颜色与透明度
                    color = (r, g, b, base_alpha)
                    
                    # 绘制点
                    x = self.x + r * np.cos(angle_rad)
                    y = self.y + r * np.sin(angle_rad)
                    
                    point_size = max(1, int(current_radius / 30))
                    point_bbox = [
                        int(x - point_size/2), int(y - point_size/2),
                        int(x + point_size/2), int(y + point_size/2)
                    ]
                    
                    # 每5度画一个点
                    image_draw.ellipse(point_bbox, fill=color, outline=None)
            
            # 3. 添加边缘轮廓 (更清晰的3D边界)
            if self.has_outer_rim:
                # 边缘宽度
                rim_width = max(1, int(current_radius * 0.02))
                
                # 材质特定的边缘处理
                if self.material == 'glass':
                    rim_color = tuple(min(c + 70, 255) for c in self.base_color)
                    rim_alpha = int(self.alpha * 0.7)
                elif self.material == 'crystal':
                    rim_color = tuple(min(c + 50, 255) for c in self.base_color)
                    rim_alpha = int(self.alpha * 0.85)
                elif self.material == 'soap':
                    rim_color = (240, 240, 255)  # 肥皂泡几乎是白色边缘
                    rim_alpha = int(self.alpha * 0.6)
                else:  # 'gel'
                    rim_color = tuple(min(c + 30, 255) for c in self.base_color)
                    rim_alpha = int(self.alpha * 0.9)
                    
                rim_color_with_alpha = rim_color + (rim_alpha,)
                
                # 泡泡外边界
                outer_bbox = [
                    int(self.x - current_radius), int(self.y - current_radius),
                    int(self.x + current_radius), int(self.y + current_radius)
                ]
                
                # 绘制边缘
                image_draw.ellipse(outer_bbox, fill=None, outline=rim_color_with_alpha, width=rim_width)
            
            # 4. 添加内部发光 (增强核心光源感)
            if self.has_inner_glow:
                # 内部发光大小
                inner_radius = int(current_radius * 0.55)
                
                # 材质特定的内部发光
                if self.material == 'glass':
                    glow_color = tuple(min(c + 60, 255) for c in self.base_color)
                    glow_alpha = int(self.alpha * 0.4)
                elif self.material == 'crystal':
                    glow_color = tuple(min(c + 80, 255) for c in self.base_color)
                    glow_alpha = int(self.alpha * 0.6)
                elif self.material == 'soap':
                    glow_color = tuple(min(c + 50, 255) for c in self.base_color)
                    glow_alpha = int(self.alpha * 0.3)
                else:  # 'gel'
                    glow_color = tuple(min(c + 70, 255) for c in self.base_color)
                    glow_alpha = int(self.alpha * 0.7)
                    
                glow_color_with_alpha = glow_color + (glow_alpha,)
                
                # 内部发光位置 (相对于光源方向稍微偏移)
                glow_offset_x = int(current_radius * 0.1 * self.light_source_x)
                glow_offset_y = int(current_radius * 0.1 * self.light_source_y)
                
                inner_bbox = [
                    int(self.x - inner_radius + glow_offset_x), 
                    int(self.y - inner_radius + glow_offset_y),
                    int(self.x + inner_radius + glow_offset_x), 
                    int(self.y + inner_radius + glow_offset_y)
                ]
                
                # 绘制内部发光
                image_draw.ellipse(inner_bbox, fill=glow_color_with_alpha, outline=None)
                
                # 对于某些材质，添加额外的内部发光层
                if self.material in ['crystal', 'gel']:
                    inner_inner_radius = int(inner_radius * 0.6)
                    inner_glow_color = tuple(min(c + 100, 255) for c in self.base_color)
                    inner_glow_alpha = int(glow_alpha * 0.8)
                    inner_glow_color_with_alpha = inner_glow_color + (inner_glow_alpha,)
                    
                    inner_inner_bbox = [
                        int(self.x - inner_inner_radius + glow_offset_x * 1.2), 
                        int(self.y - inner_inner_radius + glow_offset_y * 1.2),
                        int(self.x + inner_inner_radius + glow_offset_x * 1.2), 
                        int(self.y + inner_inner_radius + glow_offset_y * 1.2)
                    ]
                    
                    image_draw.ellipse(inner_inner_bbox, fill=inner_glow_color_with_alpha, outline=None)
            
            # 5. 添加高光反光点 (3D效果的关键)
            for highlight in self.highlights:
                # 计算高光位置
                highlight_x = self.x + highlight['offset_x']
                highlight_y = self.y + highlight['offset_y']
                
                # 泡泡脉动也影响高光大小
                highlight_radius = highlight['radius']
                if self.pulsate:
                    highlight_radius *= pulse_factor
                
                # 高光强度
                highlight_intensity = int(255 * highlight['intensity'])
                highlight_alpha = int(self.alpha * highlight['intensity'] * 0.9)
                
                # 特定于材质的高光调整
                if self.material == 'glass':
                    # 玻璃 - 锐利清晰的高光
                    highlight_alpha = int(highlight_alpha * 0.9)
                    blur_factor = highlight['blur'] * 0.8
                elif self.material == 'crystal':
                    # 水晶 - 强烈的高光
                    highlight_alpha = int(highlight_alpha * 1.1)
                    blur_factor = highlight['blur'] * 0.7
                elif self.material == 'soap':
                    # 肥皂泡 - 柔和的高光
                    highlight_alpha = int(highlight_alpha * 0.8)
                    blur_factor = highlight['blur'] * 1.2
                else:  # 'gel'
                    # 凝胶 - 中等强度高光
                    highlight_alpha = int(highlight_alpha * 1.0)
                    blur_factor = highlight['blur'] * 0.9
                
                highlight_color = (highlight_intensity, highlight_intensity, highlight_intensity, 
                                    highlight_alpha)
                
                # 绘制高光
                highlight_bbox = [
                    int(highlight_x - highlight_radius), 
                    int(highlight_y - highlight_radius),
                    int(highlight_x + highlight_radius), 
                    int(highlight_y + highlight_radius)
                ]
                
                image_draw.ellipse(highlight_bbox, fill=highlight_color, outline=None)
                
                # 为高光添加柔和的模糊边缘
                outer_highlight_radius = highlight_radius * (1.0 + blur_factor)
                outer_highlight_alpha = int(highlight_alpha * 0.3)
                outer_highlight_color = (highlight_intensity, highlight_intensity, highlight_intensity, 
                                        outer_highlight_alpha)
                
                outer_highlight_bbox = [
                    int(highlight_x - outer_highlight_radius), 
                    int(highlight_y - outer_highlight_radius),
                    int(highlight_x + outer_highlight_radius), 
                    int(highlight_y + outer_highlight_radius)
                ]
                
                image_draw.ellipse(outer_highlight_bbox, fill=outer_highlight_color, outline=None)
        except Exception as e:
            # 如果出现任何错误，简单跳过该泡泡的绘制
            print(f"跳过泡泡绘制，错误: {e}")

def add_dreamy_bubbles_to_video(input_video_path, output_video_path, num_bubbles=40):
    # 打开视频文件
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"错误: 无法打开视频文件 {input_video_path}")
        return

    # 获取视频的基本信息
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"视频信息: {width}x{height} @ {fps:.2f} FPS, 总帧数: {total_frames}")

    # 设置视频编码器和输出文件
    # 对于mp4，常用的编码器是 'mp4v' 或 'avc1'
    # 对于avi，可以是 'XVID'
    fourcc = cv2.VideoWriter_fourcc(*'XVID')  # 使用XVID编码器
    output_path_avi = output_video_path.replace('.mp4', '.avi')  # 将输出格式改为avi
    out = cv2.VideoWriter(output_path_avi, fourcc, fps, (width, height))

    # 初始化泡泡列表 - 减少泡泡数量以降低计算负担
    bubbles = [Bubble(width, height) for _ in range(num_bubbles)]
    
    # 确保材质分布多样化
    for i, bubble in enumerate(bubbles):
        # 基于所需分布选择材质
        if i < num_bubbles * 0.3:
            bubble.material = 'glass'
        elif i < num_bubbles * 0.6:
            bubble.material = 'crystal'
        elif i < num_bubbles * 0.8:
            bubble.material = 'soap'
        else:
            bubble.material = 'gel'
        
        # 重置泡泡以应用新的材质属性
        bubble.reset()
            
    # 确保泡泡起始位置分布均匀且随机
    for i, bubble in enumerate(bubbles):
        # 简化的位置分布模式
        sector = i % 8
        if sector == 0:  # 顶部
            bubble.x = random.randint(0, width)
            bubble.y = -random.randint(10, 50)
        elif sector == 1:  # 底部
            bubble.x = random.randint(0, width)
            bubble.y = height + random.randint(10, 50)
        elif sector == 2:  # 左侧
            bubble.x = -random.randint(10, 50)
            bubble.y = random.randint(0, height)
        elif sector == 3:  # 右侧
            bubble.x = width + random.randint(10, 50)
            bubble.y = random.randint(0, height)
        elif sector == 4:  # 左上角
            bubble.x = -random.randint(10, 50)
            bubble.y = -random.randint(10, 50)
        elif sector == 5:  # 右上角
            bubble.x = width + random.randint(10, 50)
            bubble.y = -random.randint(10, 50)
        elif sector == 6:  # 左下角
            bubble.x = -random.randint(10, 50)
            bubble.y = height + random.randint(10, 50)
        else:  # 右下角
            bubble.x = width + random.randint(10, 50)
            bubble.y = height + random.randint(10, 50)
        
        # 随机初始大小分布 - 确保不同的初始大小
        bubble.radius = random.randint(8, 40)
        
        # 方向随机化，但更简单的方式
        bubble.dx = random.uniform(-0.5, 0.5)
        bubble.dy = random.uniform(-0.5, 0.5)
        
        # 确保有一个有效的移动方向
        if abs(bubble.dx) < 0.1 and abs(bubble.dy) < 0.1:
            # 太慢了，增加速度
            bubble.dx = random.choice([-0.3, 0.3])
            bubble.dy = random.choice([-0.3, 0.3])

    frame_num = 0
    while True:
        ret, frame_bgr = cap.read() # OpenCV读取的是BGR格式
        if not ret:
            break # 视频读取完毕或出错

        frame_num += 1
        print(f"正在处理帧: {frame_num}/{total_frames}", end='\r')

        # 1. 将OpenCV的BGR帧转换为Pillow的RGBA图像 (以便绘制透明元素)
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_frame = Image.fromarray(frame_rgb).convert("RGBA")

        # 2. 创建一个与帧大小相同的完全透明的覆盖层 (RGBA格式)
        pil_overlay = Image.new("RGBA", pil_frame.size, (0, 0, 0, 0))
        draw_context = ImageDraw.Draw(pil_overlay) # 获取绘制上下文

        # 3. 更新每个泡泡的位置并将其绘制到覆盖层上
        for bubble in bubbles:
            bubble.update()
            try:
                bubble.draw(draw_context)
            except Exception as e:
                print(f"跳过泡泡绘制，错误: {str(e)[:50]}...")
                continue

        # 4. 将带有泡泡的覆盖层与原始帧进行Alpha混合
        #    pil_frame是背景，pil_overlay是前景（带透明泡泡）
        pil_combined = Image.alpha_composite(pil_frame, pil_overlay)

        # 5. 将混合后的Pillow图像 (RGBA) 转换回OpenCV的BGR格式以供写入
        #    因为大多数视频格式不直接支持Alpha通道，所以转回RGB再转BGR
        combined_rgb = pil_combined.convert("RGB")
        frame_final_bgr = cv2.cvtColor(np.array(combined_rgb), cv2.COLOR_RGB2BGR)

        # 6. 写入处理后的帧到输出视频
        out.write(frame_final_bgr)

        # (可选) 如果想实时预览，可以取消下面两行的注释
        cv2.imshow('Dreamy Bubbles Effect', frame_final_bgr)
        if cv2.waitKey(1) & 0xFF == ord('q'): # 按 'q' 退出
            break

    print("\n视频处理完成!")

    # 释放资源
    cap.release()
    out.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    input_path = "./tt.mp4"  # <--- 修改为你的输入视频路径
    output_path = "./test_bubble.mp4"  # <--- 输出视频的路径

    # 检查输入文件是否存在
    import os
    if not os.path.exists(input_path):
        print(f"错误: 输入视频文件 '{input_path}' 不存在。请检查路径。")
    else:
        print(f"开始处理视频: {input_path} -> {output_path}")
        add_dreamy_bubbles_to_video(input_path, output_path, num_bubbles=40)  # 减少泡泡数量
        print(f"完成! 请注意输出文件格式为AVI: {output_path.replace('.mp4', '.avi')}")
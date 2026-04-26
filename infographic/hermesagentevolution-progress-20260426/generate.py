#!/usr/bin/env python3
"""Generate HermesAgentEvolution progress infographic - pop-laboratory style"""

from PIL import Image, ImageDraw, ImageFont
import os, subprocess, sys

# Find CJK font
def find_font():
    paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    # search
    r = subprocess.run("fc-list :lang=zh file 2>/dev/null | head -1 | cut -d: -f1", shell=True, capture_output=True, text=True)
    if r.stdout.strip() and os.path.exists(r.stdout.strip()):
        return r.stdout.strip()
    r = subprocess.run("find /usr/share/fonts -name '*.ttf' -o -name '*.ttc' 2>/dev/null | head -5", shell=True, capture_output=True, text=True)
    for line in r.stdout.strip().split('\n'):
        if line and os.path.exists(line):
            return line
    return None

font_path = find_font()
print(f"Font: {font_path}")

W, H = 1080, 1920
img = Image.new('RGB', (W, H), '#F2F2F2')
draw = ImageDraw.Draw(img)

# Colors
TEAL = '#B8D8BE'
PINK = '#E91E63'
YELLOW = '#FFF200'
CHARCOAL = '#2D2926'
WHITE = '#FFFFFF'
GREEN = '#4CAF50'
RED = '#E53935'
GRAY = '#757575'
BLUE_GRAY = '#37474F'

# Grid lines (faint blueprint)
for x in range(0, W, 60):
    draw.line([(x, 0), (x, H)], fill='#E0E0E0', width=1)
for y in range(0, H, 60):
    draw.line([(0, y), (W, y)], fill='#E0E0E0', width=1)

# Ruler marks
for x in range(0, W, 120):
    draw.line([(x, 0), (x, 8)], fill=CHARCOAL, width=1)
    draw.line([(x, H-8), (x, H)], fill=CHARCOAL, width=1)
for y in range(0, H, 120):
    draw.line([(0, y), (8, y)], fill=CHARCOAL, width=1)
    draw.line([(W-8, y), (W, y)], fill=CHARCOAL, width=1)

# Load fonts
try:
    font_title = ImageFont.truetype(font_path, 64)
    font_subtitle = ImageFont.truetype(font_path, 28)
    font_header = ImageFont.truetype(font_path, 36)
    font_body = ImageFont.truetype(font_path, 24)
    font_small = ImageFont.truetype(font_path, 20)
    font_number = ImageFont.truetype(font_path, 48)
except:
    font_title = ImageFont.load_default()
    font_subtitle = font_title
    font_header = font_title
    font_body = font_title
    font_small = font_title
    font_number = font_title

# Helper: draw rounded rect
def rounded_rect(draw, xy, radius, fill, outline=None):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)

def draw_module(x, y, w, h, coord, title, content_lines, accent=None):
    """Draw a module with coordinate label"""
    # Module background
    rounded_rect(draw, (x, y, x+w, y+h), 12, WHITE, CHARCOAL)
    
    # Coordinate label
    draw.text((x+14, y+10), coord, fill=GRAY, font=font_small)
    
    # Title with accent bar
    bar_color = accent or TEAL
    draw.rectangle([(x+14, y+40), (x+14+6, y+68)], fill=bar_color)
    draw.text((x+28, y+38), title, fill=CHARCOAL, font=font_header)
    
    # Content lines
    ty = y + 82
    for line in content_lines:
        if line.startswith('🔴'):
            draw.text((x+18, ty), line, fill=PINK, font=font_body)
        elif line.startswith('🟡'):
            draw.text((x+18, ty), line, fill='#FF9800', font=font_body)
        elif line.startswith('🟢'):
            draw.text((x+18, ty), line, fill=GREEN, font=font_body)
        elif line.startswith('✅'):
            draw.text((x+18, ty), line, fill=GREEN, font=font_body)
        elif line.startswith('❌'):
            draw.text((x+18, ty), line, fill=RED, font=font_body)
        elif line.startswith('📊') or line.startswith('📈'):
            draw.text((x+18, ty), line, fill=BLUE_GRAY, font=font_number)
        else:
            draw.text((x+18, ty), line, fill=CHARCOAL, font=font_body)
        ty += 36

# === HEADER ===
header_y = 40
# Title background bar
rounded_rect(draw, (32, header_y, W-32, header_y+180), 16, CHARCOAL)

# Yellow highlight stripe
draw.rectangle([(50, header_y+24), (W-50, header_y+28)], fill=YELLOW)

draw.text((60, header_y+40), "HermesAgentEvolution", fill=WHITE, font=font_title)
draw.text((60, header_y+110), "项目进展汇报", fill=TEAL, font=font_title)

# Subtitle
draw.text((60, header_y+170), "2026年4月26日 · 4迭代全完成 · 19,003行代码 · 48文件", fill='#B0BEC5', font=font_small)

# === MODULES ===
margin = 32
content_start = header_y + 210
col_w = (W - margin * 3) // 2
row_h = 440

# SEC-A: Iteration Progress (left, top)
draw_module(
    margin, content_start, col_w, row_h,
    "SEC-A", "迭代进度",
    [
        "✅ 迭代1 基础框架    100%",
        "✅ 迭代2 学习能力进化  100%",
        "✅ 迭代3 工具能力进化  100%",
        "✅ V2 架构改造        100%",
        "📅 迭代4            未规划",
    ],
    TEAL
)

# SEC-B: Code Scale (right, top)
draw_module(
    margin * 2 + col_w, content_start, col_w, row_h,
    "SEC-B", "代码规模",
    [
        "V1 核心源码   7,821行 / 20文件",
        "V2 微服务     7,428行 / 12文件",
        "测试代码      3,754行 / 16文件",
        "",
        "📊 合计       19,003行 / 48文件",
    ],
    '#42A5F5'
)

# SEC-C: Test Results (left, middle)
test_start = content_start + row_h + 24
draw_module(
    margin, test_start, col_w, 380,
    "SEC-C", "测试报告",
    [
        "✅ 通过: 103 (84.4%)",
        "❌ 失败: 19",
        "📈 总计: 122",
        "",
        "失败分布:",
        "  · association_discovery: 10",
        "  · association_fixed:     2",
        "  · learning_integration:  7",
    ],
    YELLOW
)

# SEC-D: V2 Architecture (right, middle)
draw_module(
    margin * 2 + col_w, test_start, col_w, 380,
    "SEC-D", "V2 架构亮点",
    [
        "⚡ 事件驱动微服务",
        "   FastAPI + Docker + Redis",
        "🧠 强化学习",
        "   DQN / PPO / A2C",
        "🎓 元学习",
        "   MAML / Reptile",
        "🔄 反思机制与持续优化",
        "🔧 动态工具发现与组合",
    ],
    '#7E57C2'
)

# SEC-E: Issues (full width, bottom)
issue_start = test_start + 380 + 24
draw_module(
    margin, issue_start, col_w * 2 + margin, 440,
    "SEC-E", "问题追踪",
    [
        "🔴 高优先级 — API不匹配导致19个测试失败",
        "     · discovered_by 参数不存在",
        "     · update_memory_entry 方法缺失",
        "     · 集成测试全部挂起",
        "",
        "🟡 中优先级 — 无Git版本控制",
        "🟡 中优先级 — 飞书通知仍用模拟模式",
        "",
        "🟢 低优先级 — 迭代4未规划",
        "🟢 低优先级 — 38个pytest弃用警告 (Python 3.12 SQLite adapter)",
    ],
    PINK
)

# Corner metadata
draw.text((W-300, H-40), "Build: 20260426-0311 · DeepSeek V4 Pro", fill=GRAY, font=font_small)
draw.text((20, H-40), "SEC-001-EVOLUTION", fill=GRAY, font=font_small)

# Cross-hair targets in corners
for cx, cy in [(30, 30), (W-30, 30), (30, H-30), (W-30, H-30)]:
    draw.line([(cx-10, cy), (cx+10, cy)], fill=CHARCOAL, width=1)
    draw.line([(cx, cy-10), (cx, cy+10)], fill=CHARCOAL, width=1)
    draw.ellipse([cx-4, cy-4, cx+4, cy+4], outline=CHARCOAL, width=1)

out_path = "/mnt/c/Users/1/hermes_agent_evolution/infographic/hermesagentevolution-progress-20260426/infographic.png"
img.save(out_path, "PNG", quality=95)
print(f"Saved: {out_path}")
print(f"Size: {os.path.getsize(out_path)} bytes")

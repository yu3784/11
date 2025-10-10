import sys
import os
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import json
import pyautogui
pyautogui.PAUSE = 0.065  # 设置pyautogui操作间的默认延迟为65ms
import cv2
import numpy as np
import time
import pytesseract
import logging
import queue
from threading import Thread
from functools import lru_cache
from pynput import keyboard
import pyuac
import pyperclip
import glob
from datetime import datetime
from PIL import Image, ImageTk

# 配置日志 - 每次启动创建新的日志文件并清理旧文件
from datetime import datetime
import glob

def cleanup_old_logs(max_files=2):
    """清理旧的日志文件，只保留最新的几个"""
    try:
        log_files = glob.glob('app_*.log')
        if len(log_files) > max_files:
            # 按修改时间排序，删除最老的文件
            log_files.sort(key=os.path.getmtime)
            deleted_count = 0
            for old_file in log_files[:-max_files]:
                os.remove(old_file)
                deleted_count += 1
                print(f"已删除旧日志文件: {old_file}")
            print(f"共删除 {deleted_count} 个旧日志文件，保留最新 {max_files} 个")
    except Exception as e:
        print(f"清理日志文件时出错: {e}")

# 清理旧日志文件
cleanup_old_logs()

# 创建新的日志文件
log_filename = f'app_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(filename=log_filename, level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 简化日志调用
def log(message):
    logging.info(message)
    print(message)  # 同时打印到控制台方便调试
    
    # 定义不在UI中显示的日志消息关键词
    ui_hidden_keywords = [
        "已拥有管理员权限",
        "坐标配置文件",
        "用户配置文件",
        "窗口大小已恢复",
        "窗口大小已保存",
        "配置文件",
        "当前模式:",
        "当前延迟配置:",
        "当前最低价格设置:",
        "当前最高价格设置:",
        "调试截图已启用",
        "模式类别切换到:",
        "模式切换到:",
        "配置已保存到",
        "用户设置已保存到",
        "坐标配置已保存到",
        "加载成功",
        "子弹数量:",
        "单发价格范围:",
        "刷新延迟:",
        "截图延迟:",
        "调试模式:",
        "按L键进入配装界面",
        "当前tesseract_cmd:",
        "点击配装方案坐标:",
        "配装方案价格:",
        "单发子弹价格:",
        "直接点击判定游戏模式区域坐标",
        "低于最低价格",
        "视为识别失败",
        "截图失败",
        "点击卡片",
        "位置失败",
        "购买按钮坐标未设置",
        "调试模式已启用",
        "价格合适但不执行购买操作",
        "金额：",
        "在范围内执行购买",
        "单发价格",
        "低于最低单价",
        "价格识别失败",
        "get_card_price 返回 None",
        "返回大战场刷新次数阈值"
    ]
    
    # 定义只在UI中显示的日志消息关键词（白名单）
    ui_show_keywords = [
        "第",
        "次刷新 识别价格：",
        "高于最高价格",
        "高于最高单价",
        "跳过"
    ]
    
    # 检查是否应该在UI中显示此消息（使用白名单机制）
    should_show_in_ui = False
    for keyword in ui_show_keywords:
        if keyword in message:
            should_show_in_ui = True
            break
    
    # 如果白名单没有匹配，再检查黑名单
    if should_show_in_ui:
        for keyword in ui_hidden_keywords:
            if keyword in message:
                should_show_in_ui = False
                break
    
    # 将日志消息放入队列供UI显示（仅当不在隐藏列表中时）
    if should_show_in_ui:
        try:
            if 'log_queue' in globals() and log_queue: # 确保log_queue已初始化
                log_queue.put(message)
        except:
            pass  # 如果队列不可用，忽略错误

# 设置Tesseract环境（支持开发环境和打包环境）
def setup_tesseract():
    try:
        if getattr(sys, 'frozen', False):
            # 打包后的环境 - 使用内置的tessdata
            base_path = sys._MEIPASS
            
            # 查找内置的Tesseract可执行文件
            tesseract_exe = os.path.join(base_path, 'tesseract.exe')
            tessdata_dir = os.path.join(base_path, 'tessdata')
            
            if os.path.exists(tesseract_exe) and os.path.exists(tessdata_dir):
                pytesseract.pytesseract.tesseract_cmd = tesseract_exe
                os.environ['TESSDATA_PREFIX'] = tessdata_dir
                log(f"使用内置Tesseract: {tesseract_exe}")
                log(f"使用内置语言包: {tessdata_dir}")
                return True
            else:
                # 如果内置组件缺失，尝试使用系统安装的Tesseract
                log("警告: 内置Tesseract组件缺失，尝试使用系统安装的Tesseract")
        else:
            # 开发环境 - 优先使用项目本地的tessdata_mini
            current_dir = os.path.dirname(os.path.abspath(__file__))
            local_tessdata = os.path.join(current_dir, 'tessdata_mini')
            
            # 检查项目本地是否有tessdata_mini文件夹
            if os.path.exists(local_tessdata):
                # 查找系统安装的tesseract.exe
                possible_tesseract_paths = [
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
                    r'C:\Tesseract-OCR\tesseract.exe'
                ]
                
                for tesseract_path in possible_tesseract_paths:
                    if os.path.exists(tesseract_path):
                        pytesseract.pytesseract.tesseract_cmd = tesseract_path
                        os.environ['TESSDATA_PREFIX'] = local_tessdata
                        log(f"开发环境: 使用系统Tesseract - {tesseract_path}")
                        log(f"使用项目本地语言包: {local_tessdata}")
                        return True
            
            # 如果本地tessdata_mini不存在，使用系统默认路径
            dev_tessdata = r'C:\Program Files\Tesseract-OCR\tessdata'
            dev_tesseract = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            
            if os.path.exists(dev_tesseract) and os.path.exists(dev_tessdata):
                pytesseract.pytesseract.tesseract_cmd = dev_tesseract
                os.environ['TESSDATA_PREFIX'] = dev_tessdata
                log(f"开发环境: 使用系统Tesseract - {dev_tesseract}")
                return True
        
        # 尝试查找系统安装的Tesseract
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Tesseract-OCR\tesseract.exe'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                tessdata_path = os.path.join(os.path.dirname(path), 'tessdata')
                if os.path.exists(tessdata_path):
                    os.environ["TESSDATA_PREFIX"] = tessdata_path
                    log(f"使用系统Tesseract: {path}")
                    return True
        
        # 如果所有尝试都失败
        log("错误: 未找到Tesseract OCR引擎")
        messagebox.showerror("OCR错误", "未找到Tesseract OCR引擎，请安装或检查程序完整性")
        return False
    
    except Exception as e:
        log(f"配置Tesseract时出错: {str(e)}")
        return False

# 初始化OCR配置
if not setup_tesseract():
    log("OCR功能可能不可用")

# 清理调试截图函数
def cleanup_debug_screenshots(max_files=4):
    """清理调试截图文件，保留最新的max_files个文件"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # 查找所有调试截图文件
        debug_files = glob.glob(os.path.join(current_dir, "debug_*.png"))
        
        if len(debug_files) > max_files:
            # 按修改时间排序，最新的在前
            debug_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            # 删除超出数量限制的旧文件
            files_to_delete = debug_files[max_files:]
            deleted_count = 0
            
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    log(f"删除调试截图失败 {file_path}: {e}")
            
            # 清理完成（简化日志输出）
                
    except Exception as e:
        log(f"清理调试截图时出错: {e}")

# 全局常量
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

# 全局变量
is_running = False
adjust_price_clicks = 0
loop_thread = None
valid_cards = []
delays = {}
consecutive_failure_count = 0
grab_no_stock_failure_count = 0  # 满仓模式抢无货专用失败计数器
loadout_grab_no_stock_failure_count = 0  # 滚仓模式抢无货专用失败计数器
config = {}
log_queue = queue.Queue()  # 用于线程安全的日志传递
click_counter = 0        # 点击次数计数器
debug_screenshot_enabled = True  # 调试截图开关（默认开启）
app_instance = None      # 全局app实例，用于快捷键调用

# 滚仓模式专用变量
loadout_refresh_count = 0  # 滚仓模式刷新次数计数器
loadout_total_amount = 0   # 滚仓模式总购买金额
loadout_last_price = 0     # 滚仓模式最后一次单价
total_refresh_count = 0    # 所有模式的总刷新次数计数器
fullstock_refresh_count = 0  # 满仓模式刷新次数计数器

# UI输入变量（需全局可访问）
max_price_var = None   # 最高价格
delay_stable_var = None # 页面稳定延迟
delay_buy_var = None   # 购买页延迟
loadout_info_var = None # 滚仓模式信息显示
return_battlefield_threshold_var = None # 返回大战场刷新次数阈值
USER_SETTINGS_FILE = 'user_settings.json'

# 内置默认配置，避免依赖外部文件
DEFAULT_CONFIG = {
    "cards_config": [
        {
            "name": "金蛋",
            "wantBuy": 1,
            "position": [0.3016, 0.2324],
            "quantity_control_pos": [0.909, 0.776],
            "buy_button_pos": [0.837, 0.846],
            "price_region": [0.155, 0.15, 0.1, 0.05],
            "max_price": 35,
            "min_price": 0
        },
        {
            "name": "紫蛋",
            "wantBuy": 1,
            "position": [0.544, 0.213],
            "quantity_control_pos": [0.9094, 0.7222],
            "buy_button_pos": [0.827, 0.799],
            "price_region": [0.155, 0.15, 0.1, 0.05],
            "max_price": 35,
            "min_price": 0
        },
        {
            "name": "肉蛋",
            "wantBuy": 1,
            "position": [0.806, 0.221],
            "quantity_control_pos": [0.9094, 0.7222],
            "buy_button_pos": [0.827, 0.799],
            "price_region": [0.155, 0.15, 0.1, 0.05],
            "max_price": 35,
            "min_price": 0
        }
    ],
    "delays": {
        "page_stable_delay": 30,
        "buy_page_wait_delay": 5
    }
}

DEFAULT_USER_SETTINGS = {
    "page_stable_delay": 30,
    "buy_page_wait_delay": 0,
    "配装方案1_min_price": 0,
    "配装方案1_max_price": 100,
    "bullet_count": 4800,
    "bullet_min_price": 300.0,
    "bullet_max_price": 500.0,
    "refresh_delay": 30,
    "screenshot_delay": 15,
    "肉蛋_min_price": 200,
    "肉蛋_max_price": 300,
    "金蛋_min_price": 0,
    "金蛋_max_price": 35,
    "配装方案2_min_price": 0,
    "配装方案2_max_price": 100,
    "配装方案3_min_price": 0,
    "配装方案3_max_price": 100,
    "return_battlefield_threshold": 200,
    "grab_no_stock_enabled": False  # 抢无货功能默认关闭
}

@lru_cache(maxsize=1)
def load_config():
    """加载配置文件（优先使用内置配置）"""
    global config
    # 首先使用内置默认配置
    config = DEFAULT_CONFIG.copy()
    
    # 尝试加载外部配置文件进行覆盖（可选）
    try:
        if os.path.exists('keys.json'):
            with open('keys.json', 'r', encoding='utf-8') as f:
                external_config = json.load(f)
                # 合并外部配置到默认配置
                config.update(external_config)
                log(f"外部配置文件 keys.json 加载成功，已合并到内置配置")
        else:
            log(f"使用内置默认配置（未找到 keys.json）")
    except json.JSONDecodeError:
        log(f"[警告] 配置文件 keys.json 格式错误，使用内置默认配置")
    except Exception as e:
        log(f"[警告] 读取 keys.json 时发生错误: {str(e)}，使用内置默认配置")
    
    return config

def load_user_settings():
    """加载用户设置（优先使用内置默认配置）"""
    # 首先使用内置默认配置
    user_settings = DEFAULT_USER_SETTINGS.copy()
    
    # 尝试加载外部配置文件进行覆盖（可选）
    try:
        if os.path.exists(USER_SETTINGS_FILE):
            with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                external_settings = json.load(f)
                # 合并外部设置到默认设置
                user_settings.update(external_settings)
                log(f"外部用户配置文件 {USER_SETTINGS_FILE} 加载成功，已合并到内置配置")
        else:
            log(f"使用内置默认用户设置（未找到 {USER_SETTINGS_FILE}）")
    except json.JSONDecodeError:
        log(f"[警告] 用户配置文件 {USER_SETTINGS_FILE} 格式错误，使用内置默认设置")
    except Exception as e:
        log(f"[警告] 读取 {USER_SETTINGS_FILE} 时发生错误: {str(e)}，使用内置默认设置")
    
    return user_settings

def save_window_geometry(master):
    """保存窗口大小和位置"""
    try:
        geometry = master.geometry()
        user_settings = load_user_settings()
        user_settings['window_geometry'] = geometry
        
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_settings, f, ensure_ascii=False, indent=4)
        log(f"窗口大小已保存: {geometry}")
    except Exception as e:
        log(f"保存窗口大小失败: {e}")

def load_window_geometry(master):
    """加载并应用窗口大小和位置"""
    try:
        user_settings = load_user_settings()
        if 'window_geometry' in user_settings:
            geometry = user_settings['window_geometry']
            master.geometry(geometry)
            log(f"窗口大小已恢复: {geometry}")
        else:
            # 如果没有保存的窗口大小，使用默认值
            master.geometry("700x750")
            log("使用默认窗口大小: 700x750")
    except Exception as e:
        log(f"加载窗口大小失败: {e}")
        master.geometry("700x750")  # 出错时使用默认值

def init_config():
    """初始化配置，根据UI选择的模式筛选卡片，并获取延迟配置、用户价格和最低价格"""
    global valid_cards, delays, config, max_price_var, min_price_var, mode_var, delay_stable_var, delay_buy_var
    config = load_config()  # 加载 keys.json
    user_settings = load_user_settings()  # 加载 user_settings.json

    cards_config = config.get('cards_config', []) # 从 keys.json 读取 cards_config

    # 根据UI选择的模式筛选卡片
    selected_mode_name = mode_var.get() if mode_var else "收藏第一位置" # 如果mode_var未初始化，则默认为第一个
    valid_cards = []
    current_card_settings = None
    for card in cards_config:
        if card.get('name') == selected_mode_name and card.get('wantBuy', 0) == 1:
            valid_cards.append(card)
            current_card_settings = card # 保存当前选中模式的卡片配置
            break # 假设每个模式名称唯一，找到即停止
    
    if not valid_cards:
        log(f"警告: 在模式 '{selected_mode_name}' 下未找到 'wantBuy' 为 1 的有效卡片配置。")

    # 优先从 user_settings 加载延迟，否则从 keys.json, 再否则用硬编码默认值
    delays_from_keys = config.get('delays', {})
    delays = {
        'page_stable_delay': user_settings.get('page_stable_delay', delays_from_keys.get('page_stable_delay', 20)), # 页面稳定延迟，单位毫秒
        'buy_page_wait_delay': user_settings.get('buy_page_wait_delay', delays_from_keys.get('buy_page_wait_delay', 50)) # 购买页等待延迟，单位毫秒
    }

    # 更新UI中的延迟设置
    if delay_stable_var:  # 确保UI元素已创建
        delay_stable_var.set(delays['page_stable_delay'])
    if delay_buy_var:
        delay_buy_var.set(delays['buy_page_wait_delay'])

    # 设置价格：优先从 user_settings, 其次从当前选中模式的卡片配置, 最后是硬编码默认值
    default_max_price_from_card = 35
    default_min_price_from_card = 0 # 默认最低价

    if current_card_settings: # 如果当前模式有卡片配置
        default_max_price_from_card = current_card_settings.get('max_price', 35)
        default_min_price_from_card = current_card_settings.get('min_price', 0) # 从卡片配置读取最低价
    
    # 优先从 user_settings 加载当前模式的特定价格，否则从 keys.json 中的卡片配置，最后是硬编码默认值
    max_price_to_set = user_settings.get(f'{selected_mode_name}_max_price', default_max_price_from_card)
    min_price_to_set = user_settings.get(f'{selected_mode_name}_min_price', default_min_price_from_card)

    if max_price_var:  # 确保UI元素已创建
        max_price_var.set(max_price_to_set)
    if min_price_var: # 确保UI元素已创建
        min_price_var.set(min_price_to_set)

    # 加载滚仓模式的参数
    global app_instance
    if app_instance:
        # 从user_settings加载滚仓模式参数，如果没有则使用默认值
        bullet_count = user_settings.get('bullet_count', 4080)
        bullet_min_price = user_settings.get('bullet_min_price', 0.1)
        bullet_max_price = user_settings.get('bullet_max_price', 0.5)
        refresh_delay = user_settings.get('refresh_delay', 1000)
        screenshot_delay = user_settings.get('screenshot_delay', 500)
        
        # 设置到UI
        app_instance.bullet_count_var.set(str(bullet_count))
        app_instance.bullet_min_price_var.set(str(bullet_min_price))
        app_instance.bullet_max_price_var.set(str(bullet_max_price))
        app_instance.refresh_delay_var.set(str(refresh_delay))
        app_instance.screenshot_delay_var.set(str(screenshot_delay))
        
        # 加载"数量拉满"开关状态
        quantity_max_enabled = user_settings.get('quantity_max_enabled', False)
        app_instance.quantity_max_var.set(quantity_max_enabled)
        
        # 加载"抢无货"开关状态
        grab_no_stock_enabled = user_settings.get('grab_no_stock_enabled', False)
        app_instance.grab_no_stock_var.set(grab_no_stock_enabled)
        
        # 加载返回大战场刷新次数阈值
        return_threshold = user_settings.get('return_battlefield_threshold', 200)
        return_battlefield_threshold_var.set(str(return_threshold))

    log(f"当前模式: {selected_mode_name}")
    log(f"当前延迟配置: 页面稳定={delays['page_stable_delay']}ms, 购买页等待={delays['buy_page_wait_delay']}ms")
    log(f"当前最低价格设置: {min_price_to_set}")
    log(f"当前最高价格设置: {max_price_to_set}")
    log(f"返回大战场刷新次数阈值: {return_threshold}次")

def percent_to_pixel(percent_tuple):
    """将百分比坐标转换为像素坐标"""
    return (
        int(percent_tuple[0] * SCREEN_WIDTH),
        int(percent_tuple[1] * SCREEN_HEIGHT)
    )

def get_price_region_px():
    """获取价格区域的像素坐标（根据当前选中的模式）"""
    global config, mode_var # 确保可以访问全局config和mode_var

    # 首先检查是否有自定义的价格识别区域坐标
    if COORDINATE_CONFIG['price_region']['percent'] != (0.0, 0.0, 0.0, 0.0):
        price_region_percent = COORDINATE_CONFIG['price_region']['percent']
    else:
        # 使用原有的配置逻辑
        selected_mode_name = mode_var.get() if mode_var else "收藏第一位置"
        cards_config = config.get('cards_config', [])
        current_card_settings = None

        for card in cards_config:
            if card.get('name') == selected_mode_name:
                current_card_settings = card
                break

        if not current_card_settings:
            log(f"[警告] 在模式 '{selected_mode_name}' 下未找到卡片配置，价格区域将使用默认值。")
            # 提供一个默认的 price_region，以避免程序因缺少配置而崩溃
            price_region_percent = (0.155, 0.15, 0.1, 0.05) 
        else:
            price_region_percent = current_card_settings.get('price_region', (0.155, 0.15, 0.1, 0.05))
            if price_region_percent == (0.155, 0.15, 0.1, 0.05) and not current_card_settings.get('price_region'):
                log(f"[警告] 模式 '{selected_mode_name}' 的卡片配置中未指定price_region，价格区域将使用默认值。")

    return (
        int(price_region_percent[0] * SCREEN_WIDTH),
        int(price_region_percent[1] * SCREEN_HEIGHT),
        int(price_region_percent[2] * SCREEN_WIDTH),
        int(price_region_percent[3] * SCREEN_HEIGHT)
    )

def preprocess_image_for_loadout(screenshot_np):
    """滚仓模式专用图像预处理函数 - 转换为灰度图以提高识别速度"""
    # 转换为灰度图，提高OCR识别速度
    gray = cv2.cvtColor(screenshot_np, cv2.COLOR_BGR2GRAY)
    return gray

def preprocess_image_for_fullstock(screenshot_np):
    """满仓模式图像预处理函数（原有逻辑）"""
    # 转换为灰度图
    gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
    # 图像放大(上采样) - 增加放大倍数提高识别精度
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    # 降噪处理
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    # 自适应阈值处理，提高不同光照条件下的识别率
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    # 形态学操作，去除噪点
    kernel = np.ones((2,2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    return binary

def correct_zero_eight_confusion(text, bullet_count, verbose=True, is_fullstock_mode=False):
    """修正0和8的识别错误，通过单价计算验证"""
    if not text or ('0' not in text and '8' not in text):
        return text
    
    # 满仓模式下不进行单价计算，直接返回原始文本
    if is_fullstock_mode:
        return text
    
    # 找出所有需要处理的位置：所有是'0'或'8'字符的位置
    positions = []
    for i, char in enumerate(text):
        if char in ['0', '8']:
            positions.append(i)
    
    if not positions:
        return text
    
    # 生成所有可能的组合：2^n种可能
    num_positions = len(positions)
    total_combinations = 2 ** num_positions
    
    best_candidate = None
    best_score = float('inf')  # 越小越好
    
    for combination in range(total_combinations):
        # 构造候选数字字符串
        candidate_chars = list(text)
        
        # 使用位运算决策：每一位决定对应位置是否进行替换
        for bit_index in range(num_positions):
            pos = positions[bit_index]
            # 检查第bit_index位是否为1
            if (combination >> bit_index) & 1:
                # 进行互换：0变成8，8变成0
                if candidate_chars[pos] == '0':
                    candidate_chars[pos] = '8'
                elif candidate_chars[pos] == '8':
                    candidate_chars[pos] = '0'
        
        candidate = ''.join(candidate_chars)
        
        try:
            price = int(candidate)
            if price <= 0 or bullet_count <= 0:
                continue
                
            unit_price = price / bullet_count
            
            # 检查单价是否为整数（或非常接近整数）
            decimal_part = unit_price - int(unit_price)
            
            # 计算偏离整数的程度作为评分
            if decimal_part > 0.5:
                decimal_part = 1 - decimal_part  # 更接近下一个整数
            
            score = decimal_part
            
            # 只在详细模式下输出候选价格分析
            if verbose:
                log(f"候选价格 {candidate}: 单价 {unit_price:.6f}, 偏离整数程度: {score:.6f}")
            
            if score < best_score:
                best_score = score
                best_candidate = candidate
                
            # 如果找到完美整数单价，直接返回
            if score < 0.001:
                break
                
        except (ValueError, ZeroDivisionError):
            continue
    
    if best_candidate and best_score < 0.001:  # 非常接近整数
        if best_candidate != text and verbose:
            log(f"0/8识别错误修正: '{text}' -> '{best_candidate}' (单价为整数)")
        return best_candidate
    
    return text

def get_card_price():
    """获取当前卡片价格"""
    global consecutive_failure_count
    region_px = get_price_region_px()
    try:
        screenshot = pyautogui.screenshot(region=region_px)
    except Exception as e:
        log(f"截图失败: {e}")
        consecutive_failure_count += 1
        try:
            pyautogui.press('esc') # 尝试关闭可能的弹出窗口
        except:
            pass
        return None
    
    # 保存调试截图
    if debug_screenshot_enabled:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        debug_path = os.path.join(current_dir, f"debug_price_original_{timestamp}.png")
        screenshot.save(debug_path)
        # 调试截图已保存（简化日志输出）
        
        # 清理旧的调试截图
        cleanup_debug_screenshots(max_files=4)
        
        # 在UI中显示调试截图
        if 'app_ui' in globals() and app_ui:
            app_ui.add_debug_image(debug_path, "价格识别原始截图")
    
    # 根据当前模式判断是否为滚仓模式
    try:
        current_mode = mode_var.get() if mode_var else "金蛋"
    except NameError:
        current_mode = "金蛋"
    
    is_loadout_mode = current_mode in ["配装方案1", "配装方案2", "配装方案3"]
    
    # 直接使用原始截图进行OCR识别，不进行任何预处理
    # 使用配置5：--psm 7 -c tessedit_char_whitelist=0123456789,（精准识别逗号）
    text_clean = ""
    price = None
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_tessdata = os.path.join(current_dir, 'tessdata_mini')
    
    # 只使用配置5：--psm 7 -c tessedit_char_whitelist=0123456789,（精准识别逗号）
    base_config = "--psm 7 -c tessedit_char_whitelist=0123456789,"
    
    try:
        if os.path.exists(local_tessdata):
            config = f'--tessdata-dir {local_tessdata} {base_config}'
        else:
            config = base_config
        
        # 直接使用原始截图进行OCR识别
        text = pytesseract.image_to_string(screenshot, lang='eng', config=config)
        text_raw = text.strip()
        
        # 直接处理识别结果，去除逗号
        text_clean = text_raw.replace(',', '')
        # 只保留数字
        text_clean = ''.join(filter(str.isdigit, text_clean))
        
        if text_clean:
            try:
                price = int(text_clean)
                # 滚仓模式需要计算单价
                if is_loadout_mode:
                    try:
                        bullet_count = int(app_instance.bullet_count_var.get()) if app_instance else 4080
                        if bullet_count > 0:
                            # 使用0和8纠错逻辑确保价格能被子弹数量整除
                            corrected_text = correct_zero_eight_confusion(text_clean, bullet_count, verbose=False, is_fullstock_mode=False)
                            corrected_price = int(corrected_text) if corrected_text else price
                            
                            unit_price = corrected_price / bullet_count
                            
                            # 如果纠错后的价格与原价格不同，更新显示的原始OCR结果
                            if corrected_price != price:
                                # 将纠错后的价格转换回带逗号的格式显示
                                corrected_display = f"{corrected_price:,}"
                                return (corrected_display, unit_price)
                            else:
                                return (text_raw, unit_price)
                    except (ValueError, AttributeError):
                        pass
                
                # 满仓模式直接返回价格
                return price
                
            except ValueError:
                log(f"价格转换失败: '{text_clean}'")
        
    except Exception as e:
        log(f"OCR识别失败: {e}")
    
    # OCR识别失败，检查是否开启"抢无货"功能（仅满仓模式可用）
    try:
        grab_no_stock_enabled = app_instance.grab_no_stock_var.get() if app_instance else False
    except (AttributeError, NameError):
        grab_no_stock_enabled = False
    
    # 滚仓模式下禁用抢无货功能
    if is_loadout_mode:
        # 滚仓模式：直接计入正常失败次数，不使用抢无货逻辑
        consecutive_failure_count += 1
        log(f"价格识别失败，连续失败次数: {consecutive_failure_count}")
    elif grab_no_stock_enabled:
        # 满仓模式且开启"抢无货"功能：连续识别失败四次后才等待5秒重试
        global grab_no_stock_failure_count
        grab_no_stock_failure_count += 1
        log(f"价格识别失败，满仓模式抢无货连续失败次数: {grab_no_stock_failure_count}")
        
        if grab_no_stock_failure_count >= 4:
            log(f"满仓模式抢无货连续识别失败4次，等待5秒后重试")
            grab_no_stock_failure_count = 0  # 重置满仓模式抢无货失败计数器
            time.sleep(5)
        return None
    else:
        # 满仓模式未开启"抢无货"功能：正常计入失败次数
        consecutive_failure_count += 1
        log(f"价格识别失败，连续失败次数: {consecutive_failure_count}")
    
    return None

def get_secondary_price(bullet_count, bullet_min_price, bullet_max_price, debug_screenshot=False):
    """获取二次识别区域的价格，专用于滚仓模式二次验证"""
    region_percent = COORDINATE_CONFIG['secondary_price_region']['percent']
    region_px = (
        int(region_percent[0] * SCREEN_WIDTH),
        int(region_percent[1] * SCREEN_HEIGHT),
        int(region_percent[2] * SCREEN_WIDTH),
        int(region_percent[3] * SCREEN_HEIGHT)
    )
    
    try:
        screenshot = pyautogui.screenshot(region=region_px)
    except Exception as e:
        log(f"二次识别截图失败: {e}")
        return None
    
    # 保存调试截图
    if debug_screenshot:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        debug_path = os.path.join(current_dir, f"debug_secondary_price_{timestamp}.png")
        screenshot.save(debug_path)
        
        # 清理旧的调试截图
        cleanup_debug_screenshots(max_files=4)
        
        # 在UI中显示调试截图
        if 'app_ui' in globals() and app_ui:
            app_ui.add_debug_image(debug_path, "二次识别价格截图")
    
    # 使用与主要价格识别相同的OCR配置
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_tessdata = os.path.join(current_dir, 'tessdata_mini')
    
    base_config = "--psm 7 -c tessedit_char_whitelist=0123456789,"
    
    try:
        if os.path.exists(local_tessdata):
            config = f'--tessdata-dir {local_tessdata} {base_config}'
        else:
            config = base_config
        
        # 直接使用原始截图进行OCR识别
        text = pytesseract.image_to_string(screenshot, lang='eng', config=config)
        text_raw = text.strip()
        
        # 处理识别结果，去除逗号
        text_clean = text_raw.replace(',', '')
        # 只保留数字
        text_clean = ''.join(filter(str.isdigit, text_clean))
        
        if text_clean:
            try:
                price = int(text_clean)
                
                # 使用0和8纠错逻辑确保价格能被子弹数量整除
                corrected_text = correct_zero_eight_confusion(text_clean, bullet_count, verbose=False, is_fullstock_mode=False)
                corrected_price = int(corrected_text) if corrected_text else price
                
                # 计算单发价格
                if bullet_count > 0:
                    unit_price = corrected_price / bullet_count
                    
                    # 检查单发价格是否在范围内
                    if bullet_min_price <= unit_price <= bullet_max_price:
                        log(f"二次识别成功: 总价 {corrected_price} 单价 {unit_price:.2f} 在范围内")
                        return (corrected_price, unit_price, True)  # 返回总价、单价和验证结果
                    else:
                        log(f"二次识别: 总价 {corrected_price} 单价 {unit_price:.2f} 不在范围内 ({bullet_min_price}-{bullet_max_price})")
                        return (corrected_price, unit_price, False)
                
            except ValueError:
                log(f"二次识别价格转换失败: '{text_clean}'")
        
    except Exception as e:
        log(f"二次识别OCR失败: {e}")
    
    log("二次识别失败")
    return None

def recognize_fenghuo_region(debug_screenshot=False):
    """判定游戏模式区域识别"""
    region_percent = COORDINATE_CONFIG['fenghuo_region']['percent']
    region_px = (
        int(region_percent[0] * SCREEN_WIDTH),
        int(region_percent[1] * SCREEN_HEIGHT),
        int(region_percent[2] * SCREEN_WIDTH),
        int(region_percent[3] * SCREEN_HEIGHT)
    )
    try:
        screenshot = pyautogui.screenshot(region=region_px)
    except Exception as e:
        log(f"截图失败: {e}")
        return False
    
    # 保存调试截图
    if debug_screenshot:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        debug_path = os.path.join(current_dir, f"debug_region_original_{timestamp}.png")
        screenshot.save(debug_path)
        # 调试截图已保存（简化日志输出）
        
        # 清理旧的调试截图
        cleanup_debug_screenshots(max_files=4)
        
        # 在UI中显示调试截图
        if 'app_ui' in globals() and app_ui:
            app_ui.add_debug_image(debug_path, "原始截图")
    
    screenshot_np = np.array(screenshot)
    gray = cv2.cvtColor(screenshot_np, cv2.COLOR_RGB2GRAY)
    
    # 只使用方法1: 简单放大 + 二值化
    method = lambda img: cv2.threshold(cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC), 127, 255, cv2.THRESH_BINARY)[1]
    
    # 只使用配置1: 单行文本
    ocr_config = '--psm 7 --oem 3'
    
    try:
        processed_img = method(gray)
        
        # 保存处理后的调试图像
        if debug_screenshot:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            debug_path = os.path.join(current_dir, f"debug_processed_1_{timestamp}.png")
            if processed_img is not None:
                cv2.imwrite(debug_path, processed_img)
                # 在UI中显示调试截图
                if 'app_ui' in globals() and app_ui:
                    app_ui.add_debug_image(debug_path, "处理后截图 (方法1)")
        
        try:
            # 添加tessdata路径到配置中
            current_dir = os.path.dirname(os.path.abspath(__file__))
            local_tessdata = os.path.join(current_dir, 'tessdata_mini')
            
            if os.path.exists(local_tessdata):
                full_config = f'--tessdata-dir {local_tessdata} {ocr_config}'
            else:
                full_config = ocr_config
            
            text = pytesseract.image_to_string(processed_img, lang='chi_sim', config=full_config)
            text_clean = text.strip().replace(' ', '').replace('\n', '')
            
            if debug_screenshot:
                log(f"游戏模式判定 方法1 配置1: '{text_clean}'")
            
            # 检查多种匹配模式
            if any(pattern in text_clean for pattern in ['退出游戏', '退出', '游戏', '烽火地带', '烽火']):
                log(f"游戏模式判定成功 (方法1 配置1): '{text_clean}'")
                return True
            
            # 检查是否包含关键字符组合或烽火地带任意字符
            if ('退' in text_clean and '出' in text_clean) or ('游' in text_clean and '戏' in text_clean) or any(char in text_clean for char in ['烽', '火', '地', '带']):
                log(f"游戏模式判定成功 (字符匹配 方法1 配置1): '{text_clean}'")
                return True
                
        except Exception as e:
            if debug_screenshot:
                log(f"OCR识别失败 方法1 配置1: {e}")
                log(f"当前tesseract_cmd: {pytesseract.pytesseract.tesseract_cmd}")
                
    except Exception as e:
        if debug_screenshot:
            log(f"图像处理失败 方法1: {e}")
    
    if debug_screenshot:
        log("游戏模式判定失败")
    return False

def process_card(card_config):
    """处理单个卡片（判断最低和最高价格）"""
    global is_running, click_counter, total_refresh_count, consecutive_failure_count, fullstock_refresh_count
    if not is_running:
        return False

    # 获取页面稳定延迟
    page_delay = delays.get('page_stable_delay', 20) / 1000.0 # 页面稳定延迟，从配置中获取，默认为20毫秒，转换为秒

    # 获取UI设定的价格范围
    try:
        max_price_ui = int(max_price_var.get())  # 获取UI最高价格
        min_price_ui = int(min_price_var.get())  # 获取UI最低价格
    except ValueError:
        log(f"[错误] 价格必须是数字！")
        return False
    
    if min_price_ui < 0 or max_price_ui < 0:
        log(f"[错误] 价格不能为负数！")
        return False
    if min_price_ui > max_price_ui:
        log(f"[错误] 最低价格不能高于最高价格！")
        return False

    # 检查是否仍在运行
    if not is_running:
        return False

    position_percent = card_config.get('position', (0.3016, 0.2324))
    pos_px = percent_to_pixel(position_percent)
    try:
        pyautogui.moveTo(pos_px[0], pos_px[1])
        pyautogui.click()
        # 使用可中断的延迟替代time.sleep
        interruptible_sleep(page_delay)
    except Exception as e:
        log(f"点击卡片 '{card_config.get('name')}' 位置失败: {e}")
        return False

    # 再次检查是否仍在运行
    if not is_running:
        return False

    # 判断当前模式
    try:
        current_mode = mode_var.get() if mode_var else "金蛋"
    except NameError:
        current_mode = "金蛋"
    
    is_loadout_mode = current_mode in ["配装方案1", "配装方案2", "配装方案3"]
    
    # 根据模式和用户设置决定是否点击数量控制按钮
    should_click_quantity = False
    if is_loadout_mode:
        # 滚仓模式总是点击数量控制按钮
        should_click_quantity = True
    else:
        # 满仓模式根据"数量拉满"开关决定
        try:
            should_click_quantity = app_instance.quantity_max_var.get() if app_instance else False
        except (AttributeError, NameError):
            should_click_quantity = False
    
    if should_click_quantity and 'quantity_control_pos' in card_config:
        quantity_control_pos = card_config.get('quantity_control_pos')
        quantity_control_px = percent_to_pixel(quantity_control_pos)
        try:
            pyautogui.moveTo(quantity_control_px[0], quantity_control_px[1])
            pyautogui.click()
            # 此处可以根据需要增加短暂延时
        except Exception as e:
            log(f"点击卡片 '{card_config.get('name')}' 的数量控制按钮失败: {e}")
            # 即使数量控制失败，也尝试继续获取价格并购买，因为某些卡片可能不需要调整数量
            # return False # 如果数量控制是必须的，则取消注释此行

    # 再次检查是否仍在运行
    if not is_running:
        return False

    price = get_card_price()
    if price is None:
        try:
            pyautogui.press('esc')
        except:
            pass
        return False

    # 满仓模式的刷新次数计数
    if not is_loadout_mode:
        fullstock_refresh_count += 1
        total_refresh_count += 1  # 增加总刷新次数计数
    
    # 判断价格是否低于最低价格，视为识别失败
    if price < min_price_ui:
        log(f"价格 {price} 低于最低价格 {min_price_ui}，视为识别失败")
        consecutive_failure_count += 1
        try:
            pyautogui.press('esc')
        except:
            pass
        return None  # 返回None表示识别失败
    
    # 判断价格是否高于最高价格，跳过但不计入失败
    if price > max_price_ui:
        # 只在满仓模式下输出日志，滚仓模式的日志在process_loadout_plan中处理
        if not is_loadout_mode:
            log(f"第{fullstock_refresh_count}次刷新 识别价格：{price} 高于最高价格 {max_price_ui}，跳过")
        # 价格高于最高价时也重置连续失败计数器，因为价格识别是成功的
        consecutive_failure_count = 0
        try:
            pyautogui.press('esc')
        except:
            pass
        return False  # 返回False表示跳过，不计入失败

    # 价格识别成功且在范围内，重置连续失败计数器
    consecutive_failure_count = 0
    global grab_no_stock_failure_count, loadout_grab_no_stock_failure_count
    grab_no_stock_failure_count = 0  # 重置满仓模式抢无货失败计数器
    loadout_grab_no_stock_failure_count = 0  # 重置滚仓模式抢无货失败计数器

    # 取消购买页等待延迟，价格合适时立即购买

    # 检查调试模式
    try:
        debug_mode = app_instance.debug_mode_var.get() if app_instance else False
    except (AttributeError, NameError):
        debug_mode = False
    
    if debug_mode:
        log(f"调试模式已启用，价格合适但不执行购买操作。卡片: {card_config.get('name', '未知')}, 价格: {price}")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False

    # 在购买操作前检查是否仍在运行
    if not is_running:
        log(f"购买操作前检查：程序已停止，跳过购买 {card_config.get('name', '未知')}")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False

    buy_pos = card_config.get('buy_button_pos', (0.822, 0.796))
    buy_pos_px = percent_to_pixel(buy_pos)
    try:
        pyautogui.moveTo(buy_pos_px[0], buy_pos_px[1])
        pyautogui.click()
        click_counter += 1
        total_refresh_count += 1  # 增加总刷新次数
        # 更新UI中的点击次数
        if root and root.winfo_exists(): # 确保root存在
            root.after(0, update_click_count)
    except Exception as e:
        log(f"点击卡片 '{card_config.get('name')}' 的购买按钮失败: {e}")
        return False

    try:
        pyautogui.press('esc') # 尝试关闭购买成功后的弹窗或返回
    except:
        pass

    # log(f"[+]成功购买卡片 '{card_config.get('name')}'，价格: {price} (设定范围: {min_price_ui}-{max_price_ui})") # 注释掉购买成功日志
    return True

def process_loadout_plan():
    """处理配装方案模式的逻辑"""
    global is_running, consecutive_failure_count, click_counter, loadout_refresh_count, loadout_total_amount, loadout_last_price, total_refresh_count
    
    # 获取当前模式
    current_mode = mode_var.get() if mode_var else "金蛋"
    if current_mode not in ["配装方案1", "配装方案2", "配装方案3"]:
        return False
    
    # 获取滚仓模式的延迟设置
    try:
        bullet_count = int(app_instance.bullet_count_var.get()) if app_instance else 4080
        bullet_min_price = float(app_instance.bullet_min_price_var.get()) if app_instance else 0.1
        bullet_max_price = float(app_instance.bullet_max_price_var.get()) if app_instance else 0.5
        refresh_delay = float(app_instance.refresh_delay_var.get()) / 1000.0 if app_instance else 1.0
        screenshot_delay = float(app_instance.screenshot_delay_var.get()) / 1000.0 if app_instance else 0.5
        debug_mode = app_instance.debug_mode_var.get() if app_instance else False
    except (ValueError, AttributeError):
        log(f"[错误] 子弹数量、价格范围和延迟设置必须是数字！")
        return False
    
    log(f"子弹数量: {bullet_count}")
    log(f"单发价格范围: {bullet_min_price} - {bullet_max_price}")
    log(f"刷新延迟: {refresh_delay*1000}ms, 截图延迟: {screenshot_delay*1000}ms")
    log(f"调试模式: {'启用' if debug_mode else '禁用'}")
    
    # L键进入配装界面（立即进入，无延迟）
    try:
        pyautogui.press('l')
        loadout_refresh_count += 1  # 增加刷新次数
        total_refresh_count += 1  # 增加总刷新次数
        log(f"按L键进入配装界面 (第{loadout_refresh_count}次刷新，总计第{total_refresh_count}次)")
        # 更新UI显示
        if root and root.winfo_exists():
            root.after(0, update_loadout_info)
    except Exception as e:
        log(f"按L键失败: {e}")
        return False
    
    # 获取配装方案坐标
    loadout_key = f"loadout_plan_{current_mode[-1]}"  # 提取数字
    if loadout_key not in COORDINATE_CONFIG:
        log(f"配装方案坐标未配置: {loadout_key}")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    # 点击配装方案坐标
    loadout_pos = COORDINATE_CONFIG[loadout_key]['percent']
    if len(loadout_pos) < 2 or loadout_pos[0] <= 0 or loadout_pos[1] <= 0:
        log(f"配装方案坐标未正确设置: {loadout_pos}")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    loadout_px = percent_to_pixel(loadout_pos)
    try:
        pyautogui.moveTo(loadout_px[0], loadout_px[1])
        pyautogui.click()
        # 刷新延迟只控制点击配装方案坐标后的等待时间
        time.sleep(refresh_delay)
        log(f"点击配装方案坐标: {loadout_px}")
    except Exception as e:
        log(f"点击配装方案坐标失败: {e}")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    # 截图延迟：在点击方案坐标后等待设定时间再截图识别
    time.sleep(screenshot_delay)
    
    # 获取价格
    price_result = get_card_price()
    if price_result is None:
        log("价格识别失败，get_card_price 返回 None")
        consecutive_failure_count += 1
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    # 处理返回值（可能是元组或单个值）
    if isinstance(price_result, tuple):
        # 滚仓模式返回 (原始OCR结果, 单价)
        original_ocr, single_bullet_price = price_result
        price = single_bullet_price * bullet_count  # 计算总价格用于统计
        # 滚仓模式下忽略小数部分，提高识别和计算速度
        display_unit_price = int(single_bullet_price)
    else:
        # 满仓模式返回单个价格值
        price = price_result
        single_bullet_price = price / bullet_count
        display_unit_price = int(single_bullet_price)
    
    # 判断单发价格是否在合理范围内，不在范围内立即返回
    if single_bullet_price < bullet_min_price:
        consecutive_failure_count += 1
        if isinstance(price_result, tuple):
            # 滚仓模式
            log(f"第{loadout_refresh_count}次刷新 总价 {int(price)} 单价 {display_unit_price} 低于最低价 识别失败第{consecutive_failure_count}次")
        else:
            # 满仓模式
            log(f"第{fullstock_refresh_count}次刷新 总价 {int(price)} 单价 {display_unit_price} 低于最低价 识别失败第{consecutive_failure_count}次")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    if single_bullet_price > bullet_max_price:
        # 价格高于最高价不是识别失败，应该重置失败计数器
        consecutive_failure_count = 0
        if isinstance(price_result, tuple):
            # 滚仓模式
            log(f"第{loadout_refresh_count}次刷新 总价 {int(price)} 单价 {display_unit_price} 高于最高价 跳过")
        else:
            # 满仓模式
            log(f"第{fullstock_refresh_count}次刷新 总价 {int(price)} 单价 {display_unit_price} 高于最高价 跳过")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    # 价格识别成功且在合理范围内，输出识别结果并重置失败计数器
    if isinstance(price_result, tuple):
        # 滚仓模式
        log(f"第{loadout_refresh_count}次刷新 总价 {int(price)} 单价 {display_unit_price} 低于最高价 购买")
    else:
        # 满仓模式
        log(f"第{fullstock_refresh_count}次刷新 总价 {int(price)} 单价 {display_unit_price} 低于最高价 购买")
    
    consecutive_failure_count = 0
    global grab_no_stock_failure_count
    grab_no_stock_failure_count = 0  # 同时重置抢无货失败计数器
    
    # 检查调试模式
    if debug_mode:
        log(f"调试模式已启用，价格合适但不执行购买操作。单发价格: {single_bullet_price:.2f}")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    # 价格合适，执行购买前先进行二次验证
    # 滚仓模式下，价格识别区域就是购买按钮位置，先点击进入购买界面
    
    # 获取价格识别区域的中心点作为点击位置
    price_region = COORDINATE_CONFIG['price_region']['percent']
    if len(price_region) < 4 or price_region[0] <= 0 or price_region[1] <= 0:
        log("价格识别区域坐标未设置")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False
    
    # 计算价格识别区域的中心点坐标
    center_x = price_region[0] + price_region[2] / 2
    center_y = price_region[1] + price_region[3] / 2
    click_pos_px = percent_to_pixel((center_x, center_y))
    
    try:
        # 点击进入购买界面
        pyautogui.moveTo(click_pos_px[0], click_pos_px[1])
        pyautogui.click()
        log(f"滚仓模式：点击价格识别区域中心点 ({center_x:.4f}, {center_y:.4f}) 进入购买界面")
        
        # 等待界面稳定
        time.sleep(0.5)
        
        # 进行二次价格识别验证
        log("开始二次价格识别验证")
        secondary_result = get_secondary_price(bullet_count, bullet_min_price, bullet_max_price, debug_screenshot=debug_screenshot_enabled)
        
        if secondary_result is None:
            log("二次识别失败，执行ESC返回")
            try:
                pyautogui.press('esc')
                time.sleep(0.5)
            except:
                pass
            return False
        
        secondary_price, secondary_unit_price, is_in_range = secondary_result
        
        if not is_in_range:
            log(f"二次识别价格不在范围内，执行ESC返回")
            try:
                pyautogui.press('esc')
                time.sleep(0.5)
            except:
                pass
            return False
        
        # 二次验证通过，点击二次识别区域进行购买
        secondary_region = COORDINATE_CONFIG['secondary_price_region']['percent']
        secondary_center_x = secondary_region[0] + secondary_region[2] / 2
        secondary_center_y = secondary_region[1] + secondary_region[3] / 2
        secondary_click_pos_px = percent_to_pixel((secondary_center_x, secondary_center_y))
        
        pyautogui.moveTo(secondary_click_pos_px[0], secondary_click_pos_px[1])
        pyautogui.click()
        click_counter += 1
        
        # 更新滚仓统计信息（使用二次识别的价格）
        loadout_total_amount += secondary_price
        loadout_last_price = secondary_unit_price
        
        # 更新UI中的点击次数和滚仓信息
        if root and root.winfo_exists():
            root.after(0, update_click_count)
            root.after(0, update_loadout_info)
        
        log(f"滚仓模式二次验证通过：点击二次识别区域 ({secondary_center_x:.4f}, {secondary_center_y:.4f}) 完成购买")
        
        # 购买成功后触发返回大战场流程
        log("购买成功，触发返回大战场流程")
        return_to_battlefield(current_mode)
        
        return True
        
    except Exception as e:
        log(f"购买流程失败: {e}")
        try:
            pyautogui.press('esc')
        except:
            pass
        return False

def return_to_battlefield(current_mode):
    """通用的返回大战场流程"""
    global is_running
    log("开始执行返回大战场流程")
    
    # 循环执行esc和检测，直到检测到烽火地带
    while is_running:
        try:
            pyautogui.press('esc')
            interruptible_sleep(1.5)  # esc后等待1.5秒再进行判定游戏模式区域
        except Exception as e:
            log(f"执行返回操作失败: {e}")
        
        # 检查运行状态
        if not is_running:
            log("检测到暂停信号，停止返回大战场流程")
            return
            
        # 检查是否识别到"烽火地带"中的任意一个字
        if recognize_fenghuo_region(debug_screenshot=debug_screenshot_enabled):
            log("检测到烽火地带区域，继续执行")
            break
        else:
            log("未检测到烽火地带，继续执行esc")
            interruptible_sleep(0.1)
    
    # 根据模式执行不同的后续处理
    if current_mode in ["配装方案1", "配装方案2", "配装方案3"]:
        # 滚仓模式的特殊处理
        loadout_return_sequence(current_mode)
    else:
        # 满仓模式的处理
        fullstock_return_sequence()

def loadout_return_sequence(current_mode):
    """滚仓模式专用的返回后续处理函数"""
    global is_running, loop_thread
    log("执行滚仓模式返回后续处理")
    
    try:
        # 连续失败计数器
        failure_count = 0
        max_failures = 5
        
        # 1. 连续失败超过五次则按ESC并进行游戏模式区域识别
        while failure_count < max_failures:
            if not is_running:
                return
                
            # 尝试识别游戏模式区域
            if recognize_fenghuo_region(debug_screenshot=debug_screenshot_enabled):
                log("识别到'烽火地带'，继续执行后续操作")
                
                # 点击切换大战场位置
                log("识别到'烽火地带'，点击切换大战场位置")
                
                # 直接从coordinate_settings.json读取battlefield_switch坐标
                try:
                    with open(COORDINATE_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        saved_coords = json.load(f)
                        if 'battlefield_switch' in saved_coords:
                            battlefield_coord = saved_coords['battlefield_switch']['percent']
                            log(f"从配置文件读取到切换大战场位置坐标: {battlefield_coord}")
                        else:
                            battlefield_coord = COORDINATE_CONFIG['battlefield_switch']['percent']
                            log(f"配置文件中未找到battlefield_switch，使用默认坐标: {battlefield_coord}")
                except Exception as e:
                    log(f"读取配置文件失败: {e}，使用默认坐标")
                    battlefield_coord = COORDINATE_CONFIG['battlefield_switch']['percent']
                
                if len(battlefield_coord) >= 2 and battlefield_coord[0] > 0 and battlefield_coord[1] > 0:  # 确保坐标已设置
                    # 只使用前两个值作为点击坐标
                    click_coord = (battlefield_coord[0], battlefield_coord[1])
                    battlefield_px = percent_to_pixel(click_coord)
                    pyautogui.click(battlefield_px)
                    log(f"点击切换大战场位置: {battlefield_coord}")
                    interruptible_sleep(2)

                    # 按ESC三次
                    pyautogui.press('esc')
                    interruptible_sleep(2)
                    pyautogui.press('esc')
                    interruptible_sleep(2)
                    pyautogui.press('esc')
                    interruptible_sleep(0.5)
                    log("按ESC三次，每次间隔2秒，最后一次间隔0.5秒")

                    # 直接点击判定游戏模式区域坐标
                    fenghuo_region = COORDINATE_CONFIG.get('fenghuo_region', {}).get('percent', (0.5, 0.5))
                    fenghuo_px = percent_to_pixel(fenghuo_region)
                    pyautogui.click(fenghuo_px)
                    log(f"直接点击判定游戏模式区域坐标: {fenghuo_region}")
                    interruptible_sleep(2)
                break
            else:
                failure_count += 1
                log(f"未识别到烽火地带，失败次数: {failure_count}/{max_failures}")
                interruptible_sleep(2)
                
        # 如果连续失败超过五次，按ESC
        if failure_count >= max_failures:
            log("连续失败超过五次，按ESC键")
            pyautogui.press('esc')
            interruptible_sleep(2)
        
        # 滚仓模式专用：进入地图的三个步骤
        log("开始执行滚仓模式进入地图流程")
        
        # 等待2秒后开始点击进入地图的三个区域
        interruptible_sleep(2)
        
        # 进入地图的三个步骤
        # 步骤1: 点击坐标 (0.8109, 0.8833, 0.0042, 0.0046)
        if not is_running:
            return
        coord1 = (0.8109, 0.8833)
        coord1_px = percent_to_pixel(coord1)
        pyautogui.click(coord1_px)
        log(f"点击进入地图坐标1: {coord1}")
        interruptible_sleep(1)  # 等待1秒
        
        # 步骤2: 点击坐标 (0.4276, 0.2426, 0.0031, 0.0093)
        if not is_running:
            return
        coord2 = (0.4276, 0.2426)
        coord2_px = percent_to_pixel(coord2)
        pyautogui.click(coord2_px)
        log(f"点击进入地图坐标2: {coord2}")
        interruptible_sleep(1)  # 等待1秒
        
        # 步骤3: 点击坐标 (0.8536, 0.6296, 0.0042, 0.0037)
        if not is_running:
            return
        coord3 = (0.8536, 0.6296)
        coord3_px = percent_to_pixel(coord3)
        pyautogui.click(coord3_px)
        log(f"点击进入地图坐标3: {coord3}")
        
        # 按L键进入配装
        pyautogui.press('l')
        log("按L键进入配装")
        interruptible_sleep(0.5)
        
        # 开始后续的识别操作
        log("滚仓模式返回后续处理完成，继续循环")
        
        # 只有在循环线程存在且活动时才确保循环继续运行
        if loop_thread and loop_thread.is_alive():
            is_running = True
        else:
            log("循环线程未运行，滚仓模式返回后续处理结束")
    
    except Exception as e:
        log(f"滚仓模式返回后续处理出错: {e}")
        import traceback
        log(f"错误详情: {traceback.format_exc()}")

def fullstock_return_sequence():
    """满仓模式的返回后续处理函数"""
    global is_running, loop_thread
    log("执行满仓模式返回后续处理")
    
    try:
        # 连续失败计数器
        failure_count = 0
        max_failures = 5
        
        # 1. 连续失败超过五次则按ESC并进行游戏模式区域识别
        while failure_count < max_failures:
            if not is_running:
                return
                
            # 尝试识别游戏模式区域
            if recognize_fenghuo_region(debug_screenshot=debug_screenshot_enabled):
                log("识别到'烽火地带'，继续执行后续操作")
                
                # 点击切换大战场位置
                log("识别到'烽火地带'，点击切换大战场位置")
                
                # 直接从coordinate_settings.json读取battlefield_switch坐标
                try:
                    with open(COORDINATE_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                        saved_coords = json.load(f)
                        if 'battlefield_switch' in saved_coords:
                            battlefield_coord = saved_coords['battlefield_switch']['percent']
                            log(f"从配置文件读取到切换大战场位置坐标: {battlefield_coord}")
                        else:
                            battlefield_coord = COORDINATE_CONFIG['battlefield_switch']['percent']
                            log(f"配置文件中未找到battlefield_switch，使用默认坐标: {battlefield_coord}")
                except Exception as e:
                    log(f"读取配置文件失败: {e}，使用默认坐标")
                    battlefield_coord = COORDINATE_CONFIG['battlefield_switch']['percent']
                
                if len(battlefield_coord) >= 2 and battlefield_coord[0] > 0 and battlefield_coord[1] > 0:  # 确保坐标已设置
                    # 只使用前两个值作为点击坐标
                    click_coord = (battlefield_coord[0], battlefield_coord[1])
                    battlefield_px = percent_to_pixel(click_coord)
                    pyautogui.click(battlefield_px)
                    log(f"点击切换大战场位置: {battlefield_coord}")
                    interruptible_sleep(2)

                    # 按ESC三次
                    pyautogui.press('esc')
                    interruptible_sleep(2)
                    pyautogui.press('esc')
                    interruptible_sleep(2)
                    pyautogui.press('esc')
                    interruptible_sleep(0.5)
                    log("按ESC三次，每次间隔2秒，最后一次间隔0.5秒")

                    # 直接点击判定游戏模式区域坐标
                    fenghuo_region = COORDINATE_CONFIG.get('fenghuo_region', {}).get('percent', (0.5, 0.5))
                    fenghuo_px = percent_to_pixel(fenghuo_region)
                    pyautogui.click(fenghuo_px)
                    log(f"直接点击判定游戏模式区域坐标: {fenghuo_region}")
                    interruptible_sleep(2)
                break
            else:
                failure_count += 1
                log(f"未识别到烽火地带，失败次数: {failure_count}/{max_failures}")
                interruptible_sleep(2)
                
        # 如果连续失败超过五次，按ESC
        if failure_count >= max_failures:
            log("连续失败超过五次，按ESC键")
            pyautogui.press('esc')
            interruptible_sleep(2)
        
        # 满仓模式专用：直接点击交易行位置，不进入地图
        log("开始执行满仓模式后续流程")
        
        # 等待2秒后点击交易行位置
        interruptible_sleep(2)
        
        # 点击交易行位置
        trading_house_pos = (0.3656, 0.0574)
        trading_house_px = percent_to_pixel(trading_house_pos)
        pyautogui.click(trading_house_px)
        log("点击交易行位置")
        interruptible_sleep(1)
        
        # 开始后续的识别操作
        log("满仓模式返回后续处理完成，继续循环")
        
        # 只有在循环线程存在且活动时才确保循环继续运行
        if loop_thread and loop_thread.is_alive():
            is_running = True
        else:
            log("循环线程未运行，满仓模式返回后续处理结束")
    
    except Exception as e:
        log(f"满仓模式返回后续处理出错: {e}")
        import traceback
        log(f"错误详情: {traceback.format_exc()}")

def loop_function():
    """循环执行函数（放在新线程中）"""
    global is_running, consecutive_failure_count, total_refresh_count
    
    # 获取用户设置的返回大战场刷新次数阈值
    try:
        threshold = int(return_battlefield_threshold_var.get()) if return_battlefield_threshold_var else 200
    except (ValueError, AttributeError):
        threshold = 200  # 如果获取失败，使用默认值
    
    # 检查是否为配装方案模式
    current_mode = mode_var.get() if mode_var else "金蛋"
    if current_mode in ["配装方案1", "配装方案2", "配装方案3"]:
        log(f"配装方案模式: {current_mode}")
        while is_running:
            # 检查总刷新次数是否达到阈值
            if total_refresh_count >= threshold:
                log(f"总刷新次数已达到{threshold}次，触发返回大战场流程")
                return_to_battlefield(current_mode)
                # 不设置is_running为False，让循环继续
                if root and root.winfo_exists():
                    root.after(0, update_status, f"达到{threshold}次刷新限制，重新开始")
                # 重置计数器，继续循环
                total_refresh_count = 0
                continue
            
            if not process_loadout_plan():
                if consecutive_failure_count >= 5:
                    log("配装方案连续失败5次，触发返回大战场流程")
                    return_to_battlefield(current_mode)
                    # 不设置is_running为False，让循环继续
                    if root and root.winfo_exists():
                        root.after(0, update_status, "连续失败，重新开始")
                    # 重置失败计数器，继续循环
                    consecutive_failure_count = 0
                    continue
            if is_running:
                interruptible_sleep(0.1)  # 短暂延迟后继续
        return
    
    # 原有的卡片模式逻辑
    if not valid_cards:
        log("没有有效的卡片配置")
        is_running = False
        # 更新状态显示
        if 'root' in globals() and root.winfo_exists(): # 确保UI已创建且存在
            root.after(0, update_status, "没有有效卡片配置")
        return
    
    # 只获取一次有效卡片位置
    cards_to_process = valid_cards.copy()
    
    while is_running:
        # 检查总刷新次数是否达到阈值
        if total_refresh_count >= threshold:
            log(f"总刷新次数已达到{threshold}次，触发返回大战场流程")
            return_to_battlefield(current_mode)
            # 不设置is_running为False，让循环继续
            if root and root.winfo_exists():
                root.after(0, update_status, f"达到{threshold}次刷新限制，重新开始")
            # 重置计数器，继续循环
            total_refresh_count = 0
            continue
            
        for card in cards_to_process:
            if not is_running:
                break
            
            # 检查连续失败次数
            if consecutive_failure_count >= 5:
                log("连续失败5次，触发返回大战场流程")
                return_to_battlefield(current_mode)
                # 不设置is_running为False，让循环继续
                if root and root.winfo_exists():
                    root.after(0, update_status, "连续失败，重新开始")
                # 重置失败计数器，继续循环
                consecutive_failure_count = 0
                continue

            # 处理卡片
            process_card(card)
            
        # 将极短延迟移到外层循环，减少不必要的暂停
        if is_running: # 仅在运行时才延迟
            time.sleep(0.01) # 循环间隔延迟，避免CPU占用过高（保持极短延迟不变）

def start_loop():
    """开始循环（在新线程中运行）"""
    global is_running, loop_thread, consecutive_failure_count, click_counter, total_refresh_count
    if is_running:
        log("循环已在运行中")
        return
    
    click_counter = 0 # 每次启动时重置点击计数器
    total_refresh_count = 0 # 每次启动时重置总刷新计数器
    # 保存UI中的参数到配置
    save_config_from_ui()
    init_config()  # 重新初始化配置
    is_running = True
    # adjust_price_clicks = 0 # 这个变量似乎没有在其他地方使用，考虑是否移除
    consecutive_failure_count = 0
    log("循环已启动 (F9暂停/继续, F10停止)")
    # 更新状态显示
    root.after(0, update_status, "运行中")
    loop_thread = Thread(
        target=loop_function,
        daemon=True
    )
    loop_thread.start()

def stop_loop():
    """停止循环"""
    global is_running, consecutive_failure_count, click_counter, grab_no_stock_failure_count, loadout_grab_no_stock_failure_count
    is_running = False
    consecutive_failure_count = 0
    click_counter = 0 # 停止时也重置点击计数器
    grab_no_stock_failure_count = 0  # 重置满仓模式抢无货失败计数器
    loadout_grab_no_stock_failure_count = 0  # 重置滚仓模式抢无货失败计数器
    # 更新状态显示
    if 'root' in globals() and root.winfo_exists():
        root.after(0, update_status, "未运行")
        root.after(0, update_click_count) # 更新点击次数显示为0

def pause_loop():
    """暂停/继续循环"""
    global is_running
    if loop_thread and loop_thread.is_alive(): # 仅当循环线程存在且活动时才操作
        old_status = is_running
        is_running = not is_running
        status_text = "暂停中" if not is_running else "运行中"
        log_message = "暂停" if not is_running else "继续"
        # 更新状态显示
        if 'root' in globals() and root.winfo_exists():
            root.after(0, update_status, status_text)
    elif not is_running and not (loop_thread and loop_thread.is_alive()):
        log("循环未启动，无法暂停/继续。请先按F8启动。")
    else: # is_running is True but thread is not alive (e.g. after auto-stop)
        log("循环已结束，无法暂停/继续。请按F8重新启动。")

def save_config_from_ui():
    """从UI保存参数到配置 (keys.json 和 user_settings.json)"""
    global config, mode_var, min_price_var, max_price_var, delay_stable_var, delay_buy_var, app_instance
    
    if not config: # 如果全局 config 未加载，尝试加载一次
        config = load_config()
        if not config: # 如果加载失败，则初始化为空字典，避免后续 .get 报错
             config = {"cards_config": [], "delays": {}}
    
    user_settings_to_save = {}
    selected_mode_name = mode_var.get() if mode_var else "收藏第一位置"

    # 1. 保存延迟配置到 user_settings.json (也更新全局 config 中的 delays)
    try:
        page_delay = int(delay_stable_var.get())
        buy_delay = int(delay_buy_var.get())
        
        if 'delays' not in config:
            config['delays'] = {}
        config['delays']['page_stable_delay'] = page_delay
        config['delays']['buy_page_wait_delay'] = buy_delay
        
        user_settings_to_save['page_stable_delay'] = page_delay
        user_settings_to_save['buy_page_wait_delay'] = buy_delay
    except ValueError:
        log(f"[错误] 延迟值必须是数字！")
        return
    except TypeError: # 处理 config['delays'] 可能为 None 的情况
        log(f"[错误] 内部配置错误 (delays)。")
        return

    # 2. 保存UI价格 (最低和最高) 到 user_settings.json (针对当前模式)
    #    并更新 keys.json 中对应模式卡片的 min_price 和 max_price
    try:
        min_price_ui = int(min_price_var.get())
        max_price_ui = int(max_price_var.get())

        if min_price_ui < 0 or max_price_ui < 0:
            log(f"[错误] 价格不能为负数！")
            return
        if min_price_ui > max_price_ui:
            log(f"[错误] 最低价格不能高于最高价格！")
            return

        user_settings_to_save[f'{selected_mode_name}_min_price'] = min_price_ui
        user_settings_to_save[f'{selected_mode_name}_max_price'] = max_price_ui

    except ValueError:
        log(f"[错误] 价格必须是数字！")
        return
    except TypeError:
        log(f"[错误] 内部配置错误 (prices)。")
        return

    # 3. 保存滚仓模式的参数到 user_settings.json
    if app_instance:
        try:
            # 保存滚仓模式的参数
            bullet_count = int(app_instance.bullet_count_var.get())
            bullet_min_price = float(app_instance.bullet_min_price_var.get())
            bullet_max_price = float(app_instance.bullet_max_price_var.get())
            refresh_delay = int(app_instance.refresh_delay_var.get())
            screenshot_delay = int(app_instance.screenshot_delay_var.get())
            
            user_settings_to_save['bullet_count'] = bullet_count
            user_settings_to_save['bullet_min_price'] = bullet_min_price
            user_settings_to_save['bullet_max_price'] = bullet_max_price
            user_settings_to_save['refresh_delay'] = refresh_delay
            user_settings_to_save['screenshot_delay'] = screenshot_delay
            
            # 保存"数量拉满"开关状态
            quantity_max_enabled = app_instance.quantity_max_var.get()
            user_settings_to_save['quantity_max_enabled'] = quantity_max_enabled
            
            # 保存"抢无货"开关状态
            grab_no_stock_enabled = app_instance.grab_no_stock_var.get()
            user_settings_to_save['grab_no_stock_enabled'] = grab_no_stock_enabled
            
            # 保存返回大战场刷新次数阈值
            return_threshold = int(return_battlefield_threshold_var.get())
            user_settings_to_save['return_battlefield_threshold'] = return_threshold
            
        except ValueError:
            log(f"[错误] 滚仓模式参数必须是数字！")
            return

    # 3. 保存到 keys.json 文件 (包含更新后的卡片价格和通用延迟)
    try:
        with open('keys.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        log("配置已保存到 keys.json")
    except Exception as e:
        log(f"保存配置到 keys.json 失败: {e}")
        return # 如果保存keys.json失败，也阻止保存user_settings.json

    # 4. 保存到 user_settings.json 文件 (包含特定模式的价格和通用延迟)
    try:
        # 先读取旧的 user_settings，然后更新，避免覆盖其他模式的设置
        existing_user_settings = load_user_settings()
        existing_user_settings.update(user_settings_to_save)
        with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_user_settings, f, ensure_ascii=False, indent=4)
        log(f"用户设置已保存到 {USER_SETTINGS_FILE}")
    except Exception as e:
        log(f"保存用户设置到 {USER_SETTINGS_FILE} 失败: {e}")
        messagebox.showerror("错误", f"保存用户设置到 {USER_SETTINGS_FILE} 失败: {e}")

def log_to_queue(message):
    """线程安全的日志输出"""
    logging.info(message)
    if log_queue: # 确保log_queue已初始化
        log_queue.put(message)

def update_log_display():
    """定期从队列获取日志并更新UI"""
    while not log_queue.empty():
        message = log_queue.get()
        log_text.configure(state='normal')  # 允许编辑
        log_text.insert(tk.END, message + "\n")
        log_text.see(tk.END)  # 滚动到最新日志
        log_text.configure(state='disabled')  # 禁用编辑
    if 'root' in globals() and root.winfo_exists():
        root.after(100, update_log_display)  # 每100毫秒检查一次

def update_status(status):
    """更新状态显示"""
    if 'status_var' in globals():
        status_var.set(f"状态: {status}")

def update_click_count():
    """更新点击次数显示"""
    if 'click_count_var' in globals():
        click_count_var.set(f"本次运行共点击购买按钮 {click_counter} 次")

def update_loadout_info():
    """更新滚仓模式信息显示"""
    if 'loadout_info_var' in globals() and loadout_info_var:
        info_text = f"第{loadout_refresh_count}次刷新 | 购买金额: {loadout_total_amount} | 单价: {loadout_last_price:.2f}"
        loadout_info_var.set(info_text)

# 后台热键监听逻辑
def interruptible_sleep(duration):
    """可中断的延迟函数，每10ms检查一次is_running状态"""
    global is_running
    start_time = time.time()
    while time.time() - start_time < duration and is_running:
        time.sleep(0.01)  # 每10ms检查一次状态，提高响应速度

def on_key_press(key):
    """后台捕获按键事件（不受窗口焦点影响）"""
    global is_running, app_instance # 需要访问 is_running 来判断是否启动
    try:
        if key == keyboard.Key.f1:
            # F1快捷键：开始通用框选区域
            if app_instance:
                log("F1快捷键触发：开始通用框选区域")
                # 调用通用框选功能
                app_instance.start_generic_region_selection()
            else:
                log("应用实例未初始化，无法使用F1快捷键")
        elif key == keyboard.Key.f8:
            if not is_running: # 仅在未运行时启动
                start_loop()
            else:
                log("循环已在运行中，无需重复启动 (F9暂停/继续, F10停止)")
        elif key == keyboard.Key.f9:
            pause_loop()
        elif key == keyboard.Key.f10:
            stop_loop()
    except AttributeError:
        pass  # 忽略特殊按键（如Ctrl、Alt等组合键，需扩展可加逻辑）

# 全局坐标配置
COORDINATE_CONFIG = {
    'fenghuo_region': {
        'name': '判定游戏模式区域',
        'percent': (0.0698, 0.3037, 0.0458, 0.0232),
        'description': '判定游戏模式文字识别区域 (x%, y%, width%, height%)'
    },
    'price_region': {
        'name': '价格区域',
        'percent': (0.0, 0.0, 0.0, 0.0),  # 将在后面设置
        'description': '价格文字识别区域 (x%, y%, width%, height%)'
    },
    'return_button': {
        'name': '返回按钮',
        'percent': (0.0521, 0.0648, 0.0, 0.0),  # x%, y%, 点击坐标
        'description': '返回按钮点击位置 (x%, y%)'
    },
    'buy_button': {
        'name': '购买按钮',
        'percent': (0.0, 0.0, 0.0, 0.0),  # 将在后面设置
        'description': '购买按钮点击位置 (x%, y%)'
    },
    'battlefield_switch': {
        'name': '切换大战场位置',
        'percent': (0.0, 0.0, 0.0, 0.0),  # x%, y%, 点击坐标
        'description': '切换大战场模式的点击位置 (x%, y%)'
    },
    'loadout_plan_1': {
        'name': '配装方案1坐标',
        'percent': (0.0719, 0.2713, 0.0141, 0.0148),  # x%, y%, width%, height%
        'description': '配装方案1的点击位置 (x%, y%, width%, height%)'
    },
    'loadout_plan_2': {
        'name': '配装方案2坐标',
        'percent': (0.0, 0.0, 0.0, 0.0),  # x%, y%, width%, height%
        'description': '配装方案2的点击位置 (x%, y%, width%, height%)'
    },
    'loadout_plan_3': {
        'name': '配装方案3坐标',
        'percent': (0.0, 0.0, 0.0, 0.0),  # x%, y%, width%, height%
        'description': '配装方案3的点击位置 (x%, y%, width%, height%)'
    },
    'secondary_price_region': {
        'name': '二次识别价格区域',
        'percent': (0.4828, 0.6870, 0.0479, 0.0222),  # x%, y%, width%, height%
        'description': '滚仓模式二次价格识别区域 (x%, y%, width%, height%)'
    }
}

# 坐标配置文件
COORDINATE_SETTINGS_FILE = 'coordinate_settings.json'

def load_coordinate_settings():
    """加载坐标配置，优先使用内置配置，然后尝试加载外部配置文件进行合并"""
    global COORDINATE_CONFIG
    
    # 使用内置默认坐标配置（已在全局变量中定义）
    log("使用内置默认坐标配置")
    
    # 尝试加载外部坐标配置文件进行合并
    try:
        with open(COORDINATE_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            saved_coords = json.load(f)
            # 获取当前模式，如果mode_var未定义则使用默认值
            try:
                current_mode = mode_var.get() if mode_var else "金蛋"
            except NameError:
                current_mode = "金蛋"
            
            # 模式列表定义
            full_warehouse_modes = ['金蛋', '紫蛋', '肉蛋']
            loadout_modes = ['配装方案1', '配装方案2', '配装方案3']
            all_modes = full_warehouse_modes + loadout_modes
            
            # 加载共享坐标（满仓和滚仓模式间共享）
            if 'shared' in saved_coords:
                shared_coords = saved_coords['shared']
                for key, value in shared_coords.items():
                    if key in COORDINATE_CONFIG:
                        COORDINATE_CONFIG[key]['percent'] = tuple(value['percent'])
            
            # 加载价格识别区域（满仓和滚仓模式分别独立保存）
            if current_mode in full_warehouse_modes:
                # 满仓模式使用fullstock_price_shared区域
                if 'fullstock_price_shared' in saved_coords and 'price_area' in saved_coords['fullstock_price_shared']:
                    COORDINATE_CONFIG['price_region']['percent'] = tuple(saved_coords['fullstock_price_shared']['price_area']['percent'])
                elif current_mode in saved_coords and 'price_area' in saved_coords[current_mode]:
                    COORDINATE_CONFIG['price_region']['percent'] = tuple(saved_coords[current_mode]['price_area']['percent'])
            elif current_mode in loadout_modes:
                # 滚仓模式使用loadout_price_shared区域
                if 'loadout_price_shared' in saved_coords and 'price_area' in saved_coords['loadout_price_shared']:
                    COORDINATE_CONFIG['price_region']['percent'] = tuple(saved_coords['loadout_price_shared']['price_area']['percent'])
                elif current_mode in saved_coords and 'price_area' in saved_coords[current_mode]:
                    COORDINATE_CONFIG['price_region']['percent'] = tuple(saved_coords[current_mode]['price_area']['percent'])
            elif current_mode in saved_coords and 'price_area' in saved_coords[current_mode]:
                # 其他模式使用独立价格区域
                COORDINATE_CONFIG['price_region']['percent'] = tuple(saved_coords[current_mode]['price_area']['percent'])
            
            # 加载购买按钮坐标（满仓和滚仓模式间共享）
            if current_mode in all_modes and 'buy_button_shared' in saved_coords:
                if 'buy_button' in saved_coords['buy_button_shared']:
                    COORDINATE_CONFIG['buy_button']['percent'] = tuple(saved_coords['buy_button_shared']['buy_button']['percent'])
            
            # 加载当前模式的坐标配置
            if current_mode in saved_coords:
                mode_coords = saved_coords[current_mode]
                for key, value in mode_coords.items():
                    # 排除已在共享部分处理的坐标
                    if key in COORDINATE_CONFIG and key not in ['price_area', 'buy_button', 'fenghuo_region', 'return_button', 'battlefield_switch']:
                        COORDINATE_CONFIG[key]['percent'] = tuple(value['percent'])
                log(f"外部坐标配置文件 {COORDINATE_SETTINGS_FILE} 加载成功并合并，模式: {current_mode}")
            else:
                log(f"外部配置中模式 {current_mode} 不存在，使用内置默认设置")
    except FileNotFoundError:
        log(f"外部坐标配置文件 {COORDINATE_SETTINGS_FILE} 不存在，使用内置默认设置")
    except Exception as e:
        log(f"加载外部坐标配置时发生错误: {e}，使用内置默认设置")

def save_coordinate_settings():
    """保存坐标配置"""
    try:
        # 获取当前模式，如果mode_var未定义则使用默认值
        try:
            current_mode = mode_var.get() if mode_var else "金蛋"
        except NameError:
            current_mode = "金蛋"
        
        # 读取现有配置文件
        existing_coords = {}
        try:
            with open(COORDINATE_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                existing_coords = json.load(f)
        except FileNotFoundError:
            pass
        
        # 共享坐标配置（满仓和滚仓模式间共享）
        shared_coords = ['fenghuo_region', 'return_button', 'battlefield_switch']
        # 满仓模式列表
        full_warehouse_modes = ['金蛋', '紫蛋', '肉蛋']
        # 配装方案模式列表（滚仓模式下的三个方案）
        loadout_modes = ['配装方案1', '配装方案2', '配装方案3']
        # 所有模式列表（满仓+滚仓）
        all_modes = full_warehouse_modes + loadout_modes
        
        # 保存共享坐标
        if 'shared' not in existing_coords:
            existing_coords['shared'] = {}
        for key in shared_coords:
            if key in COORDINATE_CONFIG:
                existing_coords['shared'][key] = {
                    'name': COORDINATE_CONFIG[key]['name'],
                    'percent': COORDINATE_CONFIG[key]['percent'],
                    'description': COORDINATE_CONFIG[key]['description']
                }
        
        # 保存价格识别区域（满仓和滚仓模式分别独立保存）
        if current_mode in full_warehouse_modes:
            # 满仓模式使用fullstock_price_shared区域
            if 'fullstock_price_shared' not in existing_coords:
                existing_coords['fullstock_price_shared'] = {}
            existing_coords['fullstock_price_shared']['price_area'] = {
                'name': COORDINATE_CONFIG['price_region']['name'],
                'percent': COORDINATE_CONFIG['price_region']['percent'],
                'description': COORDINATE_CONFIG['price_region']['description']
            }
        elif current_mode in loadout_modes:
            # 滚仓模式使用loadout_price_shared区域
            if 'loadout_price_shared' not in existing_coords:
                existing_coords['loadout_price_shared'] = {}
            existing_coords['loadout_price_shared']['price_area'] = {
                'name': COORDINATE_CONFIG['price_region']['name'],
                'percent': COORDINATE_CONFIG['price_region']['percent'],
                'description': COORDINATE_CONFIG['price_region']['description']
            }
        else:
            # 其他模式使用独立的价格识别区域
            if current_mode not in existing_coords:
                existing_coords[current_mode] = {}
            existing_coords[current_mode]['price_area'] = {
                'name': COORDINATE_CONFIG['price_region']['name'],
                'percent': COORDINATE_CONFIG['price_region']['percent'],
                'description': COORDINATE_CONFIG['price_region']['description']
            }
        
        # 保存购买按钮坐标（满仓和滚仓模式间共享）
        if current_mode in all_modes and 'buy_button' in COORDINATE_CONFIG:
            # 为所有满仓和滚仓模式保存相同的购买按钮坐标
            if 'buy_button_shared' not in existing_coords:
                existing_coords['buy_button_shared'] = {}
            existing_coords['buy_button_shared']['buy_button'] = {
                'name': COORDINATE_CONFIG['buy_button']['name'],
                'percent': COORDINATE_CONFIG['buy_button']['percent'],
                'description': COORDINATE_CONFIG['buy_button']['description']
            }
        
        # 保存其他坐标配置
        if current_mode in loadout_modes:
            # 配装方案模式：共享坐标同步到所有配装方案，配装方案坐标只保存到当前方案
            for key, config in COORDINATE_CONFIG.items():
                if key not in shared_coords and key != 'price_region' and key != 'buy_button':
                    # 检查是否为配装方案坐标
                    if key.startswith('loadout_plan_'):
                        # 配装方案坐标只保存到当前方案
                        if current_mode not in existing_coords:
                            existing_coords[current_mode] = {}
                        existing_coords[current_mode][key] = {
                            'name': config['name'],
                            'percent': config['percent'],
                            'description': config['description']
                        }
                    else:
                        # 其他坐标（如判定游戏模式区域等）同步到所有配装方案
                        for mode in loadout_modes:
                            if mode not in existing_coords:
                                existing_coords[mode] = {}
                            existing_coords[mode][key] = {
                                'name': config['name'],
                                'percent': config['percent'],
                                'description': config['description']
                            }
        elif current_mode in full_warehouse_modes:
            # 满仓模式：保存当前模式独立的坐标（除了共享坐标）
            if current_mode not in existing_coords:
                existing_coords[current_mode] = {}
            for key, config in COORDINATE_CONFIG.items():
                if key not in shared_coords and key != 'price_region' and key != 'buy_button':
                    existing_coords[current_mode][key] = {
                        'name': config['name'],
                        'percent': config['percent'],
                        'description': config['description']
                    }
        else:
            # 其他模式：保存当前模式独立的坐标
            if current_mode not in existing_coords:
                existing_coords[current_mode] = {}
            for key, config in COORDINATE_CONFIG.items():
                if key not in shared_coords and key != 'price_region':
                    existing_coords[current_mode][key] = {
                        'name': config['name'],
                        'percent': config['percent'],
                        'description': config['description']
                    }
        
        # 保存到文件
        with open(COORDINATE_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_coords, f, ensure_ascii=False, indent=2)
        log(f"坐标配置已保存到 {COORDINATE_SETTINGS_FILE}，模式: {current_mode}")
        return True
    except Exception as e:
        log(f"保存坐标配置时发生错误: {e}")
        return False

# 屏幕区域框选功能
class RegionSelector:
    def __init__(self, callback):
        self.callback = callback
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.selecting = False
        
    def start_selection(self):
        """开始区域选择"""
        log("请在屏幕上拖拽选择区域...")
        # 创建全屏透明窗口用于选择
        self.selection_window = tk.Toplevel()
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-alpha', 0.3)
        self.selection_window.configure(bg='black')
        self.selection_window.attributes('-topmost', True)
        
        # 绑定鼠标事件
        self.selection_window.bind('<Button-1>', self.on_click)
        self.selection_window.bind('<B1-Motion>', self.on_drag)
        self.selection_window.bind('<ButtonRelease-1>', self.on_release)
        self.selection_window.bind('<Escape>', self.cancel_selection)
        
        # 创建画布
        self.canvas = tk.Canvas(self.selection_window, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 添加提示文字
        screen_width = self.selection_window.winfo_screenwidth()
        screen_height = self.selection_window.winfo_screenheight()
        self.canvas.create_text(screen_width//2, 50, text="拖拽鼠标选择区域，按ESC取消", 
                               fill='white', font=('Arial', 16))
        
        self.selection_window.focus_set()
        
    def on_click(self, event):
        self.start_x = event.x_root
        self.start_y = event.y_root
        self.selecting = True
        
    def on_drag(self, event):
        if self.selecting:
            self.canvas.delete('selection')
            x1, y1 = self.start_x - self.selection_window.winfo_rootx(), self.start_y - self.selection_window.winfo_rooty()
            x2, y2 = event.x, event.y
            self.canvas.create_rectangle(x1, y1, x2, y2, outline='red', width=2, tags='selection')
            
    def on_release(self, event):
        if self.selecting:
            self.end_x = event.x_root
            self.end_y = event.y_root
            self.selecting = False
            
            # 计算选择区域
            x1, y1 = min(self.start_x, self.end_x), min(self.start_y, self.end_y)
            x2, y2 = max(self.start_x, self.end_x), max(self.start_y, self.end_y)
            width, height = x2 - x1, y2 - y1
            
            # 转换为百分比
            screen_width = self.selection_window.winfo_screenwidth()
            screen_height = self.selection_window.winfo_screenheight()
            
            x_percent = x1 / screen_width
            y_percent = y1 / screen_height
            width_percent = width / screen_width
            height_percent = height / screen_height
            
            # 关闭选择窗口
            self.selection_window.destroy()
            
            # 调用回调函数
            self.callback((x_percent, y_percent, width_percent, height_percent))
            
    def cancel_selection(self, event):
        self.selection_window.destroy()
        log("区域选择已取消")

class AppUI:
    def __init__(self, master):
        self.master = master
        global root, status_var, delay_stable_var, delay_buy_var, log_text, click_count_var, max_price_var, mode_var, min_price_var, app_instance
        root = master # 将 master 赋值给全局的 root
        app_instance = self # 设置全局app实例

        master.title("屯仓抢金弹助手")
        
        # 加载保存的窗口大小，如果没有则使用默认值
        load_window_geometry(master)
        master.minsize(650, 700) # 设置最小尺寸
        
        # 绑定窗口关闭事件，保存窗口大小
        def on_closing():
            save_window_geometry(master)
            master.destroy()
        
        master.protocol("WM_DELETE_WINDOW", on_closing)

        # 设置主窗口背景色
        master.configure(bg='#f0f0f0')
        
        # 主框架，分为左右两部分，使用现代化设计
        main_frame = tk.Frame(master, bg='#f0f0f0', padx=4, pady=4)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧框架 - 参数和坐标配置
        left_frame = tk.Frame(main_frame, bg='#f0f0f0')
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))

        # 右侧框架 - 日志和状态
        right_frame = tk.Frame(main_frame, bg='#f0f0f0')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- 左侧：参数设置 --- 
        # 创建参数设置卡片
        params_card = tk.Frame(left_frame, bg='white', relief='solid', bd=1)
        params_card.pack(fill=tk.X, pady=(0, 4))
        
        # 参数设置标题
        params_title_frame = tk.Frame(params_card, bg='#2c3e50', height=24)
        params_title_frame.pack(fill=tk.X)
        params_title_frame.pack_propagate(False)
        
        params_title = tk.Label(params_title_frame, text="⚙️ 参数设置", 
                               bg='#2c3e50', fg='white', font=('微软雅黑', 8, 'bold'))
        params_title.pack(expand=True)
        
        # 参数设置内容区域
        params_content = tk.Frame(params_card, bg='white', padx=6, pady=4)
        params_content.pack(fill=tk.X)
        
        params_labelframe = params_content  # 保持兼容性

        # 模式选择 - 两级分类
        tk.Label(params_labelframe, text="模式类别:", bg='white', font=('微软雅黑', 8)).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.category_var = tk.StringVar(value="满仓") # 默认值
        category_options = ["满仓", "滚仓"] 
        self.category_dropdown = ttk.Combobox(params_labelframe, textvariable=self.category_var, values=category_options, width=16, state="readonly", font=('微软雅黑', 8))
        self.category_dropdown.grid(row=0, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        self.category_dropdown.bind("<<ComboboxSelected>>", self.on_category_change) # 绑定类别切换事件
        
        # 具体模式选择
        tk.Label(params_labelframe, text="具体模式:", bg='white', font=('微软雅黑', 8)).grid(row=1, column=0, sticky=tk.W, pady=2)
        mode_var = tk.StringVar(value="金蛋") # 默认值
        self.mode_options_map = {
            "满仓": ["金蛋", "紫蛋", "肉蛋"],
            "滚仓": ["配装方案1", "配装方案2", "配装方案3"]
        }
        self.mode_dropdown = ttk.Combobox(params_labelframe, textvariable=mode_var, values=self.mode_options_map["满仓"], width=16, state="readonly", font=('微软雅黑', 8))
        self.mode_dropdown.grid(row=1, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        self.mode_dropdown.bind("<<ComboboxSelected>>", self.on_mode_change) # 绑定模式切换事件

        # 满仓模式专用控件
        # 最低价格
        self.min_price_label = tk.Label(params_labelframe, text="最低价格:", bg='white', font=('微软雅黑', 8))
        self.min_price_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        min_price_var = tk.StringVar() # 初始值由 init_config 设置
        self.min_price_entry = ttk.Entry(params_labelframe, textvariable=min_price_var, width=18, font=('微软雅黑', 8))
        self.min_price_entry.grid(row=2, column=1, sticky=tk.EW, pady=2, padx=(8, 0))

        # 最高价格
        self.max_price_label = tk.Label(params_labelframe, text="最高价格:", bg='white', font=('微软雅黑', 8))
        self.max_price_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        max_price_var = tk.StringVar() # 初始值由 init_config 设置
        self.max_price_entry = ttk.Entry(params_labelframe, textvariable=max_price_var, width=18, font=('微软雅黑', 8))
        self.max_price_entry.grid(row=3, column=1, sticky=tk.EW, pady=2, padx=(8, 0))

        # 页面稳定延迟
        self.page_delay_label = tk.Label(params_labelframe, text="页面稳定延迟(ms):", bg='white', font=('微软雅黑', 8))
        self.page_delay_label.grid(row=4, column=0, sticky=tk.W, pady=2)
        delay_stable_var = tk.StringVar() # 初始值由 init_config 设置
        self.page_delay_entry = ttk.Entry(params_labelframe, textvariable=delay_stable_var, width=18, font=('微软雅黑', 8))
        self.page_delay_entry.grid(row=4, column=1, sticky=tk.EW, pady=2, padx=(8, 0))

        # 购买页等待延迟
        self.buy_delay_label = tk.Label(params_labelframe, text="购买页等待延迟(ms):", bg='white', font=('微软雅黑', 8))
        self.buy_delay_label.grid(row=5, column=0, sticky=tk.W, pady=2)
        delay_buy_var = tk.StringVar() # 初始值由 init_config 设置
        self.buy_delay_entry = ttk.Entry(params_labelframe, textvariable=delay_buy_var, width=18, font=('微软雅黑', 8))
        self.buy_delay_entry.grid(row=5, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        
        # 数量拉满开关（满仓模式专用）
        self.quantity_max_label = tk.Label(params_labelframe, text="数量拉满:", bg='white', font=('微软雅黑', 8))
        self.quantity_max_label.grid(row=6, column=0, sticky=tk.W, pady=2)
        self.quantity_max_var = tk.BooleanVar(value=False)  # 默认关闭
        self.quantity_max_check = tk.Checkbutton(params_labelframe, text="启用数量控制按钮点击", variable=self.quantity_max_var, bg='white', font=('微软雅黑', 8))
        self.quantity_max_check.grid(row=6, column=1, sticky=tk.W, pady=2, padx=(8, 0))
        
        # 抢无货开关（满仓模式专用）
        self.grab_out_of_stock_label = tk.Label(params_labelframe, text="抢无货:", bg='white', font=('微软雅黑', 8))
        self.grab_out_of_stock_label.grid(row=7, column=0, sticky=tk.W, pady=2)
        self.grab_no_stock_var = tk.BooleanVar(value=False)  # 默认关闭
        self.grab_out_of_stock_check = tk.Checkbutton(params_labelframe, text="连续识别失败4次后等待5秒重试", variable=self.grab_no_stock_var, bg='white', font=('微软雅黑', 8))
        self.grab_out_of_stock_check.grid(row=7, column=1, sticky=tk.W, pady=2, padx=(8, 0))
        
        # 滚仓模式专用配置
        # 子弹数量
        self.bullet_count_label = tk.Label(params_labelframe, text="子弹数量:", bg='white', font=('微软雅黑', 8))
        self.bullet_count_label.grid(row=8, column=0, sticky=tk.W, pady=2)
        self.bullet_count_var = tk.StringVar() # 初始值由 init_config 设置
        self.bullet_count_entry = ttk.Entry(params_labelframe, textvariable=self.bullet_count_var, width=18, font=('微软雅黑', 8))
        self.bullet_count_entry.grid(row=8, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        
        # 单发最低价格
        self.bullet_min_price_label = tk.Label(params_labelframe, text="单发最低价格:", bg='white', font=('微软雅黑', 8))
        self.bullet_min_price_label.grid(row=9, column=0, sticky=tk.W, pady=2)
        self.bullet_min_price_var = tk.StringVar() # 初始值由 init_config 设置
        self.bullet_min_price_entry = ttk.Entry(params_labelframe, textvariable=self.bullet_min_price_var, width=18, font=('微软雅黑', 8))
        self.bullet_min_price_entry.grid(row=9, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        
        # 单发最高价格
        self.bullet_max_price_label = tk.Label(params_labelframe, text="单发最高价格:", bg='white', font=('微软雅黑', 8))
        self.bullet_max_price_label.grid(row=10, column=0, sticky=tk.W, pady=2)
        self.bullet_max_price_var = tk.StringVar() # 初始值由 init_config 设置
        self.bullet_max_price_entry = ttk.Entry(params_labelframe, textvariable=self.bullet_max_price_var, width=18, font=('微软雅黑', 8))
        self.bullet_max_price_entry.grid(row=10, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        
        # 刷新延迟
        self.refresh_delay_label = tk.Label(params_labelframe, text="刷新延迟(ms):", bg='white', font=('微软雅黑', 8))
        self.refresh_delay_label.grid(row=11, column=0, sticky=tk.W, pady=2)
        self.refresh_delay_var = tk.StringVar() # 初始值由 init_config 设置
        self.refresh_delay_entry = ttk.Entry(params_labelframe, textvariable=self.refresh_delay_var, width=18, font=('微软雅黑', 8))
        self.refresh_delay_entry.grid(row=11, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        
        # 截图延迟
        self.screenshot_delay_label = tk.Label(params_labelframe, text="截图延迟(ms):", bg='white', font=('微软雅黑', 8))
        self.screenshot_delay_label.grid(row=12, column=0, sticky=tk.W, pady=2)
        self.screenshot_delay_var = tk.StringVar() # 初始值由 init_config 设置
        self.screenshot_delay_entry = ttk.Entry(params_labelframe, textvariable=self.screenshot_delay_var, width=18, font=('微软雅黑', 8))
        self.screenshot_delay_entry.grid(row=12, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        
        # 调试模式开关
        self.debug_mode_label = tk.Label(params_labelframe, text="调试模式:", bg='white', font=('微软雅黑', 8))
        self.debug_mode_label.grid(row=13, column=0, sticky=tk.W, pady=2)
        self.debug_mode_var = tk.BooleanVar(value=False)
        self.debug_mode_check = tk.Checkbutton(params_labelframe, text="启用（禁用购买操作）", variable=self.debug_mode_var, bg='white', font=('微软雅黑', 8))
        self.debug_mode_check.grid(row=13, column=1, sticky=tk.W, pady=2, padx=(8, 0))
        
        # 返回大战场刷新次数阈值（通用设置）
        self.return_threshold_label = tk.Label(params_labelframe, text="返回大战场阈值:", bg='white', font=('微软雅黑', 8))
        self.return_threshold_label.grid(row=14, column=0, sticky=tk.W, pady=2)
        self.return_threshold_var = tk.StringVar() # 初始值由 init_config 设置
        self.return_threshold_entry = ttk.Entry(params_labelframe, textvariable=self.return_threshold_var, width=18, font=('微软雅黑', 8))
        self.return_threshold_entry.grid(row=14, column=1, sticky=tk.EW, pady=2, padx=(8, 0))
        
        # 保存满仓模式专用控件以便控制显示/隐藏
        self.fullstock_specific_widgets = [
            self.min_price_label, self.min_price_entry,
            self.max_price_label, self.max_price_entry,
            self.page_delay_label, self.page_delay_entry,
            self.buy_delay_label, self.buy_delay_entry,
            self.quantity_max_label, self.quantity_max_check,
            self.grab_out_of_stock_label, self.grab_out_of_stock_check
        ]
        
        # 保存滚仓模式专用控件以便控制显示/隐藏
        self.loadout_specific_widgets = [
            self.bullet_count_label, self.bullet_count_entry,
            self.bullet_min_price_label, self.bullet_min_price_entry,
            self.bullet_max_price_label, self.bullet_max_price_entry,
            self.refresh_delay_label, self.refresh_delay_entry,
            self.screenshot_delay_label, self.screenshot_delay_entry,
            self.debug_mode_label, self.debug_mode_check
        ]
        
        # 保存通用控件（所有模式都显示）
        self.common_widgets = [
            self.return_threshold_label, self.return_threshold_entry
        ]
        
        params_labelframe.grid_columnconfigure(1, weight=1) # 让输入框可伸缩
        
        # --- 坐标配置区域 ---
        # 创建坐标配置卡片
        coords_card = tk.Frame(left_frame, bg='white', relief='solid', bd=1)
        coords_card.pack(fill=tk.X, pady=(0, 8))
        
        # 坐标配置标题
        coords_title_frame = tk.Frame(coords_card, bg='#27ae60', height=24)
        coords_title_frame.pack(fill=tk.X)
        coords_title_frame.pack_propagate(False)
        
        coords_title = tk.Label(coords_title_frame, text="🎯 坐标配置", 
                               bg='#27ae60', fg='white', font=('微软雅黑', 8, 'bold'))
        coords_title.pack(expand=True)
        
        # 坐标配置内容区域
        coords_content = tk.Frame(coords_card, bg='white', padx=6, pady=4)
        coords_content.pack(fill=tk.X)
        
        coords_labelframe = coords_content  # 保持兼容性
        
        # 调试截图开关和说明
        debug_frame = tk.Frame(coords_labelframe, bg='white')
        debug_frame.grid(row=0, column=0, columnspan=5, sticky=tk.EW, pady=(0,6))
        
        self.debug_screenshot_var = tk.BooleanVar(value=True)  # 默认开启调试截图
        debug_check = tk.Checkbutton(debug_frame, text="启用调试截图", variable=self.debug_screenshot_var, 
                                   command=self.update_debug_screenshot, bg='white', font=('微软雅黑', 8))
        debug_check.pack(side=tk.LEFT)
        
        tip_label = tk.Label(debug_frame, text="💡 点击'框选'选择区域，或手动输入坐标", 
                           font=('微软雅黑', 7), foreground='#7f8c8d', bg='white')
        tip_label.pack(side=tk.RIGHT)
        
        # 分隔线
        separator = tk.Frame(coords_labelframe, height=1, bg='#ecf0f1')
        separator.grid(row=1, column=0, columnspan=5, sticky=tk.EW, pady=(0,6))
        
        # 表头
        tk.Label(coords_labelframe, text="坐标项目", font=('微软雅黑', 8, 'bold'), bg='white', fg='#2c3e50').grid(row=2, column=0, sticky=tk.W, pady=3)
        tk.Label(coords_labelframe, text="当前坐标", font=('微软雅黑', 8, 'bold'), bg='white', fg='#2c3e50').grid(row=2, column=1, sticky=tk.W, pady=3)
        tk.Label(coords_labelframe, text="操作", font=('微软雅黑', 8, 'bold'), bg='white', fg='#2c3e50').grid(row=2, column=2, sticky=tk.W, pady=3)
        tk.Label(coords_labelframe, text="手动输入", font=('微软雅黑', 8, 'bold'), bg='white', fg='#2c3e50').grid(row=2, column=3, sticky=tk.W, pady=3)
        
        # 判定游戏模式区域
        tk.Label(coords_labelframe, text="判定游戏模式区域:", bg='white', font=('微软雅黑', 8)).grid(row=3, column=0, sticky=tk.W, pady=4)
        self.fenghuo_coord_var = tk.StringVar()
        self.fenghuo_coord_label = tk.Label(coords_labelframe, textvariable=self.fenghuo_coord_var, 
                                           font=('Consolas', 7), foreground='#3498db', bg='white')
        self.fenghuo_coord_label.grid(row=3, column=1, sticky=tk.W, pady=4, padx=3)
        select_btn1 = tk.Button(coords_labelframe, text="📍 框选", width=7, bg='#3498db', fg='white', 
                               font=('微软雅黑', 7), relief='flat', cursor='hand2',
                               command=lambda: self.select_region('fenghuo_region'))
        select_btn1.grid(row=3, column=2, pady=4, padx=2)
        self.fenghuo_entry = tk.Entry(coords_labelframe, width=14, font=('Consolas', 7), relief='solid', bd=1)
        self.fenghuo_entry.grid(row=3, column=3, pady=4, padx=3)
        set_btn1 = tk.Button(coords_labelframe, text="✓", width=2, bg='#27ae60', fg='white', 
                            font=('微软雅黑', 7), relief='flat', cursor='hand2',
                            command=lambda: self.set_manual_coords('fenghuo_region', self.fenghuo_entry.get()))
        set_btn1.grid(row=3, column=4, pady=4, padx=2)
        
        # 价格区域
        tk.Label(coords_labelframe, text="价格区域:", bg='white', font=('微软雅黑', 8)).grid(row=4, column=0, sticky=tk.W, pady=4)
        self.price_coord_var = tk.StringVar()
        self.price_coord_label = tk.Label(coords_labelframe, textvariable=self.price_coord_var, 
                                         font=('Consolas', 7), foreground='#3498db', bg='white')
        self.price_coord_label.grid(row=4, column=1, sticky=tk.W, pady=4, padx=3)
        select_btn2 = tk.Button(coords_labelframe, text="📍 框选", width=7, bg='#3498db', fg='white', 
                               font=('微软雅黑', 7), relief='flat', cursor='hand2',
                               command=lambda: self.select_region('price_region'))
        select_btn2.grid(row=4, column=2, pady=4, padx=2)
        self.price_entry = tk.Entry(coords_labelframe, width=14, font=('Consolas', 7), relief='solid', bd=1)
        self.price_entry.grid(row=4, column=3, pady=4, padx=3)
        set_btn2 = tk.Button(coords_labelframe, text="✓", width=2, bg='#27ae60', fg='white', 
                            font=('微软雅黑', 7), relief='flat', cursor='hand2',
                            command=lambda: self.set_manual_coords('price_region', self.price_entry.get()))
        set_btn2.grid(row=4, column=4, pady=4, padx=2)
        
        # 返回按钮位置
        tk.Label(coords_labelframe, text="返回按钮位置:", bg='white', font=('微软雅黑', 8)).grid(row=5, column=0, sticky=tk.W, pady=4)
        self.return_coord_var = tk.StringVar()
        self.return_coord_label = tk.Label(coords_labelframe, textvariable=self.return_coord_var, 
                                          font=('Consolas', 8), foreground='#3498db', bg='white')
        self.return_coord_label.grid(row=5, column=1, sticky=tk.W, pady=6, padx=5)
        select_btn3 = tk.Button(coords_labelframe, text="📍 框选", width=8, bg='#3498db', fg='white', 
                               font=('微软雅黑', 8), relief='flat', cursor='hand2',
                               command=lambda: self.select_region('return_button'))
        select_btn3.grid(row=5, column=2, pady=6, padx=2)
        self.return_entry = tk.Entry(coords_labelframe, width=16, font=('Consolas', 8), relief='solid', bd=1)
        self.return_entry.grid(row=5, column=3, pady=6, padx=5)
        set_btn3 = tk.Button(coords_labelframe, text="✓", width=3, bg='#27ae60', fg='white', 
                            font=('微软雅黑', 8), relief='flat', cursor='hand2',
                            command=lambda: self.set_manual_coords('return_button', self.return_entry.get()))
        set_btn3.grid(row=5, column=4, pady=6, padx=2)
        
        # 购买按钮位置
        buy_label = tk.Label(coords_labelframe, text="购买按钮位置:", bg='white', font=('微软雅黑', 9))
        buy_label.grid(row=6, column=0, sticky=tk.W, pady=6)
        self.buy_coord_var = tk.StringVar()
        self.buy_coord_label = tk.Label(coords_labelframe, textvariable=self.buy_coord_var, 
                                       font=('Consolas', 8), foreground='#3498db', bg='white')
        self.buy_coord_label.grid(row=6, column=1, sticky=tk.W, pady=6, padx=5)
        select_btn4 = tk.Button(coords_labelframe, text="📍 框选", width=8, bg='#3498db', fg='white', 
                               font=('微软雅黑', 8), relief='flat', cursor='hand2',
                               command=lambda: self.select_region('buy_button'))
        select_btn4.grid(row=6, column=2, pady=6, padx=2)
        self.buy_entry = tk.Entry(coords_labelframe, width=16, font=('Consolas', 8), relief='solid', bd=1)
        self.buy_entry.grid(row=6, column=3, pady=6, padx=5)
        set_btn4 = tk.Button(coords_labelframe, text="✓", width=3, bg='#27ae60', fg='white', 
                            font=('微软雅黑', 8), relief='flat', cursor='hand2',
                            command=lambda: self.set_manual_coords('buy_button', self.buy_entry.get()))
        set_btn4.grid(row=6, column=4, pady=6, padx=2)
        
        # 保存购买按钮相关控件以便控制显示/隐藏
        self.buy_button_widgets = [buy_label, self.buy_coord_label, select_btn4, self.buy_entry, set_btn4]
        
        # 切换大战场位置
        tk.Label(coords_labelframe, text="切换大战场位置:", bg='white', font=('微软雅黑', 9)).grid(row=7, column=0, sticky=tk.W, pady=6)
        self.battlefield_coord_var = tk.StringVar()
        self.battlefield_coord_label = tk.Label(coords_labelframe, textvariable=self.battlefield_coord_var, 
                                               font=('Consolas', 8), foreground='#3498db', bg='white')
        self.battlefield_coord_label.grid(row=7, column=1, sticky=tk.W, pady=6, padx=5)
        select_btn5 = tk.Button(coords_labelframe, text="📍 框选", width=8, bg='#3498db', fg='white', 
                               font=('微软雅黑', 8), relief='flat', cursor='hand2',
                               command=lambda: self.select_region('battlefield_switch'))
        select_btn5.grid(row=7, column=2, pady=6, padx=2)
        self.battlefield_entry = tk.Entry(coords_labelframe, width=16, font=('Consolas', 8), relief='solid', bd=1)
        self.battlefield_entry.grid(row=7, column=3, pady=6, padx=5)
        set_btn5 = tk.Button(coords_labelframe, text="✓", width=3, bg='#27ae60', fg='white', 
                            font=('微软雅黑', 8), relief='flat', cursor='hand2',
                            command=lambda: self.set_manual_coords('battlefield_switch', self.battlefield_entry.get()))
        set_btn5.grid(row=7, column=4, pady=6, padx=2)
        
        # 配装方案坐标（只在配装方案模式下显示）
        # 配装方案1坐标
        self.loadout1_label = tk.Label(coords_labelframe, text="配装方案1坐标:", bg='white', font=('微软雅黑', 9))
        self.loadout1_label.grid(row=8, column=0, sticky=tk.W, pady=6)
        self.loadout1_coord_var = tk.StringVar()
        self.loadout1_coord_label = tk.Label(coords_labelframe, textvariable=self.loadout1_coord_var, 
                                            font=('Consolas', 8), foreground='#3498db', bg='white')
        self.loadout1_coord_label.grid(row=8, column=1, sticky=tk.W, pady=6, padx=5)
        self.loadout1_select_btn = tk.Button(coords_labelframe, text="📍 框选", width=8, bg='#3498db', fg='white', 
                                           font=('微软雅黑', 8), relief='flat', cursor='hand2',
                                           command=lambda: self.select_region('loadout_plan_1'))
        self.loadout1_select_btn.grid(row=8, column=2, pady=6, padx=2)
        self.loadout1_entry = tk.Entry(coords_labelframe, width=16, font=('Consolas', 8), relief='solid', bd=1)
        self.loadout1_entry.grid(row=8, column=3, pady=6, padx=5)
        self.loadout1_set_btn = tk.Button(coords_labelframe, text="✓", width=3, bg='#27ae60', fg='white', 
                                        font=('微软雅黑', 8), relief='flat', cursor='hand2',
                                        command=lambda: self.set_manual_coords('loadout_plan_1', self.loadout1_entry.get()))
        self.loadout1_set_btn.grid(row=8, column=4, pady=6, padx=2)
        
        # 配装方案2坐标
        self.loadout2_label = tk.Label(coords_labelframe, text="配装方案2坐标:", bg='white', font=('微软雅黑', 9))
        self.loadout2_label.grid(row=9, column=0, sticky=tk.W, pady=6)
        self.loadout2_coord_var = tk.StringVar()
        self.loadout2_coord_label = tk.Label(coords_labelframe, textvariable=self.loadout2_coord_var, 
                                            font=('Consolas', 8), foreground='#3498db', bg='white')
        self.loadout2_coord_label.grid(row=9, column=1, sticky=tk.W, pady=6, padx=5)
        self.loadout2_select_btn = tk.Button(coords_labelframe, text="📍 框选", width=8, bg='#3498db', fg='white', 
                                           font=('微软雅黑', 8), relief='flat', cursor='hand2',
                                           command=lambda: self.select_region('loadout_plan_2'))
        self.loadout2_select_btn.grid(row=9, column=2, pady=6, padx=2)
        self.loadout2_entry = tk.Entry(coords_labelframe, width=16, font=('Consolas', 8), relief='solid', bd=1)
        self.loadout2_entry.grid(row=9, column=3, pady=6, padx=5)
        self.loadout2_set_btn = tk.Button(coords_labelframe, text="✓", width=3, bg='#27ae60', fg='white', 
                                        font=('微软雅黑', 8), relief='flat', cursor='hand2',
                                        command=lambda: self.set_manual_coords('loadout_plan_2', self.loadout2_entry.get()))
        self.loadout2_set_btn.grid(row=9, column=4, pady=6, padx=2)
        
        # 配装方案3坐标
        self.loadout3_label = tk.Label(coords_labelframe, text="配装方案3坐标:", bg='white', font=('微软雅黑', 9))
        self.loadout3_label.grid(row=10, column=0, sticky=tk.W, pady=6)
        self.loadout3_coord_var = tk.StringVar()
        self.loadout3_coord_label = tk.Label(coords_labelframe, textvariable=self.loadout3_coord_var, 
                                            font=('Consolas', 8), foreground='#3498db', bg='white')
        self.loadout3_coord_label.grid(row=10, column=1, sticky=tk.W, pady=6, padx=5)
        self.loadout3_select_btn = tk.Button(coords_labelframe, text="📍 框选", width=8, bg='#3498db', fg='white', 
                                           font=('微软雅黑', 8), relief='flat', cursor='hand2',
                                           command=lambda: self.select_region('loadout_plan_3'))
        self.loadout3_select_btn.grid(row=10, column=2, pady=6, padx=2)
        self.loadout3_entry = tk.Entry(coords_labelframe, width=16, font=('Consolas', 8), relief='solid', bd=1)
        self.loadout3_entry.grid(row=10, column=3, pady=6, padx=5)
        self.loadout3_set_btn = tk.Button(coords_labelframe, text="✓", width=3, bg='#27ae60', fg='white', 
                                        font=('微软雅黑', 8), relief='flat', cursor='hand2',
                                        command=lambda: self.set_manual_coords('loadout_plan_3', self.loadout3_entry.get()))
        self.loadout3_set_btn.grid(row=10, column=4, pady=6, padx=2)
        
        # 存储配装方案控件引用，用于显示/隐藏
        self.loadout_coord_widgets = [
            [self.loadout1_label, self.loadout1_coord_label, self.loadout1_select_btn, self.loadout1_entry, self.loadout1_set_btn],
            [self.loadout2_label, self.loadout2_coord_label, self.loadout2_select_btn, self.loadout2_entry, self.loadout2_set_btn],
            [self.loadout3_label, self.loadout3_coord_label, self.loadout3_select_btn, self.loadout3_entry, self.loadout3_set_btn]
        ]
        
        # 存储配装方案控件的引用，用于显示/隐藏
        self.loadout_widgets = [
            self.loadout1_label, self.loadout1_coord_label, self.loadout1_select_btn, self.loadout1_entry, self.loadout1_set_btn,
            self.loadout2_label, self.loadout2_coord_label, self.loadout2_select_btn, self.loadout2_entry, self.loadout2_set_btn,
            self.loadout3_label, self.loadout3_coord_label, self.loadout3_select_btn, self.loadout3_entry, self.loadout3_set_btn
        ]
        
        coords_labelframe.grid_columnconfigure(1, weight=1)

        # --- 右侧 --- 
        # 状态显示卡片
        status_card = tk.Frame(right_frame, bg='white', relief='solid', bd=1)
        status_card.pack(fill=tk.X, pady=(15, 10))
        
        # 状态显示标题
        status_title_frame = tk.Frame(status_card, bg='#e74c3c', height=28)
        status_title_frame.pack(fill=tk.X)
        status_title_frame.pack_propagate(False)
        
        status_title_label = tk.Label(status_title_frame, text="📊 运行状态", bg='#e74c3c', fg='white', 
                                     font=('微软雅黑', 8, 'bold'))
        status_title_label.pack(side=tk.LEFT, padx=10, pady=6)
        
        # 状态显示内容
        status_content = tk.Frame(status_card, bg='white', padx=10, pady=8)
        status_content.pack(fill=tk.X)
        
        status_var = tk.StringVar(value="状态: 未运行")
        status_label = tk.Label(status_content, textvariable=status_var, font=("微软雅黑", 8), 
                               bg='white', fg='#2c3e50')
        status_label.pack(side=tk.RIGHT)
        
        # 调试截图显示卡片
        debug_img_card = tk.Frame(right_frame, bg='white', relief='solid', bd=1, height=200)
        debug_img_card.pack(fill=tk.X, pady=(0, 10))
        debug_img_card.pack_propagate(False)  # 防止内容撑大容器
        
        # 调试截图标题
        debug_img_title_frame = tk.Frame(debug_img_card, bg='#16a085', height=28)
        debug_img_title_frame.pack(fill=tk.X)
        debug_img_title_frame.pack_propagate(False)
        
        debug_img_title_label = tk.Label(debug_img_title_frame, text="🖼️ 调试截图", bg='#16a085', fg='white', 
                                         font=('微软雅黑', 8, 'bold'))
        debug_img_title_label.pack(side=tk.LEFT, padx=10, pady=6)
        
        # 清除截图按钮
        clear_img_btn = tk.Button(debug_img_title_frame, text="🗑️ 清除", bg='#e74c3c', fg='white',
                                 font=('微软雅黑', 7), relief='flat', cursor='hand2',
                                 command=self.clear_debug_images)
        clear_img_btn.pack(side=tk.RIGHT, padx=10, pady=4)
        
        # 调试截图内容区域（左右并排显示）
        debug_img_content = tk.Frame(debug_img_card, bg='white')
        debug_img_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建左右两个框架用于并排显示截图
        self.debug_img_frame = tk.Frame(debug_img_content, bg='white')
        self.debug_img_frame.pack(fill=tk.BOTH, expand=True)
        
        # 存储截图标签的列表（最多2个）
        self.debug_img_labels = []
        
        # 运行日志卡片
        log_card = tk.Frame(right_frame, bg='white', relief='solid', bd=1)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # 运行日志标题
        log_title_frame = tk.Frame(log_card, bg='#9b59b6', height=28)
        log_title_frame.pack(fill=tk.X)
        log_title_frame.pack_propagate(False)
        
        log_title_label = tk.Label(log_title_frame, text="📝 运行日志", bg='#9b59b6', fg='white', 
                                  font=('微软雅黑', 8, 'bold'))
        log_title_label.pack(side=tk.LEFT, padx=10, pady=6)
        
        # 运行日志内容区域
        log_content = tk.Frame(log_card, bg='white', padx=10, pady=10)
        log_content.pack(fill=tk.BOTH, expand=True)
        
        # 保持兼容性
        log_labelframe = log_content

        global log_text
        log_text = scrolledtext.ScrolledText(log_labelframe, wrap=tk.WORD, height=10, width=40, font=('微软雅黑', 10))
        log_text.pack(fill=tk.BOTH, expand=True)
        log_text.configure(state='disabled') # 默认不可编辑
        
        # 启动日志显示更新
        update_log_display()

        # --- 底部框架 --- 
        bottom_frame = tk.Frame(master, bg='#ecf0f1', padx=20, pady=15)
        bottom_frame.pack(fill=tk.X)

        # 按钮框架
        button_frame = tk.Frame(bottom_frame, bg='#ecf0f1')
        button_frame.pack(fill=tk.X, pady=(0,10))

        # 第一行按钮：运行控制
        control_frame = tk.Frame(button_frame, bg='#ecf0f1')
        control_frame.pack(fill=tk.X, pady=(0,10))
        
        start_btn = tk.Button(control_frame, text="▶️ 开始运行", command=start_loop, width=12, 
                              bg='#27ae60', fg='white', font=('微软雅黑', 8, 'bold'), 
                              relief='flat', cursor='hand2', pady=6)
        start_btn.pack(side=tk.LEFT, padx=(0,4))
        
        pause_btn = tk.Button(control_frame, text="⏸️ 暂停/继续", command=pause_loop, width=12, 
                             bg='#f39c12', fg='white', font=('微软雅黑', 8, 'bold'), 
                             relief='flat', cursor='hand2', pady=6)
        pause_btn.pack(side=tk.LEFT, padx=2)
        
        stop_btn = tk.Button(control_frame, text="⏹️ 停止运行", command=stop_loop, width=12, 
                            bg='#e74c3c', fg='white', font=('微软雅黑', 8, 'bold'), 
                            relief='flat', cursor='hand2', pady=6)
        stop_btn.pack(side=tk.LEFT, padx=(4,0))
        
        # 第二行按钮：设置保存
        save_frame = tk.Frame(button_frame, bg='#ecf0f1')
        save_frame.pack(fill=tk.X)
        
        save_btn = tk.Button(save_frame, text="💾 保存所有设置", command=self.save_all_settings, width=16, 
                            bg='#3498db', fg='white', font=('微软雅黑', 8, 'bold'), 
                            relief='flat', cursor='hand2', pady=6)
        save_btn.pack(side=tk.LEFT, padx=(0,4))
        
        reset_btn = tk.Button(save_frame, text="🔄 重置坐标", command=self.reset_coordinates, width=12, 
                             bg='#95a5a6', fg='white', font=('微软雅黑', 8, 'bold'), 
                             relief='flat', cursor='hand2', pady=6)
        reset_btn.pack(side=tk.LEFT, padx=2)
        
        # 测试按钮：直接识别原始截图
        test_btn = tk.Button(save_frame, text="🔍 测试原始识别", command=self.test_raw_ocr, width=14, 
                            bg='#9b59b6', fg='white', font=('微软雅黑', 8, 'bold'), 
                            relief='flat', cursor='hand2', pady=6)
        test_btn.pack(side=tk.LEFT, padx=(4,0))
        
        # 信息显示区域
        info_frame = tk.Frame(bottom_frame, bg='#ecf0f1')
        info_frame.pack(fill=tk.X, pady=(6,0))
        
        # 点击次数显示
        self.click_count_var = tk.StringVar(value="本次运行共点击购买按钮 0 次")
        click_count_label = tk.Label(info_frame, textvariable=self.click_count_var, 
                                   bg='#ecf0f1', fg='#2c3e50', font=('微软雅黑', 8))
        click_count_label.pack(fill=tk.X, pady=(0,3))
        global click_count_var
        click_count_var = self.click_count_var
        
        # 滚仓信息显示
        self.loadout_info_var = tk.StringVar(value="滚仓模式：第0次刷新 | 购买金额：0 | 单价：0")
        loadout_info_label = tk.Label(info_frame, textvariable=self.loadout_info_var, 
                                     bg='#ecf0f1', fg='#8e44ad', font=('微软雅黑', 8))
        loadout_info_label.pack(fill=tk.X, pady=(0,3))
        global loadout_info_var
        loadout_info_var = self.loadout_info_var
        
        # 设置全局变量
        global return_battlefield_threshold_var
        return_battlefield_threshold_var = self.return_threshold_var

        # 热键提示
        hotkey_label = tk.Label(info_frame, text="⌨️ 快捷键: F8:开始 | F9:暂停/继续 | F10:停止", 
                              bg='#ecf0f1', fg='#7f8c8d', font=('微软雅黑', 7))
        hotkey_label.pack(fill=tk.X, pady=(0,3))

        # 版权信息
        copyright_label = tk.Label(info_frame, text="© 2025 P1nKM41D 版权所有 | 软件版本:v1.0.1", 
                                 bg='#ecf0f1', fg='#95a5a6', font=("微软雅黑", 7))
        copyright_label.pack(fill=tk.X)

        # 启动日志更新
        update_log_display()
        
        # 初始化坐标显示
        self.update_coordinate_display()
        # 初始化配装方案坐标控件的显示状态
        self.toggle_loadout_coordinates_visibility()
        
    def update_coordinate_display(self):
        """更新坐标显示"""
        for key, config in COORDINATE_CONFIG.items():
            coord_text = f"({config['percent'][0]:.2%}, {config['percent'][1]:.2%}"
            if len(config['percent']) > 2:
                coord_text += f", {config['percent'][2]:.2%}, {config['percent'][3]:.2%})"
            else:
                coord_text += ")"
                
            if key == 'fenghuo_region':
                self.fenghuo_coord_var.set(coord_text)
            elif key == 'price_region':
                self.price_coord_var.set(coord_text)
            elif key == 'return_button':
                self.return_coord_var.set(coord_text)
            elif key == 'buy_button':
                self.buy_coord_var.set(coord_text)
            elif key == 'battlefield_switch':
                self.battlefield_coord_var.set(coord_text)
            elif key == 'loadout_plan_1':
                self.loadout1_coord_var.set(coord_text)
            elif key == 'loadout_plan_2':
                self.loadout2_coord_var.set(coord_text)
            elif key == 'loadout_plan_3':
                self.loadout3_coord_var.set(coord_text)
                
    def select_region(self, region_key):
        """选择屏幕区域"""
        def on_region_selected(coords):
            COORDINATE_CONFIG[region_key]['percent'] = coords
            self.update_coordinate_display()
            log(f"{COORDINATE_CONFIG[region_key]['name']} 坐标已更新")
            
        selector = RegionSelector(on_region_selected)
        selector.start_selection()
        
    def start_generic_region_selection(self):
        """通用框选区域功能，将坐标复制到剪贴板"""
        def on_region_selected(coords):
            # 格式化坐标信息为可直接粘贴的格式
            x_percent, y_percent, width_percent, height_percent = coords
            # 使用逗号分隔的格式，可以直接粘贴到输入框
            coord_text = f"{x_percent:.4f},{y_percent:.4f},{width_percent:.4f},{height_percent:.4f}"
            
            # 复制到剪贴板
            pyperclip.copy(coord_text)
            log(f"框选完成，坐标已复制到剪贴板: {coord_text}")
            log(f"可直接粘贴到坐标输入框使用")
            
        selector = RegionSelector(on_region_selected)
        selector.start_selection()
        
    def save_coordinates(self):
        """保存坐标配置"""
        if save_coordinate_settings():
            log("坐标配置已保存")
        else:
            log("保存坐标配置失败")
    
    def save_all_settings(self):
        """保存所有设置（配置、坐标和窗口大小）"""
        try:
            # 保存配置文件
            save_config_from_ui()
            # 保存坐标配置
            # 保存窗口大小
            save_window_geometry(self.master)
            if save_coordinate_settings():
                log("所有设置已保存成功")
            else:
                log("坐标配置保存失败")
        except Exception as e:
            log(f"保存设置时发生错误: {e}")
    
    def clear_debug_images(self):
        """清除所有调试截图"""
        try:
            # 清除UI中的截图显示
            for label in self.debug_img_labels:
                label.destroy()
            self.debug_img_labels.clear()
            log("已清除所有调试截图显示")
        except Exception as e:
            log(f"清除调试截图失败: {str(e)}")
    
    def add_debug_image(self, image_path, description=""):
        """在UI中添加调试截图显示（左右并排显示最新的两张截图）"""
        try:
            if not os.path.exists(image_path):
                return
            
            # 限制显示的截图数量为2张
            max_images = 2
            if len(self.debug_img_labels) >= max_images:
                # 移除最旧的截图
                oldest_label = self.debug_img_labels.pop(0)
                oldest_label.destroy()
            
            # 加载并调整图片大小
            img = Image.open(image_path)
            # 计算缩放比例，保持宽高比（调整为适合左右并排显示）
            max_width, max_height = 150, 120
            img_width, img_height = img.size
            scale = min(max_width/img_width, max_height/img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # 转换为tkinter可用的格式
            photo = ImageTk.PhotoImage(img)
            
            # 创建显示框架（左右并排布局）
            img_container = tk.Frame(self.debug_img_frame, bg='white', relief='solid', bd=1)
            
            # 根据当前截图数量决定布局位置
            if len(self.debug_img_labels) == 0:
                # 第一张截图放在左边
                img_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2), pady=2)
            else:
                # 第二张截图放在右边
                img_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(2, 0), pady=2)
            
            # 添加描述标签
            if description:
                desc_label = tk.Label(img_container, text=description, bg='white', 
                                     font=('微软雅黑', 7), fg='#666')
                desc_label.pack(pady=2)
            
            # 添加图片标签
            img_label = tk.Label(img_container, image=photo, bg='white')
            img_label.image = photo  # 保持引用避免被垃圾回收
            img_label.pack(pady=2)
            
            # 添加时间戳
            timestamp = datetime.now().strftime("%H:%M:%S")
            time_label = tk.Label(img_container, text=f"时间: {timestamp}", bg='white',
                                 font=('微软雅黑', 6), fg='#999')
            time_label.pack(pady=1)
            
            # 保存到列表中
            self.debug_img_labels.append(img_container)
            
        except Exception as e:
            log(f"添加调试截图显示失败: {str(e)}")
    
    def reset_coordinates(self):
        """重置所有坐标为默认值"""
        result = messagebox.askyesno("确认重置", "确定要重置所有坐标为默认值吗？\n此操作不可撤销！")
        if result:
            try:
                # 重置COORDINATE_CONFIG中的坐标
                for key in COORDINATE_CONFIG:
                    if key != 'fenghuo_region':  # 保留判定游戏模式区域的坐标
                        COORDINATE_CONFIG[key]['percent'] = (0.0, 0.0, 0.0, 0.0)
                
                # 更新显示
                self.update_coordinate_display()
                log("坐标已重置为默认值")
                messagebox.showinfo("成功", "坐标已重置为默认值！")
            except Exception as e:
                log(f"重置坐标时发生错误: {e}")
                messagebox.showerror("错误", f"重置坐标时发生错误: {e}")
    
    def set_manual_coords(self, region_key, coord_text):
        """手动设置坐标"""
        try:
            # 解析坐标文本，支持多种格式
            coord_text = coord_text.strip()
            if not coord_text:
                messagebox.showerror("错误", "请输入坐标数据")
                return
            
            # 尝试解析不同格式的坐标
            coords = None
            
            # 格式1: (x, y, width, height)
            if coord_text.startswith('(') and coord_text.endswith(')'):
                coord_text = coord_text[1:-1]  # 去掉括号
                parts = [float(x.strip()) for x in coord_text.split(',')]
                if len(parts) == 4:
                    coords = tuple(parts)
            
            # 格式2: x,y,width,height
            elif ',' in coord_text:
                parts = [float(x.strip()) for x in coord_text.split(',')]
                if len(parts) == 4:
                    coords = tuple(parts)
            
            # 格式3: x y width height (空格分隔)
            elif ' ' in coord_text:
                parts = [float(x.strip()) for x in coord_text.split()]
                if len(parts) == 4:
                    coords = tuple(parts)
            
            if coords is None:
                messagebox.showerror("错误", "坐标格式不正确\n支持格式:\n1. (x,y,width,height)\n2. x,y,width,height\n3. x y width height")
                return
            
            # 验证坐标范围
            x, y, width, height = coords
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 <= width <= 1 and 0 <= height <= 1):
                messagebox.showerror("错误", "坐标值必须在0-1之间（百分比格式）")
                return
            
            if x + width > 1 or y + height > 1:
                messagebox.showerror("错误", "坐标区域超出屏幕范围")
                return
            
            # 更新坐标配置
            COORDINATE_CONFIG[region_key]['percent'] = coords
            
            # 更新显示
            self.update_coordinate_display()
            
            # 保存配置
            save_coordinate_settings()
            
            log(f"{COORDINATE_CONFIG[region_key]['name']} 坐标已手动设置为: {coords}")
            
        except ValueError:
            messagebox.showerror("错误", "坐标格式不正确，请输入数字")
        except Exception as e:
            messagebox.showerror("错误", f"设置坐标时发生错误: {e}")

    def update_debug_screenshot(self):
        """更新调试截图全局变量"""
        global debug_screenshot_enabled
        debug_screenshot_enabled = self.debug_screenshot_var.get()
        log(f"调试截图已{'启用' if debug_screenshot_enabled else '禁用'}")
    
    def test_raw_ocr(self):
        """测试功能：直接识别原始截图数字，不进行预处理"""
        try:
            # 获取价格区域坐标
            price_region = COORDINATE_CONFIG.get('price_region', {}).get('percent', (0, 0, 0, 0))
            if price_region == (0, 0, 0, 0):
                messagebox.showwarning("警告", "请先设置价格区域坐标")
                return
            
            # 截取价格区域
            x, y, width, height = price_region
            left = int(x * SCREEN_WIDTH)
            top = int(y * SCREEN_HEIGHT)
            right = int((x + width) * SCREEN_WIDTH)
            bottom = int((y + height) * SCREEN_HEIGHT)
            
            screenshot = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
            
            # 保存原始截图用于调试
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_filename = f"test_raw_ocr_{timestamp}.png"
            screenshot.save(debug_filename)
            log(f"原始截图已保存: {debug_filename}")
            
            # 直接使用OCR识别，不进行任何预处理
            import pytesseract
            
            # 尝试多种OCR配置
            ocr_configs = [
                '--psm 8 -c tessedit_char_whitelist=0123456789',  # 只识别数字
                '--psm 7 -c tessedit_char_whitelist=0123456789',  # 单行文本
                '--psm 6 -c tessedit_char_whitelist=0123456789',  # 单个文本块
                '--psm 8 -c tessedit_char_whitelist=0123456789,',  # 包含逗号
                '--psm 7 -c tessedit_char_whitelist=0123456789,',  # 包含逗号
            ]
            
            results = []
            for i, config in enumerate(ocr_configs):
                try:
                    text = pytesseract.image_to_string(screenshot, config=config).strip()
                    if text:
                        results.append(f"配置{i+1}: '{text}'")
                        log(f"OCR配置{i+1}识别结果: '{text}'")
                except Exception as e:
                    results.append(f"配置{i+1}: 识别失败 - {e}")
                    log(f"OCR配置{i+1}识别失败: {e}")
            
            # 显示结果
            if results:
                result_text = "\n".join(results)
                messagebox.showinfo("原始OCR识别结果", f"截图区域: {price_region}\n\n识别结果:\n{result_text}\n\n原始截图已保存为: {debug_filename}")
            else:
                messagebox.showwarning("识别结果", "所有OCR配置都未能识别出内容")
                
        except Exception as e:
            log(f"测试原始OCR识别失败: {e}")
            messagebox.showerror("错误", f"测试原始OCR识别失败: {e}")
    
    def toggle_loadout_coordinates_visibility(self):
        """控制配装方案坐标控件的显示/隐藏"""
        selected_mode = mode_var.get()
        is_loadout_mode = selected_mode in ["配装方案1", "配装方案2", "配装方案3"]
        
        # 显示或隐藏配装方案坐标控件
        for widgets in self.loadout_coord_widgets:
            for widget in widgets:
                if is_loadout_mode:
                    widget.grid()
                else:
                    widget.grid_remove()
    
    def toggle_buy_button_visibility(self):
        """控制购买按钮配置的显示/隐藏（滚仓模式下隐藏）"""
        selected_mode = mode_var.get()
        is_loadout_mode = selected_mode in ["配装方案1", "配装方案2", "配装方案3"]
        
        # 在滚仓模式下隐藏购买按钮配置，因为价格区域就是购买按钮位置
        for widget in self.buy_button_widgets:
            if is_loadout_mode:
                widget.grid_remove()
            else:
                widget.grid()
    
    def toggle_loadout_specific_widgets(self):
        """控制满仓和滚仓模式专用控件的显示/隐藏"""
        selected_mode = mode_var.get()
        is_loadout_mode = selected_mode in ["配装方案1", "配装方案2", "配装方案3"]
        
        # 控制满仓模式专用控件
        if hasattr(self, 'fullstock_specific_widgets'):
            for widget in self.fullstock_specific_widgets:
                if is_loadout_mode:
                    widget.grid_remove()
                else:
                    widget.grid()
        
        # 控制滚仓模式专用控件（除了调试模式控件）
        if hasattr(self, 'loadout_specific_widgets'):
            for widget in self.loadout_specific_widgets:
                # 调试模式控件在两种模式下都显示
                if widget in [self.debug_mode_label, self.debug_mode_check]:
                    widget.grid()
                else:
                    if is_loadout_mode:
                        widget.grid()
                    else:
                        widget.grid_remove()
    
    def on_category_change(self, event=None):
        """处理模式类别切换事件"""
        selected_category = self.category_var.get()
        log(f"模式类别切换到: {selected_category}")
        
        # 更新具体模式的选项
        new_mode_options = self.mode_options_map[selected_category]
        self.mode_dropdown['values'] = new_mode_options
        # 设置默认选择第一个选项
        mode_var.set(new_mode_options[0])
        # 触发模式切换事件
        self.on_mode_change()
    
    def on_mode_change(self, event=None):
        selected_mode = mode_var.get()
        log(f"模式切换到: {selected_mode}")
        # 模式切换时，重新初始化配置以加载新模式的价格
        init_config()
        # 重新加载当前模式的坐标配置
        load_coordinate_settings()
        # 更新坐标显示
        self.update_coordinate_display()
        # 控制配装方案坐标控件的显示/隐藏
        self.toggle_loadout_coordinates_visibility()
        # 控制购买按钮配置的显示/隐藏
        self.toggle_buy_button_visibility()
        # 控制滚仓模式专用控件的显示/隐藏
        self.toggle_loadout_specific_widgets() 

# 主程序启动部分
if __name__ == "__main__":
    if not pyuac.isUserAdmin():
        log("以管理员权限重新启动...")
        pyuac.runAsAdmin()
    else:
        log("已拥有管理员权限")
        # 加载坐标配置
        load_coordinate_settings()
        tk_root = tk.Tk()
        app = AppUI(tk_root) # 使用新的UI类
        global app_ui
        app_ui = app  # 设置全局变量以便其他函数访问
        init_config() # 在UI元素创建后，再次调用以确保UI变量被正确赋值
        # 启动后台热键监听
        listener = keyboard.Listener(on_press=on_key_press)
        listener.start()
        tk_root.mainloop()
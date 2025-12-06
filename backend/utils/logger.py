import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 尝试导入颜色库，如果不存在，定义替代函数
try:
    from colorama import init, Fore, Back, Style
    init(autoreset=True)  # 初始化colorama
    
    # 定义颜色函数
    def colored(text, color=None, on_color=None, attrs=None):
        """为文本添加颜色"""
        result = ""
        
        # 前景色
        if color:
            if color.lower() == "red":
                result += Fore.RED
            elif color.lower() == "green":
                result += Fore.GREEN
            elif color.lower() == "yellow":
                result += Fore.YELLOW
            elif color.lower() == "blue":
                result += Fore.BLUE
            elif color.lower() == "magenta":
                result += Fore.MAGENTA
            elif color.lower() == "cyan":
                result += Fore.CYAN
            elif color.lower() == "white":
                result += Fore.WHITE
                
        # 背景色
        if on_color:
            if on_color.lower() == "on_red":
                result += Back.RED
            elif on_color.lower() == "on_green":
                result += Back.GREEN
            elif on_color.lower() == "on_yellow":
                result += Back.YELLOW
            elif on_color.lower() == "on_blue":
                result += Back.BLUE
            elif on_color.lower() == "on_magenta":
                result += Back.MAGENTA
            elif on_color.lower() == "on_cyan":
                result += Back.CYAN
            elif on_color.lower() == "on_white":
                result += Back.WHITE
                
        # 文字属性
        if attrs:
            if "bold" in attrs:
                result += Style.BRIGHT
                
        # 添加文本和重置样式
        result += text + Style.RESET_ALL
        return result
        
except ImportError:
    # 如果没有安装colorama，提供一个不执行任何操作的替代函数
    def colored(text, color=None, on_color=None, attrs=None):
        """不支持颜色的替代函数"""
        return text

# 创建日志目录
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 自定义日志格式化器
class ColoredFormatter(logging.Formatter):
    """带颜色的日志格式化器"""
    
    COLORS = {
        'DEBUG': ('cyan', None, None),
        'INFO': ('green', None, None),
        'WARNING': ('yellow', None, None),
        'ERROR': ('red', None, None),
        'CRITICAL': ('white', 'on_red', ['bold']),
    }
    
    def format(self, record):
        log_message = super().format(record)
        levelname = record.levelname
        
        if levelname in self.COLORS:
            color, on_color, attrs = self.COLORS[levelname]
            log_message = colored(log_message, color, on_color, attrs)
            
        return log_message

# 配置日志格式
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 为文件使用普通格式化器
file_handler = RotatingFileHandler(
    filename=os.path.join(log_dir, "app.log"),
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
file_handler.setFormatter(formatter)

# 为控制台使用彩色格式化器
console_handler = logging.StreamHandler()
colored_formatter = ColoredFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(colored_formatter)

# 创建日志记录器
logger = logging.getLogger("oa_system")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ASCII艺术字符函数
def ascii_header(text, symbol='=', width=80):
    """创建ASCII艺术风格的标题"""
    padding = max(0, (width - len(text) - 2)) // 2
    return colored(f"\n{symbol * padding} {text} {symbol * padding}\n", "cyan", attrs=["bold"])

def progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█'):
    """
    创建命令行进度条
    @params:
        iteration   - 当前迭代次数 [必需]
        total       - 总迭代次数 [必需]
        prefix      - 前缀字符串 [可选]
        suffix      - 后缀字符串 [可选]
        decimals    - 小数位数 [可选]
        length      - 进度条长度 [可选] 
        fill        - 进度条填充字符 [可选]
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    output = f'\r{prefix} |{colored(bar, "green")}| {percent}% {suffix}'
    sys.stdout.write(output)
    sys.stdout.flush()
    
    # 完成时换行
    if iteration == total: 
        sys.stdout.write('\n')
        sys.stdout.flush()

def setup_logging():
    """初始化日志系统"""
    # 日志已经在模块级别初始化
    return logger

def log_request(method: str, url: str, client_ip: str, headers: dict = None):
    """记录HTTP请求日志"""
    logger.info(f"收到请求 - 方法: {method} - URL: {url} - 客户端IP: {client_ip}")

def log_user_action(user_id: int, action: str, details: str = None):
    """记录用户操作日志"""
    logger.info(f"用户ID: {user_id} - 操作: {action} - 详情: {details}")

def log_error(error: Exception, context: str = None):
    """记录错误日志"""
    logger.error(f"错误: {str(error)} - 上下文: {context}")

def log_workflow_action(workflow_id: int, action: str, details: str = None):
    """记录工作流操作日志"""
    logger.info(f"工作流ID: {workflow_id} - 操作: {action} - 详情: {details}")

def log_system_event(event: str, details: str = None):
    """记录系统事件日志"""
    logger.info(f"系统事件: {event} - 详情: {details}")

def log_security_event(event: str, details: str = None):
    """记录安全事件日志"""
    logger.warning(f"安全事件: {event} - 详情: {details}")

def log_performance_metric(metric: str, value: float, details: str = None):
    """记录性能指标日志"""
    logger.info(f"性能指标: {metric} - 值: {value} - 详情: {details}")

# 专为系统启动和关键点设计的美化日志函数
def log_banner(message, banner_type="info"):
    """打印一个引人注目的横幅"""
    width = 80
    if banner_type == "start":
        # 修复中文字符宽度计算问题
        def get_string_width(s):
            """计算字符串显示宽度，考虑中文字符宽度为2"""
            width = 0
            for c in s:
                # 检查是否是中文字符或其他全角字符
                if ord(c) > 127:
                    width += 2  # 中文和其他全角字符宽度为2
                else:
                    width += 1  # ASCII字符宽度为1
            return width
        
        top_bottom = colored("╔" + "═" * (width - 2) + "╗", "cyan", attrs=["bold"])
        filler = colored("║" + " " * (width - 2) + "║", "cyan", attrs=["bold"])
        title = colored("║" + "SYSTEM STARTUP".center(width - 2) + "║", "cyan", attrs=["bold"])
        
        print("\n" + top_bottom)
        print(filler)
        print(title)
        print(filler)
        
        msg_color = "green"
        for line in message.split('\n'):
            # 计算真实显示宽度
            line_width = get_string_width(line)
            
            # 居中显示消息，并保留颜色
            padding_left = (width - 2 - line_width) // 2
            padding_right = width - 2 - line_width - padding_left
            
            formatted_msg = " " * padding_left + line + " " * padding_right
            
            # 确保右边框对齐
            if get_string_width(formatted_msg) != width - 2:
                # 如果计算有误，调整右侧填充
                padding_right += (width - 2) - get_string_width(formatted_msg)
                formatted_msg = " " * padding_left + line + " " * max(0, padding_right)
            
            print(colored("║", "cyan", attrs=["bold"]) + colored(formatted_msg, msg_color) + colored("║", "cyan", attrs=["bold"]))
        
        print(filler)
        print(top_bottom + "\n")
    elif banner_type == "end":
        print(colored("\n" + "=" * width, "blue", attrs=["bold"]))
        print(colored(" " + message.center(width - 2) + " ", "green", attrs=["bold"]))
        print(colored("=" * width + "\n", "blue", attrs=["bold"]))
    elif banner_type == "section":
        # 添加处理中文字符的函数
        def get_string_width(s):
            """计算字符串显示宽度，考虑中文字符宽度为2"""
            width = 0
            for c in s:
                if ord(c) > 127:
                    width += 2
                else:
                    width += 1
            return width
        
        # 使用真实显示宽度计算边框长度
        message_width = get_string_width(message)
        side_len = (width - message_width - 4) // 2
        # 确保不会出现负值
        side_len = max(0, side_len)
        
        # 输出带居中标题的分隔线
        print(colored("\n◄" + "─" * side_len + " ", "yellow") + 
              colored(message, "yellow", attrs=["bold"]) + 
              colored(" " + "─" * side_len + "►\n", "yellow"))
    else:  # 默认info类型
        print(colored("\n■ " + message + "\n", "cyan"))

def print_routes_table(routes, title="路由列表"):
    """打印格式化的路由表格"""
    if not routes:
        return
    
    log_banner(title, "section")
    
    # 计算最大宽度
    path_width = max(len(str(route.get("path", ""))) for route in routes) + 2
    method_width = 20  # 方法通常不会很长
    
    # 打印表头
    header = f"│ {'路径'.ljust(path_width)} │ {'HTTP方法'.ljust(method_width)} │"
    separator = f"├{'─' * (path_width + 2)}┼{'─' * (method_width + 2)}┤"
    top_border = f"┌{'─' * (path_width + 2)}┬{'─' * (method_width + 2)}┐"
    bottom_border = f"└{'─' * (path_width + 2)}┴{'─' * (method_width + 2)}┘"
    
    print(colored(top_border, "blue"))
    print(colored(header, "blue"))
    print(colored(separator, "blue"))
    
    # 打印路由
    for i, route in enumerate(routes):
        path = str(route.get("path", "无路径")).ljust(path_width)
        methods = str(route.get("methods", "无方法")).ljust(method_width)
        
        # 交替行颜色
        color = "green" if i % 2 == 0 else "cyan"
        row = f"│ {path} │ {methods} │"
        print(colored(row, color))
    
    print(colored(bottom_border, "blue"))
    print(f"共 {colored(str(len(routes)), 'yellow', attrs=['bold'])} 个路由") 
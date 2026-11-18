# 课程设计 Demo 的集中配置。所有阈值均为模拟假设，不代表现场设备标准。

DEVICE_ID = "PUMP-001"
DEVICE_NAME = "智能抽油机-001"
LOCATION = "模拟井场 A"

# 模拟器按 1 分钟一个采样点累计能耗。每次点击生成一条数据。
SAMPLING_INTERVAL_MINUTES = 1.0

# R01/R02 需要连续满足条件的采样点数。
DIAGNOSIS_WINDOW_SIZE = 3

OVERLOAD_CURRENT = 50.0
OVERLOAD_LOAD = 90.0
LOW_PRODUCTION_RATIO = 0.80
STOP_STROKE = 0.10
STOP_POWER = 0.10
NORMAL_STROKE_MIN = 3.0
NORMAL_STROKE_MAX = 8.0
MIN_STROKE = 0.10
MAX_STROKE = 15.0

BASELINE = {
    "stroke_rate": 6.0,
    "motor_current": 32.0,
    "load": 55.0,
    "production": 18.5,
    "power": 10.2,
}

CONDITION_LABELS = {
    "normal": "正常运行",
    "overload": "电机过载",
    "low_supply": "疑似供液不足",
    "stop": "异常停机",
}

MAX_HISTORY = 100

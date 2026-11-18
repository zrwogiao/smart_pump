# 智抽云——智能抽油机监测与运行优化系统

课程设计 Demo，使用模拟数据演示抽油机运行监测、规则诊断、报警管理、运行优化和历史查询。

技术路线：Python + Streamlit + Pandas + Plotly + SQLite。

> 所有工况、诊断阈值和优化结果均为课程设计模拟假设，不连接真实设备，不能用于现场生产控制。

详细操作见 `智能抽油机系统使用说明书.docx`，也可直接阅读
`智能抽油机系统使用说明书.md`。

## 功能

- 运行看板：统一展示运行健康度、关键指标、趋势、报警态势、工况构成和快捷入口。
- 运行总览：正常、电机过载、疑似供液不足、异常停机四工况模拟，支持单步演示和一键完整场景。
- 智能诊断：R01-R04 规则证据链，展示当前值、阈值、连续命中次数和判断结论。
- 报警闭环：未处理、处理中、已关闭三种状态，支持处理人、备注和事件持续时间。
- 运行机理：模拟示功图、泵效、充满系数、冲次利用率和产量基准比。
- 运行优化：节能、产量、综合平衡三种目标，支持候选方案搜索、Pareto 前沿和推荐方案。
- 历史数据：按日期和工况筛选，报警统计，运行/报警 CSV 导出，一键生成 PDF 运行报告。
- 持久化：运行数据、报警和处理状态写入 SQLite，应用重启后仍可查询。

## 环境

- 已测试：Python 3.13.9（项目虚拟环境）；代码兼容 Python 3.10+。
- 依赖范围见 `requirements.txt`，本次实际验证版本见 `requirements-lock.txt`。
- 开发测试依赖见 `requirements-dev.txt`。

## Windows 启动

如果接收方已经安装 Python 3.10+，可以直接双击项目根目录的
`一键启动.bat` 或 `start.bat`。首次运行会自动创建虚拟环境、安装依赖并启动系统。
系统会在后台运行并自动打开浏览器。

暂停系统时双击：

```text
一键暂停.bat
```

也可以使用英文入口 `stop.bat`。暂停脚本只停止通过启动脚本启动的 Streamlit 进程。

也可以手动执行：

在项目根目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

如果 PowerShell 阻止激活脚本，不需要执行 `Activate.ps1`，直接使用上面的 Python 绝对路径命令即可。

浏览器打开 Streamlit 输出的本机地址，默认通常为：

```text
http://localhost:8501
```

首次启动会自动创建 `data/pump.db` 和演示设备记录，不需要手工建库。

## 测试

安装开发依赖后运行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

自动化测试使用 `SMART_PUMP_DB_PATH` 指向临时数据库，不会写入正式 `data/pump.db`。

## 演示步骤

1. 运行总览：点击“一键完整演示”，自动生成正常、过载、供液不足、停机和恢复数据。
2. 智能诊断：查看 R01/R02/R03 的规则证据、连续命中次数和报警事件。
3. 处理报警：将事件从“未处理”更新为“处理中”或“已关闭”，填写处理人和备注。
4. 运行总览：切换到“示功图分析”，展示模拟泵效、充满系数和载荷位移曲线。
5. 运行优化：执行“方案搜索与推荐”，比较 Pareto 前沿和候选冲次。
6. 历史数据：筛选日期和工况，生成 PDF 运行报告并导出 CSV。

## 项目结构

```text
smart_pump/
├── app.py
├── pages/
│   ├── 0_运行看板.py
│   ├── 1_运行总览.py
│   ├── 2_智能诊断.py
│   ├── 3_运行优化.py
│   └── 4_历史数据.py
├── core/
│   ├── config.py
│   ├── alarm_events.py
│   ├── database.py
│   ├── diagnosis.py
│   ├── indicator.py
│   ├── metrics.py
│   ├── optimizer.py
│   ├── report.py
│   ├── scenario.py
│   ├── service.py
│   └── simulator.py
├── utils/
│   └── charts.py
├── tests/
├── data/                 # 首次运行自动创建 pump.db
├── requirements.txt
├── requirements-lock.txt
├── requirements-dev.txt
├── TEST_REPORT.md
└── DEMO_GUIDE.md
```

## 数据与实现口径

- `load` 表示负载率，单位 `%`，不是载荷 `kN`。
- `energy` 表示累计能耗，单位 `kWh`。每次点击生成一个模拟采样点，按 1 分钟采样间隔用 `power / 60` 累加。
- R01：最近 3 条采样的电流或负载率均超限才报警。
- R02：最近 3 条采样均在运行且模拟产量低于基线的 80% 才报警。
- R03：停机状态或冲次、功率同时接近零时报警。
- R04：冲次超出 3-8 次/min 的演示范围时报警。
- 同一连续异常事件只写入一条报警；恢复后再次连续越限会生成新事件报警。
- 示功图、泵效、充满系数和 Pareto 候选方案均由模拟公式生成。
- PDF 报告中的统计、诊断和优化内容来自当前筛选范围及最新运行状态。

## 数据库维护

需要清空演示数据时，先停止应用并备份 `data/pump.db`，再删除该文件；下次启动会自动创建空数据库。不要在应用运行中删除数据库。

## 已知边界

- 当前不是定时采集系统，数据由页面按钮主动生成。
- 诊断和优化模型为课程设计简化规则，不包含机器学习或真实机理模型。
- 多设备总览尚未纳入当前版本，当前演示设备为 PUMP-001。
- 系统不提供设备控制、用户权限、真实传感器接入或工业级告警联锁。

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#64748B")
TEAL = colors.HexColor("#0F766E")
HEADER_FILL = colors.HexColor("#E8EEF5")
CALLOUT_FILL = colors.HexColor("#F4F6F9")
BORDER = colors.HexColor("#D7DBE2")


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="STSong-Light",
            fontSize=22,
            leading=28,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName="STSong-Light",
            fontSize=10.5,
            leading=16,
            textColor=MUTED,
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "ReportH1",
            parent=base["Heading1"],
            fontName="STSong-Light",
            fontSize=14,
            leading=20,
            textColor=TEAL,
            spaceBefore=12,
            spaceAfter=7,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontName="STSong-Light",
            fontSize=9.5,
            leading=15,
            textColor=INK,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontName="STSong-Light",
            fontSize=8,
            leading=12,
            textColor=MUTED,
        ),
        "table": ParagraphStyle(
            "ReportTable",
            parent=base["BodyText"],
            fontName="STSong-Light",
            fontSize=8,
            leading=11,
            textColor=INK,
        ),
        "table_header": ParagraphStyle(
            "ReportTableHeader",
            parent=base["BodyText"],
            fontName="STSong-Light",
            fontSize=8,
            leading=11,
            textColor=INK,
            alignment=TA_CENTER,
        ),
    }


def _p(value, style):
    return Paragraph(escape(str(value)), style)


def _table(rows, widths, styles):
    data = [
        [_p(cell, styles["table_header"]) for cell in rows[0]]
    ] + [
        [_p(cell, styles["table"]) for cell in row]
        for row in rows[1:]
    ]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_FILL),
                ("TEXTCOLOR", (0, 0), (-1, 0), INK),
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.white]),
            ]
        )
    )
    return table


def _safe_number(value, digits=2):
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def generate_running_report(
    *,
    device_id,
    start_date,
    end_date,
    running,
    alarm_events,
    diagnosis,
    health_score,
    optimization=None,
):
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="智抽云智能抽油机运行报告",
        author="智能抽油机项目组",
    )

    def page_furniture(canvas, document):
        canvas.saveState()
        canvas.setFont("STSong-Light", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            17 * mm,
            A4[1] - 10 * mm,
            "智抽云｜智能抽油机运行报告",
        )
        canvas.drawRightString(
            A4[0] - 17 * mm,
            9 * mm,
            f"第 {document.page} 页",
        )
        canvas.restoreState()

    story = [
        Paragraph("智抽云｜智能抽油机运行报告", styles["title"]),
        Paragraph(
            (
                f"设备 {escape(str(device_id))}　｜　"
                f"统计周期 {escape(str(start_date))} 至 {escape(str(end_date))}　｜　"
                f"生成时间 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            styles["subtitle"],
        ),
    ]

    summary_rows = [
        ["指标", "结果"],
        ["运行采样数", len(running)],
        ["异常采样数", int((running["status"] != "正常").sum()) if not running.empty else 0],
        ["报警事件数", len(alarm_events)],
        [
            "平均电流",
            f'{_safe_number(running["motor_current"].mean())} A'
            if not running.empty
            else "-",
        ],
        [
            "平均负载率",
            f'{_safe_number(running["load"].mean())} %'
            if not running.empty
            else "-",
        ],
        [
            "平均模拟产量",
            f'{_safe_number(running["production"].mean())} m³/d'
            if not running.empty
            else "-",
        ],
        [
            "平均功率",
            f'{_safe_number(running["power"].mean())} kW'
            if not running.empty
            else "-",
        ],
        ["运行健康度", f"{_safe_number(health_score, 0)}%"],
    ]
    story.extend(
        [
            Paragraph("一、运行摘要", styles["h1"]),
            _table(summary_rows, [74 * mm, 74 * mm], styles),
        ]
    )

    story.append(Paragraph("二、当前诊断", styles["h1"]))
    story.append(
        Paragraph(
            (
                f"当前规则：{escape(str(diagnosis.get('rule_id', '-')))}　"
                f"诊断结果：{escape(str(diagnosis.get('alarm_type', '正常')))}　"
                f"等级：{escape(str(diagnosis.get('level', '正常')))}"
            ),
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"原因说明：{escape(str(diagnosis.get('message', '-')))}",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            f"处理建议：{escape(str(diagnosis.get('suggestion', '-')))}",
            styles["body"],
        )
    )

    evidence = diagnosis.get("evidence") or []
    if evidence:
        evidence_rows = [["指标", "当前值", "阈值", "命中", "结论"]]
        for item in evidence:
            evidence_rows.append(
                [
                    item.get("label", item.get("metric", "-")),
                    f'{item.get("value", "-")} {item.get("unit", "")}',
                    f'{item.get("threshold", "-")} {item.get("unit", "")}',
                    f'{item.get("hits", 0)}/{item.get("window_size", 0)}',
                    "满足" if item.get("passed") else "未满足",
                ]
            )
        story.append(
            _table(
                evidence_rows,
                [40 * mm, 38 * mm, 38 * mm, 24 * mm, 28 * mm],
                styles,
            )
        )

    story.append(PageBreak())
    story.append(Paragraph("三、报警事件", styles["h1"]))
    if alarm_events.empty:
        story.append(Paragraph("所选周期内没有报警事件。", styles["body"]))
    else:
        alarm_rows = [["时间", "规则", "类型", "等级", "持续时间", "状态"]]
        for _, event in alarm_events.head(18).iterrows():
            alarm_rows.append(
                [
                    str(event["timestamp"]),
                    str(event["rule_id"]),
                    str(event["alarm_type"]),
                    str(event["level"]),
                    f'{event["duration_minutes"]} 分钟',
                    str(event["status"]),
                ]
            )
        story.append(
            _table(
                alarm_rows,
                [
                    38 * mm,
                    20 * mm,
                    42 * mm,
                    18 * mm,
                    30 * mm,
                    28 * mm,
                ],
                styles,
            )
        )
        story.append(
            Paragraph(
                "报警事件按同一连续异常过程聚合，持续时间为模拟采样时长。",
                styles["small"],
            )
        )

    if optimization:
        story.append(Paragraph("四、优化建议", styles["h1"]))
        optimization_rows = [
            ["指标", "优化前", "优化后", "变化"],
            [
                "功率",
                f'{optimization["current_power"]:.2f} kW',
                f'{optimization["optimized_power"]:.2f} kW',
                f'{optimization["power_change_pct"]:+.2f}%',
            ],
            [
                "日能耗",
                f'{optimization["current_energy"]:.2f} kWh',
                f'{optimization["optimized_energy"]:.2f} kWh',
                f'{(optimization["optimized_energy"] / optimization["current_energy"] - 1) * 100:+.2f}%',
            ],
            [
                "模拟产量",
                f'{optimization["current_production"]:.2f} m³/d',
                f'{optimization["optimized_production"]:.2f} m³/d',
                f'{optimization["production_change_pct"]:+.2f}%',
            ],
        ]
        story.append(
            _table(
                optimization_rows,
                [48 * mm, 42 * mm, 42 * mm, 42 * mm],
                styles,
            )
        )
        story.append(
            Paragraph(
                escape(str(optimization.get("recommendation", ""))),
                styles["body"],
            )
        )

    story.extend(
        [
            Spacer(1, 10),
            Paragraph(
                (
                    "说明：本报告来自课程设计模拟系统。工况、诊断阈值和优化结果"
                    "均为演示假设，不连接真实设备，不能作为现场生产或安全决策依据。"
                ),
                styles["small"],
            ),
        ]
    )
    doc.build(story, onFirstPage=page_furniture, onLaterPages=page_furniture)
    return buffer.getvalue()

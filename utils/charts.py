import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

INK = "#172033"
MUTED = "#64748B"
GRID = "#E2E8F0"
TEAL = "#0F766E"
BLUE = "#2563EB"
AMBER = "#D97706"
RED = "#DC2626"
SLATE = "#94A3B8"


def _base_layout(fig, *, height=360, margin=None):
    fig.update_layout(
        height=height,
        font=dict(family="Microsoft YaHei, Arial", color=INK, size=11),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=margin or dict(l=42, r=18, t=42, b=32),
        hoverlabel=dict(
            bgcolor="#0F172A",
            bordercolor="#0F172A",
            font=dict(color="#F8FAFC", size=11),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10, color=MUTED),
        ),
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        linecolor=GRID,
        tickfont=dict(size=10, color=MUTED),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID,
        zeroline=False,
        tickfont=dict(size=10, color=MUTED),
    )
    return fig


def _add_alarm_markers(fig, alarms, data):
    if alarms is None or alarms.empty:
        return
    start = pd.to_datetime(data["timestamp"]).min()
    end = pd.to_datetime(data["timestamp"]).max()
    timestamps = pd.to_datetime(alarms["timestamp"])
    visible = alarms[(timestamps >= start) & (timestamps <= end)]
    for _, alarm in visible.tail(8).iterrows():
        fig.add_vline(
            x=pd.to_datetime(alarm["timestamp"]),
            line_width=1,
            line_dash="dot",
            line_color=RED if alarm.get("level") == "高" else AMBER,
            opacity=0.45,
        )


def dashboard_trend_chart(df: pd.DataFrame, alarms=None):
    if df.empty:
        return None
    data = df.sort_values("timestamp").tail(40).copy()
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.13,
        row_heights=[0.48, 0.52],
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["load"],
            mode="lines",
            name="负载率 %",
            line=dict(color=TEAL, width=2.2),
            fill="tozeroy",
            fillcolor="rgba(15,118,110,0.08)",
            hovertemplate="负载率 %{y:.1f}%<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["motor_current"],
            mode="lines",
            name="电流 A",
            line=dict(color=BLUE, width=1.8),
            hovertemplate="电流 %{y:.1f} A<extra></extra>",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=data["timestamp"],
            y=data["production"],
            name="产量 m³/d",
            marker_color="rgba(37,99,235,0.55)",
            hovertemplate="产量 %{y:.1f} m³/d<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=data["timestamp"],
            y=data["power"],
            mode="lines+markers",
            name="功率 kW",
            line=dict(color=AMBER, width=2),
            marker=dict(size=4),
            hovertemplate="功率 %{y:.1f} kW<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.update_yaxes(title_text="负载 / 电流", row=1, col=1)
    fig.update_yaxes(title_text="产量 / 功率", row=2, col=1)
    fig.update_layout(barmode="overlay")
    _add_alarm_markers(fig, alarms, data)
    return _base_layout(fig, height=430, margin=dict(l=48, r=18, t=28, b=30))


def trend_chart(df: pd.DataFrame, alarms=None):
    if df.empty:
        return None
    data = df.sort_values("timestamp").copy()
    metrics = [
        ("stroke_rate", "冲次", "次/min", 1, 1, TEAL),
        ("motor_current", "电机电流", "A", 1, 2, BLUE),
        ("load", "负载率", "%", 2, 1, AMBER),
        ("power", "功率", "kW", 2, 2, RED),
    ]
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=[item[1] for item in metrics],
        vertical_spacing=0.16,
        horizontal_spacing=0.1,
    )
    for column, title, unit, row, col, color in metrics:
        fig.add_trace(
            go.Scatter(
                x=data["timestamp"],
                y=data[column],
                mode="lines+markers",
                name=title,
                line=dict(color=color, width=2),
                marker=dict(size=4),
                hovertemplate=(
                    f"{title}：%{{y:.2f}} {unit}<extra></extra>"
                ),
            ),
            row=row,
            col=col,
        )
        fig.update_yaxes(title_text=unit, row=row, col=col)

    fig.update_layout(showlegend=False)
    fig.update_annotations(font=dict(size=11, color=INK))
    _add_alarm_markers(fig, alarms, data)
    return _base_layout(fig, height=560)


def health_gauge(score):
    score = float(score)
    color = TEAL if score >= 80 else AMBER if score >= 55 else RED
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number=dict(suffix="%", font=dict(size=32, color=INK)),
            title=dict(text="运行健康度", font=dict(size=13, color=MUTED)),
            gauge=dict(
                axis=dict(
                    range=[0, 100],
                    tickwidth=0,
                    tickfont=dict(size=9, color=MUTED),
                ),
                bar=dict(color=color, thickness=0.68),
                bgcolor="#F1F5F9",
                borderwidth=0,
                steps=[
                    dict(range=[0, 55], color="#FEE2E2"),
                    dict(range=[55, 80], color="#FEF3C7"),
                    dict(range=[80, 100], color="#D1FAE5"),
                ],
                threshold=dict(
                    line=dict(color=color, width=3),
                    thickness=0.82,
                    value=score,
                ),
            ),
        )
    )
    fig.update_layout(
        height=255,
        margin=dict(l=22, r=22, t=48, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Microsoft YaHei, Arial"),
    )
    return fig


def alarm_distribution_chart(alarms: pd.DataFrame):
    if alarms.empty:
        return None
    counts = (
        alarms["alarm_type"]
        .value_counts()
        .rename_axis("报警类型")
        .reset_index(name="次数")
    )
    fig = px.bar(
        counts,
        x="次数",
        y="报警类型",
        orientation="h",
        color="次数",
        color_continuous_scale=["#CCFBF1", TEAL],
        text="次数",
    )
    fig.update_coloraxes(showscale=False)
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_line_width=0,
        hovertemplate="%{y}: %{x} 次<extra></extra>",
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title="",
        bargap=0.35,
    )
    return _base_layout(fig, height=300, margin=dict(l=100, r=25, t=15, b=30))


def condition_donut(df: pd.DataFrame):
    if df.empty:
        return None
    counts = (
        df["condition"]
        .value_counts()
        .rename_axis("condition")
        .reset_index(name="count")
    )
    labels = {
        "normal": "正常运行",
        "overload": "电机过载",
        "low_supply": "供液不足",
        "stop": "异常停机",
    }
    counts["工况"] = counts["condition"].map(labels).fillna(counts["condition"])
    fig = px.pie(
        counts,
        names="工况",
        values="count",
        hole=0.66,
        color="工况",
        color_discrete_map={
            "正常运行": TEAL,
            "电机过载": RED,
            "供液不足": AMBER,
            "异常停机": SLATE,
        },
    )
    fig.update_traces(
        textinfo="percent",
        textposition="inside",
        hovertemplate="%{label}: %{value} 条<extra></extra>",
    )
    fig.update_layout(showlegend=True)
    return _base_layout(fig, height=300, margin=dict(l=12, r=12, t=10, b=10))


def alarm_timeline_chart(alarms: pd.DataFrame):
    if alarms.empty:
        return None
    data = alarms.copy()
    data["日期"] = pd.to_datetime(data["timestamp"]).dt.date
    grouped = (
        data.groupby(["日期", "alarm_type"], as_index=False)
        .size()
        .rename(columns={"alarm_type": "报警类型", "size": "次数"})
    )
    fig = px.bar(
        grouped,
        x="日期",
        y="次数",
        color="报警类型",
        barmode="stack",
        color_discrete_sequence=[RED, AMBER, BLUE, TEAL],
    )
    fig.update_layout(xaxis_title="", yaxis_title="报警次数", bargap=0.35)
    return _base_layout(fig, height=300)


def comparison_chart(
    current_power,
    optimized_power,
    current_production,
    optimized_production,
):
    df = pd.DataFrame(
        {
            "指标": ["功率", "模拟产量"],
            "优化前": [current_power, current_production],
            "优化后": [optimized_power, optimized_production],
        }
    )
    long_df = df.melt(id_vars="指标", var_name="方案", value_name="数值")
    fig = px.bar(
        long_df,
        x="指标",
        y="数值",
        color="方案",
        barmode="group",
        text_auto=".2f",
        color_discrete_map={"优化前": SLATE, "优化后": TEAL},
    )
    fig.update_traces(
        textposition="outside",
        cliponaxis=False,
        marker_line_width=0,
    )
    fig.update_layout(xaxis_title="", yaxis_title="")
    return _base_layout(fig, height=360)


def indicator_diagram_chart(curve: pd.DataFrame, condition_label="正常运行"):
    if curve.empty:
        return None
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=curve["displacement"],
            y=curve["load"],
            mode="lines",
            line=dict(color=TEAL, width=2.8),
            fill="toself",
            fillcolor="rgba(15,118,110,0.10)",
            customdata=curve["stroke"],
            hovertemplate=(
                "位移 %{x:.2f}<br>载荷 %{y:.1f} kN<br>"
                "%{customdata}<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(
        title_text="相对位移",
        range=[-0.03, 1.03],
        tickformat=".1f",
    )
    fig.update_yaxes(title_text="模拟载荷（kN）")
    fig.update_layout(
        title=dict(
            text=f"{condition_label}示功图",
            font=dict(size=13, color=INK),
            x=0,
        )
    )
    return _base_layout(fig, height=390, margin=dict(l=52, r=20, t=44, b=38))


def pareto_chart(candidates, recommended=None):
    if not candidates:
        return None
    data = pd.DataFrame(candidates)
    fig = go.Figure()
    feasible = data[data["feasible"]]
    infeasible = data[~data["feasible"]]
    pareto = feasible[feasible["is_pareto"]]

    if not infeasible.empty:
        fig.add_trace(
            go.Scatter(
                x=infeasible["optimized_power"],
                y=infeasible["optimized_production"],
                mode="markers",
                name="超出约束",
                marker=dict(color="#CBD5E1", size=8),
                customdata=infeasible["target_stroke"],
                hovertemplate=(
                    "冲次 %{customdata:.2f}<br>功率 %{x:.2f} kW<br>"
                    "产量 %{y:.2f} m³/d<extra></extra>"
                ),
            )
        )
    if not feasible.empty:
        fig.add_trace(
            go.Scatter(
                x=feasible["optimized_power"],
                y=feasible["optimized_production"],
                mode="markers",
                name="可行方案",
                marker=dict(
                    color=feasible["score"],
                    colorscale=[[0, "#CCFBF1"], [1, TEAL]],
                    size=9,
                    colorbar=dict(title="评分", thickness=10),
                    line=dict(color="#FFFFFF", width=0.5),
                ),
                customdata=feasible["target_stroke"],
                hovertemplate=(
                    "冲次 %{customdata:.2f}<br>功率 %{x:.2f} kW<br>"
                    "产量 %{y:.2f} m³/d<extra></extra>"
                ),
            )
        )
    if not pareto.empty:
        ordered = pareto.sort_values("optimized_power")
        fig.add_trace(
            go.Scatter(
                x=ordered["optimized_power"],
                y=ordered["optimized_production"],
                mode="lines",
                name="Pareto 前沿",
                line=dict(color=AMBER, width=2, dash="dash"),
                hoverinfo="skip",
            )
        )
    if recommended:
        fig.add_trace(
            go.Scatter(
                x=[recommended["optimized_power"]],
                y=[recommended["optimized_production"]],
                mode="markers+text",
                name="推荐方案",
                text=[f'推荐 {recommended["target_stroke"]:.2f} 次/min'],
                textposition="top center",
                marker=dict(
                    color=RED,
                    size=15,
                    symbol="star",
                    line=dict(color="#FFFFFF", width=1),
                ),
                hovertemplate=(
                    "推荐冲次 %{customdata:.2f}<extra></extra>"
                ),
                customdata=[recommended["target_stroke"]],
            )
        )
    fig.update_xaxes(title_text="模拟功率（kW）")
    fig.update_yaxes(title_text="模拟产量（m³/d）")
    return _base_layout(fig, height=440)

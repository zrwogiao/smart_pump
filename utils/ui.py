import html

import pandas as pd
import streamlit as st

ACCENT = "#0F766E"
NAVY = "#0F172A"
BLUE = "#2563EB"
AMBER = "#B45309"
RED = "#B91C1C"
MUTED = "#64748B"
BORDER = "#E2E8F0"


GLOBAL_CSS = """
<style>
:root {
  --ink: #172033;
  --muted: #64748B;
  --line: #E2E8F0;
  --surface: #FFFFFF;
  --canvas: #F4F6F8;
  --navy: #0F172A;
  --teal: #0F766E;
  --blue: #2563EB;
  --amber: #B45309;
  --red: #B91C1C;
}

.stApp {
  background: var(--canvas);
  color: var(--ink);
}

.block-container {
  max-width: 1480px;
  padding-top: 1.15rem;
  padding-bottom: 2.2rem;
}

[data-testid="stSidebar"] {
  background: #111827;
  border-right: 1px solid #1F2937;
  color: #CBD5E1;
}

[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
[data-testid="stSidebar"] [data-testid="stSidebarNav"] a span,
[data-testid="stSidebar"] [data-testid="stSidebarNav"] [data-testid="stIconMaterial"],
[data-testid="stSidebar"] [data-testid="stSidebarHeader"] button span {
  color: #CBD5E1 !important;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
[data-testid="stSidebar"] label {
  color: #CBD5E1 !important;
}

[data-testid="stSidebar"] a {
  border-radius: 6px;
}

[data-testid="stSidebar"] a:hover {
  background: #1E293B;
}

[data-testid="stSidebar"] a[aria-current="page"] {
  background: #0F766E;
  color: #FFFFFF;
}

[data-testid="stSidebar"] a[aria-current="page"] span,
[data-testid="stSidebar"] a[aria-current="page"] [data-testid="stIconMaterial"] {
  color: #FFFFFF !important;
}

.brand-block {
  padding: 4px 2px 14px 2px;
  border-bottom: 1px solid #293548;
  margin-bottom: 12px;
}

.brand-mark {
  display: flex;
  align-items: center;
  gap: 9px;
  color: #F8FAFC;
  font-size: 1.08rem;
  font-weight: 750;
  letter-spacing: 0;
}

.brand-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #2DD4BF;
  box-shadow: 0 0 0 4px rgba(45, 212, 191, 0.12);
}

.brand-sub {
  margin-top: 5px;
  color: #94A3B8;
  font-size: 0.76rem;
  line-height: 1.45;
}

.dashboard-hero {
  position: relative;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
  flex-wrap: wrap;
  background: #0F172A;
  border: 1px solid #1E293B;
  border-radius: 8px;
  padding: 22px 24px 20px 24px;
  margin: 0 0 16px 0;
}

.dashboard-hero::after {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: #2DD4BF;
}

.hero-kicker {
  color: #5EEAD4;
  font-size: 0.73rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 6px;
}

.hero-title {
  color: #F8FAFC;
  font-size: 1.75rem;
  line-height: 1.18;
  font-weight: 760;
  margin: 0;
}

.hero-subtitle {
  color: #AFC0D4;
  font-size: 0.86rem;
  line-height: 1.5;
  margin-top: 7px;
}

.hero-meta {
  color: #8192A8;
  font-size: 0.75rem;
  margin-top: 8px;
}

.hero-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  text-align: right;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1;
  white-space: nowrap;
}

.status-chip::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.status-success {
  color: #047857;
  background: #D1FAE5;
}

.status-warning {
  color: #92400E;
  background: #FEF3C7;
}

.status-danger {
  color: #991B1B;
  background: #FEE2E2;
}

.status-info {
  color: #1D4ED8;
  background: #DBEAFE;
}

.status-neutral {
  color: #475569;
  background: #E2E8F0;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
  gap: 12px;
  margin: 4px 0 16px 0;
}

.kpi-card {
  position: relative;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px 15px 13px 15px;
  min-height: 100px;
}

.kpi-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  right: 0;
  height: 3px;
  background: #94A3B8;
}

.kpi-card.tone-good::before { background: #0F766E; }
.kpi-card.tone-blue::before { background: #2563EB; }
.kpi-card.tone-warn::before { background: #D97706; }
.kpi-card.tone-danger::before { background: #DC2626; }

.kpi-label {
  color: var(--muted);
  font-size: 0.74rem;
  font-weight: 650;
  line-height: 1.3;
  min-height: 19px;
}

.kpi-value {
  color: var(--ink);
  font-size: 1.43rem;
  line-height: 1.25;
  font-weight: 760;
  margin-top: 7px;
  overflow-wrap: anywhere;
}

.kpi-helper {
  color: #7C8CA1;
  font-size: 0.7rem;
  line-height: 1.35;
  margin-top: 6px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin: 4px 0 8px 0;
}

.section-kicker {
  color: #0F766E;
  font-size: 0.68rem;
  font-weight: 750;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  margin-bottom: 2px;
}

.section-title {
  color: var(--ink);
  font-size: 1rem;
  line-height: 1.25;
  font-weight: 730;
}

.section-note {
  color: var(--muted);
  font-size: 0.72rem;
}

.panel-caption {
  color: var(--muted);
  font-size: 0.73rem;
  line-height: 1.45;
}

.diagnosis-block {
  border-left: 3px solid #94A3B8;
  padding: 2px 0 2px 12px;
  margin: 4px 0 10px 0;
}

.diagnosis-block.good { border-left-color: #0F766E; }
.diagnosis-block.warn { border-left-color: #D97706; }
.diagnosis-block.danger { border-left-color: #DC2626; }

.diagnosis-title {
  color: var(--ink);
  font-size: 0.95rem;
  font-weight: 730;
}

.diagnosis-copy {
  color: #526277;
  font-size: 0.78rem;
  line-height: 1.55;
  margin-top: 5px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px 11px;
}

.alert-level {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 34px;
  height: 24px;
  border-radius: 5px;
  font-size: 0.68rem;
  font-weight: 750;
}

.alert-level.high { color: #991B1B; background: #FEE2E2; }
.alert-level.mid { color: #92400E; background: #FEF3C7; }
.alert-level.low { color: #1D4ED8; background: #DBEAFE; }

.alert-main {
  min-width: 0;
}

.alert-title {
  color: var(--ink);
  font-size: 0.79rem;
  font-weight: 690;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.alert-meta {
  color: var(--muted);
  font-size: 0.67rem;
  margin-top: 2px;
}

.alert-status {
  color: #475569;
  background: #F1F5F9;
  border-radius: 5px;
  padding: 4px 7px;
  font-size: 0.65rem;
  font-weight: 650;
  white-space: nowrap;
}

.alert-status.processed {
  color: #047857;
  background: #D1FAE5;
}

.rule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
  margin: 4px 0 12px 0;
}

.rule-card {
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-left: 3px solid #94A3B8;
  border-radius: 8px;
  padding: 11px 12px;
}

.rule-card.triggered {
  border-left-color: #DC2626;
  background: #FFFBFB;
}

.rule-card.watching {
  border-left-color: #D97706;
  background: #FFFCF5;
}

.rule-card.normal {
  border-left-color: #0F766E;
}

.rule-topline {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}

.rule-name {
  color: var(--ink);
  font-size: 0.8rem;
  font-weight: 720;
}

.rule-state {
  color: #475569;
  background: #F1F5F9;
  border-radius: 5px;
  padding: 3px 6px;
  font-size: 0.64rem;
  font-weight: 650;
}

.rule-card.triggered .rule-state {
  color: #991B1B;
  background: #FEE2E2;
}

.rule-card.watching .rule-state {
  color: #92400E;
  background: #FEF3C7;
}

.rule-card.normal .rule-state {
  color: #047857;
  background: #D1FAE5;
}

.rule-progress {
  height: 5px;
  background: #EDF1F5;
  border-radius: 999px;
  overflow: hidden;
  margin: 10px 0 6px 0;
}

.rule-progress-fill {
  height: 100%;
  border-radius: 999px;
  background: #0F766E;
}

.rule-card.watching .rule-progress-fill { background: #D97706; }
.rule-card.triggered .rule-progress-fill { background: #DC2626; }

.rule-meta {
  color: var(--muted);
  font-size: 0.68rem;
  line-height: 1.4;
}

.empty-panel {
  background: #FFFFFF;
  border: 1px dashed #CBD5E1;
  border-radius: 8px;
  padding: 26px 22px;
  text-align: center;
  margin: 8px 0 14px 0;
}

.empty-title {
  color: var(--ink);
  font-size: 1rem;
  font-weight: 720;
}

.empty-copy {
  color: var(--muted);
  font-size: 0.78rem;
  line-height: 1.55;
  margin-top: 6px;
}

div[data-testid="stMetric"] {
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 12px 14px;
}

div[data-testid="stVerticalBlockBorderWrapper"] {
  background: #FFFFFF;
  border-radius: 8px;
}

div[data-testid="stVerticalBlockBorderWrapper"] > div {
  border-color: var(--line) !important;
}

.stButton > button,
.stDownloadButton > button {
  border-radius: 6px;
  font-weight: 650;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
  background: #0F766E;
  border-color: #0F766E;
}

.stButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {
  background: #115E59;
  border-color: #115E59;
}

div[role="radiogroup"] {
  gap: 7px;
  flex-wrap: wrap;
}

div[role="radiogroup"] label {
  background: #FFFFFF;
  border: 1px solid #D8E0EA;
  border-radius: 6px;
  padding: 7px 10px;
  min-height: 36px;
}

div[role="radiogroup"] label:has(input:checked) {
  background: #ECFDF5;
  border-color: #5EEAD4;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

[data-testid="stPlotlyChart"] {
  border-radius: 8px;
  overflow: hidden;
}

@media (max-width: 720px) {
  .block-container {
    padding-left: 0.8rem;
    padding-right: 0.8rem;
    padding-top: 0.8rem;
  }

  .dashboard-hero {
    padding: 19px 18px;
    align-items: flex-start;
  }

  .hero-title {
    font-size: 1.48rem;
  }

  .hero-right {
    align-items: flex-start;
    text-align: left;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 9px;
  }

  .kpi-card {
    min-height: 94px;
    padding: 12px;
  }

  .kpi-value {
    font-size: 1.22rem;
  }

  .alert-row {
    grid-template-columns: 38px minmax(0, 1fr);
  }

  .alert-status {
    grid-column: 2;
    justify-self: start;
  }
}
/* ===== 油气生产管控台 · 专业风格增强 ===== */
.app-commandbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  background: #0B1220;
  border: 1px solid #1E293B;
  border-left: 4px solid #14B8A6;
  border-radius: 8px;
  padding: 10px 16px;
  margin: 0 0 12px 0;
}
.commandbar-left {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}
.commandbar-emblem {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
  border-radius: 7px;
  background: #134E4A;
  border: 1px solid #0F766E;
  display: flex;
  align-items: center;
  justify-content: center;
}
.commandbar-emblem svg { width: 20px; height: 20px; }
.commandbar-sys { min-width: 0; }
.commandbar-name {
  color: #F1F5F9;
  font-size: 0.9rem;
  font-weight: 740;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.commandbar-sub {
  color: #7F93AA;
  font-size: 0.66rem;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  margin-top: 3px;
}
.commandbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.field-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid #24344A;
  background: #152238;
  color: #B9C8DA;
  border-radius: 5px;
  padding: 5px 9px;
  font-size: 0.7rem;
  line-height: 1;
}
.field-tag b {
  color: #E2E8F0;
  font-weight: 700;
  font-family: var(--font-mono, monospace);
}
.field-tag.sim {
  border-color: #7C4A12;
  background: #3A2A12;
  color: #FCD34D;
  font-weight: 650;
}
.live-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #6EE7B7;
  font-size: 0.7rem;
  font-weight: 650;
}
.live-indicator::before {
  content: "";
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #34D399;
  box-shadow: 0 0 0 3px rgba(52, 211, 153, 0.16);
}

.state-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-left: 3px solid #0F766E;
  border-radius: 8px;
  padding: 12px 14px;
  margin: 0 0 14px 0;
}
.state-banner.warn { border-left-color: #D97706; }
.state-banner.danger { border-left-color: #DC2626; }
.state-banner-code {
  font-family: var(--font-mono, monospace);
  font-size: 0.72rem;
  color: #0F766E;
  font-weight: 700;
  letter-spacing: 0.06em;
  white-space: nowrap;
  padding-top: 2px;
}
.state-banner.warn .state-banner-code { color: #B45309; }
.state-banner.danger .state-banner-code { color: #B91C1C; }
.state-banner-title {
  color: var(--ink);
  font-size: 0.86rem;
  font-weight: 730;
}
.state-banner-copy {
  color: var(--muted);
  font-size: 0.74rem;
  line-height: 1.55;
  margin-top: 3px;
}

.quick-plan-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(238px, 1fr));
  gap: 12px;
  margin: 10px 0 12px 0;
}
.plan-card {
  position: relative;
  background: #FFFFFF;
  border: 1px solid var(--line);
  border-top: 3px solid #94A3B8;
  border-radius: 8px;
  padding: 13px 14px 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 9px;
}
.plan-card.tone-good { border-top-color: #0F766E; }
.plan-card.tone-blue { border-top-color: #2563EB; }
.plan-card.tone-warn { border-top-color: #D97706; }
.plan-card.tone-danger { border-top-color: #DC2626; }
.plan-card.recommended { box-shadow: inset 0 0 0 1px #5EEAD4; }
.plan-topline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.plan-name {
  color: var(--ink);
  font-size: 0.9rem;
  font-weight: 750;
}
.plan-badge {
  border-radius: 5px;
  padding: 3px 7px;
  font-size: 0.64rem;
  font-weight: 700;
  white-space: nowrap;
  background: #F1F5F9;
  color: #475569;
}
.plan-badge.tone-good { color: #047857; background: #D1FAE5; }
.plan-badge.tone-blue { color: #1D4ED8; background: #DBEAFE; }
.plan-badge.tone-warn { color: #92400E; background: #FEF3C7; }
.plan-badge.tone-danger { color: #991B1B; background: #FEE2E2; }
.plan-target {
  display: flex;
  align-items: baseline;
  gap: 7px;
  color: var(--muted);
  font-size: 0.71rem;
}
.plan-target b {
  font-family: var(--font-mono, monospace);
  font-size: 1.16rem;
  color: var(--ink);
  font-weight: 750;
}
.plan-effects {
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: #F8FAFC;
  border: 1px solid #EEF2F6;
  border-radius: 6px;
  padding: 8px 9px;
}
.effect-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 0.71rem;
  color: var(--muted);
}
.effect-row b {
  font-family: var(--font-mono, monospace);
  color: var(--ink);
  font-weight: 700;
  font-size: 0.74rem;
}
.effect-row em {
  font-style: normal;
  font-family: var(--font-mono, monospace);
  font-size: 0.68rem;
  font-weight: 700;
  min-width: 56px;
  text-align: right;
}
.effect-row em.down-good { color: #047857; }
.effect-row em.up-bad { color: #B91C1C; }
.effect-row em.flat { color: #64748B; }
.plan-reason {
  color: #526277;
  font-size: 0.71rem;
  line-height: 1.5;
  flex: 1;
}
.plan-meta {
  color: #94A3B8;
  font-size: 0.66rem;
}
.effect-legend {
  color: var(--muted);
  font-size: 0.68rem;
  line-height: 1.5;
}
div[data-testid="stMetric"] .metric-label { letter-spacing: 0.04em; }
</style>
"""


TONE_CLASS = {
    "good": "status-success",
    "success": "status-success",
    "warning": "status-warning",
    "warn": "status-warning",
    "danger": "status-danger",
    "error": "status-danger",
    "info": "status-info",
    "neutral": "status-neutral",
}


def _compact_html(fragment):
    return "".join(line.strip() for line in fragment.splitlines())


def apply_global_style():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def page_header(
    title,
    subtitle,
    *,
    kicker="SMART PUMP OPERATIONS",
    status_label=None,
    status_tone="info",
    meta="",
):
    status_html = ""
    if status_label:
        tone_class = TONE_CLASS.get(status_tone, "status-info")
        status_html = (
            f'<span class="status-chip {tone_class}">'
            f"{html.escape(str(status_label))}</span>"
        )
    meta_html = (
        f'<div class="hero-meta">{html.escape(str(meta))}</div>'
        if meta
        else ""
    )
    st.markdown(
        _compact_html(f"""
        <div class="dashboard-hero">
          <div>
            <div class="hero-kicker">{html.escape(str(kicker))}</div>
            <div class="hero-title">{html.escape(str(title))}</div>
            <div class="hero-subtitle">{html.escape(str(subtitle))}</div>
            {meta_html}
          </div>
          <div class="hero-right">{status_html}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def metric_grid(items):
    cards = []
    for item in items:
        tone = item.get("tone", "neutral")
        tone_class = {
            "good": "tone-good",
            "success": "tone-good",
            "blue": "tone-blue",
            "info": "tone-blue",
            "warn": "tone-warn",
            "warning": "tone-warn",
            "danger": "tone-danger",
            "error": "tone-danger",
        }.get(tone, "")
        helper = item.get("helper", "")
        helper_html = (
            f'<div class="kpi-helper">{html.escape(str(helper))}</div>'
            if helper
            else ""
        )
        cards.append(
            _compact_html(f"""
            <div class="kpi-card {tone_class}">
              <div class="kpi-label">{html.escape(str(item["label"]))}</div>
              <div class="kpi-value">{html.escape(str(item["value"]))}</div>
              {helper_html}
            </div>
            """)
        )
    st.markdown(
        _compact_html(
            f'<div class="kpi-grid">{"".join(cards)}</div>'
        ),
        unsafe_allow_html=True,
    )


def section_header(title, *, kicker=None, note=None):
    kicker_html = (
        f'<div class="section-kicker">{html.escape(str(kicker))}</div>'
        if kicker
        else ""
    )
    note_html = (
        f'<div class="section-note">{html.escape(str(note))}</div>'
        if note
        else ""
    )
    st.markdown(
        _compact_html(f"""
        <div class="section-head">
          <div>{kicker_html}<div class="section-title">{html.escape(str(title))}</div></div>
          {note_html}
        </div>
        """),
        unsafe_allow_html=True,
    )


def diagnosis_block(title, copy, tone="neutral"):
    tone_class = {
        "good": "good",
        "success": "good",
        "warning": "warn",
        "warn": "warn",
        "danger": "danger",
        "error": "danger",
    }.get(tone, "")
    st.markdown(
        _compact_html(f"""
        <div class="diagnosis-block {tone_class}">
          <div class="diagnosis-title">{html.escape(str(title))}</div>
          <div class="diagnosis-copy">{html.escape(str(copy))}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def alert_list(alarms: pd.DataFrame, limit=6):
    if alarms.empty:
        empty_panel(
            "暂无报警事件",
            "当前没有需要展示的报警记录。",
        )
        return

    rows = []
    for _, alarm in alarms.head(limit).iterrows():
        level = str(alarm.get("level", "低"))
        level_class = {"高": "high", "中": "mid"}.get(level, "low")
        processed = str(alarm.get("status", "")) in {"已处理", "已关闭"}
        status_class = "processed" if processed else ""
        rows.append(
            _compact_html(f"""
            <div class="alert-row">
              <span class="alert-level {level_class}">{html.escape(level)}</span>
              <div class="alert-main">
                <div class="alert-title">
                  {html.escape(str(alarm.get("rule_id", "-")))} ·
                  {html.escape(str(alarm.get("alarm_type", "报警")))}
                </div>
                <div class="alert-meta">
                  {html.escape(str(alarm.get("timestamp", "")))}
                </div>
              </div>
              <span class="alert-status {status_class}">
                {html.escape(str(alarm.get("status", "未处理")))}
              </span>
            </div>
            """)
        )
    st.markdown(
        _compact_html(f'<div class="alert-list">{"".join(rows)}</div>'),
        unsafe_allow_html=True,
    )


def empty_panel(title, copy):
    st.markdown(
        _compact_html(f"""
        <div class="empty-panel">
          <div class="empty-title">{html.escape(str(title))}</div>
          <div class="empty-copy">{html.escape(str(copy))}</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def rule_cards(rules):
    state_labels = {
        "triggered": "已触发",
        "watching": "观察中",
        "normal": "正常",
    }
    cards = []
    for rule in rules:
        status = rule.get("status", "normal")
        hits = int(rule.get("hits", 0))
        window = max(1, int(rule.get("window_size", 1)))
        progress = min(100, round(hits / window * 100))
        cards.append(
            _compact_html(f"""
            <div class="rule-card {status}">
              <div class="rule-topline">
                <div class="rule-name">
                  {html.escape(str(rule.get("rule_id", "")))} ·
                  {html.escape(str(rule.get("alarm_type", "")))}
                </div>
                <span class="rule-state">
                  {state_labels.get(status, status)}
                </span>
              </div>
              <div class="rule-progress">
                <div class="rule-progress-fill" style="width:{progress}%"></div>
              </div>
              <div class="rule-meta">
                命中 {hits}/{window} · 等级
                {html.escape(str(rule.get("level", "-")))}
              </div>
            </div>
            """)
        )
    st.markdown(
        _compact_html(f'<div class="rule-grid">{"".join(cards)}</div>'),
        unsafe_allow_html=True,
    )


def sidebar_brand():
    st.markdown(
        _compact_html("""
        <div class="brand-block">
          <div class="brand-mark"><span class="brand-dot"></span>智抽云</div>
          <div class="brand-sub">智能抽油机监测与运行优化系统</div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def command_bar(device_id, location, *, condition_label=None, mode="SIMULATION"):
    """页面顶部的系统标识栏，呈现平台、井场、设备与数据来源。"""
    condition_tag = (
        f'<span class="field-tag">工况 <b>{html.escape(str(condition_label))}</b></span>'
        if condition_label
        else ""
    )
    st.markdown(
        _compact_html(f"""
        <div class="app-commandbar">
          <div class="commandbar-left">
            <div class="commandbar-emblem">
              <svg viewBox="0 0 24 24" fill="none" stroke="#5EEAD4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M12 2v20M5 7h14M7 7v4a5 5 0 0 0 10 0V7M9 21h6"/>
              </svg>
            </div>
            <div class="commandbar-sys">
              <div class="commandbar-name">智抽云 · 抽油机生产运行管控台</div>
              <div class="commandbar-sub">SCADA-style operations console · 课程演示环境</div>
            </div>
          </div>
          <div class="commandbar-right">
            <span class="field-tag">井场 <b>{html.escape(str(location))}</b></span>
            <span class="field-tag">设备 <b>{html.escape(str(device_id))}</b></span>
            {condition_tag}
            <span class="field-tag sim">{html.escape(str(mode))}</span>
            <span class="live-indicator">在线</span>
          </div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def condition_banner(code, title, copy, *, tone="info"):
    """工况/诊断摘要条，用语义色标注当前运行状态。"""
    tone_class = {"danger": "danger", "warning": "warn", "warn": "warn"}.get(tone, "")
    st.markdown(
        _compact_html(f"""
        <div class="state-banner {tone_class}">
          <div class="state-banner-code">{html.escape(str(code))}</div>
          <div>
            <div class="state-banner-title">{html.escape(str(title))}</div>
            <div class="state-banner-copy">{html.escape(str(copy))}</div>
          </div>
        </div>
        """),
        unsafe_allow_html=True,
    )


def _effect_class(value, *, lower_is_good):
    if abs(value) < 0.05:
        return "flat"
    good = value <= 0 if lower_is_good else value >= 0
    return "down-good" if good else "up-bad"


def plan_cards(plans, *, key_prefix="plan"):
    """渲染一键优化方案卡片，返回被点击方案的 plan_id（若有）。"""
    grids = st.columns(len(plans), gap="medium")
    clicked_id = None
    for column, plan in zip(grids, plans):
        with column:
            expected = plan["expected"]
            tone = {
                "good": "tone-good",
                "blue": "tone-blue",
                "warn": "tone-warn",
                "danger": "tone-danger",
            }.get(plan.get("tone"), "")
            badge_tone = tone or "tone-blue"
            rec_word = " · 推荐" if plan.get("recommended") else ""
            power_pct = float(expected["power_change_pct"])
            prod_pct = float(expected["production_change_pct"])
            saving = float(expected["daily_saving_kwh"])
            st.markdown(
                _compact_html(f"""
                <div class="plan-card {tone} {'recommended' if plan.get('recommended') else ''}">
                  <div class="plan-topline">
                    <div class="plan-name">{html.escape(str(plan['name']))}</div>
                    <span class="plan-badge {badge_tone}">{html.escape(str(plan['badge']))}{html.escape(rec_word)}</span>
                  </div>
                  <div class="plan-target">
                    目标冲次 <b>{plan['target_stroke']:.1f}</b> 次/min · 评分 {expected['score']:.1f}
                  </div>
                  <div class="plan-effects">
                    <div class="effect-row">
                      <span>预计功率</span>
                      <b>{expected['optimized_power']:.2f} kW</b>
                      <em class="{_effect_class(power_pct, lower_is_good=True)}">{power_pct:+.1f}%</em>
                    </div>
                    <div class="effect-row">
                      <span>日耗电节省</span>
                      <b>{saving:+.2f} kWh</b>
                      <em class="{_effect_class(saving, lower_is_good=False)}">{'节能' if saving >= 0 else '增耗'}</em>
                    </div>
                    <div class="effect-row">
                      <span>模拟产量</span>
                      <b>{expected['optimized_production']:.2f} m³/d</b>
                      <em class="{_effect_class(prod_pct, lower_is_good=False)}">{prod_pct:+.1f}%</em>
                    </div>
                  </div>
                  <div class="plan-reason">{html.escape(str(plan['reason']))}</div>
                  <div class="plan-meta">目标导向 {html.escape(str(plan['objective']))} · 风险 {html.escape(str(plan['risk']))}</div>
                </div>
                """),
                unsafe_allow_html=True,
            )
            if st.button(
                "一键应用此方案",
                key=f"{key_prefix}_{plan['plan_id']}",
                type="primary" if plan.get("recommended") else "secondary",
                icon=":material/bolt:",
                width="stretch",
            ):
                clicked_id = str(plan["plan_id"])
    return clicked_id

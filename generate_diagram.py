"""Generate architecture diagram for the health agent graph."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(20, 28))
ax.set_xlim(0, 20)
ax.set_ylim(0, 28)
ax.axis("off")
fig.patch.set_facecolor("#0d1117")

# --- Colours ---
C_SUP = "#58a6ff"
C_SPEC = "#3fb950"
C_TOOL = "#f0883e"
C_DIRECT = "#d2a8ff"
C_TEXT = "#e6edf3"
C_SUB = "#8b949e"
C_BORDER = "#30363d"
C_BG = "#161b22"


def box(x, y, w, h, color, label, sub=None, fs=14):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15,rounding_size=0.3",
                        facecolor=color, edgecolor="white", lw=1.8, alpha=0.92, zorder=3)
    ax.add_patch(p)
    ty = y + h/2 + (0.15 if sub else 0)
    ax.text(x + w/2, ty, label, ha="center", va="center", fontsize=fs,
            fontweight="bold", color="white", zorder=4)
    if sub:
        ax.text(x + w/2, y + h/2 - 0.25, sub, ha="center", va="center",
                fontsize=fs - 4, color="#ffffffbb", zorder=4, style="italic")


def bg(x, y, w, h):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.4",
                        facecolor=C_BG, edgecolor=C_BORDER, lw=1.2, alpha=0.7, zorder=1)
    ax.add_patch(p)


def tools(x, y, items, fs=12, lh=0.48):
    for i, t in enumerate(items):
        ty = y - i * lh
        ax.plot(x - 0.2, ty, "s", color=C_TOOL, markersize=7, zorder=4)
        ax.text(x, ty, t, ha="left", va="center", fontsize=fs, color=C_TEXT,
                zorder=4, family="monospace")


def arrow(x1, y1, x2, y2, color=C_SUP, lw=1.8):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=lw), zorder=2)


# ==================== LAYOUT ====================

# Title
ax.text(10, 27.3, "Health Coach Agent  -  Architecture", ha="center",
        fontsize=22, fontweight="bold", color=C_TEXT, zorder=5)
ax.text(10, 26.85, "Supervisor + Specialist Subagents  |  LangGraph  |  gpt-4o-mini",
        ha="center", fontsize=12, color=C_SUB, zorder=5)

# User
box(7.5, 25.6, 5, 0.9, "#484f58", "User Query", fs=15)
arrow(10, 25.6, 10, 25.0, lw=2.5)

# Supervisor
box(5, 23.8, 10, 1.1, C_SUP, "Supervisor  (health_coach)",
    "gpt-4o-mini  |  delegates to specialists or direct tools", fs=16)

# Direct tools (right of supervisor)
bg(15.5, 23.5, 4.2, 3.2)
ax.text(17.6, 26.4, "DIRECT TOOLS", ha="center", fontsize=11,
        fontweight="bold", color=C_SUB, zorder=2)
box(15.8, 25.5, 3.6, 0.7, C_DIRECT, "python_interpreter",
    "PythonREPL - charts & analysis", fs=11)
box(15.8, 24.4, 3.6, 0.7, C_DIRECT, "get_protein_recommendation",
    "Auto-fetches weight", fs=10)
arrow(15, 24.35, 15.8, 25.8, color=C_DIRECT, lw=1.5)
arrow(15, 24.35, 15.8, 24.7, color=C_DIRECT, lw=1.5)

# --- Specialists (stacked in 2 columns, 3 rows) ---

specs = [
    ("health_data", "Data retrieval specialist", [
        "get_recovery_data", "get_sleep_data", "get_workout_data",
        "get_running_workouts", "get_tennis_workouts", "get_weight_data",
        "get_weight_stats", "get_heart_rate_data", "get_withings_summary",
        "get_recovery_trends", "get_protein_recommendation",
    ]),
    ("analytics", "ML & statistics specialist", [
        "analyze_recovery_factors", "analyze_correlations",
        "predict_recovery", "predict_sleep_performance",
        "get_weekly_insights", "detect_patterns",
    ]),
    ("environment", "Weather, transport, tides", [
        "get_weather", "get_air_quality", "get_weather_forecast",
        "get_transport_status", "get_tide_times", "get_perfect_walk_times",
    ]),
    ("exercise", "Training plans & programmes", [
        "get_weight_data", "get_workout_data", "get_recovery_data",
    ]),
    ("behaviour_change", "COM-B coaching & habits", [
        "get_recovery_data", "get_weight_data", "get_workout_data",
    ]),
    ("nutrition", "Dietary recommendations", [
        "get_protein_recommendation", "get_weight_data", "get_workout_data",
    ]),
]

# 2 columns, 3 rows
col_x = [0.3, 10.3]
row_y = [16.5, 9.5, 3.5]  # top of each row (more space for top row)
col_w = 9.4
lh = 0.48  # line height for tools

for idx, (name, subtitle, tool_list) in enumerate(specs):
    col = idx % 2
    row = idx // 2
    bx = col_x[col]
    n = len(tool_list)
    bh = n * lh + 2.3  # extra height to prevent clipping
    by = row_y[row] + (6.5 - bh)  # align tops with added slack

    bg(bx, by, col_w, bh)
    box(bx + 0.3, by + bh - 1.2, col_w - 0.6, 1.0, C_SPEC, name, subtitle, fs=14)
    tools(bx + 0.8, by + bh - 1.7, tool_list, fs=11, lh=lh)

    # Arrow from supervisor
    sx = bx + col_w / 2
    arrow(10, 23.8, sx, by + bh, color=C_SPEC, lw=1.3)

# Legend
ly = 0.6
items = [
    (C_SUP, "Supervisor Agent"), (C_SPEC, "Specialist Subagent (wrapped as tool)"),
    (C_DIRECT, "Direct Supervisor Tool"), (C_TOOL, "Domain Tool (within specialist)"),
]
for i, (c, lab) in enumerate(items):
    lx = 0.8 + i * 5.0
    ax.plot(lx, ly, "s", color=c, markersize=10, zorder=4)
    ax.text(lx + 0.35, ly, lab, ha="left", va="center", fontsize=11, color=C_TEXT, zorder=4)

plt.savefig("/Users/asiflaldin/Documents/Projects/whoop-data/agent_architecture.png",
            dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print("Saved: agent_architecture.png")

"""figstyle 예시: 유변학 + 입도분포 그림, 시리즈 그라데이션 그림"""
import numpy as np
from matplotlib.lines import Line2D

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import figstyle as fs  # noqa: E402

fs.use()
rng = np.random.default_rng(3)

# ---------- 그림 1: 유변학 + 입도 분포 ----------
fig, (ax, axh) = fs.figure(ncols=2)

rate = np.logspace(0, 2, 11)
stress = {"Sample A": 12 * rate**0.21, "Sample B": 6.2 * rate**0.2 * (1 + 0.05 * np.log(rate))}
for (_name, s), m in zip(stress.items(), fs.MARKERS):
    ax.plot(rate, s, "-", marker=m, color=fs.BLACK, mfc=fs.BLACK)
ax.set(xscale="log", yscale="log", xlim=(0.8, 200), ylim=(0.1, 100),
       xlabel="Shear rate (1/s)", ylabel="Stress (Pa)")

ax2 = fs.twin_y(ax, color=fs.PINK)
for (_name, s), m in zip(stress.items(), fs.MARKERS):
    ax2.plot(rate, s / rate, "-", marker=m, color=fs.BLACK, mfc=fs.PINK, mec=fs.PINK)
ax2.set(yscale="log", ylim=(0.1, 100), ylabel="Viscosity (Pa·s)")
ax2.yaxis.label.set_rotation(270)
ax2.yaxis.labelpad = 22

# 범례: 모양만 구분하는 빈 마커 (Origin 스타일)
handles = [Line2D([], [], color=fs.BLACK, marker=m, mfc="white", label=n)
           for n, m in zip(stress, fs.MARKERS)]
ax.legend(handles=handles, loc="upper left")

size = rng.normal(192, 38, 180)
bins = np.arange(90, 335, 20)
axh.hist(size, bins=bins, color=fs.BAR_GRAY, edgecolor="white", linewidth=1)
x = np.linspace(90, 330, 300)
axh.plot(x, len(size) * 20 / (38 * np.sqrt(2 * np.pi)) * np.exp(-(x - 192) ** 2 / (2 * 38**2)),
         color=fs.PINK)
axh.set(xlim=(90, 330), ylim=(0, 50), xlabel="Size distribution (nm)", ylabel="Counts")

fs.save(fig, "example_origin")

# ---------- 그림 2: 시리즈 결과 → 그라데이션 ----------
fig, axes = fs.figure(ncols=2)
conc = [0.1, 0.25, 0.5, 1.0, 2.0]
for c, col in zip(conc, fs.gradient(len(conc), fs.PINK)):
    axes[0].plot(rate, 3 * c * rate**(-0.6 + 0.1 * c), "o-", color=col, label=f"{c} wt%")
axes[0].set(xscale="log", yscale="log", xlabel="Shear rate (1/s)", ylabel="Viscosity (Pa·s)")
axes[0].legend(loc="lower left", )   # 일부러 겹치는 위치 → 저장 때 자동 수정

t = np.linspace(0, 60, 61)
for T, col in zip([25, 40, 55, 70], fs.gradient(4, fs.BLUE)):
    axes[1].plot(t, 100 * (1 - np.exp(-t * T / 900)), color=col, lw=2, label=f"{T} °C")
axes[1].set(xlim=(0, 60), ylim=(0, 100), xlabel="Time (min)", ylabel="Conversion (%)")
axes[1].legend(loc="lower right", )

fs.save(fig, "example_gradient")

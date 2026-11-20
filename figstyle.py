"""
figstyle.py - Origin 느낌의 논문 그림 스타일을 어디서나 똑같이 맞추는 모듈

기본 규칙
    Arial 18 pt (범례 14 pt) · 축/눈금 굵기 1 pt · 바깥 눈금 8 pt (보조 4 pt)
    주눈금 사이 보조눈금 1개 · 데이터 선 1 pt · 마커 8 pt · 에러바 캡 4 pt
    그림 높이 10 cm, 그래프 영역은 기본 정사각형, 테두리는 기본 L자
    로그축 눈금은 0.1, 1, 10, 100 처럼 일반 숫자로 표시
    색: 회색 → 핑크 → 초록 → 파랑 / 시리즈 결과는 gradient()로 그라데이션

사용법
    import figstyle
    figstyle.use()
    fig, ax = figstyle.figure()               # 높이 10 cm, 정사각형 그래프, L자 테두리
    fig, axes = figstyle.figure(ncols=2)      # 패널 여러 개 (폭은 자동)
    fig, ax = figstyle.figure(square=False, width_cm=16)   # 가로로 긴 그림
    ax.plot(x, y, "s-", label="Sample A")
    ax2 = figstyle.twin_y(ax, color=figstyle.PINK)   # 오른쪽 축(색 입힘)
    for c, y in zip(figstyle.gradient(5), ys): ax.plot(x, y, color=c)
    figstyle.save(fig, "fig1")                # figures/fig1.pdf + .png + .svg
                                              # 저장할 때 범례가 데이터와 겹치면 자동으로 옮김

설정을 바꾸려면 아래 대문자 상수만 고치면 모든 그림에 반영돼요.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from cycler import cycler
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter

# ---------------- 색 ----------------
GRAY = "#7A7A7A"
PINK = "#F0507A"
GREEN = "#2BA36B"
BLUE = "#2F6FD0"
BLACK = "#000000"
BAR_GRAY = "#BEBEBE"          # 히스토그램/막대용 연회색
COLORS = [GRAY, PINK, GREEN, BLUE]
MARKERS = ["s", "D", "o", "^", "v", "p"]   # Origin 기본 순서와 비슷하게

# ---------------- 크기 ----------------
FONT = ["Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"]
FONT_SIZE = 18
LEGEND_SIZE = 14
LINE_W = 1.0        # 축, 눈금 굵기 (pt)
MAJOR_LEN = 8       # 주눈금 길이 (pt)
MINOR_LEN = 4       # 보조눈금 길이 (pt)
HEIGHT_CM = 10      # 그림 전체 높이 (cm) - 저장 파일도 정확히 이 높이
WIDTH_PER_PANEL = 1.15  # 패널당 폭 = 높이 × 이 값 (축 라벨 자리 포함)

STYLE = {
    "font.family": "sans-serif",
    "font.sans-serif": FONT,
    "font.size": FONT_SIZE,
    "axes.labelsize": FONT_SIZE,
    "axes.titlesize": FONT_SIZE,
    "xtick.labelsize": FONT_SIZE,
    "ytick.labelsize": FONT_SIZE,
    "legend.fontsize": LEGEND_SIZE,
    # 수식($...$)도 Arial로
    "mathtext.fontset": "custom",
    "mathtext.rm": "Arial",
    "mathtext.it": "Arial:italic",
    "mathtext.bf": "Arial:bold",
    "axes.unicode_minus": False,
    # 축
    "axes.linewidth": LINE_W,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.prop_cycle": cycler(color=COLORS),
    "axes.labelpad": 8,
    # 눈금: 바깥, 1 pt, 8 pt, 보조눈금 1개
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": LINE_W,
    "ytick.major.width": LINE_W,
    "xtick.minor.width": LINE_W,
    "ytick.minor.width": LINE_W,
    "xtick.major.size": MAJOR_LEN,
    "ytick.major.size": MAJOR_LEN,
    "xtick.minor.size": MINOR_LEN,
    "ytick.minor.size": MINOR_LEN,
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "xtick.minor.ndivs": 2,       # 주눈금 사이 보조눈금 1개
    "ytick.minor.ndivs": 2,
    "xtick.major.pad": 6,
    "ytick.major.pad": 6,
    # 데이터
    "lines.linewidth": 1.0,
    "lines.markersize": 8,
    "lines.markeredgewidth": 1.0,
    "errorbar.capsize": 4,
    "patch.linewidth": 1.0,
    # 범례
    "legend.frameon": False,
    "legend.handlelength": 1.8,
    "legend.borderaxespad": 0.3,
    # 저장
    "figure.dpi": 100,
    "savefig.dpi": 600,
    "savefig.bbox": None,   # 여백을 잘라내지 않아야 높이 10 cm가 그대로 유지됨
    "pdf.fonttype": 42,     # PDF/일러스트레이터에서 글자 편집 가능
    "ps.fonttype": 42,
    "svg.fonttype": "none",  # SVG 글자를 텍스트로 유지 (Origin/PPT에서 편집)
}


def use(korean=False):
    """스타일 적용. 한글 라벨을 쓰면 korean=True."""
    mpl.rcParams.update(mpl.rcParamsDefault)
    mpl.rcParams.update(STYLE)
    if korean:
        import platform
        k = {"Windows": "Malgun Gothic", "Darwin": "AppleGothic"}.get(platform.system(), "NanumGothic")
        mpl.rcParams["font.sans-serif"] = [FONT[0], k] + FONT[1:]


def figure(nrows=1, ncols=1, height_cm=HEIGHT_CM, width_cm=None,
           square=True, box=False, **kwargs):
    """그림 만들기. 전체 높이 10 cm 고정, 폭은 패널 수에 맞춰 자동.

    square=True  : 그래프 영역(축 안쪽)을 정사각형으로
    width_cm     : 폭을 직접 정하고 싶을 때 (cm)
    box=True     : 네 면 테두리 (기본은 L자)
    """
    h = height_cm / 2.54
    w = width_cm / 2.54 if width_cm else h / nrows * WIDTH_PER_PANEL * ncols
    kwargs.setdefault("layout", "constrained")
    fig, axes = plt.subplots(nrows, ncols, figsize=(w, h), **kwargs)
    for ax in np.atleast_1d(axes).ravel():
        if square:
            ax.set_box_aspect(1)
        if box:
            set_box(ax)
    return fig, axes


def set_box(ax):
    """Origin 기본처럼 네 면 테두리 (위/오른쪽은 눈금 없이 선만)."""
    for s in ("top", "right"):
        ax.spines[s].set_visible(True)


def twin_y(ax, color=PINK):
    """오른쪽 y축을 만들고 축선·눈금·글자를 같은 색으로 맞춤."""
    ax2 = ax.twinx()
    if ax.get_box_aspect() is not None:      # 정사각형 설정을 같이 맞춰야 데이터가 안 어긋남
        ax2.set_box_aspect(ax.get_box_aspect())
    ax2.spines["right"].set_visible(True)
    ax2.spines["right"].set_color(color)
    ax2.tick_params(axis="y", which="both", colors=color)
    ax2.yaxis.label.set_color(color)
    return ax2


def gradient(n, color=PINK, light=0.75, dark=0.35):
    """시리즈 결과용 그라데이션 n개 (연한색 → 진한색). color는 기준색."""
    base = np.array(to_rgb(color))
    lo = base + (1 - base) * light          # 흰색 쪽으로
    hi = base * (1 - dark)                  # 검은색 쪽으로
    cmap = LinearSegmentedColormap.from_list("g", [lo, base, hi])
    return [cmap(t) for t in np.linspace(0, 1, n)] if n > 1 else [color]


def _plain(v, _pos=None):
    """로그축 라벨: 0.1, 1, 10, 100 (10^n 대신)."""
    if v <= 0:
        return ""
    s = f"{v:.10g}"
    return s if "e" not in s else f"$10^{{{int(np.log10(v))}}}$"


def tidy(fig):
    """그림 전체 마무리: 로그축 라벨을 일반 숫자로, 보조눈금 정리."""
    for ax in fig.axes:
        for axis, scale in ((ax.xaxis, ax.get_xscale()), (ax.yaxis, ax.get_yscale())):
            if scale == "log":
                axis.set_major_locator(LogLocator(base=10))
                axis.set_major_formatter(FuncFormatter(_plain))
                axis.set_minor_locator(LogLocator(base=10, subs=np.arange(2, 10)))
                axis.set_minor_formatter(NullFormatter())


# ---------------- 범례 자동 배치 ----------------
_LOCS = ["upper left", "upper right", "lower left", "lower right",
         "upper center", "lower center", "center left", "center right"]


def _data_points(ax):
    """ax와 같은 자리에 겹친 축(twin)까지 포함한 데이터 좌표(화면 픽셀)."""
    pts = []
    siblings = [a for a in ax.figure.axes
                if a.get_position().bounds == ax.get_position().bounds]
    for a in siblings:
        for line in a.get_lines():
            xy = line.get_xydata()
            if len(xy) == 0:
                continue
            d = a.transData.transform(xy)
            d = d[np.isfinite(d).all(axis=1)]
            if line.get_linestyle() not in ("None", "", " ") and len(d) > 1:
                # 선 위의 점을 촘촘히 채워서 '선이 지나가는 곳'도 겹침으로 판단
                seg = []
                for p0, p1 in zip(d[:-1], d[1:]):
                    n = max(2, int(np.hypot(*(p1 - p0)) / 3))
                    seg.append(np.linspace(p0, p1, n))
                d = np.vstack(seg)
            pts.append(d)
        for patch in a.patches:
            bb = patch.get_window_extent()
            if bb.width > 0 and bb.height > 0:
                gx, gy = np.meshgrid(np.linspace(bb.x0, bb.x1, 6),
                                     np.linspace(bb.y0, bb.y1, 6))
                pts.append(np.c_[gx.ravel(), gy.ravel()])
        for coll in a.collections:
            try:
                for path in coll.get_paths():
                    v = path.vertices
                    if len(v):
                        pts.append(coll.get_transform().transform(v))
                off = coll.get_offsets()
                if len(off):
                    pts.append(coll.get_offset_transform().transform(off))
            except Exception:
                pass
    return np.vstack(pts) if pts else np.empty((0, 2))


def _overlaps(leg, ax, renderer, pad=4):
    """데이터와 겹치거나, 범례가 그래프 영역 밖으로 삐져나가면 True."""
    raw = leg.get_window_extent(renderer)
    bb = raw.padded(pad)
    frame = ax.get_window_extent(renderer)
    if raw.x0 < frame.x0 - 1 or raw.x1 > frame.x1 + 1 or raw.y0 < frame.y0 - 1 or raw.y1 > frame.y1 + 1:
        return True
    pts = _data_points(ax)
    if not len(pts):
        return False
    inside = ((pts[:, 0] >= bb.x0) & (pts[:, 0] <= bb.x1) &
              (pts[:, 1] >= bb.y0) & (pts[:, 1] <= bb.y1))
    return bool(inside.any())


def _grow_top(ax):
    """위쪽 여백을 눈금 한 칸만큼 늘림 (축 끝이 항상 눈금 숫자에 딱 맞도록)."""
    for a in [x for x in ax.figure.axes
              if x.get_position().bounds == ax.get_position().bounds]:
        lo, hi = a.get_ylim()
        if a.get_yscale() == "log":
            a.set_ylim(lo, 10 ** np.ceil(np.log10(hi) + 1e-9))   # 다음 10의 거듭제곱
        else:
            ticks = a.get_yticks()
            step = ticks[1] - ticks[0] if len(ticks) > 1 else (hi - lo) * 0.2
            a.set_ylim(lo, (np.floor(hi / step + 1e-9) + 1) * step)


def _rebuild(ax, old, ncols, loc):
    """같은 항목·글자 크기로 범례를 다시 만듦 (열 개수, 위치만 바꿈)."""
    handles = old.legend_handles
    labels = [t.get_text() for t in old.get_texts()]
    size = old.get_texts()[0].get_fontsize() if labels else LEGEND_SIZE
    old.remove()
    compact = dict(handlelength=1.2, handletextpad=0.4, columnspacing=0.8) if ncols > 1 else {}
    return ax.legend(handles=handles, labels=labels, loc=loc, ncols=ncols,
                     fontsize=size, **compact)


def fix_legends(fig, verbose=True):
    """범례가 데이터와 겹치면 순서대로 시도:
    1) 다른 위치로 이동  2) 가로(여러 열) 배치로 바꿔 이동
    3) 위쪽 여백을 눈금 한 칸씩 늘림  4) 그래프 오른쪽 밖으로
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    for ax in fig.axes:
        leg = ax.get_legend()
        if leg is None or not _overlaps(leg, ax, renderer):
            continue
        n = len(leg.get_texts())
        col_options = [leg._ncols] + [c for c in range(2, n + 1) if c != leg._ncols]
        found = None
        for grow in range(4):          # 0: 여백 그대로, 1~3: 위 여백 늘리며
            if grow:
                _grow_top(ax)
            for ncols in col_options:
                for loc in _LOCS:
                    leg = _rebuild(ax, leg, ncols, loc)
                    fig.canvas.draw()
                    if not _overlaps(leg, ax, renderer):
                        found = (loc, ncols, grow)
                        break
                if found:
                    break
            if found:
                break
        if found and verbose:
            loc, ncols, grow = found
            how = f"'{loc}'" + (f", {ncols}열 가로 배치" if ncols > 1 else "")
            print(f"범례를 {how}로 옮겼어요" + (" (위쪽 여백도 늘림)" if grow else ""))
        if not found:
            twin = any(a is not ax and a.get_position().bounds == ax.get_position().bounds
                       for a in fig.axes)
            leg = _rebuild(ax, leg, 1, "upper left")
            leg.set_bbox_to_anchor((1.25 if twin else 1.02, 1), transform=ax.transAxes)
            if verbose:
                print("빈 자리가 없어서 범례를 그래프 오른쪽 밖으로 뺐어요")


def save(fig, name, folder="figures", formats=("pdf", "png", "svg")):
    """figures/ 에 PDF(논문), PNG(미리보기), SVG(Origin/PPT 편집용) 저장."""
    import warnings
    tidy(fig)
    with warnings.catch_warnings():   # 범례 자리를 시험하는 동안 나오는 레이아웃 경고만 숨김
        warnings.filterwarnings("ignore", message="constrained_layout not applied")
        fix_legends(fig)
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in formats:
        p = out / f"{name}.{ext}"
        fig.savefig(p)
        paths.append(p)
    print("저장:", ", ".join(str(p) for p in paths))
    return paths

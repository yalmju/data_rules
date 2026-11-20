#!/usr/bin/env python3
"""
devlog.py - 작업 세션 기록 + git 점검 도우미

사용법 (프로젝트 폴더에서):
    python devlog.py start   # 작업 시작: 컴퓨터 기록, 최신 코드 받기, 환경 점검
    python devlog.py end     # 작업 끝: 저장(commit) + 올리기(push) + 기록
    python devlog.py log     # 최근 작업 기록 보기

기록은 .devlog/<컴퓨터이름>.jsonl 에 컴퓨터별로 따로 저장돼요.
컴퓨터마다 파일이 달라서, 여러 컴퓨터에서 써도 기록끼리 충돌하지 않아요.
"""

import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:  # Windows 콘솔에서 한글이 깨지지 않도록
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

LOG_DIR = Path(".devlog")
GITIGNORE_MUST_HAVE = [".env", ".venv/", "venv/", "__pycache__/"]


# ---------- 공통 ----------

def git(*args):
    # core.quotepath=false: 한글 파일 이름이 "\354\240..."처럼 깨지지 않게
    return subprocess.run(["git", "-c", "core.quotepath=false", *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def say(icon, msg):
    print(f"{icon} {msg}")


def machine():
    """기록에 남길 컴퓨터 이름. 공개 저장소라면 환경변수 DEVLOG_NAME에 별명을 정해두세요
    (예: 연구실PC, 집노트북). 없으면 실제 컴퓨터 이름을 써요."""
    return os.environ.get("DEVLOG_NAME") or platform.node() or "unknown"


def now():
    return datetime.now().isoformat(timespec="seconds")


def in_venv():
    return sys.prefix != getattr(sys, "base_prefix", sys.prefix)


def env_info():
    return {"machine": machine(), "python": platform.python_version()}


def write_log(entry):
    LOG_DIR.mkdir(exist_ok=True)
    path = LOG_DIR / f"{re.sub(r'[^A-Za-z0-9._-]', '_', machine())}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_logs():
    entries = []
    if LOG_DIR.exists():
        for p in LOG_DIR.glob("*.jsonl"):
            for line in p.read_text(encoding="utf-8").splitlines():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return sorted(entries, key=lambda e: e.get("time", ""))


def ensure_repo():
    if git("rev-parse", "--is-inside-work-tree").returncode != 0:
        say("❌", "여기는 git 저장소가 아니에요. 프로젝트 폴더에서 실행해 주세요.")
        sys.exit(1)
    root = git("rev-parse", "--show-toplevel").stdout.strip()
    os.chdir(root)


def branch():
    return git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def has_upstream():
    return git("rev-parse", "--abbrev-ref", "@{u}").returncode == 0


def dirty_files():
    out = git("status", "--porcelain").stdout
    files = [l[3:] for l in out.splitlines() if l.strip()]
    return [f for f in files if not f.startswith(".devlog")]  # 기록 파일은 제외


def ahead_behind():
    r = git("rev-list", "--left-right", "--count", "HEAD...@{u}")
    if r.returncode != 0:
        return 0, 0
    a, b = r.stdout.split()
    return int(a), int(b)


def fetch():
    r = git("fetch", "--quiet")
    if r.returncode != 0:
        err = r.stderr.lower()
        if "authentication" in err or "permission denied" in err or "could not read username" in err:
            say("🔑", "GitHub 로그인이 안 돼 있어요. 이 컴퓨터에 토큰이나 SSH 키 설정이 필요해요.")
        elif "could not resolve host" in err:
            say("🌐", "인터넷 연결을 확인해 주세요.")
        else:
            say("⚠️", f"GitHub에서 최신 정보를 못 받았어요: {r.stderr.strip()}")
        return False
    return True


# ---------- 점검 ----------

def check_gitignore():
    gi = Path(".gitignore")
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    lines = {l.strip() for l in text.splitlines()}
    missing = [p for p in GITIGNORE_MUST_HAVE
               if p not in lines and p.rstrip("/") not in lines]
    if missing:
        with gi.open("a", encoding="utf-8") as f:
            if text and not text.endswith("\n"):
                f.write("\n")
            f.write("\n".join(missing) + "\n")
        say("🛡️", f".gitignore에 추가했어요 (GitHub에 올라가면 안 되는 것들): {', '.join(missing)}")


def check_requirements():
    req = Path("requirements.txt")
    if not req.exists():
        return
    try:
        from importlib.metadata import distributions
        installed = {re.sub(r"[-_.]+", "-", d.metadata["Name"]).lower()
                     for d in distributions() if d.metadata["Name"]}
    except Exception:
        return
    missing = []
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if not line or line.startswith("-"):
            continue
        name = re.split(r"[<>=!~\[; ]", line, maxsplit=1)[0]
        if re.sub(r"[-_.]+", "-", name).lower() not in installed:
            missing.append(name)
    if missing:
        say("📦", f"이 컴퓨터에 안 깔린 패키지가 있어요: {', '.join(missing)}")
        print("     → 설치: pip install -r requirements.txt")
    else:
        say("📦", "requirements.txt 패키지가 모두 설치돼 있어요.")


def show_last_session():
    logs = read_logs()
    if not logs:
        say("📝", "첫 기록이에요.")
        return
    last = logs[-1]
    when = last["time"].replace("T", " ")
    kind = "시작" if last["event"] == "start" else "종료"
    say("📝", f"마지막 기록: {when} · {last['machine']} 에서 작업 {kind}")
    if last["event"] == "start" and last["machine"] != machine():
        say("⚠️", f"{last['machine']} 에서 작업을 '끝'으로 기록하지 않았어요. "
                  "그 컴퓨터에 push 안 한 작업이 남아 있을 수 있어요.")


# ---------- 공개 저장소 업로드 전 검사 ----------

SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9_-]{20,}", "OpenAI/Anthropic 계열 API 키"),
    (r"ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}", "GitHub 토큰"),
    (r"AKIA[0-9A-Z]{16}", "AWS 키"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API 키"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "개인 키"),
    (r"(?i)(api[_-]?key|secret|password|passwd|token)\s*[=:]\s*['\"][^'\"\s]{8,}['\"]", "코드에 직접 적은 비밀번호/키"),
]
SECRET_FILES = {".env", "id_rsa", "id_ed25519", "credentials.json", "token.json", "secrets.json"}
DATA_EXT = {".csv", ".xlsx", ".xls", ".opju", ".opj", ".mat", ".h5", ".hdf5", ".npy", ".npz",
            ".tif", ".tiff", ".raw", ".spe", ".dat"}
USER_PATH = r"[A-Za-z]:\\Users\\[^\\\s'\"]+|/Users/[^/\s'\"]+|/home/[^/\s'\"]+"


def check_public(files):
    """올라갈 파일들을 검사. 막아야 할 문제가 있으면 True."""
    block, warn = [], []
    for f in files:
        p = Path(f)
        if not p.is_file():
            continue
        if p.name in SECRET_FILES or (p.name.startswith(".env") and
                                      p.name not in (".env.example", ".env.sample", ".env.template")):
            block.append(f"{f}: 비밀 정보 파일이에요")
            continue
        size = p.stat().st_size
        if size > 50 * 1024 * 1024:
            block.append(f"{f}: {size // 2**20} MB (GitHub는 100 MB 넘으면 거부, 50 MB부터 경고)")
        if p.suffix.lower() in DATA_EXT:
            warn.append(f"{f}: 데이터 파일이에요. 아직 발표 안 한 연구 데이터라면 올리지 마세요")
        if size > 2 * 1024 * 1024:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pat, what in SECRET_PATTERNS:
            if re.search(pat, text):
                block.append(f"{f}: {what}로 보이는 내용이 있어요")
                break
        m = re.search(USER_PATH, text)
        if m and p.suffix in {".py", ".ipynb", ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".cfg"}:
            warn.append(f"{f}: 내 컴퓨터 경로가 들어 있어요 ({m.group(0)}) → 다른 컴퓨터에서 안 돌고, 사용자 이름도 공개돼요")
    for w in warn:
        say("⚠️", w)
    for b in block:
        say("🚫", b)
    if block:
        print("     → 위 파일을 .gitignore에 넣거나 내용을 지운 뒤 다시 실행하세요. 이번엔 올리지 않을게요.")
        return True
    if any("데이터 파일" in w for w in warn):
        try:
            ans = input("공개 저장소에 데이터 파일도 올릴까요? (y/N): ").strip().lower()
        except EOFError:
            ans = ""
        if ans != "y":
            print("     → 이번엔 올리지 않을게요. 계속 안 올릴 파일은 .gitignore에 넣어 두세요.")
            return True
    return False


# ---------- 명령 ----------

def cmd_start():
    ensure_repo()
    info = env_info()
    print(f"\n=== 작업 시작 · {info['machine']} ({platform.system()}, Python {info['python']}) ===\n")
    if not in_venv():
        say("🐍", "가상환경 밖에서 실행 중이에요. PyCharm 인터프리터 설정을 확인해 보세요.")

    show_last_session()
    check_gitignore()

    if has_upstream():
        if fetch():
            dirty = dirty_files()
            ahead, behind = ahead_behind()
            if ahead and behind:
                say("🔀", f"이력이 갈라졌어요 (내 쪽 {ahead}개, GitHub 쪽 {behind}개). 자동으로 건드리지 않을게요.")
                print("     → 해결: git pull --rebase  (충돌 나면 Claude에게 메시지를 보여주세요)")
            elif behind and dirty:
                say("✋", f"GitHub에 새 커밋 {behind}개가 있는데, 저장 안 한 수정도 있어요.")
                print("     → 먼저 저장: git stash  →  git pull  →  git stash pop")
            elif behind:
                r = git("pull", "--ff-only")
                say("⬇️" if r.returncode == 0 else "❌",
                    f"최신 코드 {behind}개 커밋을 받았어요." if r.returncode == 0
                    else f"pull 실패: {r.stderr.strip()}")
            else:
                say("✅", "GitHub와 최신 상태가 같아요." + (f" (아직 안 올린 커밋 {ahead}개)" if ahead else ""))
            if dirty and not behind:
                say("✏️", f"저장 안 한 파일 {len(dirty)}개가 있어요.")
    else:
        say("ℹ️", "GitHub 저장소와 연결된 브랜치가 아니에요. (git push -u origin <브랜치>로 연결)")

    check_requirements()
    write_log({"event": "start", "time": now(), **info, "branch": branch()})
    print("\n좋아요, 작업 시작하세요! 끝나면: python devlog.py end\n")


def cmd_end():
    ensure_repo()
    info = env_info()
    print(f"\n=== 작업 종료 · {info['machine']} ===\n")
    check_gitignore()

    dirty = dirty_files()
    entry = {"event": "end", "time": now(), **info, "branch": branch()}
    if dirty:
        say("✏️", f"수정된 파일 {len(dirty)}개:")
        for f in dirty[:15]:
            print(f"     - {f}")
        if len(dirty) > 15:
            print(f"     ... 외 {len(dirty) - 15}개")
    default_msg = f"작업 저장 ({info['machine']}, {datetime.now():%m/%d %H:%M})"
    try:
        msg = input(f"\n커밋 메시지 (엔터 = '{default_msg}'): ").strip() or default_msg
    except EOFError:
        msg = default_msg

    git("add", "-A")
    staged = git("diff", "--cached", "--name-only").stdout.split("\n")
    if check_public([f for f in staged if f]):
        git("reset", "-q")              # 올리려던 목록만 취소 (파일 내용은 그대로)
        return
    write_log(entry | {"message": msg})  # 기록도 같이 올라가도록 커밋 직전에 남김
    git("add", ".devlog")
    r = git("commit", "-m", msg)
    if r.returncode != 0:
        if "tell me who you are" in (r.stderr + r.stdout).lower():
            say("❌", "이 컴퓨터에 git 사용자 정보가 없어요. 한 번만 설정하면 돼요:")
            print('     git config --global user.name "이름"')
            print('     git config --global user.email "GitHub 이메일"')
        else:
            say("❌", f"commit 실패: {(r.stderr or r.stdout).strip()}")
        return
    say("💾", "저장(commit) 완료.")

    if not has_upstream():
        say("ℹ️", "GitHub와 연결된 브랜치가 아니라 push는 건너뛰어요.")
        return
    if not fetch():
        say("⚠️", "push 못 했어요. 다른 컴퓨터로 옮기기 전에 꼭 다시 실행해 주세요.")
        return

    ahead, behind = ahead_behind()
    if behind:
        say("⬇️", f"그사이 GitHub에 새 커밋 {behind}개가 있어서 먼저 합칠게요.")
        r = git("pull", "--rebase")
        if r.returncode != 0:
            git("rebase", "--abort")
            say("🔀", "같은 부분을 양쪽에서 고쳐서 자동으로 못 합쳤어요. 원래 상태로 되돌려 놨어요.")
            print("     → git pull --rebase 를 직접 실행하고, 충돌 메시지를 Claude에게 보여주세요.")
            return
    r = git("push")
    if r.returncode == 0:
        say("⬆️", "GitHub에 올렸어요(push). 이제 다른 컴퓨터에서 이어서 해도 돼요!")
    else:
        say("❌", f"push 실패: {r.stderr.strip()}")


def cmd_log():
    n = 10
    ensure_repo()
    logs = read_logs()
    if not logs:
        print("기록이 아직 없어요.")
        return
    print(f"\n최근 작업 기록 {min(n, len(logs))}개\n")
    for e in logs[-n:]:
        icon = "▶" if e["event"] == "start" else "■"
        extra = f" · {e['message']}" if e.get("message") else ""
        print(f" {icon} {e['time'].replace('T', ' ')}  {e['machine']:<16} "
              f"py{e.get('python', '?')}  [{e.get('branch', '?')}]{extra}")
    print()


def main():
    cmds = {"start": cmd_start, "end": cmd_end, "log": cmd_log}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(1)
    cmds[sys.argv[1]]()


if __name__ == "__main__":
    main()

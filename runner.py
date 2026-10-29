"""GitHub Actions の中で回す：動画の URL の一覧から、1本ごとにコマ一覧（画が変わった所・秒つき）を作る。

    python runner.py items.json out/

items.json：[{"id": "短い名前", "url": "動画の直リンク（CDN）か投稿のページ"}, ...]
出力：out/<id>_<n>.jpg（1枚 5列×2段＝10コマ・1コマ 312×555・1560×1130）、out/meta.json
コマは 3fps で取り、前のコマとの違いが大きい所だけ残す（最大 30コマ＝3枚）。テロップの色・書体・縁を読めるよう、
1コマを大きめにしている（208×370 では書体が潰れた）。
"""
import glob, json, os, shutil, subprocess, sys, time, urllib.request

import numpy as np
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()  # apt-get が10分止まった（2026-10-23）ので pip の静的な ffmpeg を使う

CW, CH, COLS, ROWS, LAB = 312, 554, 5, 2, 20  # 高さは偶数（555 だと JPEG の書き出しが -22 で落ちた）
PER = COLS * ROWS
MAXF = 30


# 取りに行ってよいホスト（https だけ）。何でも取れる作りにしない（自動のセキュリティ確認の指摘・2026-10-23）
ALLOW = tuple(h.strip() for h in os.environ.get(
    "ALLOW_HOSTS", "cdninstagram.com,fbcdn.net,instagram.com,tiktok.com,tiktokcdn.com,w3schools.com").split(",") if h.strip())


def allowed(url):
    from urllib.parse import urlparse
    u = urlparse(url)
    host = (u.hostname or "").lower()
    return u.scheme == "https" and any(host == h or host.endswith("." + h) for h in ALLOW)


def fetch(url, out):
    if not allowed(url):
        raise ValueError(f"許可していないホスト: {url[:80]}")
    host = url.split("/")[2]
    if host.endswith(("cdninstagram.com", "fbcdn.net")) or url.split("?")[0].endswith(".mp4"):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(out, "wb") as f:
            shutil.copyfileobj(r, f)
    else:
        r = subprocess.run(["yt-dlp", "--no-warnings", "-f", "b[vcodec^=avc1]/bv*[vcodec^=avc1]/b[vcodec*=264]/b", "-S", "vcodec:h264", "--ffmpeg-location", FF, "-o", out.replace(".mp4", ".%(ext)s"), url], capture_output=True, text=True, timeout=300)
        # 取れた物は動画の入れ物だけを受け取る（自動のセキュリティ確認の指摘・2026-10-23）
        got = sorted(g for g in glob.glob(out.replace(".mp4", ".*")) if g.rsplit(".", 1)[-1] in ("mp4", "webm", "mkv"))
        print("yt-dlp", r.returncode, r.stderr[-300:], [(g, os.path.getsize(g)) for g in got], flush=True)
        lst = subprocess.run(["yt-dlp", "--no-warnings", "-F", url], capture_output=True, text=True, timeout=120).stdout
        print("formats", lst[-1500:], flush=True)
        if not got:
            raise RuntimeError(r.stderr[-300:])
        out = got[0]
    return out


def blocks(p):
    a = np.asarray(Image.open(p).convert("L").resize((72, 128)), dtype=np.float32)
    return a.reshape(16, 8, 9, 8).mean(axis=(1, 3))


def probe(p):
    import re
    e = subprocess.run([FF, "-protocol_whitelist", "file", "-i", p], capture_output=True, text=True).stderr
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", e)
    d = re.search(r"Duration: (\d+):(\d+):([\d.]+)", e)
    print("probe", [l.strip() for l in e.splitlines() if "Stream" in l][:3], flush=True)
    return {"w": int(m.group(1)) if m else None, "h": int(m.group(2)) if m else None,
            "duration": int(d.group(1)) * 3600 + int(d.group(2)) * 60 + float(d.group(3)) if d else 0}


def sheets(vid, path, out):
    fd = f"tmp/{vid}"
    shutil.rmtree(fd, ignore_errors=True)
    os.makedirs(fd)
    r = subprocess.run([FF, "-v", "error", "-protocol_whitelist", "file", "-i", path, "-vf",
                        f"fps=3,scale={CW}:{CH}:force_original_aspect_ratio=decrease,pad={CW}:{CH}:(ow-iw)/2:(oh-ih)/2,format=yuvj420p",
                        "-q:v", "3", f"{fd}/%05d.jpg"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("ffmpeg: " + r.stderr[-300:])
    fs = sorted(glob.glob(f"{fd}/*.jpg"))
    keep, prev = [], None
    for i, f in enumerate(fs):
        b = blocks(f)
        d = 999.0 if prev is None else float(np.abs(b - prev).max())
        if d > 14:
            keep.append((f, i / 3, d))
            prev = b
    if len(keep) > MAXF:
        keep = [keep[0]] + sorted(sorted(keep[1:], key=lambda k: -k[2])[:MAXF - 1], key=lambda k: k[1])
    font = ImageFont.load_default(16)
    n = 0
    for s in range(0, len(keep), PER):
        part = keep[s:s + PER]
        im = Image.new("RGB", (COLS * CW, ROWS * (CH + LAB)), "white")
        dr = ImageDraw.Draw(im)
        for k, (f, t, _) in enumerate(part):
            x, y = (k % COLS) * CW, (k // COLS) * (CH + LAB)
            im.paste(Image.open(f), (x, y))
            dr.text((x + 4, y + CH + 1), f"{t:.1f}s" + (f"  {vid}" if k == 0 else ""), fill="black", font=font)
        n += 1
        im.save(f"{out}/{vid}_{n}.jpg", quality=80)
    shutil.rmtree(fd, ignore_errors=True)
    return len(keep), n


def main(items_p, out):
    os.makedirs(out, exist_ok=True)
    os.makedirs("v", exist_ok=True)
    items = json.load(open(items_p, encoding="utf-8"))
    meta = {}
    for it in items:
        vid, url = it["id"], it["url"]
        t0 = time.time()
        try:
            p = fetch(url, f"v/{vid}.mp4")
            info = probe(p)
            frames, n = sheets(vid, p, out)
            info.update(frames=frames, sheets=n, secs=round(time.time() - t0, 1))
            os.remove(p)
        except Exception as e:
            info = {"error": str(e)[-300:]}
        meta[vid] = info
        time.sleep(4)  # 投稿のページから取る時に止められないよう間を空ける
        print(vid, info, flush=True)
    json.dump(meta, open(f"{out}/meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

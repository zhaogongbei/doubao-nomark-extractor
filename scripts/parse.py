#!/usr/bin/env python3
"""doubao-nomark-extractor CLI.

从豆包 / Dola / 千问对话分享链接中提取无水印图片和视频（封装自 ihmily/doubao-nomark 项目）。

用法:
    python parse.py <url> [--mode image|video|both] [--raw] [--save-dir DIR] [--json]

示例:
    python parse.py "https://www.doubao.com/thread/xxxxxx"
    python parse.py "https://www.doubao.com/thread/xxxxxx" --mode video
    python parse.py "https://www.qianwen.com/share/chat/xxxxxx" --mode both --raw
    python parse.py "https://www.doubao.com/thread/xxxxxx" --mode both --save-dir ./media
"""
import argparse
import asyncio
import json
import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from doubao_parser.image import doubao_image_parse, qianwen_image_parse
from doubao_parser.video import doubao_video_parse, yunque_video_parse

DOUBAO_HOSTS = {"doubao.com", "www.doubao.com", "dola.com", "www.dola.com"}
QIANWEN_HOSTS = {"qianwen.com", "www.qianwen.com"}


def _host_matches(url: str, allowed: set[str]) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in allowed or any(hostname.endswith(f".{h}") for h in allowed)


def _route_error(url: str) -> ValueError:
    return ValueError("不支持的链接域名（仅支持 doubao.com / dola.com / qianwen.com）")


async def _parse(url: str, mode: str, return_raw: bool) -> dict:
    result = {"url": url, "mode": mode, "return_raw": return_raw, "success": False, "images": [], "videos": []}
    if mode in ("image", "both"):
        if _host_matches(url, DOUBAO_HOSTS):
            result["images"] = await doubao_image_parse(url, return_raw=return_raw)
        elif _host_matches(url, QIANWEN_HOSTS):
            result["images"] = await qianwen_image_parse(url, return_raw=return_raw)
        else:
            raise _route_error(url)
    if mode in ("video", "both"):
        if _host_matches(url, DOUBAO_HOSTS):
            result["videos"] = await doubao_video_parse(url, return_raw=return_raw)
        elif _host_matches(url, QIANWEN_HOSTS):
            result["videos"] = await yunque_video_parse(url, return_raw=return_raw)
        else:
            raise _route_error(url)
    result["success"] = True
    return result


def _flatten_media(result: dict) -> list[tuple[str, str]]:
    """返回 (类型, url) 列表，用于下载。"""
    items: list[tuple[str, str]] = []
    for img in result.get("images") or []:
        if isinstance(img, dict) and img.get("url"):
            items.append(("image", img["url"]))
    for vid in result.get("videos") or []:
        if isinstance(vid, dict) and vid.get("url"):
            items.append(("video", vid["url"]))
    return items


def _safe_filename(media_type: str, url: str, index: int) -> str:
    ext_map = {"image": ".jpg", "video": ".mp4"}
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".mov", ".webm"):
        ext = ext_map[media_type]
    return f"{media_type}_{index:03d}{ext}"


async def _download_all(items: list[tuple[str, str]], save_dir: str) -> list[dict]:
    import httpx

    os.makedirs(save_dir, exist_ok=True)
    saved: list[dict] = []
    headers = {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/143.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=60, headers=headers) as client:
        for index, (media_type, url) in enumerate(items, start=1):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                filename = _safe_filename(media_type, url, index)
                filepath = os.path.join(save_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                saved.append({"type": media_type, "filename": filename, "path": filepath, "bytes": len(resp.content)})
            except Exception as exc:  # noqa: BLE001
                saved.append({"type": media_type, "url": url, "error": str(exc)})
    return saved


async def _main(args: argparse.Namespace) -> int:
    try:
        result = await _parse(args.url, args.mode, args.raw)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"success": False, "url": args.url, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1

    if args.save_dir and not args.raw:
        items = _flatten_media(result)
        if items:
            print(f"开始下载 {len(items)} 个资源到 {args.save_dir} ...", file=sys.stderr)
            result["saved"] = await _download_all(items, args.save_dir)
        else:
            result["saved"] = []

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="提取豆包/Dola/千问分享链接中的无水印图片和视频")
    parser.add_argument("url", help="对话分享链接（doubao.com/thread/ 或 qianwen.com/share/chat/）")
    parser.add_argument("--mode", choices=["image", "video", "both"], default="image", help="提取类型，默认 image")
    parser.add_argument("--raw", action="store_true", help="返回解析到的原始页面数据（不简化）")
    parser.add_argument("--save-dir", default=None, help="同时把媒体资源下载到该目录")
    args = parser.parse_args()
    sys.exit(asyncio.run(_main(args)))


if __name__ == "__main__":
    main()

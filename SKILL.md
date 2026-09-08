---
name: doubao-nomark-extractor
description: 从豆包（doubao.com）、豆包海外版（dola.com）、千问（qianwen.com）对话分享链接（/thread/ 或 /share/chat/）中提取无水印图片和视频，返回直链与元信息，并支持批量下载到本地。当用户提供豆包/千问等对话分享链接并要求提取、解析、下载、保存其中的 AI 生成图片或视频素材时使用；也适用于"把这个豆包链接里的图导出来""去掉水印保存视频"等需求。封装自开源项目 ihmily/doubao-nomark。
---

# Doubao Nomark Extractor

## 概述

给定一条豆包 / Dola / 千问的**对话分享链接**，本技能直接解析页面内嵌数据，取出**无水印**的原始图片直链（`image_ori_raw`）和视频直链（`fallback_api` + `logo_type=unwatermarked` 参数改写 + qAAB token 解密），返回结构化 JSON，可选一键下载到本地目录。无需部署服务，无需登录。

## 前置条件

- Python 3.10+，依赖 `httpx`、`cryptography`。
- 缺少依赖时先执行：
  ```bash
  python -m pip install httpx cryptography
  ```

## 快速开始

脚本位于 `scripts/parse.py`，所有命令在本技能目录下执行：

```bash
# 提取图片（默认）
python scripts/parse.py "https://www.doubao.com/thread/xxxxxx"

# 提取视频
python scripts/parse.py "https://www.doubao.com/thread/xxxxxx" --mode video

# 图片 + 视频，并下载到本地目录
python scripts/parse.py "https://www.doubao.com/thread/xxxxxx" --mode both --save-dir ./media

# 千问链接；--raw 返回解析到的原始页面数据
python scripts/parse.py "https://www.qianwen.com/share/chat/xxxxxx" --raw
```

## 工作流

1. **校验链接**：必须为对话分享链接——豆包/Dola 含 `/thread/`，千问含 `/share/chat/`。其他域名或不含上述路径的链接会返回错误，直接告知用户链接格式不正确。
2. **选择模式**：
   - 用户只要图片 → `--mode image`（默认）
   - 用户只要视频 → `--mode video`
   - 都要 → `--mode both`
3. **执行**：运行 `parse.py`，读取 stdout 的 JSON。
4. **处理结果**：
   - `success: true` 时，`images` 每项含 `url` / `width` / `height`；`videos` 每项含 `url` / `width` / `height` / `definition` / `duration` / `poster_url` / `codec_type` / `vid`。
   - 用户要求保存到本地时加 `--save-dir`，结果中 `saved` 数组会给出每个文件的 `path`。
   - 若用户希望将媒体交付到飞书/豆包文档或继续处理，可先 `--save-dir` 下载，再对本地文件做后续操作。

## 输出示例

```json
{
  "url": "https://www.doubao.com/thread/aef4c7a4c78c2",
  "mode": "image",
  "success": true,
  "images": [
    { "url": "https://...", "width": 1024, "height": 768 }
  ],
  "videos": []
}
```

## 常见错误与处理

| 错误信息 | 含义与处理 |
| --- | --- |
| `链接格式不正确，请使用豆包对话链接（包含 /thread/）` | 链接不是分享格式，向用户索要正确的分享链接 |
| `页面结构发生变化，无法解析图片数据` / `无法解析页面数据` | 豆包前端结构改版，解析器已失效；可提示用户稍后再试，或从上游项目同步更新 |
| `不支持的链接域名` | 仅支持 doubao.com / dola.com / qianwen.com 及其子域 |
| 网络相关 `ValueError` | 网络不通或页面不可达，可重试一次 |

## 维护说明

- 解析器源码在 `scripts/doubao_parser/`（image.py / video.py / video_crypto.py），与上游 https://github.com/ihmily/doubao-nomark 的 `doubao_parser` 目录保持一致。
- 上游发布新版本修复解析后，用以下命令同步覆盖：
  ```bash
  curl -o scripts/doubao_parser/image.py https://raw.githubusercontent.com/ihmily/doubao-nomark/main/doubao_parser/image.py
  curl -o scripts/doubao_parser/video.py https://raw.githubusercontent.com/ihmily/doubao-nomark/main/doubao_parser/video.py
  curl -o scripts/doubao_parser/video_crypto.py https://raw.githubusercontent.com/ihmily/doubao-nomark/main/doubao_parser/video_crypto.py
  ```

## 合规提示

本技能封装的开源项目仅供学习交流使用。提取和保存素材时请遵守豆包/千问平台的使用条款和相关法律法规，勿用于侵权或商业再分发场景。

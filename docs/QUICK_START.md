# 快速开始

## 环境要求

- Python 3.12
- [uv](https://docs.astral.sh/uv/)（推荐的依赖管理方式）

## 运行

本项目使用 [uv](https://docs.astral.sh/uv/) 管理依赖：

```bash
uv sync
uv run flask --app main run --debug
```

或直接运行：

```bash
uv run python main.py
```

打开 <http://127.0.0.1:5000>，注册或登录后进入「我的控制台」新建私有笔记；公开后即可通过 `/share/<note_id>` 只读分享。

## 前端第三方库同步

前端第三方库（marked、highlight.js、DOMPurify、KaTeX、Mermaid、Font Awesome 等）放在 `nooote/static/vendor/`，该目录已被 git 忽略。每次启动服务都会自动检查并下载缺失或校验失败的文件，下载内容按 `nooote/vendor.py` 中固定的 SHA-256 校验。也可以提前单独同步：

```bash
uv run python -m nooote.vendor
```

离线环境或不想在启动时访问网络时，设置 `NOOOTE_SKIP_VENDOR_SYNC=1` 跳过自动同步，改由部署流程自行准备 `static/vendor/`。

## 测试

```bash
uv run pytest
```

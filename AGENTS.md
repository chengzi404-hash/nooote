# AGENTS.md

面向在本仓库工作的开发者与自动化代理的项目说明。用户文档见 [README.md](README.md) 与 [docs/](docs/)，贡献流程与质量门槛见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 技术栈

- Python 3.12 + Flask 3.x，SQLAlchemy + SQLite
- 前端无构建步骤：原生 HTML/CSS/JS，由 Jinja 模板渲染
- 后端保持轻量，只负责存储与 JSON API；Markdown 渲染、代码高亮、图表都跑在浏览器端
- 第三方前端库自托管在 `nooote/static/vendor/`，不依赖公共 CDN

## 功能清单

- 用户系统：注册、登录、退出，密码以 Werkzeug 哈希存储；控制台、设置、笔记 API 与附件管理均需登录
- 控制台：`GET /console` 管理当前账号的私有笔记，`GET /console/settings` 设置昵称、主题（跟随系统/浅色/深色）与新笔记默认公开
- 图床与附件：`GET /console/attachments` 上传、复制链接、删除；编辑器内支持点击上传、拖拽或粘贴图片并自动插入 Markdown
- 附件通过 `/files/<id>` 访问，图片内联显示、其他文件下载；链接不可猜测，但拿到链接即可访问
- 笔记默认私有，可随时公开或取消公开；公开后通过 `/share/<note_id>` 只读访问，无编辑入口
- 公开页与私有笔记共用同一份内容，只有修改私有笔记才会改变公开页
- 编辑区与 CommonMark 预览双栏并排，输入停顿后自动保存，`Ctrl / ⌘ + S` 立即保存；宽屏下两栏滚动位置按比例双向同步
- 代码块语法高亮（highlight.js，常用语言，浅色/深色主题自动切换）
- 每个代码块右上角有一键复制按钮，复制成功后图标短暂切换为对勾
- LaTeX 数学公式（KaTeX）：行内 `$...$`、行间 `$$...$$`
- GitHub 风格提示卡片（Note、Tip、Important、Warning、Caution）与 GFM 任务列表
- Mermaid 图表直接预览：`mermaid` / `mmd` 代码块按需渲染为流程图、时序图、类图、状态图、ER 图、甘特图、饼图等，右上角按钮可在图表与源码之间切换
- 深色模式、移动端上下分栏、页面进入动画与 View Transitions
- Markdown 原始 HTML 由 DOMPurify 清洗后再渲染，CSP 仅允许同源脚本和样式
- 最近公开笔记列表与随机公开笔记入口

## 项目结构

```
main.py                  # 应用入口：终端 Banner、create_app()、app.run()
nooote/
├── __init__.py          # 应用工厂、配置加载、安全响应头、启动时同步 vendor
├── config.py            # Config 默认值与共享常量（长度限制、正则、选项元组）
├── extensions.py        # SQLAlchemy 实例
├── models.py            # User（账号与密码哈希）、Note、Attachment 模型
├── services.py          # 用户、笔记、附件的领域逻辑
├── vendor.py            # vendor 资源清单、SHA-256 校验与自动下载
├── blueprints/
│   ├── public.py        # 首页、公开只读页与旧路径重定向
│   ├── auth.py          # 注册、登录与退出
│   ├── console.py       # 控制台、私有笔记与用户设置
│   ├── notes_api.py     # 笔记 JSON API
│   └── attachments.py   # 图床、附件管理与文件读取
├── templates/           # 首页、登录注册、控制台、设置、附件、编辑器与公开页
│   └── _icons.html      # 内联 SVG 图标宏
└── static/
    ├── style.css        # 全部样式（方形控件、主题变量、Markdown 排版）
    ├── app.js           # 浏览器端渲染、自动保存、图表、复制按钮
    └── vendor/          # 第三方浏览器库（git 忽略，启动时自动同步）
tests/                   # pytest 测试
docs/                    # 用户文档：快速开始、功能、Markdown 扩展、API、配置与项目结构
```

## 前端第三方库自动同步

`nooote/static/vendor/` 被 git 忽略，因此全新克隆的仓库没有第三方文件。同步机制在 `nooote/vendor.py`：

- `ASSETS` 是声明式清单，每项包含相对路径、固定的 SHA-256 与若干镜像 URL（cdnjs / jsDelivr / unpkg）
- 应用工厂在非 `TESTING` 模式下调用 `sync_app()`，每次启动检查所有文件，仅下载缺失或校验失败的部分
- 下载后先校验 SHA-256 再原子写入磁盘，绝不使用未通过校验的内容
- 单个镜像失败会自动尝试下一个；进程内对同一目录只同步一次，避免 debug reloader 重复下载
- `python -m nooote.vendor` 可单独执行同步（CI 在跑测试前会调用它）
- `NOOOTE_SKIP_VENDOR_SYNC=1` 跳过同步，适用于离线或自带 vendor 目录的部署

新增或升级第三方库时：

1. 确认上游带有可长期引用的不可变 URL，并记录对应文件的 SHA-256
2. 在 `ASSETS` 中添加或更新条目，同时提供至少一个备用镜像
3. 在 `nooote/static/vendor/README.md` 的表格中登记版本与许可证
4. 重新运行同步，确认文件能正确落盘

## 约定

- 后端只做存储与 JSON API，不要在服务端新增渲染接口
- 共享常量放进 `nooote/config.py`，避免散落魔法数字
- 用户可见文案、文档使用中文；终端输出（Banner、日志）使用英文
- UI 图标统一使用 Font Awesome（`<i class="fa-solid fa-...">`），不使用 emoji 字符
- 面向用户的文档同时维护中文 `README.md` 与英文 `README.en.md`

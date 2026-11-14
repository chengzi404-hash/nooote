# 项目结构

```
main.py                  # 应用入口
nooote/
├── __init__.py          # 应用工厂、配置加载、安全响应头
├── config.py            # 配置默认值与共享常量
├── extensions.py        # SQLAlchemy 实例
├── models.py            # User（账号与密码哈希）、Note 与 Attachment 模型
├── services.py          # 用户、笔记与附件的领域逻辑
├── vendor.py            # vendor 资源清单、校验与自动同步
├── blueprints/
│   ├── public.py        # 首页、公开只读页与旧路径重定向
│   ├── auth.py          # 注册、登录与退出
│   ├── console.py       # 控制台、私有笔记与用户设置
│   ├── notes_api.py     # 笔记 JSON API
│   └── attachments.py   # 图床、附件管理与文件读取
├── templates/           # 首页、登录注册、控制台、设置、附件、编辑与公开页
└── static/              # 样式、浏览器端渲染脚本、图标
    └── vendor/          # marked、highlight.js、DOMPurify、KaTeX、Mermaid、Font Awesome、Lezer、Ruby Prism（启动时自动同步，含许可证）
tools/checks/            # 静态检查 bundle 的源码与重建说明
tests/                   # pytest 测试
```

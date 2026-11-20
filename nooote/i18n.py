"""Lightweight Chinese/English message catalog.

Keys are flat and dot-scoped (``settings.saved``). The default locale is
Chinese, so a missing English entry falls back to the Chinese wording and
never leaks a bare key into the interface.
"""

from __future__ import annotations

from flask import g, has_request_context, request

from .config import (
    DEFAULT_LOCALE,
    LOCALE_COOKIE,
    LOCALE_COOKIE_MAX_AGE,
    LOCALES,
)

HTML_LANGS = {"zh": "zh-CN", "en": "en"}

MESSAGES: dict[str, dict[str, str]] = {
    "zh": {
        # ---------- shared ----------
        "meta.description": "支持登录的在线 CommonMark 笔记",
        "lang.switcher_label": "切换语言",
        "lang.zh": "中",
        "lang.en": "EN",
        # ---------- site navigation ----------
        "nav.aria": "站点导航",
        "nav.features": "功能",
        "nav.workflow": "工作流",
        "nav.recent": "公开笔记",
        "nav.stack": "技术栈",
        "nav.login": "登录",
        "nav.register": "注册",
        "nav.logout": "退出登录",
        "nav.console": "进入我的控制台",
        # ---------- home ----------
        "home.title": "Nooote · 轻量的在线 Markdown 笔记",
        "home.eyebrow": "开源 · Flask · CommonMark",
        "home.hero_title": "把想法写成笔记，",
        "home.hero_accent": "让它在线上生长。",
        "home.hero_lead": (
            "Nooote 是一个轻量的在线 Markdown 笔记应用。登录后拥有自己的私有笔记空间，"
            "输入停顿即自动保存；需要分享时，一条只读链接就够了。"
        ),
        "home.cta_attachments": "图床与附件",
        "home.cta_register": "免费创建账号",
        "home.cta_login": "已有账号，登录",
        "home.random": "随机公开笔记",
        "home.stat_commonmark": "CommonMark",
        "home.stat_commonmark_hint": "标准 Markdown 渲染",
        "home.stat_autosave": "自动保存",
        "home.stat_autosave_hint": "输入停顿后即时落盘",
        "home.stat_share": "只读分享",
        "home.stat_share_hint": "公开页没有编辑入口",
        "home.features_eyebrow": "项目能力",
        "home.features_title": "为长期写作准备的编辑器",
        "home.features_lead": (
            "从纯文本输入到代码高亮、数学公式与图表预览，全部在浏览器端完成，"
            "服务端只负责存储与同步。"
        ),
        "home.feature_preview_title": "双栏实时预览",
        "home.feature_preview_body": (
            "左侧书写 Markdown，右侧同步呈现排版结果，输入停顿后自动保存到你的账号。"
        ),
        "home.feature_account_title": "账号与私有空间",
        "home.feature_account_body": (
            "注册、登录、退出都由服务端会话管理，密码以哈希存储，每篇笔记只属于它的作者。"
        ),
        "home.feature_upload_title": "图床与附件",
        "home.feature_upload_body": (
            "点击、拖拽或粘贴即可上传图片，自动插入 Markdown；所有文件通过不可猜测的链接访问。"
        ),
        "home.feature_code_title": "代码高亮与复制",
        "home.feature_code_body": (
            "highlight.js 为常用语言着色，每个代码块右上角都有一键复制按钮，随手取用示例代码。"
        ),
        "home.feature_rich_title": "公式、图表与提醒",
        "home.feature_rich_body": (
            "KaTeX 数学公式、Mermaid 图表、GitHub 风格提示卡片与任务列表，都可以直接写进笔记。"
        ),
        "home.feature_share_title": "只读链接分享",
        "home.feature_share_body": (
            "公开一篇笔记后，任何人都能通过 <code>/share/&lt;id&gt;</code> 阅读，"
            "而内容始终由你维护。"
        ),
        "home.workflow_eyebrow": "三步开始",
        "home.workflow_title": "写下第一行，剩下的交给它",
        "home.workflow_lead": "没有复杂的初始化，也没有需要安装的客户端。一个浏览器标签页就是全部工作区。",
        "home.step_account_title": "创建账号",
        "home.step_account_body": "注册后自动登录，进入属于你的控制台，所有笔记默认私有。",
        "home.step_write_title": "写一篇笔记",
        "home.step_write_body": "使用 CommonMark 写作，拖入图片或粘贴截图，预览会即时更新。",
        "home.step_share_title": "分享只读链接",
        "home.step_share_body": "需要时把笔记公开，把 <code>/share/&lt;id&gt;</code> 发给任何人，随时可以取消。",
        "home.stack_eyebrow": "技术栈",
        "home.stack_title": "轻量服务端，认真做的前端",
        "home.stack_lead": "后端保持薄，渲染与检查留在浏览器；第三方库全部自托管，不依赖公共 CDN。",
        "home.stack_aria": "技术栈列表",
        "home.recent_eyebrow": "公开笔记",
        "home.recent_title": "最近公开",
        "home.recent_lead": "这些笔记由作者主动公开，任何人都可以只读访问。",
        "home.recent_empty": "还没有公开笔记，登录后写下第一篇并选择公开吧。",
        "home.cta_eyebrow": "现在开始",
        "home.cta_title": "下一段想法，值得被保存在线上。",
        "home.footer": "Nooote · 在线 CommonMark 笔记 · MIT License",
        "home.footer_aria": "页脚链接",
        # ---------- auth ----------
        "auth.login_title": "登录 · Nooote",
        "auth.login_eyebrow": "Welcome back",
        "auth.login_hero_line1": "你的笔记",
        "auth.login_hero_line2": "还在原来的位置。",
        "auth.login_hero_lead": "登录后继续编辑私有笔记，或者把某一篇公开成只读链接。",
        "auth.point_autosave": "输入停顿后自动保存",
        "auth.point_private": "每篇笔记只有你能编辑",
        "auth.point_unpublish": "公开链接随时可以取消",
        "auth.aside_foot": "CommonMark · KaTeX · Mermaid",
        "auth.login_label": "登录",
        "auth.login_heading": "欢迎回来",
        "auth.login_hint": "登录后查看和管理你的私有笔记。",
        "auth.username": "用户名",
        "auth.password": "密码",
        "auth.confirm": "确认密码",
        "auth.username_placeholder": "你的用户名",
        "auth.password_placeholder": "输入密码",
        "auth.login_button": "登录",
        "auth.no_account": "还没有账号？",
        "auth.register_link": "注册",
        "auth.register_title": "注册 · Nooote",
        "auth.register_eyebrow": "Start writing",
        "auth.register_hero_line1": "给想法",
        "auth.register_hero_line2": "一个在线的位置。",
        "auth.register_hero_lead": "创建账号后即可拥有私有笔记空间，输入即自动保存，需要时一键公开。",
        "auth.register_point_autologin": "注册后自动登录",
        "auth.register_point_markdown": "支持 Markdown、公式与图表",
        "auth.register_point_hash": "密码只保存哈希值",
        "auth.register_aside_foot": "MIT License · 自托管 · 无追踪",
        "auth.register_label": "注册",
        "auth.register_heading": "创建账号",
        "auth.register_hint": "创建账号后即可保存私有笔记。",
        "auth.register_username_placeholder": "3-32 位字符",
        "auth.register_username_hint": "3-32 位字母、数字、下划线、点或连字符。",
        "auth.register_password_placeholder": "至少 8 位",
        "auth.register_password_hint": "至少 8 位。",
        "auth.confirm_placeholder": "再次输入密码",
        "auth.create_button": "创建账号",
        "auth.have_account": "已经有账号？",
        "auth.login_link": "登录",
        "auth.error_credentials": "用户名或密码错误",
        "auth.error_username_rule": (
            "用户名需为 {min_length}-{max_length} 位字母、数字、下划线、点或连字符"
        ),
        "auth.error_password_min": "密码至少需要 {min_length} 位",
        "auth.error_password_max": "密码不能超过 {max_length} 位",
        "auth.error_password_mismatch": "两次输入的密码不一致",
        "auth.error_username_taken": "用户名已被使用",
        # ---------- console shell ----------
        "console.nav_aria": "控制台导航",
        "console.brand_subtitle": "笔记控制台",
        "console.create_note": "新建私有笔记",
        "console.workspace": "工作区",
        "console.my_notes": "我的笔记",
        "console.attachments": "图床与附件",
        "console.account": "账户",
        "console.settings": "用户设置",
        "console.manage": "站点管理",
        "console.back_home": "返回首页",
        "console.more_apps": "更多应用",
        "console.overview_aria": "笔记概览",
        "console.overview_title": "笔记概览",
        "console.private": "私有",
        "console.public": "公开",
        "console.note_count": "共 {total} 篇笔记 · {attachments} 个附件",
        "console.no_nickname": "未设置昵称",
        "console.logout": "退出",
        "console.breadcrumb_aria": "面包屑",
        "console.console": "控制台",
        "console.browse_home": "浏览首页",
        "console.page_title": "我的控制台 · Nooote",
        "console.crumb_notes": "我的笔记",
        "console.eyebrow": "Workspace",
        "console.heading_named": "{name} 的笔记",
        "console.heading_default": "我的笔记",
        "console.lead_notes": (
            "共 {total} 篇笔记，其中 {public} 篇已公开。私有笔记只有你能看到；公开后可在"
        ),
        "console.lead_share": "只读访问，编辑私有笔记会自动同步。",
        "console.stats_aria": "笔记统计",
        "console.stat_total": "全部笔记",
        "console.stat_private": "私有",
        "console.stat_public": "公开",
        "console.stat_attachments": "附件",
        "console.empty_note": "空白笔记",
        "console.updated": "更新于",
        "console.badge_public": "公开 · 只读",
        "console.badge_private": "私有",
        "console.unpublish": "取消公开",
        "console.publish": "公开",
        "console.edit": "编辑",
        "console.delete": "删除",
        "console.confirm_delete": "删除后无法恢复，确定删除这篇笔记吗？",
        "console.empty_title": "还没有笔记",
        "console.empty_body": "点击侧边栏的「新建私有笔记」，从第一行开始写起。",
        # ---------- settings ----------
        "settings.page_title": "用户设置 · Nooote",
        "settings.crumb": "用户设置",
        "settings.eyebrow": "Settings",
        "settings.heading": "用户设置",
        "settings.lead_prefix": "当前账号：",
        "settings.lead_suffix": "。这些设置会保存在你的账号中。",
        "settings.saved": "设置已保存",
        "settings.display_name": "昵称",
        "settings.display_name_placeholder": "留空则显示为「我的笔记」",
        "settings.display_name_hint": "仅用于控制台标题，不会出现在公开笔记中。",
        "settings.appearance": "外观",
        "settings.theme_auto": "跟随系统",
        "settings.theme_light": "浅色",
        "settings.theme_dark": "深色",
        "settings.theme_hint": "主题会应用到首页、控制台和编辑器。",
        "settings.language": "界面语言",
        "settings.language_hint": "切换后立即生效，并保存在你的账号中。",
        "settings.default_public": "新笔记默认公开",
        "settings.default_public_hint": (
            "勾选后，新建的笔记会立即出现在只读的 <code>/share/&lt;id&gt;</code> 页面。"
        ),
        "settings.save": "保存设置",
        "settings.back_console": "返回控制台",
        "settings.permissions": "权限组",
        "settings.role_member": "成员",
        "settings.role_admin": "管理员",
        "settings.role_guest": "访客",
        "settings.permissions_hint": (
            "账号所在权限组决定可访问的页面与接口，权限由服务端统一校验。"
        ),
        "settings.permissions_granted": "已授予权限",
        "settings.permissions_readonly": "权限组由管理员分配，无法在设置页修改。",
        # ---------- management ----------
        "manage.page_title": "站点管理 · Nooote",
        "manage.crumb": "站点管理",
        "manage.eyebrow": "Administration",
        "manage.heading": "站点管理",
        "manage.lead": "查看站点数据总览，并为每个账号分配权限组。",
        "manage.stats_title": "站点数据",
        "manage.stat_users": "账号",
        "manage.stat_notes": "笔记",
        "manage.stat_public": "公开笔记",
        "manage.stat_private": "私有笔记",
        "manage.stat_attachments": "附件",
        "manage.stat_storage": "占用空间",
        "manage.storage_detail": "笔记正文 {notes} · 附件 {attachments}",
        "manage.groups_title": "权限组",
        "manage.groups_lead": "下列权限在服务端统一校验，路由必须声明所需权限才会放行。",
        "manage.role_members": "{count} 个账号",
        "manage.users_title": "账号与权限组",
        "manage.users_lead": "管理员可以调整其他账号的权限组，不能修改自己的权限组。",
        "manage.joined": "注册于",
        "manage.change_role": "修改权限组",
        "manage.save_role": "保存",
        "manage.self_role": "不能修改自己的权限组",
        "manage.role_updated": "已更新 {username} 的权限组",
        "manage.error_self_role": "不能修改自己的权限组，请让其他管理员操作",
        "manage.features_title": "功能开关",
        "manage.features_lead": "关闭后，对应路由与侧边栏入口立即停用；插件功能也可以单独开关。",
        "manage.features_core": "默认功能",
        "manage.feature_on": "已开启",
        "manage.feature_off": "已关闭",
        "manage.feature_enable": "开启",
        "manage.feature_disable": "关闭",
        "manage.feature_updated": "已将「{name}」设置为{state}",
        # ---------- feature flags ----------
        "features.notes.label": "笔记",
        "features.notes.description": "私有笔记列表、编辑器与保存接口",
        "features.attachments.label": "图床与附件",
        "features.attachments.description": "附件上传、管理与编辑器中插入图片；已上传文件仍可访问",
        "features.public_shares.label": "公开分享",
        "features.public_shares.description": "公开/取消公开、只读分享页与首页的公开笔记列表",
        "features.registration.label": "开放注册",
        "features.registration.description": "允许访客创建新账号；关闭后已有账号仍可登录",
        # ---------- attachments ----------
        "attachments.page_title": "图床与附件 · Nooote",
        "attachments.crumb": "图床与附件",
        "attachments.eyebrow": "Attachments",
        "attachments.heading": "图床与附件",
        "attachments.lead": (
            "上传的图片和文件通过不可猜测的随机链接访问。任何拿到链接的人都能查看，"
            "请不要上传敏感内容。"
        ),
        "attachments.upload": "上传",
        "attachments.upload_hint": (
            "单个文件上限 8 MiB。图片会插入为 Markdown 图片，其他文件插入为下载链接。"
        ),
        "attachments.copy_link": "复制链接",
        "attachments.confirm_delete": "删除后引用该附件的笔记将无法显示它，确定删除吗？",
        "attachments.delete": "删除",
        "attachments.empty_title": "还没有上传任何附件",
        "attachments.empty_body": "上传图片后，可以直接在笔记编辑器中粘贴或拖拽使用。",
        "attachments.uploaded": "已上传 {filename}",
        "attachments.deleted": "附件已删除",
        # ---------- editor ----------
        "editor.title": "{note_id} · 私有笔记 · Nooote",
        "editor.back_console": "返回控制台",
        "editor.badge_public": "公开 · 只读",
        "editor.badge_private": "私有",
        "editor.view": "查看",
        "editor.copy_link": "复制链接",
        "editor.unpublish": "取消公开",
        "editor.publish": "公开",
        "editor.saved": "已保存",
        "editor.updated": "更新于",
        "editor.edit": "编辑",
        "editor.preview": "预览",
        "editor.toolbar": "快捷编辑工具",
        "editor.bold": "加粗",
        "editor.italic": "斜体",
        "editor.strikethrough": "删除线",
        "editor.inline_code": "行内代码",
        "editor.heading": "标题",
        "editor.quote": "引用",
        "editor.bullet_list": "无序列表",
        "editor.numbered_list": "有序列表",
        "editor.task_list": "任务列表",
        "editor.link": "插入链接",
        "editor.code_block": "代码块",
        "editor.table": "插入表格",
        "editor.divider": "分隔线",
        "editor.formula": "行内公式",
        "editor.upload": "上传图片/附件",
        "editor.placeholder": (
            "在这里写点什么…（Markdown / CommonMark），也可以拖入或粘贴图片"
        ),
        "editor.empty_hint": "开始输入，预览会实时出现在这里。",
        "editor.preview_aria": "Markdown 预览",
        # ---------- share ----------
        "share.title": "{note_id} · 公开笔记 · Nooote",
        "share.back_home": "返回首页",
        "share.badge": "公开 · 只读",
        "share.updated": "更新于",
        "share.copy_link": "复制链接",
        # ---------- markdown alerts ----------
        "markdown.note": "注意",
        "markdown.tip": "提示",
        "markdown.important": "重要",
        "markdown.warning": "警告",
        "markdown.caution": "谨慎",
        # ---------- browser script ----------
        "js.just_now": "刚刚",
        "js.copied": "已复制",
        "js.copy_link": "复制链接",
        "js.copy_code": "复制代码",
        "js.copy_failed": "复制失败",
        "js.view_code": "查看代码",
        "js.view_diagram": "查看图表",
        "js.mermaid_missing_src": "缺少 Mermaid 资源地址",
        "js.mermaid_unavailable": "Mermaid 加载后不可用",
        "js.mermaid_load_failed": "无法加载 Mermaid",
        "js.mermaid_render_failed": "图表渲染失败",
        "js.mermaid_rendering": "正在渲染图表…",
        "js.saving": "保存中…",
        "js.too_large": "内容过大，无法保存",
        "js.typing": "正在输入…",
        "js.saved": "已保存",
        "js.save_failed": "保存失败，正在重试…",
        "js.uploading": "上传中… ({done}/{total})",
        "js.upload_failed": "上传失败",
        "js.editor_link_text": "链接文字",
        "js.editor_table_col": "列 {n}",
        "js.editor_table_cell": "内容",
        # ---------- errors ----------
        "error.invalid_note_id": "笔记 ID 无效",
        "error.content_required": '请求体需为包含 "content" 字符串的 JSON',
        "error.content_too_large": "笔记内容过大",
        "error.auth_required": "请先登录",
        "error.forbidden": "没有权限执行该操作",
        "error.forbidden_title": "403 · Nooote",
        "error.forbidden_heading": "没有访问权限",
        "error.forbidden_body": "当前账号所在的权限组不包含访问该页面的权限。",
        "error.feature_disabled": "该功能已被关闭",
        "error.feature_disabled_title": "403 · Nooote",
        "error.feature_disabled_heading": "功能已关闭",
        "error.feature_disabled_body": "该功能已被管理员关闭，如需使用请联系站点管理员。",
        "error.back_home": "返回首页",
        "upload.file_required": "请选择要上传的文件",
        "upload.file_too_large": "文件过大，超出上传上限",
        "upload.file_empty": "文件为空",
        "upload.login_required": "请先登录",
    },
    "en": {
        # ---------- shared ----------
        "meta.description": "An online CommonMark notes app with accounts",
        "lang.switcher_label": "Switch language",
        "lang.zh": "中",
        "lang.en": "EN",
        # ---------- site navigation ----------
        "nav.aria": "Site navigation",
        "nav.features": "Features",
        "nav.workflow": "Workflow",
        "nav.recent": "Public notes",
        "nav.stack": "Stack",
        "nav.login": "Sign in",
        "nav.register": "Sign up",
        "nav.logout": "Sign out",
        "nav.console": "Open my console",
        # ---------- home ----------
        "home.title": "Nooote · Lightweight online Markdown notes",
        "home.eyebrow": "Open source · Flask · CommonMark",
        "home.hero_title": "Write your ideas down,",
        "home.hero_accent": "and let them grow online.",
        "home.hero_lead": (
            "Nooote is a lightweight online Markdown notebook. Sign in to get a private "
            "space of your own; typing pauses save automatically, and a read-only link is "
            "all you need to share."
        ),
        "home.cta_attachments": "Files & images",
        "home.cta_register": "Create a free account",
        "home.cta_login": "I already have an account",
        "home.random": "Random public note",
        "home.stat_commonmark": "CommonMark",
        "home.stat_commonmark_hint": "Standards-based Markdown rendering",
        "home.stat_autosave": "Autosave",
        "home.stat_autosave_hint": "Saved as soon as you pause",
        "home.stat_share": "Read-only sharing",
        "home.stat_share_hint": "Public pages have no editor",
        "home.features_eyebrow": "What it does",
        "home.features_title": "An editor built for long-form writing",
        "home.features_lead": (
            "From plain text to code highlighting, math and diagrams, everything runs in "
            "the browser; the server only stores and syncs."
        ),
        "home.feature_preview_title": "Live side-by-side preview",
        "home.feature_preview_body": (
            "Write Markdown on the left and see the layout on the right, saved "
            "automatically to your account when you pause."
        ),
        "home.feature_account_title": "Accounts and private space",
        "home.feature_account_body": (
            "Registration, sign-in and sign-out are handled by server sessions, passwords "
            "are hashed, and every note belongs only to its author."
        ),
        "home.feature_upload_title": "Files and images",
        "home.feature_upload_body": (
            "Click, drag or paste to upload an image and insert it as Markdown; every file "
            "is served through an unguessable link."
        ),
        "home.feature_code_title": "Syntax highlighting and copy",
        "home.feature_code_body": (
            "highlight.js colours common languages, and every code block has a one-click "
            "copy button in its corner."
        ),
        "home.feature_rich_title": "Math, diagrams and callouts",
        "home.feature_rich_body": (
            "KaTeX math, Mermaid diagrams, GitHub-style alert cards and task lists all "
            "work directly in your notes."
        ),
        "home.feature_share_title": "Read-only link sharing",
        "home.feature_share_body": (
            "Publish a note and anyone can read it at <code>/share/&lt;id&gt;</code>, while "
            "the content stays yours to maintain."
        ),
        "home.workflow_eyebrow": "Three steps",
        "home.workflow_title": "Write the first line, it handles the rest",
        "home.workflow_lead": (
            "No complicated setup and no client to install. A single browser tab is the "
            "whole workspace."
        ),
        "home.step_account_title": "Create an account",
        "home.step_account_body": (
            "Sign up and you are signed in automatically, with every note private by default."
        ),
        "home.step_write_title": "Write a note",
        "home.step_write_body": (
            "Write in CommonMark, drop in images or paste screenshots, and the preview "
            "updates instantly."
        ),
        "home.step_share_title": "Share a read-only link",
        "home.step_share_body": (
            "Publish a note when you need to, send <code>/share/&lt;id&gt;</code> to anyone, "
            "and unpublish whenever you like."
        ),
        "home.stack_eyebrow": "Stack",
        "home.stack_title": "Thin server, a frontend done properly",
        "home.stack_lead": (
            "The backend stays thin while rendering and checks live in the browser; every "
            "third-party library is self-hosted, with no public CDN."
        ),
        "home.stack_aria": "Technology stack",
        "home.recent_eyebrow": "Public notes",
        "home.recent_title": "Recently published",
        "home.recent_lead": "These notes were published by their authors and are readable by anyone.",
        "home.recent_empty": "Nothing public yet. Sign in, write your first note and publish it.",
        "home.cta_eyebrow": "Start now",
        "home.cta_title": "Your next idea deserves a place online.",
        "home.footer": "Nooote · Online CommonMark notes · MIT License",
        "home.footer_aria": "Footer links",
        # ---------- auth ----------
        "auth.login_title": "Sign in · Nooote",
        "auth.login_eyebrow": "Welcome back",
        "auth.login_hero_line1": "Your notes",
        "auth.login_hero_line2": "are right where you left them.",
        "auth.login_hero_lead": (
            "Sign in to keep editing your private notes, or publish one as a read-only link."
        ),
        "auth.point_autosave": "Saved automatically when you pause",
        "auth.point_private": "Only you can edit each note",
        "auth.point_unpublish": "Public links can be revoked any time",
        "auth.aside_foot": "CommonMark · KaTeX · Mermaid",
        "auth.login_label": "Sign in",
        "auth.login_heading": "Welcome back",
        "auth.login_hint": "Sign in to view and manage your private notes.",
        "auth.username": "Username",
        "auth.password": "Password",
        "auth.confirm": "Confirm password",
        "auth.username_placeholder": "Your username",
        "auth.password_placeholder": "Enter your password",
        "auth.login_button": "Sign in",
        "auth.no_account": "No account yet?",
        "auth.register_link": "Sign up",
        "auth.register_title": "Sign up · Nooote",
        "auth.register_eyebrow": "Start writing",
        "auth.register_hero_line1": "Give your ideas",
        "auth.register_hero_line2": "a place online.",
        "auth.register_hero_lead": (
            "Create an account to get a private note space that saves as you type and "
            "publishes in one click."
        ),
        "auth.register_point_autologin": "Signed in right after signing up",
        "auth.register_point_markdown": "Markdown, math and diagrams included",
        "auth.register_point_hash": "Only password hashes are stored",
        "auth.register_aside_foot": "MIT License · Self-hosted · No tracking",
        "auth.register_label": "Sign up",
        "auth.register_heading": "Create your account",
        "auth.register_hint": "Create an account to save private notes.",
        "auth.register_username_placeholder": "3-32 characters",
        "auth.register_username_hint": "3-32 letters, digits, underscores, dots or hyphens.",
        "auth.register_password_placeholder": "At least 8 characters",
        "auth.register_password_hint": "At least 8 characters.",
        "auth.confirm_placeholder": "Enter the password again",
        "auth.create_button": "Create account",
        "auth.have_account": "Already have an account?",
        "auth.login_link": "Sign in",
        "auth.error_credentials": "Incorrect username or password",
        "auth.error_username_rule": (
            "The username must be {min_length}-{max_length} letters, digits, "
            "underscores, dots or hyphens"
        ),
        "auth.error_password_min": "The password must be at least {min_length} characters",
        "auth.error_password_max": "The password cannot exceed {max_length} characters",
        "auth.error_password_mismatch": "The two passwords do not match",
        "auth.error_username_taken": "That username is already taken",
        # ---------- console shell ----------
        "console.nav_aria": "Console navigation",
        "console.brand_subtitle": "Notes console",
        "console.create_note": "New private note",
        "console.workspace": "Workspace",
        "console.my_notes": "My notes",
        "console.attachments": "Files & images",
        "console.account": "Account",
        "console.settings": "Settings",
        "console.manage": "Site management",
        "console.back_home": "Back to home",
        "console.more_apps": "More apps",
        "console.overview_aria": "Note overview",
        "console.overview_title": "Overview",
        "console.private": "Private",
        "console.public": "Public",
        "console.note_count": "{total} notes · {attachments} files",
        "console.no_nickname": "No display name",
        "console.logout": "Sign out",
        "console.breadcrumb_aria": "Breadcrumb",
        "console.console": "Console",
        "console.browse_home": "Browse home",
        "console.page_title": "My console · Nooote",
        "console.crumb_notes": "My notes",
        "console.eyebrow": "Workspace",
        "console.heading_named": "{name}'s notes",
        "console.heading_default": "My notes",
        "console.lead_notes": (
            "{total} notes, {public} of them public. Only you can see private notes; once "
            "published they can be read at"
        ),
        "console.lead_share": "and edits to the private note sync automatically.",
        "console.stats_aria": "Note statistics",
        "console.stat_total": "All notes",
        "console.stat_private": "Private",
        "console.stat_public": "Public",
        "console.stat_attachments": "Files",
        "console.empty_note": "Empty note",
        "console.updated": "Updated",
        "console.badge_public": "Public · read-only",
        "console.badge_private": "Private",
        "console.unpublish": "Unpublish",
        "console.publish": "Publish",
        "console.edit": "Edit",
        "console.delete": "Delete",
        "console.confirm_delete": "Deleted notes cannot be recovered. Delete this note?",
        "console.empty_title": "No notes yet",
        "console.empty_body": "Click “New private note” in the sidebar and start writing.",
        # ---------- settings ----------
        "settings.page_title": "Settings · Nooote",
        "settings.crumb": "Settings",
        "settings.eyebrow": "Settings",
        "settings.heading": "Settings",
        "settings.lead_prefix": "Signed in as ",
        "settings.lead_suffix": ". These preferences are stored in your account.",
        "settings.saved": "Settings saved",
        "settings.display_name": "Display name",
        "settings.display_name_placeholder": "Leave empty to show “My notes”",
        "settings.display_name_hint": "Used for the console heading only, never on public notes.",
        "settings.appearance": "Appearance",
        "settings.theme_auto": "Follow system",
        "settings.theme_light": "Light",
        "settings.theme_dark": "Dark",
        "settings.theme_hint": "Applies to the home page, console and editor.",
        "settings.language": "Interface language",
        "settings.language_hint": "Takes effect immediately and is saved to your account.",
        "settings.default_public": "Publish new notes by default",
        "settings.default_public_hint": (
            "When checked, new notes immediately appear on a read-only "
            "<code>/share/&lt;id&gt;</code> page."
        ),
        "settings.save": "Save settings",
        "settings.back_console": "Back to console",
        "settings.permissions": "Permission group",
        "settings.role_member": "Member",
        "settings.role_admin": "Administrator",
        "settings.role_guest": "Guest",
        "settings.permissions_hint": (
            "The permission group on your account decides which pages and APIs you can "
            "reach; every request is checked on the server."
        ),
        "settings.permissions_granted": "Granted permissions",
        "settings.permissions_readonly": (
            "Groups are assigned by an administrator and cannot be changed here."
        ),
        # ---------- management ----------
        "manage.page_title": "Site management · Nooote",
        "manage.crumb": "Site management",
        "manage.eyebrow": "Administration",
        "manage.heading": "Site management",
        "manage.lead": "Review site-wide statistics and assign permission groups to accounts.",
        "manage.stats_title": "Site statistics",
        "manage.stat_users": "Accounts",
        "manage.stat_notes": "Notes",
        "manage.stat_public": "Public notes",
        "manage.stat_private": "Private notes",
        "manage.stat_attachments": "Files",
        "manage.stat_storage": "Storage",
        "manage.storage_detail": "Note text {notes} · attachments {attachments}",
        "manage.groups_title": "Permission groups",
        "manage.groups_lead": (
            "These permissions are checked on the server; a route is only reachable "
            "when it declares them."
        ),
        "manage.role_members": "{count} accounts",
        "manage.users_title": "Accounts & permission groups",
        "manage.users_lead": (
            "Administrators can change another account's group but never their own."
        ),
        "manage.joined": "Joined",
        "manage.change_role": "Change permission group",
        "manage.save_role": "Save",
        "manage.self_role": "You cannot change your own group",
        "manage.role_updated": "Updated the permission group for {username}",
        "manage.error_self_role": (
            "You cannot change your own permission group; ask another administrator."
        ),
        "manage.features_title": "Feature flags",
        "manage.features_lead": (
            "Disabling a feature immediately stops its routes and sidebar entry. "
            "Plugin features can be toggled independently."
        ),
        "manage.features_core": "Built-in features",
        "manage.feature_on": "On",
        "manage.feature_off": "Off",
        "manage.feature_enable": "Enable",
        "manage.feature_disable": "Disable",
        "manage.feature_updated": "Set {name} to {state}",
        # ---------- feature flags ----------
        "features.notes.label": "Notes",
        "features.notes.description": (
            "Private note list, editor, and saving API"
        ),
        "features.attachments.label": "Files & images",
        "features.attachments.description": (
            "Uploads, attachment management, and editor images; existing files "
            "stay reachable"
        ),
        "features.public_shares.label": "Public shares",
        "features.public_shares.description": (
            "Publishing, read-only share pages, and the public note list on the home page"
        ),
        "features.registration.label": "Registration",
        "features.registration.description": (
            "Allow visitors to create accounts; existing accounts can still log in"
        ),
        # ---------- attachments ----------
        "attachments.page_title": "Files & images · Nooote",
        "attachments.crumb": "Files & images",
        "attachments.eyebrow": "Attachments",
        "attachments.heading": "Files & images",
        "attachments.lead": (
            "Uploaded images and files are served through unguessable random links. Anyone "
            "with the link can view them, so do not upload anything sensitive."
        ),
        "attachments.upload": "Upload",
        "attachments.upload_hint": (
            "8 MiB per file. Images are inserted as Markdown images, other files as "
            "download links."
        ),
        "attachments.copy_link": "Copy link",
        "attachments.confirm_delete": (
            "Notes that reference this file will no longer show it. Delete it?"
        ),
        "attachments.delete": "Delete",
        "attachments.empty_title": "No files uploaded yet",
        "attachments.empty_body": "Upload an image and paste or drag it into the note editor.",
        "attachments.uploaded": "Uploaded {filename}",
        "attachments.deleted": "File deleted",
        # ---------- editor ----------
        "editor.title": "{note_id} · Private note · Nooote",
        "editor.back_console": "Back to console",
        "editor.badge_public": "Public · read-only",
        "editor.badge_private": "Private",
        "editor.view": "View",
        "editor.copy_link": "Copy link",
        "editor.unpublish": "Unpublish",
        "editor.publish": "Publish",
        "editor.saved": "Saved",
        "editor.updated": "Updated",
        "editor.edit": "Write",
        "editor.preview": "Preview",
        "editor.toolbar": "Quick formatting",
        "editor.bold": "Bold",
        "editor.italic": "Italic",
        "editor.strikethrough": "Strikethrough",
        "editor.inline_code": "Inline code",
        "editor.heading": "Heading",
        "editor.quote": "Quote",
        "editor.bullet_list": "Bullet list",
        "editor.numbered_list": "Numbered list",
        "editor.task_list": "Task list",
        "editor.link": "Insert link",
        "editor.code_block": "Code block",
        "editor.table": "Insert table",
        "editor.divider": "Divider",
        "editor.formula": "Inline formula",
        "editor.upload": "Upload image/file",
        "editor.placeholder": (
            "Write something… (Markdown / CommonMark); you can also drop or paste images"
        ),
        "editor.empty_hint": "Start typing and the preview appears here.",
        "editor.preview_aria": "Markdown preview",
        # ---------- share ----------
        "share.title": "{note_id} · Public note · Nooote",
        "share.back_home": "Back to home",
        "share.badge": "Public · read-only",
        "share.updated": "Updated",
        "share.copy_link": "Copy link",
        # ---------- markdown alerts ----------
        "markdown.note": "Note",
        "markdown.tip": "Tip",
        "markdown.important": "Important",
        "markdown.warning": "Warning",
        "markdown.caution": "Caution",
        # ---------- browser script ----------
        "js.just_now": "just now",
        "js.copied": "Copied",
        "js.copy_link": "Copy link",
        "js.copy_code": "Copy code",
        "js.copy_failed": "Copy failed",
        "js.view_code": "View code",
        "js.view_diagram": "View diagram",
        "js.mermaid_missing_src": "Missing Mermaid asset URL",
        "js.mermaid_unavailable": "Mermaid is unavailable after loading",
        "js.mermaid_load_failed": "Could not load Mermaid",
        "js.mermaid_render_failed": "Could not render the diagram",
        "js.mermaid_rendering": "Rendering diagram…",
        "js.saving": "Saving…",
        "js.too_large": "Content is too large to save",
        "js.typing": "Typing…",
        "js.saved": "Saved",
        "js.save_failed": "Save failed, retrying…",
        "js.uploading": "Uploading… ({done}/{total})",
        "js.upload_failed": "Upload failed",
        "js.editor_link_text": "link text",
        "js.editor_table_col": "Column {n}",
        "js.editor_table_cell": "Content",
        # ---------- errors ----------
        "error.invalid_note_id": "Invalid note id",
        "error.content_required": 'Expected JSON body with a "content" string',
        "error.content_too_large": "Note content is too large",
        "error.auth_required": "Authentication required",
        "error.forbidden": "You do not have permission to do that",
        "error.forbidden_title": "403 · Nooote",
        "error.forbidden_heading": "Access denied",
        "error.forbidden_body": (
            "The permission group on your account does not include access to this page."
        ),
        "error.feature_disabled": "This feature is disabled",
        "error.feature_disabled_title": "403 · Nooote",
        "error.feature_disabled_heading": "Feature disabled",
        "error.feature_disabled_body": (
            "An administrator turned this feature off. Contact the site "
            "administrator if you need it enabled."
        ),
        "error.back_home": "Back to home",
        "upload.file_required": "Choose a file to upload",
        "upload.file_too_large": "The file exceeds the upload limit",
        "upload.file_empty": "The file is empty",
        "upload.login_required": "Sign in first",
    },
}


def normalize_locale(value: str | None) -> str | None:
    """Return a supported locale code, or ``None`` for unsupported input."""
    return value if value in LOCALES else None


def _resolve_locale() -> str:
    from .services import current_user

    user = current_user()
    if user is not None:
        chosen = normalize_locale(user.locale)
        if chosen:
            return chosen

    if has_request_context():
        chosen = normalize_locale(request.cookies.get(LOCALE_COOKIE))
        if chosen:
            return chosen

    return DEFAULT_LOCALE


def current_locale() -> str:
    """Active locale: the account preference, then the cookie, then the default."""
    if not has_request_context():
        return DEFAULT_LOCALE

    cached = g.get("locale")
    if cached:
        return cached

    locale = _resolve_locale()
    g.locale = locale
    return locale


def translate(key: str, locale: str | None = None, **params) -> str:
    """Translate ``key`` with a target-locale, default-locale, key fallback chain."""
    chosen = normalize_locale(locale) or current_locale()
    message = MESSAGES.get(chosen, {}).get(key)
    if message is None:
        message = MESSAGES[DEFAULT_LOCALE].get(key)
    if message is None:
        return key
    if not params:
        return message
    try:
        return message.format(**params)
    except (KeyError, IndexError):
        return message


def t(key: str, **params) -> str:
    """Translate a key into the locale of the current request."""
    return translate(key, None, **params)


def html_lang(locale: str) -> str:
    return HTML_LANGS.get(locale, HTML_LANGS[DEFAULT_LOCALE])


def js_messages(locale: str) -> dict[str, str]:
    """Messages the browser script needs, resolved with the same fallbacks."""
    chosen = normalize_locale(locale) or DEFAULT_LOCALE
    keys = {
        key
        for source in (MESSAGES[chosen], MESSAGES[DEFAULT_LOCALE])
        for key in source
        if key.startswith(("js.", "markdown."))
    }
    return {key: translate(key, chosen) for key in sorted(keys)}


def set_locale_cookie(response, locale: str):
    response.set_cookie(
        LOCALE_COOKIE,
        locale,
        max_age=LOCALE_COOKIE_MAX_AGE,
        path="/",
        samesite="Lax",
    )
    return response

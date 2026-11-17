# 配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///notes.db` | 数据库连接，默认存放在 `instance/notes.db` |
| `SECRET_KEY` | 自动生成 | 会话签名密钥；未设置时自动生成并保存到 `instance/secret_key` |
| `UPLOAD_FOLDER` | `instance/uploads` | 附件与图片的存储目录 |
| `MAX_UPLOAD_BYTES` | `8 MiB` | 单个上传文件的大小上限 |
| `NOOOTE_ADMIN_USERNAMES` | 未设置 | 逗号分隔的用户名列表，这些账号注册后直接获得 `admin` 权限组 |
| `NOOOTE_SKIP_VENDOR_SYNC` | 未设置 | 设为任意非空值时跳过启动时的 vendor 资源同步 |

笔记内容上限为 256 KiB（`MAX_NOTE_BYTES`），请求体上限为 10 MiB。默认配置与共享常量集中在 `nooote/config.py`，可在应用工厂中覆盖。

## 界面语言

支持中文（默认）与英文。语言解析顺序为：登录账号的语言设置 → `lang` cookie → 默认中文。匿名访客切换语言时写入有效期一年的 `lang` cookie；登录用户在设置页选择后会写入账号，并优先于 cookie。所有文案集中在 `nooote/i18n.py`，没有额外的环境变量。

## 权限组

权限组与路由的权限声明见 [权限组](PERMISSIONS.md)。管理员用户名通过 `NOOOTE_ADMIN_USERNAMES` 指定，其余账号注册后默认获得 `member`。

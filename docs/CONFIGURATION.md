# 配置

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///notes.db` | 数据库连接，默认存放在 `instance/notes.db` |
| `SECRET_KEY` | 自动生成 | 会话签名密钥；未设置时自动生成并保存到 `instance/secret_key` |
| `UPLOAD_FOLDER` | `instance/uploads` | 附件与图片的存储目录 |
| `MAX_UPLOAD_BYTES` | `8 MiB` | 单个上传文件的大小上限 |
| `NOOOTE_SKIP_VENDOR_SYNC` | 未设置 | 设为任意非空值时跳过启动时的 vendor 资源同步 |

笔记内容上限为 256 KiB（`MAX_NOTE_BYTES`），请求体上限为 10 MiB。默认配置与共享常量集中在 `nooote/config.py`，可在应用工厂中覆盖。

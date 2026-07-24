# Windows 文件夹版封装设计

## 目标

为儿童影子跟读播放器制作可迁移的 Windows 文件夹版。用户从文件夹内双击
`ShadowingPlayer.exe` 即可启动，不需要另外安装 Python、libmpv、ffmpeg 或
faster-whisper 模型。

## 输出结构

```text
dist/ShadowingPlayer/
├─ ShadowingPlayer.exe
├─ models/
│  └─ faster-whisper-small/
├─ _internal/                 # PyInstaller、Qt、CTranslate2 等运行文件
└─ README.txt
```

libmpv、ffmpeg 和 ffprobe 可以位于 `_internal` 的专用子目录，由运行时加载器
加入当前进程 PATH。不会修改 Windows 全局 PATH。

## 封装方案

- 使用 PyInstaller `onedir` 模式。
- EXE 使用 `windowed` 模式，不显示命令行窗口。
- 应用图标嵌入 EXE。
- 收集 PySide6、python-mpv、pysubs2、faster-whisper、CTranslate2、
  onnxruntime 和其必要动态库。
- `libmpv-2.dll`、`ffmpeg.exe` 与 `ffprobe.exe` 随文件夹分发。
- faster-whisper `small` 模型直接复制到
  `models/faster-whisper-small`，不在第一次启动时重新下载。

## 运行时路径

开发环境继续读取：

```text
vendor/libmpv/libmpv-2.dll
%LOCALAPPDATA%/ShadowingPlayer/models/faster-whisper-small
```

封装环境优先读取：

```text
<EXE 文件夹>/models/faster-whisper-small
<PyInstaller 内部目录>/vendor/libmpv/libmpv-2.dll
<PyInstaller 内部目录>/vendor/ffmpeg/ffmpeg.exe
```

如果随包模型损坏或缺失，保留现有自动下载及错误指引作为后备路径。

用户设置、SQLite 进度与转写快取仍写入
`%LOCALAPPDATA%/ShadowingPlayer`，避免应用文件夹位于只读位置时失败。

## 图标

- 儿童友好的蓝紫色圆角播放器图标。
- 核心元素为播放三角形、对话气泡和声音回音。
- 不包含文字或水印。
- 先生成高分辨率 PNG，再转换为包含多个尺寸的 Windows `.ico`。
- 验证 16、32、48、128 和 256 像素下的辨识度。

## 构建与交付

- 新增可重复执行的 PyInstaller spec 与 PowerShell 构建脚本。
- 构建脚本检查模型、libmpv、ffmpeg 和 ffprobe，缺失时给出明确错误。
- 输出 `dist/ShadowingPlayer/`，并附带简体中文 `README.txt`。
- 不制作安装程序，不写注册表，不建立卸载项。

## 验证

1. 在封装目录以外启动 `ShadowingPlayer.exe`。
2. 确认程序不依赖项目源码或虚拟环境。
3. 打开 MKV 与 MP4，验证画面、声音、播放暂停和变速不变调。
4. 验证内嵌字幕抽取能够调用随包 ffmpeg。
5. 验证随包 faster-whisper 模型可直接加载，不发生下载。
6. 验证转写仍在背景执行并可取消。
7. 关闭程序后确认进程完整退出。

## 明确排除

- 不制作单文件版。
- 不制作 MSI、安装向导或自动更新。
- 不把用户设置、数据库或缓存写入应用文件夹。
- 不加入第三版录音、孩童模式或统计功能。

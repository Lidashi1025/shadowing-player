# 便携启动身份与易用性迭代设计规格

## 背景与根因

用户在 Windows 11 任务栏看到通用窗口图标，而不是应用的蓝紫图标。

本机诊断结果：

- 源码和打包目录中的 `app-icon.ico` 均包含 16、24、32、48、64、128、256 像素图层。
- Qt 能从 ICO 正确渲染蓝紫图标，`QIcon.isNull()` 为 `False`。
- 成品程序的 `Qt6111QWindowIcon` 顶层窗口通过 `WM_GETICON` 返回的大小图标也是正确蓝紫图标。
- 任务栏仍显示通用图标，因此故障不在 ICO、PyInstaller 资源或 Qt 窗口图标，而在 Windows 任务栏身份关联。

Microsoft 对 AppUserModelID 的要求是：若应用采用显式 ID，应将同一个 ID 同时写入启动快捷方式；目前便携文件夹只在进程上设置 `ShadowingPlayer.Desktop`，没有匹配的快捷方式属性，身份链不完整。

## 任务栏修复方案

采用适合单进程便携程序的系统定义身份：

1. 不再调用 `SetCurrentProcessExplicitAppUserModelID`。
2. 保留 EXE 资源图标、`QApplication.setWindowIcon()` 和 `MainWindow.setWindowIcon()`。
3. 新增“创建桌面快捷方式”，使用 Windows 自带 PowerShell/WScript.Shell 按当前 EXE 绝对路径生成 `.lnk`，并将 `IconLocation` 指向当前 EXE 的图标资源。
4. 程序文件夹移动后，用户可再次执行该功能覆盖旧快捷方式，使目标路径与图标同步更新。
5. 不尝试自动固定到任务栏；用户从新桌面快捷方式启动后可自行固定，避免修改 Windows 用户固定项。

## 本轮易用性优化

### 拖放打开视频

- 主窗口接受本机文件拖放。
- 仅接受单个 `.mkv` 或 `.mp4` 文件。
- 拖入合法文件时显示可接受状态，放下后调用现有 `open_video(Path)`，因此字幕发现、转写询问、进度恢复等行为完全复用。
- 多文件、文件夹和其他扩展名不接受，不弹出干扰性错误框。

### 时间与句数信息

在左侧字幕区的分段进度条下增加一行轻量信息：

- 左侧：当前播放时间，格式 `MM:SS` 或 `H:MM:SS`。
- 中间：有句子时显示 `第 N / M 句`，无句子时显示 `暂无句子`。
- 右侧：影片总时长。

信息由现有 `position_changed`、`duration_changed` 和 `current_changed` 信号更新，不增加轮询计时器。

### 工具菜单

顶部增加一个紧凑的“工具”按钮，菜单包含：

- `创建桌面快捷方式`
- `打开数据目录`
- `快捷键说明`

“打开数据目录”使用系统文件管理器打开 `%LOCALAPPDATA%\ShadowingPlayer`；“快捷键说明”显示当前设置中的实际键位，不硬编码默认键位。所有菜单项均为用户主动触发，不在启动时修改桌面或打开外部窗口。

## 模块边界

- 修改 `runtime/app_identity.py`：只负责图标路径和 Qt 应用名称/图标，不再设置显式 AppUserModelID。
- 新增 `runtime/windows_shortcut.py`：计算当前可执行文件、调用 PowerShell 创建桌面 `.lnk`，返回创建路径或抛出明确错误。
- 修改 `app.py`：移除进程 AppUserModelID 调用。
- 修改 `ui/main_window.py`：增加拖放事件、时间标签、工具菜单及三个动作。
- 修改 `ui/theme.py`：为工具按钮、菜单和时间信息补充暗色样式。
- 修改 `ui/strings.py`：新增简体中文文案。

## 测试与验收

- 单元测试证明 `main()` 不再调用显式 AppUserModelID 设置函数。
- 单元测试验证桌面快捷方式命令包含目标、工作目录、图标位置和中文快捷方式名，且 PowerShell 失败时抛出包含 stderr 的错误。
- Qt 集成测试验证合法拖放进入并调用 `open_video`，非法格式不接受。
- Qt 集成测试验证时间格式、位置/总时长更新、当前句/总句数更新。
- Qt 集成测试验证工具菜单三项均存在，快捷键说明使用当前设置。
- 完整测试、真实窗口截图、PyInstaller 构建与冻结程序冒烟测试必须通过。
- 在当前桌面实际创建新版快捷方式，并验证其目标和图标位置指向新成品 EXE。

## 范围排除

- 不实现录音、孩童模式、统计、每日目标或 AI 发音评分。
- 不修改 SQLite 结构。
- 不自动固定或取消固定任务栏项目。
- 不加入在线服务。

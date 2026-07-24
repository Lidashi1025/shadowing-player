# 儿童影子跟读播放器

Windows 11 本机播放器，以字幕时间轴为句子边界，支持 MKV／MP4、逐句跟读、单句精听和变速不变调播放。当前实现产品规划书的第二版；不包含录音、儿童模式或统计功能。

## 环境要求

- Windows 11 x64
- Python 3.12–3.14 x64（当前验证版本：3.14.3）
- `vendor/libmpv/libmpv-2.dll`，取得方式见 [vendor/libmpv/README.md](vendor/libmpv/README.md)
- `ffmpeg.exe` 与 `ffprobe.exe` 位于 PATH（读取内嵌字幕时需要）
- 首次自动转写需要网络下载 faster-whisper `small` 模型；转写本身在本机 CPU 执行

## 安装与启动

在 PowerShell 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m shadowing_player
```

点击“打开视频”后可选择 `.mkv` 或 `.mp4`。字幕来源如下：

1. 同目录、同文件名或带语言后缀的 `.srt`／`.ass`。
2. 视频内嵌文字字幕；优先选择英文轨。
3. 完全没有字幕时，可确认使用 faster-whisper 自动转写英文。

图片型字幕无法生成句子列表，程序会显示明确提示。

顶部“最近观看”会列出最近打开且仍然存在的 8 部影片。也可将单个
`.mkv` 或 `.mp4` 文件直接拖入主窗口。文件夹版用户可通过
“工具”→“创建桌面快捷方式”生成带应用图标的快捷方式；移动程序文件夹后
重新执行一次即可更新目标路径。

## 功能

- 观看模式：连续播放，句子列表和大字字幕跟随当前位置。
- 逐句跟读：每句播放 1–3 次，按句长乘以留白倍数暂停，再自动或手动进入下一句。
- 单句精听：当前句持续无限循环，按 Space 可随时暂停或继续。
- 影子跟读：以 `0.50×–1.00×` 连续播放；mpv 自动插入 `scaletempo2` 保持音调。
- 点击句子列表或分段进度条可精确跳句。
- 自动记忆每部影片的位置、速度、模式与字幕来源；重新打开时恢复但保持暂停。
- 无字幕影片以 faster-whisper `small`、CPU、int8、固定英文进行后台转写；底部显示进度、预计时间并可取消，播放控制不会被锁住。
- 转写结果保存在程序目录的 `cache\transcriptions\<影片快速哈希>.srt`，再次打开直接读取；旧版 `%LOCALAPPDATA%` 快取会自动迁移。
- 中文只从现有外部或内嵌字幕取得，以时间重叠对齐；可切换“英文／双语／隐藏”。
- 只有中文字幕时，程序自动在后台生成英文，再与现有中文对齐；第二次打开直接使用英文快取。
- 句子表格的星号可收藏句子，“复习清单”可跨影片逐句跟读；找不到来源影片时自动跳过。
- 可合并两个相邻句子，或在当前播放位置拆分句子；编辑结果保存在 SQLite。
- 字幕区显示当前播放时间、当前句数和影片总时长。
- 点击右侧句子文字会先精确跳到句首，再按当前模式播放。
- 底部双层常驻功能坞把全部快捷键功能做成可见按钮：第一层是播放与状态动作，第二层是练习参数。播放使用实心蓝，字幕／循环等激活状态使用蓝色，收藏状态使用金色。
- “工具”菜单可创建桌面快捷方式、打开数据目录并编辑全部快捷键；保存前会检查按键冲突。

全局设置保存在 `%LOCALAPPDATA%\ShadowingPlayer\settings.json`，播放进度保存在 `%LOCALAPPDATA%\ShadowingPlayer\data.sqlite`。

源码版的语音模型自动下载到：

```text
%LOCALAPPDATA%\ShadowingPlayer\models\faster-whisper-small
```

Windows 文件夹版则把模型放在程序目录的
`models\faster-whisper-small`，复制整个程序文件夹即可连同模型迁移。

自动下载失败时，程序会显示目标路径及手动下载命令。也可在项目虚拟环境中执行：

```powershell
.\.venv\Scripts\python.exe -c "from faster_whisper.utils import download_model; import os; download_model('small', output_dir=os.path.join(os.environ['LOCALAPPDATA'], 'ShadowingPlayer', 'models', 'faster-whisper-small'))"
```

## 快捷键

| 按键 | 功能 |
|---|---|
| Ctrl+O | 打开视频 |
| Ctrl+H | 最近观看 |
| Space | 播放／暂停；留白期间暂停／继续倒数 |
| ← | 重播本句；仍兼容 400ms 内连按两次为上一句 |
| Ctrl+← | 上一句 |
| → | 下一句 |
| ↑／↓ | 加速／减速 0.05 |
| L | 切换单句精听 |
| M | 依序切换英文／双语／隐藏字幕 |
| Tab | 切换播放模式 |
| S | 收藏／取消收藏当前句 |
| R | 打开跨影片复习清单 |
| F | 全屏／退出全屏 |
| F1 | 快捷键设置 |

以上功能均有常驻按钮，鼠标悬停会显示当前按键；按键也可在“工具”→“快捷键设置”中修改或恢复默认。收藏也可直接点击句子表格右侧的星号；录音不属于第二版。

## 转写性能验证

在本机以实际英文卡通的 60 秒音频测试 faster-whisper `small`、CPU、
int8、beam size 5：模型载入约 0.89 秒，转写约 3.58 秒，约为实时速度的
16.7 倍。beam size 1 虽可缩短到约 2.52 秒，但输出字符数少约 15%，因此
保留 beam size 5 作为准确度与速度的默认平衡。

## 数据库升级

第一次以第二版启动时，程序会用事务迁移第一版数据库，并在同目录建立一次性 `data.sqlite.v0.bak`。原有影片位置、速度、模式与字幕来源会保留；迁移失败时会回滚。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

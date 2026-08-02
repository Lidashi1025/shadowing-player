# Windows libmpv

本项目使用项目内 DLL，不修改 Windows 全局 PATH。

## 已验证版本

- 来源：[Shinchiro mpv-winbuild-cmake](https://github.com/shinchiro/mpv-winbuild-cmake/releases/tag/20260610)
- 压缩包：`mpv-dev-x86_64-20260610-git-304426c.7z`
- 压缩包 SHA256：`8CBB25EA784F01AFBB3F904217CAB1317430A8BCFD5680FD827A866367F71CC9`
- 目标文件：`libmpv-2.dll`

## 放置方式

1. 从发布页下载名称以 `mpv-dev-x86_64-` 开头的压缩包。不要下载普通的 `mpv-x86_64` 播放器包。
2. 校验压缩包：

   ```powershell
   Get-FileHash .\mpv-dev-x86_64-20260610-git-304426c.7z -Algorithm SHA256
   ```

3. 从压缩包根目录取出 `libmpv-2.dll`，放到本 README 所在目录：

   ```text
   vendor/libmpv/libmpv-2.dll
   ```

4. DLL 与 Python 必须采用相同架构；本项目使用 x64。

`libmpv-2.dll` 已由 `.gitignore` 排除。程序启动时只会把此目录加入当前进程的 DLL 搜索路径，然后再导入 `python-mpv`。

## 许可 / License (重要)

Shinchiro 的 Windows 构建**可能包含 GPL 组件**，具体取决于发布变体与 configure flags。  
本仓库主体为 **MIT**。若你要**公开发布文件夹版**，请自行核实所用 `libmpv-2.dll` 的许可构成：

1. 优先使用上游标注为 **LGPL** 或可确认无 GPL 传染的构建。
2. 将对应的 COPYING / LICENSE 文本放入 `packaging/licenses/`，打包脚本会复制到 dist。
3. 在 `packaging/licenses/NOTICE.txt` 中说明实际捆绑版本。

未核实前，请勿假设「放进 MIT 仓库 = 可随意再分发 libmpv/ffmpeg 二进制」。

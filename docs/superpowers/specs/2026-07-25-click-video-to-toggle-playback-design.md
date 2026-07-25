# 点击影片画面切换播放设计

## 目标

鼠标左键单击影片画面时，复用现有播放／暂停动作。未载入影片时无动作；逐句练习
处于留白阶段时，点击行为与空白键一致，暂停或继续倒数。

## 设计

新增独立的 `ClickableVideoWidget`。它只在左键于元件内按下并放开、移动距离没有
超过 Qt 拖动阈值时发出 `clicked` 信号。右键、拖动及在元件外放开均不触发。

`MainWindow` 以该元件取代普通 `QWidget` 作为 libmpv 的原生渲染目标，并把
`clicked` 连接到既有 `_toggle_if_available()`。因此影片未载入时沿用播放按钮的
禁用状态，正常播放、暂停及留白倒数全部复用 `SessionController.toggle_pause()`。

## 验证

- 元件测试覆盖左键单击、右键及拖动。
- 主视窗测试覆盖已载入时切换播放／暂停及未载入时无动作。
- 完整 pytest、compileall、Windows 封装与冻结 EXE smoke test。

# Double-Click Video Fullscreen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Toggle fullscreen by double-clicking the video without also toggling playback.

**Architecture:** Add a `double_clicked` signal and defer single-click emission until Qt's double-click interval expires. Connect the new signal to the existing fullscreen action.

**Tech Stack:** Python, PySide6, pytest, pytest-qt.

- [ ] Add failing widget tests proving double-click emits only `double_clicked`.
- [ ] Add failing main-window test proving double-click toggles fullscreen and back.
- [ ] Implement timer-based click disambiguation.
- [ ] Connect `double_clicked` to `_toggle_fullscreen()`.
- [ ] Run focused tests, complete tests, compileall, package build, and smoke test.

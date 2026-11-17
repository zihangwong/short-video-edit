# short-video-edit

一个 agent skill：把竖屏口播短视频（TikTok / Reels / 小红书 / Shorts）从原始素材一路剪到成片，按专业剪辑师的标准交付。
为 Claude Code 打造，也适用于其他支持 `SKILL.md` 的 agent。

[English](README.md)

## 它做什么

| 步骤 | 内容 |
|---|---|
| 1 粗剪 | 转写素材，对照脚本（口播数字和脚本不一致会提醒），挑最好的 take，自动收紧停顿，输出带时间码的粗剪预览和剪辑点检查 |
| 2 识别字幕 | faster-whisper 逐字时间戳 → 按 jieba 分词断成单行字幕 |
| 3 字幕特效 + 音效 | 12 种动画（砸入、落下、打字、盖章、波浪…），每个动画自动配音效；安全框检查；加速 1.2× 后时序依然正确 |
| 4 B-roll & MG | 数据卡片、设计师素材、动态图形；用 RobustVideoMatting 抠像，自动判断文字放在人物前面还是后面 |
| 5 BGM & 交付 | 动态模糊渲染、单声道人声修复、−13 LUFS 响度、BGM 自动闪避、真峰值 ≤ −1.2 dBTP、`.srt`、手机预览、TikTok/Reels 平台检查 |
| 6 定稿 | 只有用户说定稿才执行：成片移到「视频」文件夹，其他中间文件进回收站（不会永久删除） |

剪辑判断（选 take、校字幕、哪些词做特效）由 agent 做；测量和渲染由脚本完成，没看过、没测过的东西不会说「完成」。

## 环境要求

- Windows 10/11（定稿步骤和部分系统字体依赖 Windows）
- Python 3.12，`pip install -r requirements.txt`
- FFmpeg 7+（有 NVIDIA 显卡时使用 NVENC）
- Node.js 20+（用于 `npx openfilm@0.3.2`）
- 建议有 NVIDIA 显卡跑 faster-whisper，没有会退回 CPU

## 安装

```
git clone https://github.com/bubeishisuqiangua/short-video-edit.git .claude/skills/short-video-edit
pip install -r .claude/skills/short-video-edit/requirements.txt
```

然后对 agent 说：「用 short-video-edit 把这段素材和脚本剪成 episodes/ep01」。

## 第三方素材

- `assets/fonts/` 里的 **Noto Sans SC** 字体：SIL Open Font License 1.1（见 `assets/fonts/OFL.txt`）。
- **RobustVideoMatting** 模型：GPL-3.0，**不包含在仓库里**，首次使用时从[官方发布页](https://github.com/PeterL1n/RobustVideoMatting)自动下载。
- 音效和 BGM 在渲染时从 OpenFilm CC0 素材库获取，仓库不存放。
- 只使用你有权使用的素材、字体和音乐。

## 许可

本仓库代码使用 MIT 协议；第三方素材遵循各自的协议（见上）。

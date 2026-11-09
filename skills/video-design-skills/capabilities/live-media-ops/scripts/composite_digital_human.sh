#!/usr/bin/env bash
# composite_digital_human.sh — 数字人层 + 公司视频合成
# 前置：ffmpeg / ffprobe（用户机未装时脚本会直接报错提示）
#
# 用法示例：
#   bash composite_digital_human.sh --presenter p.mp4 --company c.mp4 --layout pip --output out.mp4
#   bash composite_digital_human.sh --presenter p.mp4 --company c.mp4 --audio voice.mp3 --layout background
#   bash composite_digital_human.sh --presenter p.mp4 --company c.mp4 --subtitles s.srt --layout split
#   bash composite_digital_human.sh --presenter p.mp4 --company c.mp4 --dry-run   # 只看命令不执行

set -euo pipefail

PRESENTER=""
COMPANY=""
AUDIO=""
SUBTITLES=""
LAYOUT="pip"
OUTPUT="final.mp4"
WIDTH=1080
HEIGHT=1920
FPS=30
DRY_RUN=0

usage() {
  cat <<'EOF'
用法：
  composite_digital_human.sh --presenter <数字人视频> --company <公司视频>
                            [--audio <配音>] [--subtitles <字幕.srt>]
                            [--layout pip|split|background] [--output <输出.mp4>]
                            [--width 1080] [--height 1920] [--fps 30] [--dry-run]

布局：
  pip         公司视频缩到 30% 宽，嵌在右下角（默认）
  split       左右各占一半，等比填充
  background  公司视频模糊铺底，数字人居中前景

音轨优先级：--audio > presenter 自带 > company 自带 > 静音。
所有布局输出统一为 width x height（默认 1080x1920），不会因源素材尺寸跑偏。
字幕需要 ffmpeg 编译了 libass；没编译时脚本会警告并跳过字幕，不中断出片。
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --presenter) PRESENTER="$2"; shift 2 ;;
    --company)   COMPANY="$2";   shift 2 ;;
    --audio)     AUDIO="$2";     shift 2 ;;
    --subtitles) SUBTITLES="$2"; shift 2 ;;
    --layout)    LAYOUT="$2";    shift 2 ;;
    --output)    OUTPUT="$2";    shift 2 ;;
    --width)     WIDTH="$2";     shift 2 ;;
    --height)    HEIGHT="$2";    shift 2 ;;
    --fps)       FPS="$2";       shift 2 ;;
    --dry-run)   DRY_RUN=1;      shift ;;
    --help|-h)   usage; exit 0 ;;
    *) echo "未知参数: $1" >&2; usage >&2; exit 1 ;;
  esac
done

missing=""
for bin in ffmpeg ffprobe; do
  command -v "$bin" >/dev/null 2>&1 || missing="${missing} ${bin}"
done
if [[ -n "$missing" ]]; then
  echo "缺少依赖:${missing}" >&2
  echo "" >&2
  echo "这台机器没装 ffmpeg。三条路，选一条：" >&2
  echo "  1) 装：macOS 用 brew install ffmpeg；Linux 用 apt install ffmpeg" >&2
  echo "  2) 不装，用剪映合成：数字人放主轨，公司视频放画中画，缩到右下角，导出 1080P" >&2
  echo "  3) 走零工具路线：不合成，只出分镜表 + 素材清单 + 操作步骤" >&2
  echo "" >&2
  echo "零工具路线完整步骤见 references/no-tools.md。" >&2
  exit 1
fi
[[ -n "$PRESENTER" && -f "$PRESENTER" ]] || { echo "缺少或找不到 --presenter 视频" >&2; exit 1; }
[[ -n "$COMPANY" && -f "$COMPANY" ]]     || { echo "缺少或找不到 --company 视频"   >&2; exit 1; }
[[ -z "$AUDIO" || -f "$AUDIO" ]]         || { echo "找不到 --audio 文件: $AUDIO"    >&2; exit 1; }
[[ -z "$SUBTITLES" || -f "$SUBTITLES" ]] || { echo "找不到 --subtitles 文件: $SUBTITLES" >&2; exit 1; }
case "$LAYOUT" in pip|split|background) ;; *) echo "不支持的 --layout: $LAYOUT" >&2; exit 1 ;; esac

even() { echo $(( ($1 / 2) * 2 )); }
W=$(even "$WIDTH")
H=$(even "$HEIGHT")
HALF=$(even $(( W / 2 )))
BG_W=$(even "$W")
FG_W=$(even $(( W * 6 / 10 )))
FG_H=$(even $(( H * 8 / 10 )))

has_audio() {
  [[ -n "$(ffprobe -v error -select_streams a:0 -show_entries stream=index -of csv=p=0 "$1" 2>/dev/null)" ]]
}

INPUTS=(-i "$PRESENTER" -i "$COMPANY")
AIDX=""
if [[ -n "$AUDIO" ]]; then
  INPUTS+=(-i "$AUDIO"); AIDX="2"
elif has_audio "$PRESENTER"; then
  AIDX="0"
elif has_audio "$COMPANY"; then
  AIDX="1"
fi

case "$LAYOUT" in
  pip)
    FILTER="[0:v]scale=${W}:${H}:force_original_aspect_ratio=increase,crop=${W}:${H},setsar=1[base];"
    FILTER+="[1:v]scale=iw*0.30:-2[cmp];"
    FILTER+="[base][cmp]overlay=W-w-20:H-h-20:format=auto[outv]"
    ;;
  split)
    FILTER="[0:v]scale=${HALF}:${H}:force_original_aspect_ratio=increase,crop=${HALF}:${H},setsar=1[va];"
    FILTER+="[1:v]scale=${HALF}:${H}:force_original_aspect_ratio=decrease,"
    FILTER+="pad=${HALF}:${H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1[vb];"
    FILTER+="[va][vb]hstack=inputs=2[outv]"
    ;;
  background)
    FILTER="[1:v]scale=${BG_W}:${H}:force_original_aspect_ratio=increase,crop=${BG_W}:${H},gblur=sigma=25[bg];"
    FILTER+="[0:v]scale=${FG_W}:${FG_H}:force_original_aspect_ratio=decrease,setsar=1[fg];"
    FILTER+="[bg][fg]overlay=(W-w)/2:(H-h)/2[outv]"
    ;;
esac

CUR="outv"
if [[ -n "$SUBTITLES" && -f "$SUBTITLES" ]]; then
  if ffmpeg -hide_banner -filters 2>/dev/null | awk '{print $2}' | grep -qx 'subtitles'; then
    SUB_ESC=${SUBTITLES//\'/\\\'}
    FILTER+=";[${CUR}]subtitles='${SUB_ESC}'[vsub]"
    CUR="vsub"
  else
    echo "⚠ 当前 ffmpeg 未编译 libass，烧不了字幕——本次跳过字幕，继续出无字幕成片。" >&2
    echo "  要烧字幕：换一个带 libass 的 ffmpeg，或用剪映 / 平台内加字幕再合成。" >&2
  fi
fi

MAP_ARGS=(-map "[${CUR}]")
AOPTS=()
if [[ -n "$AIDX" ]]; then
  MAP_ARGS+=(-map "${AIDX}:a:0")
  AOPTS=(-c:a aac -b:a 192k)
else
  MAP_ARGS+=(-an)
fi

CMD=(ffmpeg -y "${INPUTS[@]}" -filter_complex "$FILTER" "${MAP_ARGS[@]}"
     -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r "$FPS" "${AOPTS[@]}" -shortest "$OUTPUT")

if [[ "$DRY_RUN" == "1" ]]; then
  echo "--- 将执行 ---"
  printf '%q ' "${CMD[@]}"
  echo
  exit 0
fi

mkdir -p "$(dirname "$OUTPUT")"
echo "▶ 合成中：presenter=$PRESENTER | company=$COMPANY | 布局=$LAYOUT | ${W}x${H} → $OUTPUT"
"${CMD[@]}"
echo "✅ 成片已生成：$OUTPUT"

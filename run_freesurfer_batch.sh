#!/bin/bash
# 批量运行 FreeSurfer recon-all，适配 MIND 项目结构

# 使用绝对路径，WSL2 对相对路径的解析有时会因 cd 命令出错
INPUT_ROOT=$(realpath "./data/NIfTI")
OUTPUT_DIR=$(realpath "./data/Recon-Result")
export FS_LICENSE="/usr/local/freesurfer/license.txt"  # 必须 export 给子进程
MAX_PARALLEL=6  # FreeSurfer 是内存密集型，建议 4-8 个并行

# 检查 FreeSurfer 环境
if ! command -v recon-all &> /dev/null; then
  echo "未检测到 recon-all，请先配置好 FreeSurfer 环境！"
  exit 1
fi

if [ ! -d "$OUTPUT_DIR" ]; then
  mkdir -p "$OUTPUT_DIR"
fi

# 收集所有 NIfTI 路径和被试ID
TASKS=()
for group in HC PD prodromal; do
  [ -d "$INPUT_ROOT/$group" ] || continue
  for subj_dir in "$INPUT_ROOT/$group"/*; do
    [ -d "$subj_dir" ] || continue
    subj=$(basename "$subj_dir")
    for nii in "$subj_dir"/*.nii*; do
      [ -f "$nii" ] || continue
      # 用冒号或管道符分割，确保路径中包含空格时不会崩
      TASKS+=("$nii|$subj|$group")
    done
  done
done

echo "共找到 ${#TASKS[@]} 个任务，准备并行处理 (并行数: $MAX_PARALLEL) ..."

# 并行处理
function run_one() {
  # 使用 IFS 确保变量读取准确
  IFS='|' read -r nii_path subj group <<< "$1"
  
  # 重新组合 SID，确保唯一性
  local full_sid="${group}_${subj}"
  local target_sd="$OUTPUT_DIR/$group"
  
  mkdir -p "$target_sd"
  
  echo ">>> 开始处理: $full_sid ($group)"
  # 执行 recon-all，-no-isrunning 跳过旧锁文件
  recon-all -i "$nii_path" -s "$full_sid" -sd "$target_sd" -all -no-isrunning
  echo "<<< 处理完成: $full_sid ($group)"
}

export -f run_one
export OUTPUT_DIR

# 只保留一行 printf，修正参数传递方式
# 之前的脚本里写了两行 printf，会导致同一个任务跑两遍，产生文件锁冲突
printf "%s\n" "${TASKS[@]}" | xargs -n 1 -P $MAX_PARALLEL -I {} bash -c 'run_one "$@"' _ {}

echo "全部任务执行完毕！"

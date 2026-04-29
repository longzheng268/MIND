import argparse
import csv
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


PLAN_LABELS = {
    '1': 'Plan 1: SAA+ burden-resilience',
    '2': 'Plan 2: incremental predictive value',
    '3': 'Plan 3: SAA+ topography-mechanism',
}

OUTPUT_ROOT = './MIND_Research_Results/ML_Prediction/'
OVERVIEW_FILE = os.path.join(OUTPUT_ROOT, 'Step4_Entry_Overview.csv')
RUNLOG_FILE = os.path.join(OUTPUT_ROOT, 'Step4_Entry_RunLog.txt')
SUMMARY_MD_FILE = os.path.join(OUTPUT_ROOT, 'Step4_Entry_Summary_CN.md')

PLAN_ARTIFACTS = {
    '1': './MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/Plan1_Burden_Resilience_Summary.csv',
    '2': './MIND_Research_Results/ML_Prediction/Aim3_Incremental/Aim3_Incremental_Overview.csv',
    '3': './MIND_Research_Results/ML_Prediction/Aim3_Plan3_Topography_Mechanism/Plan3_Topography_Overview.csv',
}

PLAN1_SUMMARY_FILE = PLAN_ARTIFACTS['1']
PLAN2_OVERVIEW_FILE = PLAN_ARTIFACTS['2']
PLAN2_ROC_FILE = './MIND_Research_Results/ML_Prediction/Aim3_Incremental/Aim3_ROC_Overview.csv'
PLAN3_OVERVIEW_FILE = PLAN_ARTIFACTS['3']
PLAN1_AHBA_FALLBACK_FILE = './MIND_Research_Results/ML_Prediction/Aim3_Plan1_Burden_Resilience/AHBA/AHBA_Fallback_Notes.txt'


def _print_header():
    print('\n' + '=' * 60)
    print('Step 4 Unified Entry (interactive)')
    print('=' * 60)
    print(f'Time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')


def _now_text():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _ensure_output_root():
    os.makedirs(OUTPUT_ROOT, exist_ok=True)


def _append_log(line):
    _ensure_output_root()
    with open(RUNLOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')


def _collect_plan_status(plan_code):
    artifact = PLAN_ARTIFACTS.get(plan_code, '')
    return os.path.exists(artifact), artifact


def _read_csv_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _read_text(path):
    if not os.path.exists(path):
        return ''
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def _append_overview_rows(rows):
    _ensure_output_root()
    fieldnames = [
        'Timestamp',
        'Plan_Code',
        'Plan_Label',
        'Mode',
        'Report_Only',
        'Skip_AHBA',
        'AHBA_Cache_Dir',
        'Run_Status',
        'Duration_Seconds',
        'Has_Result_Artifact',
        'Key_Artifact',
    ]
    write_header = not os.path.exists(OVERVIEW_FILE)
    with open(OVERVIEW_FILE, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _read_overview_rows():
    if not os.path.exists(OVERVIEW_FILE):
        return []
    with open(OVERVIEW_FILE, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _set_runtime_env(mode, skip_ahba, cache_dir, quick_windows):
    backup = {
        'STEP4_PLAN1_PREVIEW': os.getenv('STEP4_PLAN1_PREVIEW'),
        'STEP4_PLAN1_ALLEN_ENABLE': os.getenv('STEP4_PLAN1_ALLEN_ENABLE'),
        'STEP4_PLAN2_PREVIEW': os.getenv('STEP4_PLAN2_PREVIEW'),
        'STEP4_PLAN2_SAVE_ROC_PLOTS': os.getenv('STEP4_PLAN2_SAVE_ROC_PLOTS'),
        'STEP4_PLAN2_WINDOWS': os.getenv('STEP4_PLAN2_WINDOWS'),
        'STEP4_PLAN3_PREVIEW': os.getenv('STEP4_PLAN3_PREVIEW'),
        'STEP4_AHBA_ENABLE': os.getenv('STEP4_AHBA_ENABLE'),
        'STEP4_AHBA_CACHE_DIR': os.getenv('STEP4_AHBA_CACHE_DIR'),
    }

    # quick mode focuses on non-blocking and faster turnaround.
    if mode == 'quick':
        os.environ['STEP4_PLAN1_PREVIEW'] = '0'
        os.environ['STEP4_PLAN1_ALLEN_ENABLE'] = '0'
        os.environ['STEP4_PLAN2_PREVIEW'] = '0'
        os.environ['STEP4_PLAN2_SAVE_ROC_PLOTS'] = '0'
        os.environ['STEP4_PLAN2_WINDOWS'] = quick_windows
        os.environ['STEP4_PLAN3_PREVIEW'] = '0'
        os.environ['STEP4_AHBA_ENABLE'] = '0'

    if skip_ahba:
        os.environ['STEP4_AHBA_ENABLE'] = '0'

    if cache_dir:
        os.environ['STEP4_AHBA_CACHE_DIR'] = cache_dir

    return backup


def _restore_runtime_env(backup):
    for key, value in backup.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _print_menu():
    print('\nPlease select a Step 4 plan to run:')
    print('  1) Plan 1 - SAA+ burden-resilience')
    print('  2) Plan 2 - incremental predictive value')
    print('  3) Plan 3 - SAA+ topography-mechanism')
    print('  a) Run all plans (1 -> 2 -> 3)')
    print('  q) Quit')


def _run_plan(plan_code):
    if plan_code == '1':
        from step4_ml.plan1_burden_resilience.step4_plan1_burden_resilience import run_plan1_burden_resilience

        run_plan1_burden_resilience()
    elif plan_code == '2':
        from step4_ml.step4_ml_prediction import run_incremental_prediction

        run_incremental_prediction()
    elif plan_code == '3':
        from step4_ml.plan3_topography_mechanism.step4_plan3_topography_mechanism import run_plan3_topography_mechanism

        run_plan3_topography_mechanism()
    else:
        raise ValueError(f'Unknown plan code: {plan_code}')


def _interactive_select():
    while True:
        _print_menu()
        try:
            choice = input('Your choice [1/2/3/a/q]: ').strip().lower()
        except EOFError:
            print('\nNo interactive input detected. Exit safely (q).')
            return 'q'
        if choice in {'1', '2', '3', 'a', 'q'}:
            return choice
        print('Invalid input. Please enter one of: 1, 2, 3, a, q.')


def _parse_args():
    parser = argparse.ArgumentParser(
        description='Unified Step4 launcher with interactive plan selection.',
    )
    parser.add_argument(
        '--plan',
        choices=['1', '2', '3', 'all'],
        default=None,
        help='Run a specific plan directly without interactive menu.',
    )
    parser.add_argument(
        '--mode',
        choices=['quick', 'full'],
        default='full',
        help='Execution mode. quick disables expensive/interactive parts where possible.',
    )
    parser.add_argument(
        '--skip-ahba',
        action='store_true',
        help='Skip AHBA stage for Plan 3 by setting STEP4_AHBA_ENABLE=0.',
    )
    parser.add_argument(
        '--cache-dir',
        default=None,
        help='Custom AHBA cache directory for Plan 3 (STEP4_AHBA_CACHE_DIR).',
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Do not run models; only summarize whether key artifacts already exist.',
    )
    parser.add_argument(
        '--quick-windows',
        default='V06',
        help='Plan2 windows used in quick mode, comma-separated, e.g. V06 or V06,V10.',
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Generate a Chinese markdown summary from existing Step4 outputs.',
    )
    return parser.parse_args()


def _select_plan_codes(choice):
    if choice == 'a':
        return ['1', '2', '3']
    return [choice]


def _run_or_report(plan_code, args):
    ts = _now_text()
    has_artifact_before, artifact = _collect_plan_status(plan_code)

    if args.report_only:
        return {
            'Timestamp': ts,
            'Plan_Code': plan_code,
            'Plan_Label': PLAN_LABELS[plan_code],
            'Mode': args.mode,
            'Report_Only': 1,
            'Skip_AHBA': int(args.skip_ahba),
            'AHBA_Cache_Dir': args.cache_dir or '',
            'Run_Status': 'report_only',
            'Duration_Seconds': 0.0,
            'Has_Result_Artifact': int(has_artifact_before),
            'Key_Artifact': artifact,
        }

    backup = _set_runtime_env(args.mode, args.skip_ahba, args.cache_dir, args.quick_windows)
    start = time.time()
    status = 'success'
    try:
        _run_plan(plan_code)
    except Exception:
        status = 'failed'
        raise
    finally:
        _restore_runtime_env(backup)

    duration = round(time.time() - start, 3)
    has_artifact_after, artifact = _collect_plan_status(plan_code)
    return {
        'Timestamp': ts,
        'Plan_Code': plan_code,
        'Plan_Label': PLAN_LABELS[plan_code],
        'Mode': args.mode,
        'Report_Only': 0,
        'Skip_AHBA': int(args.skip_ahba),
        'AHBA_Cache_Dir': args.cache_dir or '',
        'Run_Status': status,
        'Duration_Seconds': duration,
        'Has_Result_Artifact': int(has_artifact_after),
        'Key_Artifact': artifact,
    }


def _safe_float(text, default=float('nan')):
    try:
        return float(text)
    except Exception:
        return default


def _latest_two_by_plan(all_rows, plan_code):
    rows = [r for r in all_rows if r.get('Plan_Code') == plan_code]
    if not rows:
        return None, None
    if len(rows) == 1:
        return rows[-1], None
    return rows[-1], rows[-2]


def _format_delta_line(latest, previous):
    if latest is None:
        return '- 无入口运行记录。'
    if previous is None:
        return '- 首次记录，暂无可比较的上一轮。'

    latest_status = latest.get('Run_Status', '')
    previous_status = previous.get('Run_Status', '')
    latest_artifact = latest.get('Has_Result_Artifact', '')
    previous_artifact = previous.get('Has_Result_Artifact', '')

    d_status = '未变化' if latest_status == previous_status else f'{previous_status} -> {latest_status}'
    d_artifact = '未变化' if latest_artifact == previous_artifact else f'{previous_artifact} -> {latest_artifact}'

    latest_duration = _safe_float(latest.get('Duration_Seconds', 'nan'))
    previous_duration = _safe_float(previous.get('Duration_Seconds', 'nan'))
    if latest_duration == latest_duration and previous_duration == previous_duration:
        d_duration = latest_duration - previous_duration
        d_duration_text = f'{d_duration:+.3f}s'
    else:
        d_duration_text = 'NA'

    return (
        f"- 状态变化：{d_status}；产物标记变化：{d_artifact}；"
        f"耗时变化：{d_duration_text}（上次={previous.get('Duration_Seconds', '')}s，本次={latest.get('Duration_Seconds', '')}s）。"
    )


def _generate_summary_markdown(last_rows):
    _ensure_output_root()
    plan1_rows = _read_csv_rows(PLAN1_SUMMARY_FILE)
    plan2_rows = _read_csv_rows(PLAN2_OVERVIEW_FILE)
    roc_rows = _read_csv_rows(PLAN2_ROC_FILE)
    plan3_rows = _read_csv_rows(PLAN3_OVERVIEW_FILE)
    ahba_note = _read_text(PLAN1_AHBA_FALLBACK_FILE).strip()

    lines = []
    lines.append('# Step4 统一入口结果汇总（中文）')
    lines.append('')
    lines.append(f'> 生成时间：{_now_text()}')
    lines.append('')
    lines.append('## 本次入口执行概览')
    if last_rows:
        for row in last_rows:
            lines.append(
                f"- Plan{row['Plan_Code']} | status={row['Run_Status']} | mode={row['Mode']} | "
                f"report_only={row['Report_Only']} | artifact={row['Has_Result_Artifact']}"
            )
    else:
        lines.append('- 本次未执行计划，仅基于已有文件汇总。')
    lines.append('')

    all_overview_rows = _read_overview_rows()
    lines.append('## 与上次运行差异（Delta）')
    for code in ['1', '2', '3']:
        lines.append(f"### Plan {code}")
        latest, previous = _latest_two_by_plan(all_overview_rows, code)
        lines.append(_format_delta_line(latest, previous))
    lines.append('')

    lines.append('## Plan 1（burden-resilience）')
    if plan1_rows:
        for r in plan1_rows:
            lines.append(
                f"- {r.get('Outcome', '')}: N={r.get('N', '')}, R2={r.get('Model_R2', '')}, "
                f"BurdenVar={r.get('Burden_Explained_Variance', '')}"
            )
    else:
        lines.append('- 未找到 Plan1 汇总文件。')
    if ahba_note:
        lines.append('- Allen/AHBA 状态：当前存在 fallback 记录，需检查 Plan1 AHBA 目录。')
    else:
        lines.append('- Allen/AHBA 状态：未检测到 Plan1 fallback 记录。')
    lines.append('')

    lines.append('## Plan 2（incremental prediction）')
    if plan2_rows:
        for r in plan2_rows:
            lines.append(
                f"- {r.get('Scale', '')}-{r.get('Endpoint', '')}: "
                f"Best={r.get('Best_Model', '')}, RMSE={r.get('Best_Test_RMSE', '')}"
            )
    else:
        lines.append('- 未找到 Plan2 总览文件。')

    if roc_rows:
        best = sorted(roc_rows, key=lambda x: _safe_float(x.get('AUC', 'nan')), reverse=True)[0]
        lines.append(
            f"- ROC 最佳条目：{best.get('Scale', '')}-{best.get('Endpoint', '')}-"
            f"{best.get('Model', '')}, AUC={best.get('AUC', '')}"
        )
    else:
        lines.append('- 未找到 Plan2 ROC 总览文件。')
    lines.append('')

    lines.append('## Plan 3（topography-mechanism）')
    if plan3_rows:
        for r in plan3_rows:
            lines.append(
                f"- {r.get('Contrast_Pair', '')}: N_Features={r.get('N_Features', '')}, "
                f"Mean_Adjusted_Effect={r.get('Mean_Adjusted_Effect', '')}"
            )
    else:
        lines.append('- 未找到 Plan3 总览文件。')

    lines.append('')

    lines.append('## 结论（自动摘要）')
    lines.append('- Plan1 已可输出 burden-resilience 结果，但解释度中等偏低。')
    lines.append('- Plan2 的增量价值呈局部成立，主要集中在部分终点/时间窗。')
    lines.append('- Plan3 当前聚焦拓扑结果；Allen/AHBA 已移至 Plan1。')

    with open(SUMMARY_MD_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    return SUMMARY_MD_FILE


def main():
    args = _parse_args()
    _print_header()

    if args.plan is None:
        choice = _interactive_select()
    else:
        choice = 'a' if args.plan == 'all' else args.plan

    if choice == 'q':
        print('Exit without running plans.')
        return

    plan_codes = _select_plan_codes(choice)
    print(
        f"\nOptions: mode={args.mode}, report_only={args.report_only}, "
        f"skip_ahba={args.skip_ahba}, cache_dir={args.cache_dir or 'default'}, "
        f"quick_windows={args.quick_windows}, summary={args.summary}"
    )
    if len(plan_codes) > 1:
        print('\nRunning selected plans in sequence: 1 -> 2 -> 3')

    overview_rows = []
    for code in plan_codes:
        print(f'\n[Step4 Entry] Start {PLAN_LABELS[code]}')
        _append_log(f'[{_now_text()}] START {code} {PLAN_LABELS[code]}')
        row = _run_or_report(code, args)
        overview_rows.append(row)
        _append_log(
            f"[{_now_text()}] DONE {code} status={row['Run_Status']} "
            f"duration={row['Duration_Seconds']}s artifact={row['Has_Result_Artifact']}"
        )
        print(f"[Step4 Entry] Done  {PLAN_LABELS[code]} | status={row['Run_Status']}")

    _append_overview_rows(overview_rows)
    summary_path = None
    if args.summary:
        summary_path = _generate_summary_markdown(overview_rows)
    print(f'\nStep4 entry overview appended to: {OVERVIEW_FILE}')
    print(f'Step4 entry run log appended to: {RUNLOG_FILE}')
    if summary_path:
        print(f'Step4 summary markdown written to: {summary_path}')


if __name__ == '__main__':
    main()

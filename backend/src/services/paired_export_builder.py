"""配对复验获批导出的纯函数构建（仅标准库），便于脱离数据库独立核对。"""
import csv
import io


def build_paired_export_csv(note, result):
    """给定说明字段与冻结结果，生成含尾部/总组合数与逐片冻结明细的可核对 CSV。"""
    ex = result['paired_exact']
    snap = result['input_snapshot']
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['note', 'method', 'fingerprint', 'alpha', 'tail_rule', 'tie_handling',
                'association', 'numeric', 'interpretation', 'action', 'boundary'])
    w.writerow([note['title'], result['method_version'], result['fingerprint'], result['alpha'],
                ex['tail_rule'], ex['tie_handling'], ex['association'], ex['numeric'],
                note['interpretation'], note['action'], result['interpretation']])
    w.writerow(['piece_count', 'layer_count', 'total_combinations', 'total_combinations_bits',
                'tail_combinations', 'interior_combinations', 'tail_plus_interior_equals_total',
                'exact_p', 'exact_p_display', 'p_log', 'max_abs_layer', 'memo_states_used', 'memo_state_cap'])
    w.writerow([ex['piece_count'], ex['layer_count'], ex['total_combinations'],
                ex['total_combinations_bits'], ex['tail_combinations'], ex['interior_combinations'],
                int(ex['tail_combinations']) + int(ex['interior_combinations']) == int(ex['total_combinations']),
                ex['p_value'], ex['p_display'], ex['p_log'], ex['max_abs_layer'],
                ex['memo_states_used'], ex['memo_state_cap']])
    w.writerow(['layer', 'a_success_total', 'b_success_total', 'rate_a_num', 'rate_a_den',
                'rate_b_num', 'rate_b_den', 'difference_num', 'difference_den',
                'observed_s', 'interior_lower_exclusive', 'interior_upper_exclusive'])
    thresholds = {t['code']: t for t in ex['integer_thresholds']}
    for o in ex['observed_layer_statistics']:
        t = thresholds[o['code']]
        w.writerow([o['code'], o['a_success'], o['b_success'], o['rate_a_numerator'],
                    o['rate_a_denominator'], o['rate_b_numerator'], o['rate_b_denominator'],
                    o['difference_numerator'], o['difference_denominator'], t['observed_s'],
                    t['interior_lower_exclusive'], t['interior_upper_exclusive']])
    # 逐片冻结明细：每片每层两种封装成败，可与库内明细逐格核对。
    w.writerow(['frozen_piece_detail', 'layer', 'a_success', 'a_failure',
                'b_success', 'b_failure', 'source'])
    layer_codes = [l['code'] for l in sorted(snap['layers'], key=lambda x: (x['sequence'], x['code']))]
    for p in snap['pieces']:
        by = {c['layer_code']: c for c in p['cells']}
        for code in layer_codes:
            c = by[code]
            w.writerow([p['code'], code, c['a_success'], c['a_failure'],
                        c['b_success'], c['b_failure'], p.get('source', '')])
    return out.getvalue()

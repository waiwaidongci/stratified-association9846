"""配对复测整片交换标签的精确双侧证据（保留跨层关联，含并列，不模拟）。

设计：每片在全部湿度层同时交换两种封装标签（共同交换），故零假设下共 2^N 个等可能
配置。统计量为各层配对率差 D_j，双侧尾为至少一层 |D_j| 达到或超过该层观察值的全部
配置（等价于 max_j |D_j| 达到观察的最大绝对率差，并列以逐层阈值精确判定），等距并列
一律入尾。尾内组合数 = 总组合数 − 严格内部组合数；严格内部要求每个坐标同时落在
(-t_j, t_j) 逐层整数盒内，盒约束天然保留片内跨层关联。

只使用 Python 整数精确计数；DFS 分支定界 + 记忆化，并对记忆化状态数设硬上限，
预估或实际超过约 1 GiB 预算时明确拒绝（不回退到模拟或逐层独立近似）。
"""
from fractions import Fraction
from math import gcd
import math
import resource

# 实测（60片×8层、4个独立维度的近满负载）每条记忆状态边际占用约 280–300 字节：
# tuple 键含多个大整数对象 + dict 槽位 + 计数值。280 万状态约 795 MiB，
# 连同解释器基线、rem_abs 表与结果结构仍稳在 1 GiB 内；超出即拒绝。
STATE_MEMO_CAP = 2_800_000
# 真实常驻内存硬后备：每插入若干状态采样一次 ru_maxrss，越过 900 MiB 立即拒绝，
# 与状态数上限互为冗余，保证任何数据形态下都不冲破约 1 GiB 预算。
RSS_LIMIT_BYTES = 900 * 1024 * 1024
RSS_CHECK_EVERY = 65_536
# 逐片向量取 x_ij=a_success-b_success；真实率差 D_j=2*S_j/N，比例常数 2/N 对所有
# 片、所有配置相同，绝对值比较时可约去，直接以整数向量 S 计数。


class ResourceLimitError(RuntimeError):
    """枚举状态数超过约 1 GiB 内存预算，按需求拒绝，不以模拟或独立近似替代。"""


def _validate(pieces, layers):
    if not isinstance(layers, list) or not 2 <= len(layers) <= 8:
        raise ValueError('需要2..8个湿度层')
    if len({c for c, _ in layers}) != len(layers):
        raise ValueError('湿度层编号重复')
    if not isinstance(pieces, list) or not 1 <= len(pieces) <= 60:
        raise ValueError('试片数须在1..60之间')
    seen = set()
    matrix = []
    for p in pieces:
        code = p.get('code')
        if not code or code in seen:
            raise ValueError('试片编号缺失或重复')
        seen.add(code)
        cells = p.get('cells')
        if not isinstance(cells, list) or len(cells) != len(layers):
            raise ValueError('每片必须为每个湿度层提供完整封装成败记录')
        vec = []
        for cell in cells:
            vals = [cell.get('a_success'), cell.get('a_failure'),
                    cell.get('b_success'), cell.get('b_failure')]
            if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
                raise ValueError('成败标记须为0/1整数，布尔不算计数')
            a_s, a_f, b_s, b_f = vals
            if not (a_s in (0, 1) and a_f in (0, 1) and b_s in (0, 1) and b_f in (0, 1)):
                raise ValueError('每种封装在每层恰有一次成败（0/1）记录')
            if a_s + a_f != 1 or b_s + b_f != 1:
                raise ValueError('每种封装在每层恰有一次成功且一次失败记录')
            vec.append(a_s - b_s)
        matrix.append(vec)
    return len(pieces), matrix


def _reduce_columns(active, k):
    """合并逐片向量成固定整数比的湿度层（同向重复层），返回降维后的逐片向量。

    返回 (reduced_vectors, dim_layers, dim_scale)：
    dim_layers[d] 为该代表维度对应的原层下标；dim_scale[d] 为正整数缩放 q，
    使原层部分和 S_j = q * S'_d；合并只去掉恒等约束，不改变盒内计数。
    """
    if not active:
        return [], list(range(k)), [1] * k
    groups = []  # (代表层, 缩放q, 关键归一化向量)
    dim_layers = []
    dim_scale = []
    for j in range(k):
        col = [row[j] for row in active]
        if all(v == 0 for v in col):
            # 全零列在活跃片上无区分度，单独保留（其阈值盒 [-t,t]，t 来自全片观察）。
            groups.append((j, 1, tuple(col)))
            dim_layers.append(j)
            dim_scale.append(1)
            continue
        matched = None
        for rep, q, key in groups:
            rep_col = [row[rep] for row in active]
            if all(col[i] * q == rep_col[i] for i in range(len(active))):
                matched = (rep, q, key)
                break
        if matched is None:
            # 以本列 gcd 归一化，得到整数本原方向作为比例匹配键。
            g = 0
            for v in col:
                g = gcd(g, abs(v))
            g = g or 1
            key = tuple(v // g for v in col)
            groups.append((j, g, key))
            dim_layers.append(j)
            dim_scale.append(g)
    reduced = [[row[rep] // q for (rep, q, _) in groups] for row in active]
    return reduced, dim_layers, dim_scale


def _interior_count(vectors, lows, highs):
    """计数所有符号配置使各坐标严格满足 low_d < sum < high_d（整数严格内部盒）。"""
    m = len(vectors)
    d = len(lows)
    rem_abs = [[0] * d for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(d):
            rem_abs[i][j] = rem_abs[i + 1][j] + abs(vectors[i][j])
    memo = {}
    cap_hit = False
    inserts = 0

    def dfs(i, cur):
        # 剩余偏移剪枝：即使后续全部同向也无法进入盒，则该分支恒为 0。
        for j, s in enumerate(cur):
            if s + rem_abs[i][j] <= lows[j] or s - rem_abs[i][j] >= highs[j]:
                return 0
        if i == m:
            return 1
        key = (i, cur)
        cached = memo.get(key)
        if cached is not None:
            return cached
        nonlocal cap_hit, inserts
        if len(memo) >= STATE_MEMO_CAP:
            cap_hit = True
            return 0
        inserts += 1
        if inserts % RSS_CHECK_EVERY == 0:
            # Linux ru_maxrss 单位为 KiB；按进程真实峰值常驻内存作硬后备。
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 >= RSS_LIMIT_BYTES:
                cap_hit = True
                return 0
        v = vectors[i]
        plus = dfs(i + 1, tuple(s + z for s, z in zip(cur, v)))
        if cap_hit:
            return 0
        minus = dfs(i + 1, tuple(s - z for s, z in zip(cur, v)))
        if cap_hit:
            return 0
        total = plus + minus
        memo[key] = total
        return total

    interior = dfs(0, tuple(0 for _ in lows))
    if cap_hit:
        raise ResourceLimitError('配对交换枚举状态数超过约1GiB内存预算，已拒绝；不使用模拟或逐层独立计算替代')
    return interior, len(memo)


def paired_exact_test(pieces, layers, alpha):
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or not math.isfinite(alpha) \
            or not .001 <= alpha <= .1:
        raise ValueError('alpha须在.001..0.1之间')
    n, matrix = _validate(pieces, layers)
    k = len(layers)

    # 观察到的各层成功率与率差（Fraction 精确有理数）。
    observed = []
    for j, (code, name) in enumerate(layers):
        a_total = sum(p['cells'][j]['a_success'] for p in pieces)
        b_total = sum(p['cells'][j]['b_success'] for p in pieces)
        rate_a = Fraction(a_total, n)
        rate_b = Fraction(b_total, n)
        d = rate_a - rate_b
        observed.append({
            'code': code, 'name': name,
            'a_success': a_total, 'b_success': b_total,
            'rate_a_numerator': rate_a.numerator, 'rate_a_denominator': rate_a.denominator,
            'rate_b_numerator': rate_b.numerator, 'rate_b_denominator': rate_b.denominator,
            'rate_a': float(rate_a), 'rate_b': float(rate_b),
            'difference_numerator': d.numerator, 'difference_denominator': d.denominator,
            'difference': float(d), 'abs_difference': float(abs(d)),
        })

    # 全零向量片（每层两种封装结果都相同）对所有配置贡献因子 2，先剥离。
    zero_pieces = [i for i, vec in enumerate(matrix) if all(x == 0 for x in vec)]
    active = [vec for vec in matrix if any(x != 0 for x in vec)]
    zero_count = len(zero_pieces)
    m = len(active)

    total = 1 << n
    # 整数统计：D_j = 2*S_j/N，观察 S_j=Σx_ij；尾判定按各层自己的观察距离 t_j=|S_j|，
    # 配置入尾当且仅当存在层 j 使 |S_j| >= t_j；严格内部盒逐层为 (-t_j, t_j)。
    obs_s = [sum(vec[j] for vec in matrix) for j in range(k)]
    t = [abs(s) for s in obs_s]

    # 比例列合并（同向共线层），仅压缩状态空间，不改变计数。
    reduced, dim_layers, dim_scale = _reduce_columns(active, k)
    # 缩放后严格内部盒仍为整数严格不等式：-t_j/q < S' < t_j/q。
    lows = [-(t[j] // dim_scale[d]) for d, j in enumerate(dim_layers)]
    highs = [t[j] // dim_scale[d] for d, j in enumerate(dim_layers)]
    reduced_sorted = sorted(reduced, key=lambda v: sum(abs(z) for z in v), reverse=True)

    # 预检：降维后盒内每坐标整数域宽 (2*floor(t/q)-1)，与 2^m 取小作为状态上界。
    domain_product = 1
    for d, j in enumerate(dim_layers):
        width = 2 * (t[j] // dim_scale[d]) - 1
        if width <= 0:
            domain_product = 0
            break
        domain_product *= width
    preflight = min(1 << m, domain_product)
    if preflight > STATE_MEMO_CAP:
        raise ResourceLimitError(
            '配对交换精确枚举预估状态数 %d 超过约1GiB预算，已拒绝；不使用模拟或逐层独立计算替代' % preflight)

    if m == 0 or any(x == 0 for x in t):
        # 存在观察距离为 0 的层：任何配置在该层都满足 |D|>=0，全部入尾。
        interior_active, states = 0, 0
    else:
        interior_active, states = _interior_count(reduced_sorted, lows, highs)
    interior = interior_active * (1 << zero_count)
    tail = total - interior
    if not 0 <= tail <= total:
        raise AssertionError('尾内组合数超出总组合数')

    p = Fraction(tail, total)
    p_numeric = float(p)
    log_p = float(math.log(p)) if p > 0 else None
    max_abs = max(Fraction(o['difference_numerator'], o['difference_denominator']) for o in observed)
    max_layer = max(
        observed,
        key=lambda o: abs(o['difference_numerator']) / o['difference_denominator'])['code']

    integer_thresholds = [{
        'code': layers[j][0],
        'observed_s': obs_s[j],
        'interior_lower_exclusive': -t[j],
        'interior_upper_exclusive': t[j],
    } for j in range(k)]

    return {
        'piece_count': n,
        'layer_count': k,
        'active_piece_count': m,
        'zero_vector_piece_count': zero_count,
        'zero_vector_piece_codes': [pieces[i]['code'] for i in zero_pieces],
        'total_combinations': str(total),
        'total_combinations_bits': n,
        'tail_combinations': str(tail),
        'interior_combinations': str(interior),
        'tail_rule': '整片在全部湿度层共同交换封装标签；统计量为各层配对率差绝对值的最大值 T=max_j |D_j|，'
                     '所有 T ≥ 观察 T 的等可能配置入双侧尾（逐层以 |D_j|≥观察|D_j| 判定，等距并列同样入尾）。',
        'tie_handling': '严格内部盒要求每层同时严格满足 |D_j| < 该层观察 |D_j|；任一层等距即不入内部，并列概率完整保留。',
        'association': '符号配置按整片施加，片内各层向量一起变号，跨层关联被完整保留，非逐层独立乘积。',
        'p_value': p_numeric if p_numeric > 0 else None,
        'p_log': log_p,
        'p_underflow': bool(p > 0 and p_numeric == 0),
        'p_display': _format_fraction_scientific(p),
        # 分子分母可达 2^60，超过 JS 安全整数范围，统一以十进制字符串保存，前端不丢精度。
        'p_numerator': str(tail),
        'p_denominator': str(total),
        'below_alpha': bool(p <= alpha),
        'alpha': alpha,
        'max_abs_layer': max_layer,
        'max_abs_difference': float(max_abs),
        'observed_layer_statistics': observed,
        'integer_thresholds': integer_thresholds,
        'reduced_dimensions': [{
            'representative_layer': layers[j][0],
            'scale': dim_scale[d],
            'interior_lower_exclusive': lows[d],
            'interior_upper_exclusive': highs[d],
        } for d, j in enumerate(dim_layers)],
        'memo_states_used': states,
        'memo_state_cap': STATE_MEMO_CAP,
        'preflight_state_bound': preflight,
        'numeric': '纯 Python 整数精确枚举与 Fraction 有理数比较；无模拟、无逐层独立近似；组合数以十进制字符串保存。',
    }


def _format_fraction_scientific(p: Fraction) -> str:
    value = float(p)
    if value > 0:
        return f'{value:.8e}'
    log10 = math.log10(p)
    return f'10^({log10:.8f})'

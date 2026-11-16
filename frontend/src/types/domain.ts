export interface User{id:number;email:string;name:string;role:'admin'|'analyst'|'viewer'}
export interface Study{id:number;code:string;name:string;period:string;description:string}
export interface Stratum{id:number;study_id:number;code:string;name:string;description:string}
export interface Count{id:number;stratum_id:number;a:number;b:number;c:number;d:number;source:string}
export interface Ratio{value:number|null;status:'finite'|'unbounded'|'undefined'}
export interface TableRow extends Count{code:string;name:string;description:string;n:number;row_a:number;row_b:number;success_total:number;failure_total:number;expected_a:number;variance_a:number;informative:boolean;odds_ratio:Ratio;rate_a:number|null;rate_b:number|null}
export interface Mass{s:number;probability:number;log_probability:number|null;in_tail:boolean}
export interface Exact{p_value:number|null;p_log:number|null;p_underflow:boolean;p_display:string;below_alpha:boolean;alpha:number;mean_numerator:number;mean_denominator:number;observed_sum:number;support_lower:number;support_upper:number;support_size:number;probability_sum:number;distribution_mean:number;distribution_variance:number;layers:{code:string;lower:number;upper:number;support_count:number}[];distribution:Mass[];tail_rule:string;numeric:string}
export interface Result{strata:TableRow[];observed_sum_a:number;expected_sum_a:number;variance_sum_a:number;cmh:number;asymptotic_p:number|null;asymptotic_p_log:number;asymptotic_p_display:string;asymptotic_p_underflow:boolean;adjusted_or:Ratio;mh_numerator:number;mh_denominator:number;pooled:{a:number;b:number;c:number;d:number;odds_ratio:Ratio;rate_a:number|null;rate_b:number|null};uninformative_codes:string[];correction:boolean;zero_shift:boolean;exact:Exact;alpha:number;input_snapshot:{study:Study;tables:TableRow[]};fingerprint:string;method_version:string;interpretation:string}
export interface Run{id:number;name:string;study_id:number;alpha:number;status:string;input_snapshot?:{study:Study;tables:TableRow[]};result?:Result;error:string;created_at:string}
export interface Note{id:number;title:string;run_id:number;interpretation:string;action:string;status:string;approved_by:string;review_comment:string}
export interface Audit{id:number;actor:string;action:string;target:string;created_at:string}

// 配对复测研究：同一试片多湿度层复测，逐片冻结两种封装成败。
export interface PairedLayer{code:string;name:string;sequence:number;description:string}
export interface PairedCell{layer_code:string;a_success:number;a_failure:number;b_success:number;b_failure:number}
export interface PairedPiece{code:string;source:string;cells:PairedCell[]}
export interface PairedStudy{id:number;code:string;name:string;period:string;description:string}
export interface PairedSnapshot{study:PairedStudy;layers:PairedLayer[];pieces:PairedPiece[]}
export interface PairedLayerStat{code:string;name:string;a_success:number;b_success:number;rate_a_numerator:number;rate_a_denominator:number;rate_b_numerator:number;rate_b_denominator:number;rate_a:number;rate_b:number;difference_numerator:number;difference_denominator:number;difference:number;abs_difference:number}
export interface PairedThreshold{code:string;observed_s:number;interior_lower_exclusive:number;interior_upper_exclusive:number}
export interface PairedExact{piece_count:number;layer_count:number;active_piece_count:number;zero_vector_piece_count:number;zero_vector_piece_codes:string[];total_combinations:string;total_combinations_bits:number;tail_combinations:string;interior_combinations:string;tail_rule:string;tie_handling:string;association:string;p_value:number|null;p_log:number|null;p_underflow:boolean;p_display:string;p_numerator:string;p_denominator:string;below_alpha:boolean;alpha:number;max_abs_layer:string;max_abs_difference:number;observed_layer_statistics:PairedLayerStat[];integer_thresholds:PairedThreshold[];reduced_dimensions:{representative_layer:string;scale:number;interior_lower_exclusive:number;interior_upper_exclusive:number}[];memo_states_used:number;memo_state_cap:number;preflight_state_bound:number;numeric:string}
export interface PairedResult{paired_exact:PairedExact;alpha:number;input_snapshot:PairedSnapshot;fingerprint:string;method_version:string;interpretation:string}
export interface PairedRun{id:number;name:string;study_id:number;alpha:number;status:string;input_snapshot?:PairedSnapshot;result?:PairedResult;error:string;created_at:string}
export interface PairedNote{id:number;title:string;run_id:number;interpretation:string;action:string;status:string;approved_by:string;review_comment:string}

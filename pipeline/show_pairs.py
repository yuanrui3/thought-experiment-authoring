"""Print pairs compactly: version A in full, then only what changes in B."""
import json, sys, difflib
def show(p, pid=''):
    a, b = p['version_a'].split(), p['version_b'].split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    segs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != 'equal':
            segs.append('  A: «%s»\n  B: «%s»' % (' '.join(a[i1:i2]), ' '.join(b[j1:j2])))
    print('=' * 100)
    print('%s | %s | %s | predicts %s / %s | words A=%d B=%d' % (pid, p['factor_id'], p['title'], p['predicted_direction'], p['predicted_size'], len(a), len(b)))
    print('A: ' + p['version_a'])
    print('DIFF:\n' + '\n'.join(segs))
    print('Q: %s  [1=%s | 7=%s]' % (p['judgment_question'], p['scale_label_1'], p['scale_label_7']))
    print('CHECK: %s  a) %s  b) %s  c) %s  key A=%s B=%s' % (p['comprehension_question'], p['option_a'], p['option_b'], p['option_c'], p['correct_option_version_a'], p['correct_option_version_b']))
    print('INTENDED: ' + p['intended_difference'])
    print('WHY: ' + p['prediction_rationale'])
if __name__ == '__main__':
    d = json.load(open(sys.argv[1]))
    want = sys.argv[2:] 
    for label, res in d['authors'].items():
        tier = label.split(':')[1]
        if want and tier not in want: continue
        for p in res['pairs']:
            show(p, 'au_%s' % tier)

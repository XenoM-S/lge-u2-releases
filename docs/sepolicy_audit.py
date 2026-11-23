#!/usr/bin/env python3
"""
sepolicy_audit.py - find types/attributes referenced by device sepolicy files
that are never declared in external/sepolicy or the device dirs themselves.

Catches every 'unknown type X' checkpolicy error in ONE pass instead of one
build attempt per error.

Usage:
    python3 sepolicy_audit.py EXTERNAL_DIR DEVICE_DIR [DEVICE_DIR ...]

Example (run from the top of the Android tree):
    python3 sepolicy_audit.py external/sepolicy device/lge/u2-common/selinux

Background (cm-12.1 external/sepolicy/Android.mk):
  * policy.conf order: security_classes, initial_sids, access_vectors,
    global_macros, mls_macros, mls, policy_capabilities, te_macros,
    attributes, *.te, roles, users, initial_sid_contexts, fs_use,
    genfs_contexts, port_contexts.
  * 'attributes' (declares attribute dev_type; fs_type; ... ) comes before
    all *.te files.
  * BOARD_SEPOLICY_UNION is a WHITELIST of file names, NOT an ordering.
    In the '*.te' group, ALL external .te files are concatenated first
    (alphabetical - $(wildcard) sorts), then ALL device .te files whose
    name appears in BOARD_SEPOLICY_UNION, alphabetical, in the order the
    dirs appear in BOARD_SEPOLICY_DIRS. Device glue order is e.g.:
        device.te -> domain.te -> powervr_device.te -> pvrsrvinit.te
  * Declarations must appear EXACTLY ONCE in the glued policy.conf and
    before the first rule that uses them. Duplicate 'type X ...;' lines
    across files are fatal: checkpolicy 'duplicate declaration of
    type/attribute'. Rules (allow/neverallow/...) may repeat freely.
"""

import os
import re
import sys

RULE_KW = ('allow', 'neverallow', 'auditallow', 'dontaudit',
           'type_transition', 'type_change', 'type_member')
SKIP_IDS = {'self', '*'}
CTX_FILES = ('file_contexts', 'property_contexts', 'service_contexts',
             'genfs_contexts', 'ueventd_contexts')

TOKEN = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
DECL_TYPE = re.compile(r'^\s*type\s+([A-Za-z0-9_]+)\s*(,|$)')
DECL_ATTR = re.compile(r'^\s*attribute\s+([A-Za-z0-9_]+)\s*$')
DECL_ALIAS = re.compile(r'^\s*typealias\s+([A-Za-z0-9_]+)\s+alias\s+([A-Za-z0-9_]+)\s*$')
DECL_TYPEATTR = re.compile(r'^\s*typeattribute\s+([A-Za-z0-9_]+)\s+(.+)$')
DECL_PERMISSIVE = re.compile(r'^\s*permissive\s+([A-Za-z0-9_]+)\s*$')
DEFINE_NAME = re.compile(r'define\(`([A-Za-z0-9_]+)')
OBJ_R = re.compile(r'object_r:([A-Za-z0-9_]+):')
SEAPP_DOM = re.compile(r'\bdomain=([A-Za-z0-9_]+)')
# m4 macro invocations, e.g. init_daemon_domain(pvrsrvinit). They carry no
# terminating ';' so they would otherwise be glued to the next rule.
MACRO_CALL = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*\(([^()]*)\)')

# identifiers that must NOT be declared, with the real cm-12.1 fix instead
HINTS = {
    'system': 'KK "system" domain does not exist in cm-12.1: use '
              'unconfineddomain (catch-all) or system_app (uid=system apps) '
              'instead - do NOT declare type system;',
}


def clean_line(line):
    line = re.sub(r'#[^\n]*', '', line)          # shell-style comments
    line = re.sub(r'\bdnl\b[^\n]*', '', line)    # m4 comments
    return line


def statements(path):
    """Yield (start_line, stmt) for each ';'-terminated statement.

    define(`...', `...') macro bodies are skipped line-wise so their rule
    templates do not produce false hits.
    """
    out = []
    buf, start, in_define = '', None, False
    with open(path, 'r', errors='replace') as fh:
        for lineno, raw in enumerate(fh, 1):
            line = clean_line(raw)
            if in_define:
                if line.rstrip().endswith("')") or line.rstrip().endswith("')dnl"):
                    in_define = False
                continue
            if re.match(r'\s*define\(', line):
                in_define = True
                continue
            if not buf.strip():
                start = lineno
            buf += line + '\n'
            while ';' in buf:
                stmt, buf = buf.split(';', 1)
                if stmt.strip():
                    out.append((start, stmt))
                if buf.strip():
                    pass
                start = lineno
    if buf.strip():
        out.append((start, buf))
    return out


def ids(text):
    return [t for t in TOKEN.findall(text) if t not in SKIP_IDS]


def collect_decls(path, types, attrs, aliases, decl_map=None):
    """Parse type/attribute/alias declarations from one file.

    decl_map (optional) records every declaration as name -> [(path, line)]
    so the caller can detect duplicates across the whole glued set.
    """
    for line, stmt in statements(path):
        m = DECL_TYPE.match(stmt)
        if m:
            types.add(m.group(1))
            if decl_map is not None:
                decl_map.setdefault(m.group(1), []).append((path, line))
            continue
        m = DECL_ATTR.match(stmt)
        if m:
            attrs.add(m.group(1))
            if decl_map is not None:
                decl_map.setdefault(m.group(1), []).append((path, line))
            continue
        m = DECL_ALIAS.match(stmt)
        if m:
            aliases.add(m.group(1))
            aliases.add(m.group(2))
            if decl_map is not None:
                decl_map.setdefault(m.group(2), []).append((path, line))
            continue


def collect_defines(path, defines):
    try:
        with open(path, 'r', errors='replace') as fh:
            text = fh.read()
    except OSError:
        return
    for m in DEFINE_NAME.finditer(text):
        defines.add(m.group(1))


def audit_file(path, known, classes, defines, findings):
    """Findings: list of (line, identifier, kind)."""
    base = os.path.basename(path)
    for lineno, stmt in statements(path):
        # context files: object_r:TYPE: and seapp domain=
        if base in CTX_FILES or base == 'seapp_contexts':
            for m in OBJ_R.finditer(stmt):
                if m.group(1) not in known:
                    findings.append((lineno, m.group(1), 'context label'))
            for m in SEAPP_DOM.finditer(stmt):
                if m.group(1) not in known:
                    findings.append((lineno, m.group(1), 'seapp domain'))
            continue

        stmt_nq = re.sub(r'"[^"]*"', ' "" ', stmt)   # drop quoted strings

        # pull out m4 macro invocations (they have no ';' of their own and
        # would otherwise merge with the following rule statement)
        for m in MACRO_CALL.finditer(stmt_nq):
            name, args = m.group(1), m.group(2)
            if name in defines:
                for t in ids(args):
                    if t not in known:
                        findings.append((lineno, t, 'macro arg (' + name + ')'))
            else:
                findings.append((lineno, name, 'unknown macro/statement'))
        stmt_nq = MACRO_CALL.sub(' ', stmt_nq)

        toks = ids(stmt_nq)
        if not toks:
            continue
        kw = toks[0]

        if kw in RULE_KW:
            left, sep, right = stmt_nq.partition(':')
            if not sep:
                findings.append((lineno, '<no class>', 'malformed rule'))
                continue
            for t in ids(left)[1:]:                       # drop keyword
                if t not in known:
                    findings.append((lineno, t, kw + ' (subject/target)'))
            rcls = ids(right)
            if rcls and rcls[0] not in classes:
                findings.append((lineno, rcls[0], 'unknown class'))
            # type_transition default type sits right of the class
            if kw in ('type_transition', 'type_change', 'type_member'):
                for t in rcls[1:]:
                    if t not in known:
                        findings.append((lineno, t, kw + ' (target type)'))
            continue

        m = DECL_TYPEATTR.match(stmt_nq)
        if m:
            if m.group(1) not in known:
                findings.append((lineno, m.group(1), 'typeattribute (type)'))
            for t in ids(m.group(2)):
                if t not in known:
                    findings.append((lineno, t, 'typeattribute (attribute)'))
            continue

        m = DECL_PERMISSIVE.match(stmt_nq)
        if m:
            if m.group(1) not in known:
                findings.append((lineno, m.group(1), 'permissive'))
            continue

        if DECL_TYPE.match(stmt_nq) or DECL_ATTR.match(stmt_nq) \
                or DECL_ALIAS.match(stmt_nq):
            continue  # declarations were collected already

        # macro calls were extracted above; anything left whose first token
        # is neither a rule nor a declaration is bogus
        findings.append((lineno, kw, 'unknown macro/statement'))


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ext_dir, dev_dirs = sys.argv[1], sys.argv[2:]

    types, attrs, aliases, classes, defines = set(), set(), set(), set(), set()
    decl_map = {}   # name -> [(path, line), ...] every declaration seen
    seen = set()    # paths already scanned (a dir may be passed twice)

    sc = os.path.join(ext_dir, 'security_classes')
    if os.path.exists(sc):
        with open(sc, 'r', errors='replace') as fh:
            for line in fh:
                m = re.match(r'\s*class\s+([A-Za-z0-9_]+)', clean_line(line))
                if m:
                    classes.add(m.group(1))

    for path in [os.path.join(ext_dir, f) for f in sorted(os.listdir(ext_dir))]:
        if os.path.isfile(path) and path not in seen:
            seen.add(path)
            collect_decls(path, types, attrs, aliases, decl_map)
            collect_defines(path, defines)
    known = types | attrs | aliases

    dev_findings = {}
    for d in dev_dirs:
        for f in sorted(os.listdir(d)):
            path = os.path.join(d, f)
            if not os.path.isfile(path) or path in seen:
                continue
            seen.add(path)
            collect_decls(path, types, attrs, aliases, decl_map)
            collect_defines(path, defines)
    known = types | attrs | aliases  # refresh with device declarations

    duplicates = {name: locs for name, locs in decl_map.items()
                  if len(locs) > 1}
    dup_total = sum(len(locs) - 1 for locs in duplicates.values())

    for d in dev_dirs:
        for f in sorted(os.listdir(d)):
            path = os.path.join(d, f)
            if not os.path.isfile(path):
                continue
            findings = []
            audit_file(path, known, classes, defines, findings)
            if findings:
                dev_findings[path] = findings

    if duplicates:
        print('=== DUPLICATE declarations (fatal: checkpolicy says '
              '"duplicate declaration of type/attribute") ===')
        for name in sorted(duplicates):
            locs = duplicates[name]
            where = ', '.join('%s:%s' % (p, l) for p, l in locs)
            print('  %-22s %d x: %s' % (name + ':', len(locs), where))
        print('  Fix: keep exactly ONE declaration, in the device .te file '
              'that glues FIRST (alphabetical), delete the rest. Rules may '
              'repeat, declarations may not.')
        print()

    if not dev_findings:
        if dup_total:
            print('%d duplicate declaration(s) found.' % dup_total)
            return 1
        print('OK - no unknown types/attributes and no duplicate '
              'declarations in %d device dir(s).' % len(dev_dirs))
        return 0

    total = 0
    for path, findings in dev_findings.items():
        print('=== %s ===' % path)
        for lineno, ident, kind in findings:
            total += 1
            print('  line %-4s %-24s %s' % (lineno, ident, kind))
        print()

    # Suggest declarations. Use ", dev_type" for things that look like
    # device nodes (file_contexts under /dev/ or *_device naming).
    devish = set()
    for d in dev_dirs:
        fc = os.path.join(d, 'file_contexts')
        if os.path.exists(fc):
            with open(fc, 'r', errors='replace') as fh:
                for line in fh:
                    for m in OBJ_R.finditer(line):
                        if re.search(r'(/dev/|\bdevices?/)', line):
                            devish.add(m.group(1))
    for path, findings in dev_findings.items():
        for _l, ident, kind in findings:
            if kind == 'context label' or ident.endswith('_device'):
                devish.add(ident)

    missing = sorted({ident for fl in dev_findings.values()
                      for _l, ident, kind in fl
                      if kind not in ('unknown class', 'unknown macro/statement',
                                      'malformed rule')
                      and ident not in (classes | defines)
                      and ident != '<no class>'})
    if missing:
        print('=== Missing declarations (paste at the TOP of your device '
              'domain.te) ===')
        for ident in missing:
            users = ['%s:%s' % (os.path.basename(p), l)
                     for p, fl in dev_findings.items()
                     for l, i, k in fl if i == ident]
            if ident in HINTS:
                print('  %-38s # used at %s' % (ident + ':', HINTS[ident]))
                continue
            suffix = ', dev_type' if (ident in devish or
                                      ident.endswith('_device')) else ''
            print('  %-38s # used at %s'
                  % ('type %s%s;' % (ident, suffix), ', '.join(users[:4])))
        print()
    print('%d problem(s) found. Reminder: only files listed in '
          'BOARD_SEPOLICY_UNION are actually concatenated - check your '
          'BoardConfig.' % (total + dup_total))
    return 1


if __name__ == '__main__':
    sys.exit(main())
